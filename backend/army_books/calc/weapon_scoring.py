from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from army_books.calc.engine import calculate_ev
from army_books.calc.specials import has_rule


LIMITED_SUSTAINED_ROUNDS = 4


@dataclass(frozen=True)
class WeaponEvProfile:
    sustained_ev: float
    burst_ev: float
    is_limited: bool


def weapon_ev_profile(
    *,
    weapon: Any,
    attacks: float,
    quality: float,
    defense: float,
    special_rules: dict[str, Any] | None,
    target_special_rules: dict[str, Any] | None = None,
    combat_context: dict[str, Any] | None = None,
) -> WeaponEvProfile:
    burst_ev = calculate_ev(
        attacks,
        quality,
        defense,
        weapon.ap,
        special_rules,
        target_special_rules=target_special_rules,
        combat_context=combat_context,
    )
    is_limited = weapon_has_limited_rule(weapon)
    sustained_ev = burst_ev / LIMITED_SUSTAINED_ROUNDS if is_limited else burst_ev
    return WeaponEvProfile(
        sustained_ev=sustained_ev,
        burst_ev=burst_ev,
        is_limited=is_limited,
    )


def weapon_has_limited_rule(weapon: Any) -> bool:
    return has_rule(getattr(weapon, "special_rules", None), "Limited")
