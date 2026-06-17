from __future__ import annotations

from typing import Any


def rule_value(rules: dict[str, Any] | None, name: str, default: int | bool = 1) -> Any:
    if not rules:
        return default
    for key, value in rules.items():
        if key.lower() == name.lower():
            if value is True:
                return default
            return value
    return default


def has_rule(rules: dict[str, Any] | None, name: str) -> bool:
    if not rules:
        return False
    return any(key.lower() == name.lower() for key in rules)


def int_rule(rules: dict[str, Any] | None, name: str, default: int = 1) -> int:
    value = rule_value(rules, name, default)
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def hit_modifier(modifiers: dict[str, Any] | None) -> int:
    if not modifiers:
        return 0
    penalty = 0
    if modifiers.get("stealth"):
        penalty += 1
    if modifiers.get("indirect"):
        penalty += 1
    return penalty
