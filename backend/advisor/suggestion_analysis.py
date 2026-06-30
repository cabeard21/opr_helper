from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from army_books.calc.weapon_scoring import weapon_ev_profile
from army_books.models import Faction, Unit, UnitUpgradeOption
from advisor.packages import _variant_weapons_and_rules
from lists.analysis import default_target_profiles, weapon_combat_context
from lists.loadouts import weapon_attack_count
from lists.validation import is_hero, unit_selection_points

from advisor.reconciliation import ReconciledSuggestion


DAMAGE_OUTPUT_BENCHMARKS_750 = {
    "infantry": 25.0,
    "elite": 12.0,
    "monster": 8.0,
}
LOW_DAMAGE_OUTPUT_SCORE = 45.0


@dataclass(frozen=True)
class SuggestionAnalysis:
    point_limit: int
    total_points: int
    point_delta: int
    activation_count: int
    largest_group_points: int
    largest_group_share: float
    mobility_count: int
    screen_count: int
    ranged_count: int
    melee_count: int
    anti_tough_count: int
    support_count: int
    target_ev: dict[str, float]
    damage_output_score: float
    damage_output_benchmarks: dict[str, float]
    ranged_ev: float
    melee_ev: float
    issues: tuple[str, ...]


def analyze_reconciled_suggestion(
    *,
    faction: Faction,
    point_limit: int,
    reconciled: ReconciledSuggestion,
) -> SuggestionAnalysis:
    unit_lookup = {
        unit.id: unit
        for unit in Unit.objects.filter(
            faction=faction,
            id__in=[suggested.unit_id for suggested in reconciled.suggestion.units],
        )
        .prefetch_related("weapon_slots__weapon", "upgrade_sections__options")
        .order_by("name", "id")
    }
    points_by_index: dict[int, int] = {}
    mobility_count = 0
    screen_count = 0
    ranged_count = 0
    melee_count = 0
    anti_tough_count = 0
    support_count = 0
    target_ev = {target.id: 0.0 for target in default_target_profiles()}
    ranged_ev = 0.0
    melee_ev = 0.0

    for index, suggested in enumerate(reconciled.suggestion.units):
        unit = unit_lookup.get(suggested.unit_id)
        if unit is None:
            continue
        points = _suggested_unit_points(
            unit,
            suggested.model_count,
            suggested.selected_upgrade_ids,
            suggested.selected_upgrade_selections,
            suggested.combined_from_count,
        )
        points_by_index[index] = points
        roles = _role_flags(unit=unit, points=points, point_limit=point_limit)
        mobility_count += int(roles["mobility"])
        screen_count += int(roles["screen"])
        ranged_count += int(roles["ranged"])
        melee_count += int(roles["melee"])
        anti_tough_count += int(roles["anti_tough"])
        support_count += int(roles["support"])
        unit_ev = _unit_ev(
            unit,
            suggested.model_count,
            suggested.combined_from_count,
            suggested.selected_upgrade_ids,
            suggested.selected_upgrade_selections,
        )
        for target_id, ev in unit_ev["targets"].items():
            target_ev[target_id] = round(target_ev[target_id] + ev, 6)
        ranged_ev = round(ranged_ev + unit_ev["ranged"], 6)
        melee_ev = round(melee_ev + unit_ev["melee"], 6)

    largest_group_points = _largest_group_points(reconciled.suggestion.units, points_by_index)
    largest_group_share = round(largest_group_points / point_limit, 4) if point_limit > 0 else 0
    activation_count = reconciled.suggestion.activation_count
    damage_output_benchmarks = scaled_damage_output_benchmarks(point_limit)
    analysis = SuggestionAnalysis(
        point_limit=point_limit,
        total_points=reconciled.computed_total_points,
        point_delta=reconciled.point_delta,
        activation_count=activation_count,
        largest_group_points=largest_group_points,
        largest_group_share=largest_group_share,
        mobility_count=mobility_count,
        screen_count=screen_count,
        ranged_count=ranged_count,
        melee_count=melee_count,
        anti_tough_count=anti_tough_count,
        support_count=support_count,
        target_ev=target_ev,
        damage_output_score=damage_output_score(target_ev, point_limit),
        damage_output_benchmarks=damage_output_benchmarks,
        ranged_ev=ranged_ev,
        melee_ev=melee_ev,
        issues=(),
    )
    return replace(analysis, issues=tuple(_analysis_issues(analysis)))


