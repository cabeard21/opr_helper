from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from army_books.calc.engine import calculate_distribution, calculate_ev
from lists.loadouts import EffectiveLoadout, effective_loadout, split_aura_rules
from lists.models import ArmyList, ListUnit
from lists.validation import list_unit_points


DEFAULT_TARGETS = (
    {"id": "infantry", "name": "Infantry", "defense": 5, "tough": 1, "unit_size": 3},
    {"id": "elite", "name": "Elite", "defense": 3, "tough": 3, "unit_size": 3},
    {
        "id": "monster",
        "name": "Monster",
        "defense": 2,
        "tough": 10,
        "unit_size": 1,
        "special_rules": {"Regeneration": True},
    },
)


@dataclass(frozen=True)
class TargetProfile:
    id: str
    name: str
    defense: int
    tough: int
    unit_size: int = 1
    special_rules: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, str | int | dict[str, Any]]:
        result: dict[str, str | int | dict[str, Any]] = {
            "id": self.id,
            "name": self.name,
            "defense": self.defense,
            "tough": self.tough,
            "unit_size": self.unit_size,
        }
        if self.special_rules:
            result["special_rules"] = self.special_rules
        return result


def default_target_profiles() -> list[TargetProfile]:
    return [
        TargetProfile(
            id=str(raw["id"]),
            name=str(raw["name"]),
            defense=int(raw["defense"]),
            tough=int(raw["tough"]),
            unit_size=int(raw.get("unit_size", _default_target_unit_size(str(raw["id"])))),
            special_rules=dict(raw.get("special_rules") or {}),
        )
        for raw in DEFAULT_TARGETS
    ]


def _default_target_unit_size(target_id: str) -> int:
    normalized = target_id.lower()
    if normalized in ("infantry", "elite"):
        return 3
    return 1


