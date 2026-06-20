from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from army_books.calc.engine import calculate_distribution, calculate_ev
from lists.loadouts import EffectiveLoadout, effective_loadout, split_aura_rules
from lists.models import ArmyList, ListUnit
from lists.validation import list_unit_points


DEFAULT_TARGETS = (
    {"id": "infantry", "name": "Infantry", "defense": 5, "tough": 1},
    {"id": "elite", "name": "Elite", "defense": 3, "tough": 3},
    {"id": "monster", "name": "Monster", "defense": 2, "tough": 10},
)


@dataclass(frozen=True)
class TargetProfile:
    id: str
    name: str
    defense: int
    tough: int

    def as_dict(self) -> dict[str, str | int]:
        return {
            "id": self.id,
            "name": self.name,
            "defense": self.defense,
            "tough": self.tough,
        }


def validate_targets(raw_targets: Any) -> tuple[list[TargetProfile], dict[str, str] | None]:
    if raw_targets in (None, []):
        raw_targets = DEFAULT_TARGETS
    if not isinstance(raw_targets, list | tuple):
        return [], {"targets": "Targets must be a list."}

    targets: list[TargetProfile] = []
    for index, raw_target in enumerate(raw_targets):
        if not isinstance(raw_target, dict):
            return [], {f"targets.{index}": "Target must be an object."}

        target_id = str(raw_target.get("id") or "").strip()
        name = str(raw_target.get("name") or "").strip()
        try:
            defense = int(raw_target.get("defense"))
            tough = int(raw_target.get("tough"))
        except (TypeError, ValueError):
            return [], {f"targets.{index}": "Defense and tough must be integers."}

        if not target_id:
            return [], {f"targets.{index}.id": "Target id is required."}
        if not name:
            return [], {f"targets.{index}.name": "Target name is required."}
        if defense < 2 or defense > 6:
            return [], {f"targets.{index}.defense": "Defense must be between 2 and 6."}
        if tough < 1:
            return [], {f"targets.{index}.tough": "Tough must be at least 1."}

        targets.append(TargetProfile(target_id, name, defense, tough))

    return targets, None


def analyze_army_list(army_list: ArmyList, targets: list[TargetProfile]) -> dict[str, Any]:
    entries = list(army_list.units.all())
    loadouts = {entry.id: effective_loadout(entry) for entry in entries}
    child_aura_rules = _embedded_aura_rules(entries, loadouts)
    unit_results = [
        _analyze_list_unit(
            entry=entry,
            targets=targets,
            loadout=loadouts[entry.id],
            embedded_aura_rules=child_aura_rules.get(entry.id, {}),
        )
        for entry in entries
    ]
    totals = [_total_for_target(target, unit_results) for target in targets]

    return {
        "list_id": army_list.id,
        "targets": [target.as_dict() for target in targets],
        "units": [result for result in unit_results if result is not None],
        "totals": totals,
    }


def _analyze_list_unit(
    entry: ListUnit,
    targets: list[TargetProfile],
    loadout: EffectiveLoadout,
    embedded_aura_rules: dict[str, Any],
) -> dict[str, Any] | None:
    if not loadout.weapons:
        return None

    points = list_unit_points(entry)
    unit_rules, unit_aura_rules = split_aura_rules(entry.unit.special_rules)
    applicable_rules = {
        **unit_rules,
        **loadout.extra_rules,
        **unit_aura_rules,
        **loadout.aura_rules,
        **embedded_aura_rules,
    }
    target_results = [
        _target_result(
            target=target,
            entry=entry,
            weapons=loadout.weapons,
            extra_rules=applicable_rules,
            points=points,
        )
        for target in targets
    ]

    return {
        "list_unit_id": entry.id,
        "unit_id": entry.unit_id,
        "unit_name": entry.unit.name,
        "model_count": entry.model_count,
        "points": points,
        "effective_wounds_per_100_points": effective_wounds_per_100_points(entry, points),
        "weapon_id": loadout.weapons[0].id,
        "weapon_name": loadout.summary,
        "weapon_names": loadout.weapon_names,
        "target_results": target_results,
    }


def _embedded_aura_rules(
    entries: list[ListUnit],
    loadouts: dict[int, EffectiveLoadout],
) -> dict[int, dict[str, Any]]:
    rules_by_parent: dict[int, dict[str, Any]] = {}
    for entry in entries:
        if entry.parent_entry_id is None:
            continue
        _normal_rules, unit_aura_rules = split_aura_rules(entry.unit.special_rules)
        loadout = loadouts[entry.id]
        rules_by_parent[entry.parent_entry_id] = {
            **rules_by_parent.get(entry.parent_entry_id, {}),
            **unit_aura_rules,
            **loadout.aura_rules,
        }
    return rules_by_parent


def effective_wounds_per_100_points(entry: ListUnit, points: int) -> float:
    if points <= 0:
        return 0
    total_wounds = entry.model_count * max(1, entry.unit.tough) * max(1, entry.combined_from_count)
    failed_save_rate = max(1, entry.unit.defense - 1) / 6
    effective_wounds = total_wounds / failed_save_rate
    return round((effective_wounds / points) * 100, 6)


def _target_result(
    target: TargetProfile,
    entry: ListUnit,
    weapons: list[Any],
    extra_rules: dict[str, Any],
    points: int,
) -> dict[str, float | str]:
    ev = 0.0
    p_kill_model = 0.0
    for weapon in weapons:
        attacks = weapon.attacks * entry.model_count
        special_rules = {**extra_rules, **weapon.special_rules}
        ev += calculate_ev(attacks, entry.unit.quality, target.defense, weapon.ap, special_rules)
        distribution = calculate_distribution(
            attacks,
            entry.unit.quality,
            target.defense,
            weapon.ap,
            special_rules,
        )
        p_kill_model += sum(
            point["probability"]
            for point in distribution
            if int(point["wounds"]) >= target.tough
        )

    return {
        "target_id": target.id,
        "ev": round(ev, 6),
        "wounds_per_100_points": round((ev / points) * 100, 6) if points > 0 else 0,
        "p_kill_model": round(min(1, p_kill_model), 6),
    }


def _total_for_target(
    target: TargetProfile,
    unit_results: list[dict[str, Any] | None],
) -> dict[str, float | str]:
    ev = 0.0
    points = 0
    for unit_result in unit_results:
        if unit_result is None:
            continue
        points += int(unit_result["points"])
        target_result = next(
            result for result in unit_result["target_results"] if result["target_id"] == target.id
        )
        ev += float(target_result["ev"])

    return {
        "target_id": target.id,
        "ev": round(ev, 6),
        "wounds_per_100_points": round((ev / points) * 100, 6) if points > 0 else 0,
    }
