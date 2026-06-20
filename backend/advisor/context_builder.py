from __future__ import annotations

from pathlib import Path

from django.conf import settings

from advisor.unit_scorer import UnitProfile


def build_unit_table(profiles: list[UnitProfile]) -> str:
    lines = [
        "| ID | Name | Pts | Q | Def | T | AP | EV_inf | EV_eli | EV_mon | W100 | Scout | Fast | Fly | Fear | Rng | Upgrades |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for profile in profiles:
        lines.append(
            "| {id} | {name} | {points} | {quality}+ | {defense}+ | {tough} | {ap} | "
            "{ev_inf:.2f} | {ev_eli:.2f} | {ev_mon:.2f} | {w100:.2f} | "
            "{scout} | {fast} | {flying} | {fearless} | {ranged} | {upgrades} |".format(
                id=profile.unit_id,
                name=_compact_name(profile.name),
                points=profile.points,
                quality=profile.quality,
                defense=profile.defense,
                tough=profile.tough,
                ap=profile.max_ap,
                ev_inf=profile.ev_infantry,
                ev_eli=profile.ev_elite,
                ev_mon=profile.ev_monster,
                w100=profile.wounds_per_100pts_infantry,
                scout=_yes_no(profile.has_scout),
                fast=_yes_no(profile.has_fast),
                flying=_yes_no(profile.has_flying),
                fearless=_yes_no(profile.has_fearless),
                ranged=_yes_no(profile.is_ranged),
                upgrades=_compact_upgrades(profile.upgrade_options),
            )
        )
    return "\n".join(lines)


def build_system_prompt(game: str = "AoF") -> str:
    prompt = (
        f"You are an OPR {game} army list advisor. Return only the requested structured suggestion. "
        "Use the supplied legal package table as the source of truth for package ids, points, roles, and legality. "
        "Select package ids; do not invent units, model counts, upgrade ids, or package ids. "
        "Use the zero-based returned unit index when setting join_to_unit_index for an embedded hero. "
        "Aura abilities affect only the package that has the aura and the unit it is embedded in; "
        "if selecting an aura hero to support another unit, embed it with that host. "
        "Spend as close to the point limit as possible without exceeding it. "
        "Prefer lists with enough activation count: about 7 activations at 2000 points and at least 5 when possible. "
        "Prioritize mobility in AoF, especially Scout, Fast, Flying, Strider, and transports. "
        "Respect AP and Deadly needs; include credible AP threats for tough targets. "
        "Fearless and morale support matter for contesting objectives. "
        "Never select packages marked over the 35% cap. "
        "Aim for units that can pressure roughly six wounds in an activation when the strategy requires killing. "
        "Cover composition roles when available: core scoring, mobility/objective play, anti-tough/AP, "
        "screens/cheap activations, ranged pressure, melee threats, and hero/support. "
        "Name a clear archetype and playstyle, and include warnings for missing mobility, low activation count, "
        "weak anti-tough damage, or morale vulnerability."
    )
    reference_material = build_reference_material()
    if reference_material:
        prompt = f"{prompt}\n\nAdditional local reference material:\n{reference_material}"
    return prompt


def build_reference_material() -> str:
    root = Path(settings.ADVISOR_REFERENCE_DIR)
    max_chars = int(settings.ADVISOR_REFERENCE_MAX_CHARS)
    if max_chars <= 0 or not root.exists() or not root.is_dir():
        return ""

    chunks: list[str] = []
    remaining = max_chars
    for path in sorted(root.glob("*.md")):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if not text:
            continue
        chunk = f"## {path.name}\n{text}"
        if len(chunk) > remaining:
            chunk = chunk[:remaining].rstrip()
        chunks.append(chunk)
        remaining -= len(chunk)
        if remaining <= 0:
            break
    return "\n\n".join(chunks)


def build_user_context(
    *,
    faction_name: str,
    point_limit: int,
    unit_table: str | None = None,
    user_prompt: str,
    package_table: str | None = None,
    force_org: str = "",
    correction_feedback: str = "",
) -> str:
    table = package_table if package_table is not None else unit_table or ""
    correction = f"\n\nCorrection feedback from validation:\n{correction_feedback.strip()}" if correction_feedback else ""
    return (
        f"Faction: {faction_name}\n"
        f"Point limit: {point_limit}\n"
        f"{force_org}\n"
        f"User goal: {user_prompt.strip()}\n\n"
        "Available legal packages:\n"
        f"{table}"
        f"{correction}"
    )


def _compact_name(name: str) -> str:
    return name.replace("|", "/")[:40]


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def _compact_upgrades(upgrades: tuple[str, ...]) -> str:
    if not upgrades:
        return "-"
    return "; ".join(upgrade.replace("|", "/")[:80] for upgrade in upgrades)
