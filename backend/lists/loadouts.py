from __future__ import annotations

from copy import copy
from dataclasses import dataclass
from typing import Any

from army_books.models import UnitUpgradeOption, UnitWeaponSlot, Weapon
from army_books.upgrade_matching import weapon_matches_upgrade_target
from army_books.upgrade_resolution import resolve_unit_upgrade_options
from lists.models import ListUnit


@dataclass(frozen=True)
class EffectiveLoadout:
    weapons: list[Weapon]
    upgrade_options: list[UnitUpgradeOption]
    extra_rules: dict[str, Any]
    aura_rules: dict[str, Any]

    @property
    def weapon_names(self) -> list[str]:
        return [weapon.name for weapon in self.weapons]

    @property
    def summary(self) -> str:
        if not self.weapons:
            return "No weapons"
        return " + ".join(_weapon_label(weapon) for weapon in self.weapons)

    @property
    def upgrade_cost(self) -> int:
        return sum(option.cost for option in self.upgrade_options)


@dataclass(frozen=True)
class SelectedUpgrade:
    option: UnitUpgradeOption
    quantity: int = 1


def selected_or_default_slot(entry: ListUnit) -> UnitWeaponSlot | None:
    if entry.selected_weapon_slot_id:
        return entry.selected_weapon_slot

    slots = list(entry.unit.weapon_slots.all())
    return next((slot for slot in slots if slot.is_default), None) or (slots[0] if slots else None)


def effective_loadout(entry: ListUnit) -> EffectiveLoadout:
    selected_upgrades = _resolved_selected_upgrades(entry)
    if not selected_upgrades:
        legacy_slot = selected_or_default_slot(entry)
        if legacy_slot and _is_legacy_selected_upgrade(legacy_slot):
            return EffectiveLoadout(
                weapons=[_slot_weapon(legacy_slot)],
                upgrade_options=[],
                extra_rules={},
                aura_rules={},
            )

    weapons = [_slot_weapon(slot) for slot in _default_slots(entry)]
    extra_rules: dict[str, Any] = {}
    aura_rules: dict[str, Any] = {}
    selected_options: list[UnitUpgradeOption] = []
    for selected in selected_upgrades:
        option = selected.option
        selected_options.append(option)
        section = option.section
        if section.variant.lower() == "replace":
            quantity = selected.quantity if _is_replace_any_section(section) else None
            weapons = _remove_target_weapons(weapons, section.targets, quantity=quantity)
        option_weapons = _option_weapons(option, selected.quantity)
        weapons = [*weapons, *option_weapons]
        gained_rules, gained_aura_rules = _rules_from_gains(option.gains)
        extra_rules = {**extra_rules, **gained_rules}
        aura_rules = {**aura_rules, **gained_aura_rules}
    return EffectiveLoadout(
        weapons=weapons,
        upgrade_options=selected_options,
        extra_rules=extra_rules,
        aura_rules=aura_rules,
    )


def selected_upgrade_cost(entry: ListUnit) -> int:
    selected_upgrades = _resolved_selected_upgrades(entry)
    if selected_upgrades:
        return sum(selected.option.cost * selected.quantity for selected in selected_upgrades)
    slot = selected_or_default_slot(entry)
    return slot.upgrade_cost if slot else 0


def _default_slots(entry: ListUnit) -> list[UnitWeaponSlot]:
    slots = [slot for slot in entry.unit.weapon_slots.all() if slot.is_default]
    if slots:
        return slots
    fallback = selected_or_default_slot(entry)
    return [fallback] if fallback else []


def _selected_upgrades(entry: ListUnit) -> list[SelectedUpgrade]:
    selections = getattr(entry, "selected_upgrades", None)
    if selections is None:
        return []
    return [
        SelectedUpgrade(selection.option, max(1, selection.quantity))
        for selection in selections.all()
        if selection.option.section.unit_id == entry.unit_id
    ]


def _resolved_selected_upgrades(entry: ListUnit) -> list[SelectedUpgrade]:
    selected_upgrades = _selected_upgrades(entry)
    selected_options = [selected.option for selected in selected_upgrades]
    if not selected_options:
        return []
    resolution = resolve_unit_upgrade_options(entry.unit, selected_options)
    if not resolution.is_valid:
        return selected_upgrades
    quantity_by_option = {selected.option.id: selected.quantity for selected in selected_upgrades}
    return [
        SelectedUpgrade(option, quantity_by_option.get(option.id, 1))
        for option in resolution.options
    ]