def build_metrics_correction_feedback(analysis: SuggestionAnalysis) -> str:
    if not analysis.issues:
        return ""

    metrics = (
        "List health metrics: "
        f"points {analysis.total_points}/{analysis.point_limit}; "
        f"activations {analysis.activation_count}; "
        f"mobility packages {analysis.mobility_count}; "
        f"anti-tough packages {analysis.anti_tough_count}; "
        f"ranged packages {analysis.ranged_count}; "
        f"damage output {analysis.damage_output_score:.0f}; "
        f"largest group {analysis.largest_group_share:.0%}."
    )
    return f"{metrics} {' '.join(analysis.issues)}"


def _analysis_issues(analysis: SuggestionAnalysis) -> list[str]:
    issues: list[str] = []
    if analysis.activation_count < _minimum_activation_count(analysis.point_limit):
        issues.append("Improve activation count.")
    if analysis.mobility_count == 0:
        issues.append("Add mobile objective play.")
    if analysis.anti_tough_count == 0:
        issues.append("Add credible anti-tough/AP threat.")
    if analysis.damage_output_score < LOW_DAMAGE_OUTPUT_SCORE:
        issues.append(_low_damage_output_issue(analysis))
    if analysis.largest_group_share > 0.35:
        issues.append("Reduce points concentration in the largest group.")
    return issues


def scaled_damage_output_benchmarks(point_limit: int) -> dict[str, float]:
    scale = max(1, point_limit) / 750
    return {
        target_id: round(benchmark * scale, 6)
        for target_id, benchmark in DAMAGE_OUTPUT_BENCHMARKS_750.items()
    }


def damage_output_score(target_ev: dict[str, float], point_limit: int) -> float:
    benchmarks = scaled_damage_output_benchmarks(point_limit)
    scores = [
        min(100.0, (target_ev.get(target_id, 0.0) / benchmark) * 100)
        for target_id, benchmark in benchmarks.items()
        if benchmark > 0
    ]
    return round(sum(scores) / len(scores), 6) if scores else 0.0


def _low_damage_output_issue(analysis: SuggestionAnalysis) -> str:
    targets = default_target_profiles()
    current = " / ".join(
        f"{analysis.target_ev.get(target.id, 0.0):.2f} {target.name}"
        for target in targets
    )
    expected_values = " / ".join(
        f"{analysis.damage_output_benchmarks.get(target.id, 0.0):.2f}"
        for target in targets
    )
    return (
        "Improve total damage output. "
        f"Current totals: {current} EV; "
        f"expected around {expected_values} at {analysis.point_limit} pts."
    )


def _minimum_activation_count(point_limit: int) -> int:
    if point_limit >= 2000:
        return 7
    if point_limit >= 1000:
        return 4
    return 3


def _suggested_unit_points(
    unit: Unit,
    model_count: int,
    selected_upgrade_ids: list[int],
    selected_upgrade_selections: list | None,
    combined_from_count: int,
) -> int:
    quantities = _quantity_by_option(selected_upgrade_selections)
    upgrade_cost = sum(
        option.cost * quantities.get(option.id, 1)
        for option in _upgrade_options_by_id(unit, selected_upgrade_ids)
    )
    return unit_selection_points(
        unit=unit,
        model_count=model_count,
        upgrade_cost=upgrade_cost,
        combined_count=combined_from_count,
    )


def _upgrade_options_by_id(unit: Unit, option_ids: list[int]) -> list[UnitUpgradeOption]:
    if not option_ids:
        return []
    selected = set(option_ids)
    options: list[UnitUpgradeOption] = []
    for section in unit.upgrade_sections.all():
        options.extend(option for option in section.options.all() if option.id in selected)
    return options


def _quantity_by_option(selections: list | None) -> dict[int, int]:
    quantities: dict[int, int] = {}
    for selection in selections or []:
        if hasattr(selection, "option"):
            option_id = getattr(selection, "option")
            quantity = getattr(selection, "quantity", 1)
        else:
            option_id = selection.get("option") if isinstance(selection, dict) else None
            quantity = selection.get("quantity", 1) if isinstance(selection, dict) else 1
        if option_id is None:
            continue
        quantities[int(option_id)] = max(1, int(quantity))
    return quantities


