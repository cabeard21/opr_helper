from __future__ import annotations

from math import ceil
from typing import Any
from collections import Counter, defaultdict

from lists.loadouts import selected_or_default_slot, selected_upgrade_cost
from lists.models import ArmyList, ListUnit


def unit_selection_points(
    *,
    unit: Any,
    model_count: int,
    upgrade_cost: int = 0,
    combined_count: int = 1,
) -> int:
    default_models = max(1, int(getattr(unit, "default_models", 1) or 1))
    base_points = ceil(int(unit.points) * max(1, model_count) / default_models)
    return (base_points + upgrade_cost) * max(1, combined_count)


def list_unit_points(entry: ListUnit) -> int:
    upgrade_cost = selected_upgrade_cost(entry)
    return unit_selection_points(
        unit=entry.unit,
        model_count=entry.model_count,
        upgrade_cost=upgrade_cost,
        combined_count=entry.combined_from_count,
    )


def army_list_points(army_list: ArmyList) -> int:
    return sum(list_unit_points(entry) for entry in army_list.units.all())


def validate_model_count(unit: Any, model_count: int) -> str | None:
    if model_count < unit.min_models:
        return f"Model count must be at least {unit.min_models}."
    max_models = effective_max_models(unit)
    if model_count > max_models:
        return f"Model count must be at most {max_models}."
    return None


def effective_max_models(unit: Any) -> int:
    return int(unit.max_models or unit.default_models or unit.min_models or 1)


def is_hero(unit: Any) -> bool:
    return _has_rule(unit.special_rules, "Hero")


