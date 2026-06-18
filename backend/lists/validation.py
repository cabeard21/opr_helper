from __future__ import annotations

from typing import Any

from army_books.models import UnitWeaponSlot
from lists.models import ArmyList, ListUnit


def selected_or_default_slot(entry: ListUnit) -> UnitWeaponSlot | None:
    if entry.selected_weapon_slot_id:
        return entry.selected_weapon_slot

    slots = list(entry.unit.weapon_slots.all())
    return next((slot for slot in slots if slot.is_default), None) or (slots[0] if slots else None)


def list_unit_points(entry: ListUnit) -> int:
    slot = selected_or_default_slot(entry)
    upgrade_cost = slot.upgrade_cost if slot else 0
    return entry.unit.points * entry.model_count + upgrade_cost


def army_list_points(army_list: ArmyList) -> int:
    return sum(list_unit_points(entry) for entry in army_list.units.all())


def validate_model_count(unit: Any, model_count: int) -> str | None:
    if model_count < unit.min_models:
        return f"Model count must be at least {unit.min_models}."
    if unit.max_models is not None and model_count > unit.max_models:
        return f"Model count must be at most {unit.max_models}."
    return None


def army_list_validation(army_list: ArmyList) -> dict[str, list[dict[str, Any]]]:
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    total_points = army_list_points(army_list)

    if army_list.point_limit > 0 and total_points > army_list.point_limit:
        errors.append(
            {
                "code": "over_point_limit",
                "message": f"Army list is {total_points - army_list.point_limit} pts over the limit.",
            }
        )

    for entry in army_list.units.all():
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

    return {"errors": errors, "warnings": warnings}
