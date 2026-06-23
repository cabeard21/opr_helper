from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from advisor.llm_service import ListSuggestion, SuggestedUnit
from army_books.models import Faction, Unit, UnitUpgradeOption, UnitWeaponSlot
from lists.validation import (
    effective_max_models,
    force_org_copy_limit,
    force_org_group_limit,
    force_org_group_point_cap,
    force_org_hero_limit,
    is_hero,
    unit_selection_points,
)


@dataclass(frozen=True)
class ReconciledSuggestion:
    suggestion: ListSuggestion
    computed_total_points: int
    point_delta: int
    warnings: list[str]


@dataclass(frozen=True)
class RepairAction:
    kind: Literal["add", "replace", "resize", "upgrade"]
    unit: Unit
    model_count: int
    new_total: int
    message: str
    selected_upgrade_ids: list[int] | None = None
    replace_index: int | None = None
    resize_index: int | None = None
    upgrade_index: int | None = None


def reconcile_suggestion(
    *,
    faction: Faction,
    point_limit: int,
    suggestion: ListSuggestion,
) -> ReconciledSuggestion:
    faction_units = {
        unit.id: unit
        for unit in Unit.objects.filter(faction=faction)
        .prefetch_related("weapon_slots__weapon", "upgrade_sections__options__weapons")
        .order_by("name", "id")
    }
    suggested_units = {
        unit.id: unit
        for unit in Unit.objects.filter(
            id__in=[suggested.unit_id for suggested in suggestion.units]
        ).prefetch_related("weapon_slots__weapon", "upgrade_sections__options__weapons")
    }
    reconciled_units: list[SuggestedUnit] = []
    warnings = list(suggestion.warnings)
    computed_total_points = 0
    hero_count = 0
    unit_copies: dict[int, int] = {}
    max_heroes = force_org_hero_limit(point_limit)
    max_copies = force_org_copy_limit(point_limit)
    max_groups = force_org_group_limit(point_limit)
    group_point_cap = force_org_group_point_cap(point_limit)

    for suggested in suggestion.units:
        unit = suggested_units.get(suggested.unit_id)
        if unit is None:
            warnings.append(f"{suggested.unit_name} references an unknown unit id and was skipped.")
            continue
        if unit.faction_id != faction.id:
            warnings.append(f"{suggested.unit_name} is not available to {faction.name}.")
            continue

        model_count, count_warnings = _reconcile_model_count(unit, suggested.model_count)
        warnings.extend(count_warnings)
        combined_from_count, combined_warnings = _reconcile_combined_count(
            unit,
            model_count,
            suggested.combined_from_count,
        )
        warnings.extend(combined_warnings)
        selected_upgrade_ids, upgrade_warnings = _reconcile_selected_upgrades(
            unit,
            suggested.selected_upgrade_ids,
        )
        warnings.extend(upgrade_warnings)
        unit_points = _unit_points(unit, model_count, selected_upgrade_ids, combined_from_count)
        if group_point_cap is not None and unit_points > group_point_cap:
            warnings.append(
                f"{unit.name} was skipped because it exceeds the 35% force organization unit cap."
            )
            continue
        if computed_total_points + unit_points > point_limit:
            warnings.append(f"{unit.name} was skipped because it would exceed the point limit.")
            continue
        if (
            max_groups is not None
            and suggested.parent_unit_index is None
            and _effective_group_count(reconciled_units) >= max_groups
        ):
            warnings.append(
                f"{unit.name} was skipped because force organization allows at most {max_groups} units."
            )
            continue
        if is_hero(unit):
            if max_heroes is not None and hero_count >= max_heroes:
                warnings.append(
                    f"{unit.name} was skipped because force organization allows at most {max_heroes} heroes."
                )
                continue
            hero_count += 1
        unit_copy_count = unit_copies.get(unit.id, 0)
        if max_copies is not None and unit_copy_count + combined_from_count > max_copies:
            warnings.append(
                f"{unit.name} was skipped because force organization allows at most {max_copies} copies."
            )
            continue
        unit_copies[unit.id] = unit_copy_count + combined_from_count
        reconciled = suggested.model_copy(
            update={
                "unit_name": unit.name,
                "model_count": model_count,
                "combined_from_count": combined_from_count,
                "selected_upgrade_ids": selected_upgrade_ids,
                "parent_unit_index": suggested.parent_unit_index,
            }
        )
        reconciled_units.append(reconciled)
        computed_total_points += unit_points

    unit_lookup = {unit.id: unit for unit in faction_units.values()}
    reconciled_units = _reconcile_parent_indexes(
        reconciled_units=reconciled_units,
        unit_lookup=unit_lookup,
        point_limit=point_limit,
        warnings=warnings,
    )

    reconciled_units, computed_total_points = _repair_underfilled_suggestion(
        faction_units=list(faction_units.values()),
        point_limit=point_limit,
        reconciled_units=reconciled_units,
        computed_total_points=computed_total_points,
        warnings=warnings,
    )

    reconciled_suggestion = suggestion.model_copy(
        update={
            "units": reconciled_units,
            "total_points": computed_total_points,
            "activation_count": _effective_group_count(reconciled_units),
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
    max_models = effective_max_models(unit)
    if model_count > max_models:
        model_count = max_models
        warnings.append(f"{unit.name} model count was reduced to the maximum of {max_models}.")
    return model_count, warnings


def _reconcile_combined_count(
    unit: Unit,
    model_count: int,
    requested_count: int,
) -> tuple[int, list[str]]:
    warnings: list[str] = []
    combined_count = max(1, requested_count)
    if combined_count > 1 and (model_count <= 1 or is_hero(unit)):
        combined_count = 1
        warnings.append(f"{unit.name} combined count was reduced to 1 because it cannot be combined.")
    return combined_count, warnings


def _unit_points(
    unit: Unit,
    model_count: int,
    selected_upgrade_ids: list[int] | None = None,
    combined_from_count: int = 1,
) -> int:
    slot = _default_slot(list(unit.weapon_slots.all()))
    upgrade_options = _upgrade_options_by_id(unit, selected_upgrade_ids or [])
    upgrade_cost = sum(option.cost for option in upgrade_options)
    if not upgrade_options and slot:
        upgrade_cost = slot.upgrade_cost
    return unit_selection_points(
        unit=unit,
        model_count=model_count,
        upgrade_cost=upgrade_cost,
        combined_count=combined_from_count,
    )


def _reconcile_selected_upgrades(unit: Unit, option_ids: list[int]) -> tuple[list[int], list[str]]:
    if not option_ids:
        return [], []

    warnings: list[str] = []
    selected_ids: list[int] = []
    seen_sections: set[int] = set()
    option_lookup = {option.id: option for option in _upgrade_options_by_id(unit, option_ids)}
    for option_id in option_ids:
        option = option_lookup.get(option_id)
        if option is None:
            warnings.append(f"{unit.name} ignored invalid upgrade id {option_id}.")
            continue
        if option.section_id in seen_sections:
            warnings.append(f"{unit.name} ignored {option.label}; only one upgrade per section is allowed.")
            continue
        seen_sections.add(option.section_id)
        selected_ids.append(option.id)
    return selected_ids, warnings


def _upgrade_options_by_id(unit: Unit, option_ids: list[int]) -> list[UnitUpgradeOption]:
    if not option_ids:
        return []
    wanted = set(option_ids)
    options: list[UnitUpgradeOption] = []
    for section in unit.upgrade_sections.all():
        options.extend(option for option in section.options.all() if option.id in wanted)
    option_order = {option_id: index for index, option_id in enumerate(option_ids)}
    return sorted(options, key=lambda option: option_order[option.id])


def _default_slot(slots: list[UnitWeaponSlot]) -> UnitWeaponSlot | None:
    return next((slot for slot in slots if slot.is_default), None) or (slots[0] if slots else None)


def _reconcile_parent_indexes(
    *,
    reconciled_units: list[SuggestedUnit],
    unit_lookup: dict[int, Unit],
    point_limit: int,
    warnings: list[str],
) -> list[SuggestedUnit]:
    claimed_hosts: set[int] = set()
    resolved_units: list[SuggestedUnit] = []
    for index, suggested in enumerate(reconciled_units):
        parent_index = suggested.parent_unit_index
        if parent_index is None:
            resolved_units.append(suggested)
            continue
        parent_error = _parent_index_error(
            child=suggested,
            child_index=index,
            parent_index=parent_index,
            reconciled_units=reconciled_units,
            unit_lookup=unit_lookup,
            claimed_hosts=claimed_hosts,
            point_limit=point_limit,
        )
        if parent_error:
            warnings.append(parent_error)
            resolved_units.append(suggested.model_copy(update={"parent_unit_index": None}))
            continue
        claimed_hosts.add(parent_index)
        resolved_units.append(suggested)
    return resolved_units


def _parent_index_error(
    *,
    child: SuggestedUnit,
    child_index: int,
    parent_index: int,
    reconciled_units: list[SuggestedUnit],
    unit_lookup: dict[int, Unit],
    claimed_hosts: set[int],
    point_limit: int,
) -> str | None:
    if parent_index < 0 or parent_index >= len(reconciled_units) or parent_index == child_index:
        return f"{child.unit_name} ignored invalid embedded host index {parent_index}."
    if parent_index in claimed_hosts:
        return f"{child.unit_name} ignored embedded host index {parent_index}; that host already has a hero."
    parent = reconciled_units[parent_index]
    if parent.parent_unit_index is not None:
        return f"{child.unit_name} ignored embedded host index {parent_index}; heroes cannot embed into embedded units."

    child_unit = unit_lookup.get(child.unit_id)
    parent_unit = unit_lookup.get(parent.unit_id)
    if child_unit is None or parent_unit is None:
        return f"{child.unit_name} ignored embedded host index {parent_index}; unit data was unavailable."
    if not is_hero(child_unit):
        return f"{child.unit_name} ignored embedded host index {parent_index}; only heroes can be embedded."
    if child_unit.tough > 6:
        return f"{child.unit_name} ignored embedded host index {parent_index}; only heroes up to Tough(6) can be embedded."
    if is_hero(parent_unit) or parent.model_count <= 1:
        return f"{child.unit_name} ignored embedded host index {parent_index}; host must be a multi-model non-hero unit."
    if point_limit > 0:
        group_points = _unit_points(
            parent_unit,
            parent.model_count,
            parent.selected_upgrade_ids,
            parent.combined_from_count,
        )
        group_points += _unit_points(
            child_unit,
            child.model_count,
            child.selected_upgrade_ids,
            child.combined_from_count,
        )
        if group_points > point_limit * 0.35:
            return f"{child.unit_name} ignored embedded host index {parent_index}; embedded group exceeds the 35% cap."
    return None


def _repair_underfilled_suggestion(
    *,
    faction_units: list[Unit],
    point_limit: int,
    reconciled_units: list[SuggestedUnit],
    computed_total_points: int,
    warnings: list[str],
) -> tuple[list[SuggestedUnit], int]:
    if point_limit <= 0 or computed_total_points <= 0:
        return reconciled_units, computed_total_points
    if computed_total_points >= point_limit:
        return reconciled_units, computed_total_points
    if computed_total_points < point_limit * 0.75:
        return reconciled_units, computed_total_points

    unit_lookup = {unit.id: unit for unit in faction_units}
    repaired_units = list(reconciled_units)
    repaired_total = computed_total_points
    while repaired_total < point_limit:
        action = _best_repair_action(
            faction_units=faction_units,
            unit_lookup=unit_lookup,
            point_limit=point_limit,
            reconciled_units=repaired_units,
            computed_total_points=repaired_total,
        )
        if action is None:
            break
        repaired_units = _apply_repair_action(repaired_units, action)
        repaired_total = action.new_total
        warnings.append(action.message)
    return repaired_units, repaired_total


def _best_repair_action(
    *,
    faction_units: list[Unit],
    unit_lookup: dict[int, Unit],
    point_limit: int,
    reconciled_units: list[SuggestedUnit],
    computed_total_points: int,
) -> RepairAction | None:
    actions: list[RepairAction] = []

    for index, suggested in enumerate(reconciled_units):
        unit = unit_lookup.get(suggested.unit_id)
        if unit is None:
            continue
        for selected_upgrade_ids in _upgrade_repair_candidates(unit, suggested.selected_upgrade_ids):
            action = _legal_repair_action(
                kind="upgrade",
                candidate=unit,
                model_count=suggested.model_count,
                selected_upgrade_ids=selected_upgrade_ids,
                point_limit=point_limit,
                reconciled_units=reconciled_units,
                unit_lookup=unit_lookup,
                computed_total_points=computed_total_points,
                upgrade_index=index,
            )
            if action is not None:
                actions.append(action)

        max_models = effective_max_models(unit)
        if suggested.model_count < max_models:
            next_count = suggested.model_count + 1
            action = _legal_repair_action(
                kind="resize",
                candidate=unit,
                model_count=next_count,
                selected_upgrade_ids=suggested.selected_upgrade_ids,
                point_limit=point_limit,
                reconciled_units=reconciled_units,
                unit_lookup=unit_lookup,
                computed_total_points=computed_total_points,
                resize_index=index,
            )
            if action is not None:
                actions.append(action)

    if actions:
        return min(
            actions,
            key=lambda action: (
                point_limit - action.new_total,
                -_repair_priority(action.unit),
                action.unit.name,
                action.unit.id,
            ),
        )

    for candidate in faction_units:
        model_count = _default_model_count(candidate)
        action = _legal_repair_action(
            kind="add",
            candidate=candidate,
            model_count=model_count,
            point_limit=point_limit,
            reconciled_units=reconciled_units,
            unit_lookup=unit_lookup,
            computed_total_points=computed_total_points,
        )
        if action is not None:
            actions.append(action)

        for index, suggested in enumerate(reconciled_units):
            if index in _protected_parent_indexes(reconciled_units):
                continue
            if suggested.unit_id == candidate.id and suggested.model_count == model_count:
                continue
            action = _legal_repair_action(
                kind="replace",
                candidate=candidate,
                model_count=model_count,
                point_limit=point_limit,
                reconciled_units=reconciled_units,
                unit_lookup=unit_lookup,
                computed_total_points=computed_total_points,
                replace_index=index,
            )
            if action is not None:
                actions.append(action)

    if not actions:
        return None
    return min(
        actions,
        key=lambda action: (
            point_limit - action.new_total,
            -_repair_priority(action.unit),
            action.unit.name,
            action.unit.id,
        ),
    )


def _legal_repair_action(
    *,
    kind: Literal["add", "replace", "resize", "upgrade"],
    candidate: Unit,
    model_count: int,
    point_limit: int,
    reconciled_units: list[SuggestedUnit],
    unit_lookup: dict[int, Unit],
    computed_total_points: int,
    selected_upgrade_ids: list[int] | None = None,
    replace_index: int | None = None,
    resize_index: int | None = None,
    upgrade_index: int | None = None,
) -> RepairAction | None:
    old_points = 0
    old_name = ""
    remaining_units = reconciled_units
    if replace_index is not None:
        old = reconciled_units[replace_index]
        old_unit = unit_lookup.get(old.unit_id)
        if old_unit is None:
            return None
        old_points = _unit_points(
            old_unit,
            old.model_count,
            old.selected_upgrade_ids,
            old.combined_from_count,
        )
        old_name = old_unit.name
        remaining_units = [
            suggested for index, suggested in enumerate(reconciled_units) if index != replace_index
        ]
    if resize_index is not None:
        old = reconciled_units[resize_index]
        old_unit = unit_lookup.get(old.unit_id)
        if old_unit is None:
            return None
        old_points = _unit_points(
            old_unit,
            old.model_count,
            old.selected_upgrade_ids,
            old.combined_from_count,
        )
        remaining_units = [
            suggested for index, suggested in enumerate(reconciled_units) if index != resize_index
        ]
    if upgrade_index is not None:
        old = reconciled_units[upgrade_index]
        old_unit = unit_lookup.get(old.unit_id)
        if old_unit is None:
            return None
        old_points = _unit_points(
            old_unit,
            old.model_count,
            old.selected_upgrade_ids,
            old.combined_from_count,
        )
        remaining_units = [
            suggested for index, suggested in enumerate(reconciled_units) if index != upgrade_index
        ]

    candidate_upgrade_ids = selected_upgrade_ids or []
    candidate_points = _unit_points(candidate, model_count, candidate_upgrade_ids)
    new_total = computed_total_points - old_points + candidate_points
    if new_total <= computed_total_points or new_total > point_limit:
        return None
    if not _can_include_unit(
        candidate=candidate,
        model_count=model_count,
        selected_upgrade_ids=candidate_upgrade_ids,
        point_limit=point_limit,
        existing_units=remaining_units,
        unit_lookup=unit_lookup,
        adding_group=kind == "add",
    ):
        return None

    if kind == "add":
        message = f"Added {candidate.name} to use remaining points."
    elif kind == "replace":
        message = f"{candidate.name} replaced {old_name} to use remaining points."
    elif kind == "upgrade":
        labels = ", ".join(option.label for option in _upgrade_options_by_id(candidate, candidate_upgrade_ids))
        message = f"Added {labels} to {candidate.name} to use remaining points."
    else:
        message = f"Raised {candidate.name} to {model_count} models to use remaining points."
    return RepairAction(
        kind=kind,
        unit=candidate,
        model_count=model_count,
        new_total=new_total,
        message=message,
        selected_upgrade_ids=candidate_upgrade_ids,
        replace_index=replace_index,
        resize_index=resize_index,
        upgrade_index=upgrade_index,
    )


def _can_include_unit(
    *,
    candidate: Unit,
    model_count: int,
    selected_upgrade_ids: list[int],
    point_limit: int,
    existing_units: list[SuggestedUnit],
    unit_lookup: dict[int, Unit],
    adding_group: bool,
) -> bool:
    max_heroes = force_org_hero_limit(point_limit)
    max_copies = force_org_copy_limit(point_limit)
    max_groups = force_org_group_limit(point_limit)
    group_point_cap = force_org_group_point_cap(point_limit)
    if (
        group_point_cap is not None
        and _unit_points(candidate, model_count, selected_upgrade_ids) > group_point_cap
    ):
        return False
    if max_groups is not None and adding_group and _effective_group_count(existing_units) + 1 > max_groups:
        return False

    hero_count = 0
    copies: dict[int, int] = {}
    for suggested in existing_units:
        unit = unit_lookup.get(suggested.unit_id)
        if unit is None:
            return False
        if is_hero(unit):
            hero_count += 1
        copies[unit.id] = copies.get(unit.id, 0) + max(1, suggested.combined_from_count)

    if max_heroes is not None and is_hero(candidate) and hero_count >= max_heroes:
        return False
    if max_copies is not None and copies.get(candidate.id, 0) >= max_copies:
        return False
    return True


def _apply_repair_action(
    reconciled_units: list[SuggestedUnit],
    action: RepairAction,
) -> list[SuggestedUnit]:
    if action.kind == "add":
        return [
            *reconciled_units,
            SuggestedUnit(
                unit_id=action.unit.id,
                unit_name=action.unit.name,
                model_count=action.model_count,
                selected_upgrade_ids=action.selected_upgrade_ids or [],
                parent_unit_index=None,
                justification="Added by advisor reconciliation to use remaining points legally.",
            ),
        ]
    if action.kind == "replace" and action.replace_index is not None:
        return [
            suggested
            if index != action.replace_index
            else SuggestedUnit(
                unit_id=action.unit.id,
                unit_name=action.unit.name,
                model_count=action.model_count,
                selected_upgrade_ids=action.selected_upgrade_ids or [],
                parent_unit_index=None,
                justification=f"Replaced {suggested.unit_name} to better use the point limit legally.",
            )
            for index, suggested in enumerate(reconciled_units)
        ]
    if action.kind == "resize" and action.resize_index is not None:
        return [
            suggested
            if index != action.resize_index
            else suggested.model_copy(update={"model_count": action.model_count})
            for index, suggested in enumerate(reconciled_units)
        ]
    if action.kind == "upgrade" and action.upgrade_index is not None:
        return [
            suggested
            if index != action.upgrade_index
            else suggested.model_copy(update={"selected_upgrade_ids": action.selected_upgrade_ids or []})
            for index, suggested in enumerate(reconciled_units)
        ]
    return reconciled_units


def _upgrade_repair_candidates(unit: Unit, selected_upgrade_ids: list[int]) -> list[list[int]]:
    selected_options = _upgrade_options_by_id(unit, selected_upgrade_ids)
    selected_sections = {option.section_id for option in selected_options}
    candidates: list[list[int]] = []
    for section in unit.upgrade_sections.all():
        if section.id in selected_sections:
            continue
        for option in section.options.all():
            if option.cost <= 0:
                continue
            candidates.append([*selected_upgrade_ids, option.id])
    return candidates


def _protected_parent_indexes(units: list[SuggestedUnit]) -> set[int]:
    protected: set[int] = set()
    for index, unit in enumerate(units):
        if unit.parent_unit_index is not None:
            protected.add(index)
            protected.add(unit.parent_unit_index)
    return protected


def _effective_group_count(units: list[SuggestedUnit]) -> int:
    return sum(1 for unit in units if unit.parent_unit_index is None)


def _default_model_count(unit: Unit) -> int:
    model_count = max(unit.min_models, unit.default_models)
    model_count = min(model_count, effective_max_models(unit))
    return model_count


def _repair_priority(unit: Unit) -> float:
    mobility_score = sum(
        1
        for rule_name in ("Scout", "Fast", "Flying", "Strider", "Ambush")
        if _has_rule(unit.special_rules, rule_name)
    )
    slot = _default_slot(list(unit.weapon_slots.all()))
    if slot is None:
        return mobility_score * 10
    weapon_rules = slot.weapon.special_rules or {}
    deadly = float(weapon_rules.get("Deadly") or weapon_rules.get("deadly") or 0)
    return mobility_score * 10 + slot.weapon.ap * 3 + deadly


def _has_rule(rules: dict, name: str) -> bool:
    return any(key.lower() == name.lower() and bool(value) for key, value in rules.items())
