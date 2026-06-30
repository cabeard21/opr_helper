from __future__ import annotations

from dataclasses import dataclass

from army_books.models import Unit, UnitUpgradeOption, Weapon
from army_books.upgrade_matching import weapon_matches_upgrade_target


@dataclass(frozen=True)
class UpgradeResolution:
    options: list[UnitUpgradeOption]
    warnings: list[str]
    errors: list[str]

    @property
    def option_ids(self) -> list[int]:
        return [option.id for option in self.options]

    @property
    def is_valid(self) -> bool:
        return not self.errors


def resolve_unit_upgrade_options(
    unit: Unit,
    selected_options: list[UnitUpgradeOption],
    *,
    warn_on_added_prerequisites: bool = False,
) -> UpgradeResolution:
    requested_options = _dedupe_options(selected_options)
    all_options = _upgrade_options(unit)
    selected_by_section: dict[int, UnitUpgradeOption] = {}
    resolved: list[UnitUpgradeOption] = []
    weapons = _default_weapons(unit)
    warnings: list[str] = []
    errors: list[str] = []

    for option in requested_options:
        if option.section.unit_id != unit.id:
            errors.append(f"{option.label} does not belong to {unit.name}.")
            continue
        if (
            option.section_id in selected_by_section
            and selected_by_section[option.section_id].id != option.id
            and not _is_replace_any_option(option)
        ):
            errors.append(f"Only one upgrade can be selected from {option.section.label}.")
            continue
        _ensure_option(
            unit=unit,
            option=option,
            all_options=all_options,
            selected_by_section=selected_by_section,
            resolved=resolved,
            weapons=weapons,
            warnings=warnings,
            errors=errors,
            stack=[],
            explicit=True,
            warn_on_added_prerequisites=warn_on_added_prerequisites,
        )

    if errors:
        return UpgradeResolution(options=[], warnings=warnings, errors=errors)
    return UpgradeResolution(options=resolved, warnings=warnings, errors=[])


def _ensure_option(
    *,
    unit: Unit,
    option: UnitUpgradeOption,
    all_options: list[UnitUpgradeOption],
    selected_by_section: dict[int, UnitUpgradeOption],
    resolved: list[UnitUpgradeOption],
    weapons: list[Weapon],
    warnings: list[str],
    errors: list[str],
    stack: list[int],
    explicit: bool,
    warn_on_added_prerequisites: bool,
) -> None:
    if option.id in {selected.id for selected in resolved}:
        return
    if option.id in stack:
        errors.append(f"{option.label} has a circular upgrade dependency.")
        return
    if option.section.unit_id != unit.id:
        errors.append(f"{option.label} does not belong to {unit.name}.")
        return

    selected_in_section = selected_by_section.get(option.section_id)
    if (
        selected_in_section is not None
        and selected_in_section.id != option.id
        and not _is_replace_any_option(option)
    ):
        errors.append(f"Only one upgrade can be selected from {option.section.label}.")
        return

    if _is_replace_option(option) and not _has_target_weapon(weapons, option.section.targets):
        prerequisite = _find_prerequisite_option(
            all_options=all_options,
            selected_by_section=selected_by_section,
            targets=option.section.targets,
            excluded_option_ids={option.id, *stack},
        )
        if prerequisite is None:
            errors.append(f"{option.label} requires a weapon matching {', '.join(option.section.targets)}.")
            return
        _ensure_option(
            unit=unit,
            option=prerequisite,
            all_options=all_options,
            selected_by_section=selected_by_section,
            resolved=resolved,
            weapons=weapons,
            warnings=warnings,
            errors=errors,
            stack=[*stack, option.id],
            explicit=False,
            warn_on_added_prerequisites=warn_on_added_prerequisites,
        )
        if errors or not _has_target_weapon(weapons, option.section.targets):
            errors.append(f"{option.label} requires a weapon matching {', '.join(option.section.targets)}.")
            return
        if warn_on_added_prerequisites:
            warnings.append(f"{unit.name} added {prerequisite.label} because {option.label} requires it.")

    if not _is_replace_any_option(option):
        selected_by_section[option.section_id] = option
    _apply_option(weapons, option)
    resolved.append(option)


def _dedupe_options(options: list[UnitUpgradeOption]) -> list[UnitUpgradeOption]:
    seen: set[int] = set()
    deduped: list[UnitUpgradeOption] = []
    for option in options:
        if option.id in seen:
            continue
        seen.add(option.id)
        deduped.append(option)
    return deduped


def _upgrade_options(unit: Unit) -> list[UnitUpgradeOption]:
    options: list[UnitUpgradeOption] = []
    for section in unit.upgrade_sections.all():
        options.extend(section.options.all())
    return options


def _default_weapons(unit: Unit) -> list[Weapon]:
    weapons = [
        slot.weapon
        for slot in unit.weapon_slots.all()
        if slot.is_default
        for _index in range(slot.count or 1)
    ]
    if weapons:
        return weapons
    return [slot.weapon for slot in unit.weapon_slots.all()[:1]]


def _is_replace_option(option: UnitUpgradeOption) -> bool:
    return option.section.variant.lower() == "replace"


def _is_replace_any_option(option: UnitUpgradeOption) -> bool:
    affects = option.section.affects or {}
    return _is_replace_option(option) and str(affects.get("type") or "").lower() == "any"


def _has_target_weapon(weapons: list[Weapon], targets: list[str]) -> bool:
    return any(weapon_matches_upgrade_target(weapon.name, targets) for weapon in weapons)


def _find_prerequisite_option(
    *,
    all_options: list[UnitUpgradeOption],
    selected_by_section: dict[int, UnitUpgradeOption],
    targets: list[str],
    excluded_option_ids: set[int],
) -> UnitUpgradeOption | None:
    candidates: list[UnitUpgradeOption] = []
    for option in all_options:
        if option.id in excluded_option_ids:
            continue
        selected_in_section = selected_by_section.get(option.section_id)
        if selected_in_section is not None and selected_in_section.id != option.id:
            continue
        option_weapons = list(option.weapons.all())
        if _has_target_weapon(option_weapons, targets):
            candidates.append(option)
    return min(candidates, key=lambda option: (option.cost, option.label, option.id), default=None)


def _apply_option(weapons: list[Weapon], option: UnitUpgradeOption) -> None:
    if _is_replace_option(option):
        if _is_replace_any_option(option):
            _remove_target_weapon(weapons, option.section.targets)
        else:
            weapons[:] = [
                weapon
                for weapon in weapons
                if not weapon_matches_upgrade_target(weapon.name, option.section.targets)
            ]
    weapons.extend(option.weapons.all())


def _remove_target_weapon(weapons: list[Weapon], targets: list[str]) -> None:
    for index, weapon in enumerate(weapons):
        if weapon_matches_upgrade_target(weapon.name, targets):
            del weapons[index]
            return