def validate_targets(raw_targets: Any) -> tuple[list[TargetProfile], dict[str, str] | None]:
    if raw_targets in (None, []):
        return default_target_profiles(), None
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
            unit_size = int(raw_target.get("unit_size", _default_target_unit_size(target_id)))
        except (TypeError, ValueError):
            return [], {f"targets.{index}": "Defense, tough, and unit_size must be integers."}
        special_rules = raw_target.get("special_rules") or {}
        if not isinstance(special_rules, dict):
            return [], {f"targets.{index}.special_rules": "Special rules must be an object."}

        if not target_id:
            return [], {f"targets.{index}.id": "Target id is required."}
        if not name:
            return [], {f"targets.{index}.name": "Target name is required."}
        if defense < 2 or defense > 6:
            return [], {f"targets.{index}.defense": "Defense must be between 2 and 6."}
        if tough < 1:
            return [], {f"targets.{index}.tough": "Tough must be at least 1."}
        if unit_size < 1:
            return [], {f"targets.{index}.unit_size": "Unit size must be at least 1."}

        targets.append(TargetProfile(target_id, name, defense, tough, unit_size, special_rules))

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

    effective_wounds = total_effective_wounds(entry)

    return {
        "list_unit_id": entry.id,
        "unit_id": entry.unit_id,
        "unit_name": entry.unit.name,
        "model_count": entry.model_count,
        "points": points,
        "effective_wounds": effective_wounds,
        "effective_wounds_per_100_points": effective_wounds_per_100_points(effective_wounds, points),
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


def total_effective_wounds(entry: ListUnit) -> float:
    total_wounds = entry.model_count * max(1, entry.unit.tough) * max(1, entry.combined_from_count)
    failed_save_rate = max(1, entry.unit.defense - 1) / 6
    effective_wounds = total_wounds / failed_save_rate * defensive_wound_multiplier(entry.unit.special_rules)
    return round(effective_wounds, 6)


def effective_wounds_per_100_points(effective_wounds: float, points: int) -> float:
    if points <= 0:
        return 0
    return round((effective_wounds / points) * 100, 6)


def defensive_wound_multiplier(special_rules: dict[str, Any] | None) -> float:
    if not special_rules:
        return 1.0
    for key, value in special_rules.items():
        if key.lower() == "regeneration" and bool(value):
            return 1.5
    return 1.0


def weapon_combat_context(
    weapon: Any,
    model_count: int,
    target_tough: int | None = None,
    target_unit_size: int | None = None,
) -> dict[str, Any]:
    is_melee = weapon.range == 0
    context = {
        "charging": is_melee,
        "is_melee": is_melee,
        "target_over_9": False,
        "attacking_models": model_count,
    }
    if target_tough is not None:
        context["target_tough"] = target_tough
    if target_unit_size is not None:
        context["target_unit_size"] = target_unit_size
    return context


def _target_result(
    target: TargetProfile,
    entry: ListUnit,
    weapons: list[Any],
    extra_rules: dict[str, Any],
    points: int,
) -> dict[str, float | str]:
    ev = 0.0
    ranged_ev = 0.0
    melee_ev = 0.0
    p_kill_model = 0.0
    for weapon in weapons:
        attacks = weapon.attacks * entry.model_count
        special_rules = {**extra_rules, **weapon.special_rules}
        combat_context = weapon_combat_context(weapon, entry.model_count, target.tough, target.unit_size)
        weapon_ev = calculate_ev(
            attacks,
            entry.unit.quality,
            target.defense,
            weapon.ap,
            special_rules,
            target_special_rules=target.special_rules,
            combat_context=combat_context,
        )
        ev += weapon_ev
        if weapon.range > 0:
            ranged_ev += weapon_ev
        else:
            melee_ev += weapon_ev
        distribution = calculate_distribution(
            attacks,
            entry.unit.quality,
            target.defense,
            weapon.ap,
            special_rules,
            target_special_rules=target.special_rules,
            combat_context=combat_context,
        )
        p_kill_model += sum(
            point["probability"]
            for point in distribution
            if int(point["wounds"]) >= target.tough
        )

    return {
        "target_id": target.id,
        "ev": round(ev, 6),
        "ranged_ev": round(ranged_ev, 6),
        "melee_ev": round(melee_ev, 6),
        "activation_ev": round(max(ranged_ev, melee_ev), 6),
        "wounds_per_100_points": round((ev / points) * 100, 6) if points > 0 else 0,
        "ranged_wounds_per_100_points": round((ranged_ev / points) * 100, 6) if points > 0 else 0,
        "melee_wounds_per_100_points": round((melee_ev / points) * 100, 6) if points > 0 else 0,
        "activation_wounds_per_100_points": round((max(ranged_ev, melee_ev) / points) * 100, 6)
        if points > 0
        else 0,
        "p_kill_model": round(min(1, p_kill_model), 6),
    }


def _total_for_target(
    target: TargetProfile,
    unit_results: list[dict[str, Any] | None],
) -> dict[str, float | str]:
    ev = 0.0
    ranged_ev = 0.0
    melee_ev = 0.0
    activation_ev = 0.0
    points = 0
    for unit_result in unit_results:
        if unit_result is None:
            continue
        points += int(unit_result["points"])
        target_result = next(
            result for result in unit_result["target_results"] if result["target_id"] == target.id
        )
        ev += float(target_result["ev"])
        ranged_ev += float(target_result["ranged_ev"])
        melee_ev += float(target_result["melee_ev"])
        activation_ev += float(target_result["activation_ev"])

    return {
        "target_id": target.id,
        "ev": round(ev, 6),
        "ranged_ev": round(ranged_ev, 6),
        "melee_ev": round(melee_ev, 6),
        "activation_ev": round(activation_ev, 6),
        "wounds_per_100_points": round((ev / points) * 100, 6) if points > 0 else 0,
        "ranged_wounds_per_100_points": round((ranged_ev / points) * 100, 6) if points > 0 else 0,
        "melee_wounds_per_100_points": round((melee_ev / points) * 100, 6) if points > 0 else 0,
        "activation_wounds_per_100_points": round((activation_ev / points) * 100, 6) if points > 0 else 0,
    }
