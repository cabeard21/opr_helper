from __future__ import annotations


def clamp_target(value: float) -> int:
    return max(2, min(6, int(value)))


def p_hit(quality: float, modifiers: float = 0) -> float:
    target = clamp_target(quality + modifiers)
    return (7 - target) / 6


def p_fail_defense(defense: float, ap: float) -> float:
    target = max(2, int(defense + ap))
    if target > 6:
        return 1.0
    return 1 - ((7 - target) / 6)


def expected_wounds(
    attacks: float,
    quality: float,
    defense: float,
    ap: float,
    deadly: int = 1,
    modifiers: float = 0,
) -> float:
    return attacks * p_hit(quality, modifiers) * p_fail_defense(defense, ap) * deadly
