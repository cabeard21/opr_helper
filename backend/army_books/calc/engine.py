from __future__ import annotations

from typing import Any

from army_books.calc.distribution import points, repeated_convolution
from army_books.calc.primitives import clamp_target, p_fail_defense
from army_books.calc.specials import has_rule, hit_modifier, int_rule


def calculate_ev(
    attacks: float,
    quality: float,
    defense: float,
    ap: float,
    special_rules: dict[str, Any] | None,
    modifiers: dict[str, Any] | None = None,
) -> float:
    distribution = _raw_distribution(
        attacks=attacks,
        quality=quality,
        defense=defense,
        ap=ap,
        special_rules=special_rules,
        modifiers=modifiers,
    )
    return sum(wounds * probability for wounds, probability in enumerate(distribution))


def calculate_distribution(
    attacks: float,
    quality: float,
    defense: float,
    ap: float,
    special_rules: dict[str, Any] | None,
    modifiers: dict[str, Any] | None = None,
) -> list[dict[str, float | int]]:
    return points(
        _raw_distribution(
            attacks=attacks,
            quality=quality,
            defense=defense,
            ap=ap,
            special_rules=special_rules,
            modifiers=modifiers,
        )
    )


def _raw_distribution(
    attacks: float,
    quality: float,
    defense: float,
    ap: float,
    special_rules: dict[str, Any] | None,
    modifiers: dict[str, Any] | None,
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
    )
    return repeated_convolution(per_attack, attack_count)


def _attack_count(attacks: float, special_rules: dict[str, Any] | None) -> int:
    if has_rule(special_rules, "Blast"):
        return int_rule(special_rules, "Blast", 1)
    attack_count = int(round(attacks))
    if has_rule(special_rules, "Furious"):
        attack_count += int(round(attacks / 6))
    return max(0, attack_count)


def _single_attack_distribution(
    quality: float,
    defense: float,
    ap: float,
    deadly: int,
    special_rules: dict[str, Any] | None,
    modifiers: dict[str, Any] | None,
) -> list[float]:
    if has_rule(special_rules, "Blast"):
        wound_probability = p_fail_defense(defense, ap)
    else:
        wound_probability = _wound_probability(
            quality=quality,
            defense=defense,
            ap=ap,
            special_rules=special_rules,
            modifiers=modifiers,
        )

    distribution = [0.0] * (deadly + 1)
    distribution[0] = 1 - wound_probability
    distribution[deadly] = wound_probability
    return distribution


def _wound_probability(
    quality: float,
    defense: float,
    ap: float,
    special_rules: dict[str, Any] | None,
    modifiers: dict[str, Any] | None,
) -> float:
    target = clamp_target(quality + hit_modifier(modifiers))
    normal_hit_rolls = [roll for roll in range(target, 7)]

    probability = 0.0
    for roll in normal_hit_rolls:
        if roll == 6 and has_rule(special_rules, "Poison"):
            probability += 1 / 6
            continue

        attack_ap = 6 if roll == 6 and has_rule(special_rules, "Rending") else ap
        probability += (1 / 6) * p_fail_defense(defense, attack_ap)

    return probability
