from __future__ import annotations


def weapon_matches_upgrade_target(weapon_name: str, targets: list[str]) -> bool:
    normalized_weapon = _normalize_weapon_name(weapon_name)
    singular_weapon = _singularize_final_word(normalized_weapon)
    for target in targets:
        normalized_target = _normalize_weapon_name(target)
        if normalized_weapon == normalized_target:
            return True
        if singular_weapon == _singularize_final_word(normalized_target):
            return True
    return False


def _normalize_weapon_name(value: str) -> str:
    return " ".join(str(value).strip().lower().split())


def _singularize_final_word(value: str) -> str:
    words = value.split()
    if not words:
        return value
    last = words[-1]
    if len(last) > 1 and last.endswith("s") and not last.endswith("ss"):
        words[-1] = last[:-1]
    return " ".join(words)
