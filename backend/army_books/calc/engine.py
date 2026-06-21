from __future__ import annotations

from typing import Any

from army_books.calc.distribution import convolve, points, repeated_convolution
from army_books.calc.primitives import clamp_target, p_fail_defense
from army_books.calc.specials import has_rule, hit_modifier, int_rule


def calculate_ev(
    attacks: float,
    quality: float,
    defense: float,
    ap: float,
    special_rules: dict[str, Any] | None,
    modifiers: dict[str, Any] | None = None,
    *,
    target_special_rules: dict[str, Any] | None = None,
    combat_context: dict[str, Any] | None = None,
) -> float:
    distribution = _raw_distribution(
        attacks=attacks,
        quality=quality,
        defense=defense,
        ap=ap,
        special_rules=special_rules,
        modifiers=modifiers,
        target_special_rules=target_special_rules,
        combat_context=combat_context,
    )
    return sum(wounds * probability for wounds, probability in enumerate(distribution))


def calculate_distribution(
    attacks: float,
    quality: float,
    defense: float,
    ap: float,
    special_rules: dict[str, Any] | None,
    modifiers: dict[str, Any] | None = None,
    *,
    target_special_rules: dict[str, Any] | None = None,
    combat_context: dict[str, Any] | None = None,
) -> list[dict[str, float | int]]:
    return points(
        _raw_distribution(
            attacks=attacks,
            quality=quality,
            defense=defense,
            ap=ap,
            special_rules=special_rules,
            modifiers=modifiers,
            target_special_rules=target_special_rules,
            combat_context=combat_context,
        )
    )


def _raw_distribution(
    attacks: float,
    quality: float,
    defense: float,
    ap: float,
    special_rules: dict[str, Any] | None,
    modifiers: dict[str, Any] | None,
    target_special_rules: dict[str, Any] | None,
    combat_context: dict[str, Any] | None,
) -> list[float]:
    attack_count = _attack_count(attacks, special_rules)
    deadly = int_rule(special_rules, "Deadly", 1)
    per_attack = _single_attack_distribution(
        quality=quality,
        defense=defense,
        ap=ap,
        deadly=deadly,
        special_rules=special_rules,
        modifiers=modifiers,
        target_special_rules=target_special_rules,
        combat_context=combat_context,
    )
    base_distribution = repeated_convolution(per_attack, attack_count)
    impact_distribution = _impact_distribution(
        defense=defense,
        special_rules=special_rules,
        target_special_rules=target_special_rules,
        combat_context=combat_context,
    )
    return convolve(base_distribution, impact_distribution)


def _attack_count(attacks: float, special_rules: dict[str, Any] | None) -> int:
    if has_rule(special_rules, "Blast"):
        return int_rule(special_rules, "Blast", 1)
    return max(0, int(round(attacks)))


def _single_attack_distribution(
    quality: float,
    defense: float,
    ap: float,
    deadly: int,
    special_rules: dict[str, Any] | None,
    modifiers: dict[str, Any] | None,
    target_special_rules: dict[str, Any] | None,
    combat_context: dict[str, Any] | None,
) -> list[float]:
    if has_rule(special_rules, "Blast"):
        wound_probability = p_fail_defense(defense, ap) * _regeneration_multiplier(
            special_rules,
            target_special_rules,
            hit_roll=None,
        )
    else:
        return _single_attack_distribution_from_hit_rolls(
            quality=quality,
            defense=defense,
            ap=ap,
            deadly=deadly,
            special_rules=special_rules,
            modifiers=modifiers,
            target_special_rules=target_special_rules,
            combat_context=combat_context,
        )

    distribution = [0.0] * (deadly + 1)
    distribution[0] = 1 - wound_probability
    distribution[deadly] = wound_probability
    return distribution


def _single_attack_distribution_from_hit_rolls(
    quality: float,
    defense: float,
    ap: float,
    deadly: int,
    special_rules: dict[str, Any] | None,
    modifiers: dict[str, Any] | None,
    target_special_rules: dict[str, Any] | None,
    combat_context: dict[str, Any] | None,
) -> list[float]:
    attack_ap = ap + (1 if _thrust_applies(special_rules, combat_context) else 0)
    target = clamp_target(quality + _effective_hit_modifier(special_rules, modifiers, combat_context))
    normal_hit_rolls = [roll for roll in range(target, 7)]

    distribution = [1.0]
    for roll in normal_hit_rolls:
        roll_distribution = _successful_hit_distribution(
            defense=defense,
            ap=attack_ap,
            deadly=deadly,
            special_rules=special_rules,
            target_special_rules=target_special_rules,
            hit_roll=roll,
            extra_hit_count=_extra_hit_count(special_rules, combat_context, hit_roll=roll),
        )
        distribution = _add_weighted_distribution(
            distribution,
            roll_distribution,
            1 / 6,
        )

    return distribution