def _largest_group_points(units: list[Any], points_by_index: dict[int, int]) -> int:
    group_points: dict[int, int] = {}
    for index, suggested in enumerate(units):
        parent_index = suggested.parent_unit_index
        root_index = parent_index if parent_index is not None and parent_index in points_by_index else index
        group_points[root_index] = group_points.get(root_index, 0) + points_by_index.get(index, 0)
    return max(group_points.values(), default=0)


def _role_flags(*, unit: Unit, points: int, point_limit: int) -> dict[str, bool]:
    has_ranged = any(slot.weapon.range > 0 for slot in unit.weapon_slots.all())
    has_melee = any(slot.weapon.range == 0 for slot in unit.weapon_slots.all())
    caster_level = _caster_level(unit.special_rules)
    return {
        "mobility": _has_any_rule(unit, ("Scout", "Fast", "Flying", "Strider", "Ambush")),
        "screen": point_limit > 0 and points <= point_limit * 0.12,
        "ranged": has_ranged,
        "melee": has_melee,
        "anti_tough": _is_anti_tough(unit),
        "support": (
            is_hero(unit)
            or bool(caster_level)
            or _has_any_rule(unit, ("Fearless", "Stealth", "Regeneration"))
        ),
    }


def _is_anti_tough(unit: Unit) -> bool:
    if unit.tough >= 3:
        return True
    for slot in unit.weapon_slots.all():
        rules = slot.weapon.special_rules or {}
        if slot.weapon.ap >= 2:
            return True
        if any(_rule_enabled(rules, name) for name in ("Deadly", "Disintegrate", "Melee Slayer", "Ranged Slayer")):
            return True
    return _has_any_rule(unit, ("Melee Slayer", "Ranged Slayer"))


def _unit_ev(
    unit: Unit,
    model_count: int,
    combined_from_count: int,
    selected_upgrade_ids: list[int] | None = None,
    selected_upgrade_selections: list | None = None,
) -> dict[str, Any]:
    targets = default_target_profiles()
    target_totals = {target.id: 0.0 for target in targets}
    ranged_total = 0.0
    melee_total = 0.0
    weapons, extra_rules = _variant_weapons_and_rules(
        unit,
        selected_upgrade_ids or [],
        _upgrade_selection_dicts(selected_upgrade_selections),
    )
    for weapon in weapons:
        attacks = weapon.attacks * weapon_attack_count(weapon, model_count) * max(1, combined_from_count)
        special_rules = {**(unit.special_rules or {}), **extra_rules, **(weapon.special_rules or {})}
        for target in targets:
            ev = weapon_ev_profile(
                weapon=weapon,
                attacks=attacks,
                quality=unit.quality,
                defense=target.defense,
                special_rules=special_rules,
                target_special_rules=target.special_rules,
                combat_context=weapon_combat_context(weapon, model_count, target.tough, target.unit_size),
            ).sustained_ev
            target_totals[target.id] = round(target_totals[target.id] + ev, 6)
            if weapon.range > 0:
                ranged_total += ev
            else:
                melee_total += ev
    return {
        "targets": target_totals,
        "ranged": round(ranged_total, 6),
        "melee": round(melee_total, 6),
    }


def _upgrade_selection_dicts(selections: list | None) -> list[dict[str, int]]:
    result: list[dict[str, int]] = []
    for selection in selections or []:
        if hasattr(selection, "option"):
            option_id = getattr(selection, "option")
            quantity = getattr(selection, "quantity", 1)
        else:
            option_id = selection.get("option") if isinstance(selection, dict) else None
            quantity = selection.get("quantity", 1) if isinstance(selection, dict) else 1
        if option_id is not None:
            result.append({"option": int(option_id), "quantity": max(1, int(quantity))})
    return result


def _caster_level(special_rules: dict[str, Any] | None) -> str:
    if not special_rules:
        return ""
    for key, value in special_rules.items():
        normalized = key.strip().lower()
        if normalized == "caster" and value:
            return str(value) if value not in (True, False) else "1"
        if normalized == "caster group" and value:
            return "group"
    return ""


def _has_any_rule(unit: Unit, names: tuple[str, ...]) -> bool:
    return any(_rule_enabled(unit.special_rules or {}, name) for name in names)


def _rule_enabled(rules: dict[str, Any], name: str) -> bool:
    return any(key.lower() == name.lower() and bool(value) for key, value in rules.items())
