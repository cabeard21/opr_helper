"""Parsers for Army Forge / OPR army-book payloads."""

from __future__ import annotations

import re
from typing import Any


RULE_PATTERN = re.compile(r"^\s*(?P<name>[^()]+?)(?:\((?P<value>[^)]+)\))?\s*$")
MISSING = object()


def parse_stat_target(value: Any) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if str(value).strip().lower() == "melee":
        return 0

    match = re.search(r"\d+", str(value))
    if not match:
        raise ValueError(f"Could not parse stat target from {value!r}")
    return int(match.group(0))


def parse_attacks_value(value: Any) -> float:
    if isinstance(value, int | float):
        return float(value)

    normalized = str(value).strip().lower()
    if normalized.startswith("a"):
        normalized = normalized[1:]

    dice_match = re.fullmatch(r"(?:(\d+))?d(\d+)", normalized)
    if dice_match:
        count = int(dice_match.group(1) or 1)
        sides = int(dice_match.group(2))
        return count * (sides + 1) / 2

    match = re.search(r"\d+(?:\.\d+)?", normalized)
    if not match:
        raise ValueError(f"Could not parse attacks from {value!r}")
    return float(match.group(0))


def parse_ap(value: Any) -> int:
    if value is None or value == "":
        return 0
    return parse_stat_target(value)


def parse_special_rules(
    raw_rules: Any,
    exclude_names: set[str] | None = None,
) -> dict[str, Any]:
    if raw_rules is None:
        return {}

    excluded = exclude_names or set()
    if isinstance(raw_rules, dict):
        raw_iterable = raw_rules.items()
    else:
        raw_iterable = raw_rules

    rules: dict[str, Any] = {}
    for raw_rule in raw_iterable:
        if isinstance(raw_rule, tuple):
            name, value = raw_rule
            rules[str(name)] = value
            continue

        if isinstance(raw_rule, dict):
            name = raw_rule.get("name") or raw_rule.get("label") or raw_rule.get("rule")
            value = raw_rule.get("value")
            if value is None:
                value = raw_rule.get("rating")
            if value is None:
                value = True
        else:
            match = RULE_PATTERN.match(str(raw_rule))
            if not match:
                continue
            name = match.group("name").strip()
            value = match.group("value") or True

        if isinstance(value, str) and value.isdigit():
            value = int(value)
        if name and str(name).strip() not in excluded:
            rules[str(name).strip()] = value

    return rules


def parse_unit(raw: dict[str, Any]) -> dict[str, Any]:
    special_rules = parse_special_rules(_first(raw, "special_rules", "rules", default=[]))
    return {
        "source_uid": _first(raw, "source_uid", "uid", "id"),
        "name": raw["name"],
        "quality": parse_stat_target(_first(raw, "quality", "qu", "qualityStat")),
        "defense": parse_stat_target(_first(raw, "defense", "de", "defenseStat")),
        "tough": _parse_unit_tough(raw, special_rules),
        "points": int(_first(raw, "points", "cost")),
        "special_rules": special_rules,
    }


def parse_weapon(raw: dict[str, Any]) -> dict[str, Any]:
    raw_attacks = _first(raw, "attacks_string", "attacks", "a")
    attacks_string = _attacks_string(raw_attacks)
    raw_rules = _first(raw, "special_rules", "specialRules", "rules", default=[])
    return {
        "source_uid": _first(raw, "source_uid", "uid", "id"),
        "name": raw["name"],
        "range": parse_stat_target(_first(raw, "range", "range_", default=0)),
        "attacks": parse_attacks_value(attacks_string),
        "attacks_string": attacks_string,
        "ap": _parse_weapon_ap(raw, raw_rules),
        "special_rules": parse_special_rules(raw_rules, exclude_names={"AP"}),
    }


def _parse_unit_tough(raw: dict[str, Any], special_rules: dict[str, Any]) -> int:
    if "tough" in raw and raw["tough"] is not None:
        return parse_stat_target(raw["tough"])
    if "toughness" in raw and raw["toughness"] is not None:
        return parse_stat_target(raw["toughness"])
    tough = special_rules.get("Tough", 1)
    return parse_stat_target(tough)


def _parse_weapon_ap(raw: dict[str, Any], raw_rules: Any) -> int:
    explicit_ap = _first(raw, "ap", "armorPiercing", default=None)
    if explicit_ap is not None:
        return parse_ap(explicit_ap)
    special_rules = parse_special_rules(raw_rules)
    return parse_ap(special_rules.get("AP", 0))


def _attacks_string(value: Any) -> str:
    if isinstance(value, int):
        return f"A{value}"
    if isinstance(value, float):
        if value.is_integer():
            return f"A{int(value)}"
        return f"A{value}"
    return str(value)


def _first(raw: dict[str, Any], *keys: str, default: Any = MISSING) -> Any:
    for key in keys:
        if key in raw and raw[key] is not None:
            return raw[key]
    if default is not MISSING:
        return default
    raise KeyError(f"Missing required field; tried {', '.join(keys)}")