def force_org_hero_limit(point_limit: int) -> int | None:
    if point_limit <= 0:
        return None
    return max(1, point_limit // 375)


def force_org_copy_limit(point_limit: int) -> int | None:
    if point_limit <= 0:
        return None
    return 1 + point_limit // 750


def force_org_group_limit(point_limit: int) -> int | None:
    if point_limit <= 0:
        return None
    return point_limit // 150


def force_org_group_point_cap(point_limit: int) -> float | None:
    if point_limit <= 0:
        return None
    return point_limit * 0.35


def can_host_hero(entry: ListUnit) -> bool:
    return entry.model_count > 1 and not is_hero(entry.unit)


def validate_parent_entry(entry: ListUnit, parent_entry: ListUnit | None) -> str | None:
    if parent_entry is None:
        return None
    if parent_entry.army_list_id != entry.army_list_id:
        return "Embedded heroes must join a unit in the same army list."
    if parent_entry.id == entry.id:
        return "A unit cannot embed into itself."
    if not is_hero(entry.unit):
        return "Only heroes can be embedded with units."
    if entry.unit.tough > 6:
        return "Only heroes up to Tough(6) can be embedded with units."
    if not can_host_hero(parent_entry):
        return "Heroes can only be embedded with multi-model non-hero units."
    existing_hero = (
        ListUnit.objects.filter(parent_entry=parent_entry)
        .exclude(id=entry.id)
        .select_related("unit")
        .first()
    )
    if existing_hero is not None:
        return f"{parent_entry.unit.name} already has an embedded hero."
    return None


def army_list_validation(army_list: ArmyList) -> dict[str, list[dict[str, Any]]]:
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    entries = list(army_list.units.all())
    total_points = sum(list_unit_points(entry) for entry in entries)

    if army_list.point_limit > 0 and total_points > army_list.point_limit:
        errors.append(
            {
                "code": "over_point_limit",
                "message": f"Army list is {total_points - army_list.point_limit} pts over the limit.",
            }
        )

    for entry in entries:
        if entry.unit.faction_id != army_list.faction_id:
            errors.append(
                {
                    "code": "wrong_faction",
                    "list_unit_id": entry.id,
                    "message": f"{entry.unit.name} is not from this army list faction.",
                }
            )

        if entry.selected_weapon_slot_id and entry.selected_weapon_slot.unit_id != entry.unit_id:
            errors.append(
                {
                    "code": "invalid_weapon_slot",
                    "list_unit_id": entry.id,
                    "message": f"{entry.unit.name} has a weapon slot from another unit.",
                }
            )

        model_error = validate_model_count(entry.unit, entry.model_count)
        if model_error:
            errors.append(
                {
                    "code": "invalid_model_count",
                    "list_unit_id": entry.id,
                    "message": f"{entry.unit.name}: {model_error}",
                }
            )

        if selected_or_default_slot(entry) is None:
            warnings.append(
                {
                    "code": "missing_weapon",
                    "list_unit_id": entry.id,
                    "message": f"{entry.unit.name} has no weapon available for calculation.",
                }
            )

        if entry.combined_from_count < 1:
            errors.append(
                {
                    "code": "invalid_combined_count",
                    "list_unit_id": entry.id,
                    "message": f"{entry.unit.name} combined unit count must be at least 1.",
                }
            )
        if entry.combined_from_count > 1 and entry.model_count <= 1:
            errors.append(
                {
                    "code": "invalid_combined_unit",
                    "list_unit_id": entry.id,
                    "message": f"{entry.unit.name} can only be combined when it has multiple models.",
                }
            )

        parent_error = validate_parent_entry(entry, entry.parent_entry)
        if parent_error:
            errors.append(
                {
                    "code": "invalid_embedded_hero",
                    "list_unit_id": entry.id,
                    "message": f"{entry.unit.name}: {parent_error}",
                }
            )

    errors.extend(_force_org_errors(army_list, entries))
    return {"errors": errors, "warnings": warnings}


def _force_org_errors(army_list: ArmyList, entries: list[ListUnit]) -> list[dict[str, Any]]:
    if army_list.point_limit <= 0:
        return []

    errors: list[dict[str, Any]] = []
    hero_count = sum(1 for entry in entries if is_hero(entry.unit))
    hero_limit = force_org_hero_limit(army_list.point_limit)
    if hero_limit is not None and hero_count > hero_limit:
        errors.append(
            {
                "code": "too_many_heroes",
                "message": f"Force organization allows at most {hero_limit} heroes at {army_list.point_limit} pts.",
            }
        )

    max_copies = force_org_copy_limit(army_list.point_limit)
    unit_copies = Counter()
    for entry in entries:
        unit_copies[entry.unit_id] += max(1, entry.combined_from_count)
    for unit_id, copies in unit_copies.items():
        if max_copies is not None and copies > max_copies:
            unit_name = next(entry.unit.name for entry in entries if entry.unit_id == unit_id)
            errors.append(
                {
                    "code": "too_many_unit_copies",
                    "unit_id": unit_id,
                    "message": f"{unit_name} appears {copies} times; force organization allows {max_copies}.",
                }
            )

    max_groups = force_org_group_limit(army_list.point_limit)
    effective_groups = sum(1 for entry in entries if entry.parent_entry_id is None)
    if max_groups is not None and effective_groups > max_groups:
        errors.append(
            {
                "code": "too_many_units",
                "message": f"Force organization allows at most {max_groups} effective units at {army_list.point_limit} pts.",
            }
        )

    child_points: dict[int, int] = defaultdict(int)
    for entry in entries:
        if entry.parent_entry_id:
            child_points[entry.parent_entry_id] += list_unit_points(entry)
    point_cap = force_org_group_point_cap(army_list.point_limit)
    for entry in entries:
        if entry.parent_entry_id:
            continue
        group_points = list_unit_points(entry) + child_points[entry.id]
        if point_cap is not None and group_points > point_cap:
            errors.append(
                {
                    "code": "unit_group_over_point_share",
                    "list_unit_id": entry.id,
                    "message": f"{entry.unit.name} group is {group_points} pts, over the 35% force organization cap.",
                }
            )

    return errors


def _has_rule(rules: dict[str, Any] | None, name: str) -> bool:
    if not rules:
        return False
    return any(key.lower() == name.lower() for key in rules)