def _successful_hit_distribution(
    defense: float,
    ap: float,
    deadly: int,
    special_rules: dict[str, Any] | None,
    target_special_rules: dict[str, Any] | None,
    hit_roll: int,
    extra_hit_count: int,
) -> list[float]:
    original_distribution = _hit_wound_distribution(
        defense=defense,
        ap=ap,
        deadly=deadly,
        special_rules=special_rules,
        target_special_rules=target_special_rules,
        hit_roll=hit_roll,
    )
    extra_hit_distribution = _hit_wound_distribution(
        defense=defense,
        ap=ap,
        deadly=deadly,
        special_rules=special_rules,
        target_special_rules=target_special_rules,
        hit_roll=None,
    )
    return convolve(
        original_distribution,
        repeated_convolution(extra_hit_distribution, extra_hit_count),
    )


def _hit_wound_distribution(
    defense: float,
    ap: float,
    deadly: int,
    special_rules: dict[str, Any] | None,
    target_special_rules: dict[str, Any] | None,
    hit_roll: int | None,
) -> list[float]:
    if hit_roll == 6 and has_rule(special_rules, "Poison"):
        wound_probability = _regeneration_multiplier(
            special_rules,
            target_special_rules,
            hit_roll=hit_roll,
        )
    else:
        attack_ap = ap + 4 if hit_roll == 6 and has_rule(special_rules, "Rending") else ap
        wound_probability = p_fail_defense(defense, attack_ap) * _regeneration_multiplier(
            special_rules,
            target_special_rules,
            hit_roll=hit_roll,
        )

    distribution = [0.0] * (deadly + 1)
    distribution[0] = 1 - wound_probability
    distribution[deadly] = wound_probability
    return distribution


def _add_weighted_distribution(
    current: list[float],
    addition: list[float],
    weight: float,
) -> list[float]:
    length = max(len(current), len(addition))
    result = [0.0] * length
    for wounds, probability in enumerate(current):
        result[wounds] += probability
    for wounds, probability in enumerate(addition):
        result[wounds] += probability * weight
        result[0] -= probability * weight
    return result


def _impact_distribution(
    defense: float,
    special_rules: dict[str, Any] | None,
    target_special_rules: dict[str, Any] | None,
    combat_context: dict[str, Any] | None,
) -> list[float]:
    if not _context_bool(combat_context, "charging"):
        return [1.0]

    impact_dice = int_rule(special_rules, "Impact", 0) * max(
        1,
        _context_int(combat_context, "attacking_models", 1),
    )
    if impact_dice <= 0:
        return [1.0]

    wound_probability = (5 / 6) * p_fail_defense(defense, 0) * _regeneration_multiplier(
        None,
        target_special_rules,
        hit_roll=None,
    )
    return repeated_convolution([1 - wound_probability, wound_probability], impact_dice)


def _effective_hit_modifier(
    special_rules: dict[str, Any] | None,
    modifiers: dict[str, Any] | None,
    combat_context: dict[str, Any] | None,
) -> int:
    modifier = 0 if has_rule(special_rules, "Unstoppable") else hit_modifier(modifiers)
    if _thrust_applies(special_rules, combat_context):
        modifier -= 1
    return modifier


def _extra_hit_count(
    special_rules: dict[str, Any] | None,
    combat_context: dict[str, Any] | None,
    hit_roll: int,
) -> int:
    if hit_roll != 6:
        return 0
    count = 0
    if has_rule(special_rules, "Surge"):
        count += 1
    if has_rule(special_rules, "Sergeant"):
        count += 1
    if has_rule(special_rules, "Furious") and _context_bool(combat_context, "charging"):
        count += 1
    if (
        has_rule(special_rules, "Relentless")
        and _context_bool(combat_context, "target_over_9")
        and not _context_bool(combat_context, "is_melee")
    ):
        count += 1
    return count


def _thrust_applies(
    special_rules: dict[str, Any] | None,
    combat_context: dict[str, Any] | None,
) -> bool:
    return (
        has_rule(special_rules, "Thrust")
        and _context_bool(combat_context, "charging")
        and _context_bool(combat_context, "is_melee")
    )


def _context_bool(combat_context: dict[str, Any] | None, name: str) -> bool:
    return bool((combat_context or {}).get(name))


def _context_int(combat_context: dict[str, Any] | None, name: str, default: int) -> int:
    try:
        return int((combat_context or {}).get(name, default))
    except (TypeError, ValueError):
        return default


def _regeneration_multiplier(
    special_rules: dict[str, Any] | None,
    target_special_rules: dict[str, Any] | None,
    hit_roll: int | None,
) -> float:
    if not has_rule(target_special_rules, "Regeneration"):
        return 1.0
    if has_rule(special_rules, "Bane") or has_rule(special_rules, "Unstoppable"):
        return 1.0
    if has_rule(special_rules, "Rending"):
        return 1.0
    return 2 / 3
