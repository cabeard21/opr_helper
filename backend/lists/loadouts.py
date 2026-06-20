from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from army_books.models import UnitUpgradeOption, UnitWeaponSlot, Weapon
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
        return " + ".join(self.weapon_names) if self.weapons else "No weapons"

    @property
    def upgrade_cost(self) -> int:
        return sum(option.cost for option in self.upgrade_options)


def selected_or_default_slot(entry: ListUnit) -> UnitWeaponSlot | None:
    if entry.selected_weapon_slot_id:
        return entry.selected_weapon_slot

    slots = list(entry.unit.weapon_slots.all())
    return next((slot for slot in slots if slot.is_default), None) or (slots[0] if slots else None)


def effective_loadout(entry: ListUnit) -> EffectiveLoadout:
    selected_options = _selected_options(entry)
    if not selected_options:
        legacy_slot = selected_or_default_slot(entry)
        if legacy_slot and _is_legacy_selected_upgrade(legacy_slot):
            return EffectiveLoadout(
                weapons=[legacy_slot.weapon],
                upgrade_options=[],
                extra_rules={},
                aura_rules={},
            )

    weapons = [slot.weapon for slot in _default_slots(entry)]
    extra_rules: dict[str, Any] = {}
    aura_rules: dict[str, Any] = {}
    for option in selected_options:
        section = option.section
        option_weapons = list(option.weapons.all())
        if section.variant.lower() == "replace":
            targets = {str(target).lower() for target in section.targets}
            weapons = [weapon for weapon in weapons if weapon.name.lower() not in targets]
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
    selected_options = _selected_options(entry)
    if selected_options:
        return sum(option.cost for option in selected_options)
    slot = selected_or_default_slot(entry)
    return slot.upgrade_cost if slot else 0


def _default_slots(entry: ListUnit) -> list[UnitWeaponSlot]:
    slots = [slot for slot in entry.unit.weapon_slots.all() if slot.is_default]
    if slots:
        return slots
    fallback = selected_or_default_slot(entry)
    return [fallback] if fallback else []


def _selected_options(entry: ListUnit) -> list[UnitUpgradeOption]:
    selections = getattr(entry, "selected_upgrades", None)
    if selections is None:
        return []
    return [
        selection.option
        for selection in selections.all()
        if selection.option.section.unit_id == entry.unit_id
    ]


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
