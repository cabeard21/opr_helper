from __future__ import annotations

from dataclasses import dataclass

from advisor.llm_service import ListSuggestion, SuggestedUnit
from army_books.models import Faction, Unit, UnitWeaponSlot


@dataclass(frozen=True)
class ReconciledSuggestion:
    suggestion: ListSuggestion
    computed_total_points: int
    point_delta: int
    warnings: list[str]


def reconcile_suggestion(
    *,
    faction: Faction,
    point_limit: int,
    suggestion: ListSuggestion,
) -> ReconciledSuggestion:
    units = {
        unit.id: unit
        for unit in Unit.objects.filter(
            id__in=[suggested.unit_id for suggested in suggestion.units]
        ).prefetch_related("weapon_slots__weapon")
    }
    reconciled_units: list[SuggestedUnit] = []
    warnings = list(suggestion.warnings)
    computed_total_points = 0

    for suggested in suggestion.units:
        unit = units.get(suggested.unit_id)
        if unit is None:
            warnings.append(f"{suggested.unit_name} references an unknown unit id and was skipped.")
            continue
        if unit.faction_id != faction.id:
            warnings.append(f"{suggested.unit_name} is not available to {faction.name}.")
            continue

        model_count, count_warnings = _reconcile_model_count(unit, suggested.model_count)
        warnings.extend(count_warnings)
        reconciled = suggested.model_copy(
            update={
                "unit_name": unit.name,
                "model_count": model_count,
            }
        )
        reconciled_units.append(reconciled)
        computed_total_points += _unit_points(unit, model_count)

    reconciled_suggestion = suggestion.model_copy(
        update={
            "units": reconciled_units,
            "total_points": computed_total_points,
            "activation_count": len(reconciled_units),
            "warnings": warnings,
        }
    )
    return ReconciledSuggestion(
        suggestion=reconciled_suggestion,
        computed_total_points=computed_total_points,
        point_delta=point_limit - computed_total_points,
        warnings=warnings,
    )


def _reconcile_model_count(unit: Unit, requested_count: int) -> tuple[int, list[str]]:
    warnings: list[str] = []
    model_count = requested_count
    if model_count < unit.min_models:
        model_count = unit.min_models
        warnings.append(f"{unit.name} model count was raised to the minimum of {unit.min_models}.")
    if unit.max_models is not None and model_count > unit.max_models:
        model_count = unit.max_models
        warnings.append(f"{unit.name} model count was reduced to the maximum of {unit.max_models}.")
    return model_count, warnings


def _unit_points(unit: Unit, model_count: int) -> int:
    slot = _default_slot(list(unit.weapon_slots.all()))
    upgrade_cost = slot.upgrade_cost if slot else 0
    return unit.points * model_count + upgrade_cost


def _default_slot(slots: list[UnitWeaponSlot]) -> UnitWeaponSlot | None:
    return next((slot for slot in slots if slot.is_default), None) or (slots[0] if slots else None)