def _slot_weapon(slot: UnitWeaponSlot) -> Weapon:
    return weapon_with_count(slot.weapon, slot.count)


def _option_weapons(option: UnitUpgradeOption, quantity: int) -> list[Weapon]:
    links = list(option.option_weapons.select_related("weapon").all())
    if links:
        return [
            weapon_with_count(link.weapon, (link.count * quantity) if link.count else None)
            for link in links
        ]
    return [weapon_with_count(weapon, None) for weapon in option.weapons.all()]


def _remove_target_weapons(
    weapons: list[Weapon],
    targets: list[str],
    *,
    quantity: int | None,
) -> list[Weapon]:
    if quantity is None:
        return [
            weapon
            for weapon in weapons
            if not weapon_matches_upgrade_target(weapon.name, targets)
        ]
    remaining = quantity
    kept: list[Weapon] = []
    for weapon in weapons:
        if remaining <= 0 or not weapon_matches_upgrade_target(weapon.name, targets):
            kept.append(weapon)
            continue
        count = weapon_count(weapon)
        if count is None:
            remaining -= 1
            continue
        removed = min(count, remaining)
        remaining -= removed
        if count > removed:
            kept.append(weapon_with_count(weapon, count - removed))
    return kept


def _is_replace_any_section(section: Any) -> bool:
    affects = getattr(section, "affects", None) or {}
    return section.variant.lower() == "replace" and str(affects.get("type") or "").lower() == "any"


def weapon_with_count(weapon: Weapon, count: int | None) -> Weapon:
    weapon_copy = copy(weapon)
    if count is not None:
        setattr(weapon_copy, "_opr_count", max(1, int(count)))
    return weapon_copy


def weapon_count(weapon: Any) -> int | None:
    value = getattr(weapon, "_opr_count", None)
    return int(value) if value else None


def weapon_attack_count(weapon: Any, model_count: int) -> int:
    return weapon_count(weapon) or model_count


def _weapon_label(weapon: Any) -> str:
    count = weapon_count(weapon)
    if count is None or count <= 1:
        return weapon.name
    return f"{weapon.name} x{count}"


def _is_legacy_selected_upgrade(slot: UnitWeaponSlot) -> bool:
    return not slot.is_default or slot.upgrade_cost != 0 or bool(slot.option_id or slot.upgrade_id)


def split_aura_rules(rules: dict[str, Any] | None) -> tuple[dict[str, Any], dict[str, Any]]:
    normal_rules: dict[str, Any] = {}
    aura_rules: dict[str, Any] = {}
    for name, value in (rules or {}).items():
        if is_aura_rule_name(str(name)):
            aura_rules[aura_effect_rule_name(str(name))] = value
        else:
            normal_rules[str(name)] = value
    return normal_rules, aura_rules


def aura_rule_names_from_gains(gains: list[dict[str, Any]]) -> tuple[str, ...]:
    return tuple(
        name
        for name, _value in _iter_gain_rules(gains)
        if is_aura_rule_name(name)
    )


def is_aura_rule_name(name: str) -> bool:
    return name.strip().lower().endswith(" aura")


def aura_effect_rule_name(name: str) -> str:
    clean = name.strip()
    if not is_aura_rule_name(clean):
        return clean
    return clean[:-5].strip()


def _rules_from_gains(gains: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    rules: dict[str, Any] = {}
    aura_rules: dict[str, Any] = {}
    for name, value in _iter_gain_rules(gains):
        if is_aura_rule_name(name):
            aura_rules[aura_effect_rule_name(name)] = value
        else:
            rules[name] = value
    return rules, aura_rules


def _iter_gain_rules(gains: list[dict[str, Any]]):
    for gain in gains:
        if not isinstance(gain, dict):
            continue
        content = gain.get("content")
        if not isinstance(content, list):
            continue
        for rule in content:
            if not isinstance(rule, dict):
                continue
            name = rule.get("name")
            if name:
                yield str(name), rule.get("rating", True)
