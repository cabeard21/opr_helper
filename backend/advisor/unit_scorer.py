from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from army_books.calc.engine import calculate_distribution, calculate_ev
from army_books.models import Unit, UnitWeaponSlot
from lists.analysis import DEFAULT_TARGETS, TargetProfile
from lists.validation import unit_selection_points


@dataclass(frozen=True)
class UnitProfile:
    unit_id: int
    name: str
    points: int
    quality: int
    defense: int
    tough: int
    default_models: int
    default_weapon_slot_id: int | None
    default_weapon_name: str | None
    max_ap: int
    ev_infantry: float
    ev_elite: float
    ev_monster: float
    wounds_per_100pts_infantry: float
    p_kill_infantry: float
    effective_health: int
    resilience_score: float
    has_scout: bool
    has_fast: bool
    has_flying: bool
    has_fearless: bool
    has_stealth: bool
    has_regeneration: bool
    is_ranged: bool
    upgrade_options: tuple[str, ...]


def score_faction_units(faction_id: int) -> list[UnitProfile]:
    units = (
        Unit.objects.filter(faction_id=faction_id)
        .prefetch_related("weapon_slots__weapon", "upgrade_sections__options")
        .order_by("name", "id")
    )
    targets = [
        TargetProfile(
            id=str(raw["id"]),
            name=str(raw["name"]),
            defense=int(raw["defense"]),
            tough=int(raw["tough"]),
        )
        for raw in DEFAULT_TARGETS
    ]
    return [_score_unit(unit, targets) for unit in units]


def _score_unit(unit: Unit, targets: list[TargetProfile]) -> UnitProfile:
    slots = list(unit.weapon_slots.all())
    default_slots = _default_slots(slots)
    default_slot = default_slots[0] if default_slots else None
    target_results = {
        target.id: _target_score(unit, default_slots, target)
        for target in targets
    }
    infantry_score = target_results["infantry"]
    max_ap = max((slot.weapon.ap for slot in slots if slot.is_default), default=0)
    effective_health = unit.tough * unit.default_models
    resilience_denominator = 6 - unit.defense + 1

    return UnitProfile(
        unit_id=unit.id,
        name=unit.name,
        points=unit.points,
        quality=unit.quality,
        defense=unit.defense,
        tough=unit.tough,
        default_models=unit.default_models,
        default_weapon_slot_id=default_slot.id if default_slot else None,
        default_weapon_name=default_slot.weapon.name if default_slot else None,
        max_ap=max_ap,
        ev_infantry=target_results["infantry"]["ev"],
        ev_elite=target_results["elite"]["ev"],
        ev_monster=target_results["monster"]["ev"],
        wounds_per_100pts_infantry=infantry_score["wounds_per_100_points"],
        p_kill_infantry=infantry_score["p_kill_model"],
        effective_health=effective_health,
        resilience_score=round(effective_health / resilience_denominator, 6)
        if resilience_denominator > 0
        else 0,
        has_scout=_has_rule(unit.special_rules, "Scout"),
        has_fast=_has_rule(unit.special_rules, "Fast"),
        has_flying=_has_rule(unit.special_rules, "Flying"),
        has_fearless=_has_rule(unit.special_rules, "Fearless"),
        has_stealth=_has_rule(unit.special_rules, "Stealth"),
        has_regeneration=_has_rule(unit.special_rules, "Regeneration"),
        is_ranged=bool(default_slot and default_slot.weapon.range > 0),
        upgrade_options=_compact_upgrade_options(unit),
    )


def _default_slot(slots: list[UnitWeaponSlot]) -> UnitWeaponSlot | None:
    return next((slot for slot in slots if slot.is_default), None) or (slots[0] if slots else None)


def _default_slots(slots: list[UnitWeaponSlot]) -> list[UnitWeaponSlot]:
    defaults = [slot for slot in slots if slot.is_default]
    if defaults:
        return defaults
    fallback = _default_slot(slots)
    return [fallback] if fallback else []


def _target_score(
    unit: Unit,
    slots: list[UnitWeaponSlot],
    target: TargetProfile,
) -> dict[str, float]:
    if not slots:
        return {"ev": 0, "wounds_per_100_points": 0, "p_kill_model": 0}

    points = unit_selection_points(unit=unit, model_count=unit.default_models)
    ev = 0.0
    p_kill_model = 0.0
    for slot in slots:
        weapon = slot.weapon
        attacks = weapon.attacks * unit.default_models
        special_rules = {**unit.special_rules, **weapon.special_rules}
        ev += calculate_ev(attacks, unit.quality, target.defense, weapon.ap, special_rules)
        distribution = calculate_distribution(
            attacks,
            unit.quality,
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
        "ev": round(ev, 6),
        "wounds_per_100_points": round((ev / points) * 100, 6) if points > 0 else 0,
        "p_kill_model": round(min(1, p_kill_model), 6),
    }


def _has_rule(special_rules: dict[str, Any], name: str) -> bool:
    normalized = name.lower()
    for key, value in special_rules.items():
        if key.lower() == normalized:
            return bool(value)
    return False


def _compact_upgrade_options(unit: Unit) -> tuple[str, ...]:
    options: list[str] = []
    for section in unit.upgrade_sections.all():
        targets = ", ".join(str(target) for target in section.targets[:2])
        target_summary = f" replaces {targets}" if targets else ""
        for option in section.options.all():
            options.append(f"{option.id}: {option.label} (+{option.cost}){target_summary}")
    return tuple(options[:4])
