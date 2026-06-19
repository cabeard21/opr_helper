from __future__ import annotations

from advisor.unit_scorer import UnitProfile


def build_unit_table(profiles: list[UnitProfile]) -> str:
    lines = [
        "| ID | Name | Pts | Q | Def | T | AP | EV_inf | EV_eli | EV_mon | W100 | Scout | Fast | Fear | Rng |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for profile in profiles:
        lines.append(
            "| {id} | {name} | {points} | {quality}+ | {defense}+ | {tough} | {ap} | "
            "{ev_inf:.2f} | {ev_eli:.2f} | {ev_mon:.2f} | {w100:.2f} | "
            "{scout} | {fast} | {fearless} | {ranged} |".format(
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
                fearless=_yes_no(profile.has_fearless),
                ranged=_yes_no(profile.is_ranged),
            )
        )
    return "\n".join(lines)


def build_system_prompt(game: str = "AoF") -> str:
    return (
        f"You are an OPR {game} army list advisor. Return only the requested structured suggestion. "
        "Use the supplied unit table as the source of truth for unit ids, points, and computed damage. "
        "Prefer lists with enough activation count: about 7 activations at 2000 points and at least 5 when possible. "
        "Prioritize mobility in AoF, especially Scout, Fast, Flying, Strider, and transports. "
        "Respect AP and Deadly needs; include credible AP threats for tough targets. "
        "Fearless and morale support matter for contesting objectives. "
        "Try to avoid spending more than 25% of points on a single unit unless it is durable and central. "
        "Aim for units that can pressure roughly six wounds in an activation when the strategy requires killing. "
        "Balance core damage, objective play, throwaway activations, ranged pressure, and melee threats. "
        "Name a clear archetype and playstyle, and include warnings for missing mobility, low activation count, "
        "weak anti-tough damage, or morale vulnerability."
    )


def build_user_context(
    *,
    faction_name: str,
    point_limit: int,
    unit_table: str,
    user_prompt: str,
) -> str:
    return (
        f"Faction: {faction_name}\n"
        f"Point limit: {point_limit}\n"
        f"User goal: {user_prompt.strip()}\n\n"
        "Available units:\n"
        f"{unit_table}"
    )


def _compact_name(name: str) -> str:
    return name.replace("|", "/")[:40]


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"
