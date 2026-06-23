from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from army_books.calc.engine import calculate_ev
from army_books.models import FactionSpell, Unit, UnitUpgradeOption
from lists.analysis import TargetProfile, default_target_profiles, weapon_combat_context
from lists.loadouts import aura_rule_names_from_gains, split_aura_rules
from lists.validation import (
    effective_max_models,
    force_org_copy_limit,
    force_org_group_limit,
    force_org_group_point_cap,
    force_org_hero_limit,
    is_hero,
    unit_selection_points,
)


@dataclass(frozen=True)
class AdvisorPackage:
    package_id: str
    unit_id: int
    unit_name: str
    model_count: int
    combined_from_count: int
    selected_upgrade_ids: list[int]
    upgrade_labels: list[str]
    points: int
    quality: int
    defense: int
    tough: int
    max_ap: int
    ev_infantry: float
    ev_elite: float
    ev_monster: float
    wounds_per_100pts_infantry: float
    role_tags: tuple[str, ...]
    aura_rules: tuple[str, ...]
    caster_level: str
    spell_role_tags: tuple[str, ...]
    can_embed_as_hero: bool
    can_host_embedded_hero: bool
    exceeds_group_cap: bool


def build_advisor_packages(faction_id: int, point_limit: int) -> list[AdvisorPackage]:
    units = (
        Unit.objects.filter(faction_id=faction_id)
        .prefetch_related("weapon_slots__weapon", "upgrade_sections__options__weapons")
        .order_by("name", "id")
    )
    packages: list[AdvisorPackage] = []
    spell_role_tags = _faction_spell_role_tags(faction_id)
    for unit in units:
        packages.extend(
            _packages_for_unit_variant(
                unit=unit,
                point_limit=point_limit,
                spell_role_tags=spell_role_tags,
            )
        )
        for option in _upgrade_options(unit):
            if option.cost <= 0:
                continue
            packages.extend(
                _packages_for_unit_variant(
                    unit=unit,
                    point_limit=point_limit,
                    spell_role_tags=spell_role_tags,
                    selected_upgrade_ids=[option.id],
                    upgrade_labels=[option.label],
                    package_suffix=f"o{option.id}",
                    upgrade_cost=option.cost,
                )
            )
    return packages


def build_package_table(packages: list[AdvisorPackage]) -> str:
    lines = [
        "| Package | Unit | Pts | Models | Combined | Q | Def | T | AP | EV_inf | EV_eli | EV_mon | W100 | Upgrades | Roles | Caster | Spell Roles | Aura | Embed | Legal |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for package in packages:
        lines.append(
            "| {package_id} | {unit} | {points} | {models} | {combined} | {quality}+ | {defense}+ | "
            "{tough} | {ap} | {ev_inf:.2f} | {ev_eli:.2f} | {ev_mon:.2f} | {w100:.2f} | "
            "{upgrades} | {roles} | {caster} | {spell_roles} | {aura} | {embed} | {legal} |".format(
                package_id=package.package_id,
                unit=_compact(package.unit_name, 36),
                points=package.points,
                models=package.model_count,
                combined=package.combined_from_count,
                quality=package.quality,
                defense=package.defense,
                tough=package.tough,
                ap=package.max_ap,
                ev_inf=package.ev_infantry,
                ev_eli=package.ev_elite,
                ev_mon=package.ev_monster,
                w100=package.wounds_per_100pts_infantry,
                upgrades=_compact(", ".join(package.upgrade_labels), 60) if package.upgrade_labels else "-",
                roles=", ".join(package.role_tags),
                caster=package.caster_level or "-",
                spell_roles=", ".join(package.spell_role_tags) if package.spell_role_tags else "-",
                aura=_compact(", ".join(package.aura_rules), 48) if package.aura_rules else "-",
                embed=_embed_summary(package),
                legal="over 35% cap" if package.exceeds_group_cap else "ok",
            )
        )
    return "\n".join(lines)


def prompt_packages(
    packages: list[AdvisorPackage],
    *,
    point_limit: int,
    max_rows: int,
) -> list[AdvisorPackage]:
    if max_rows <= 0:
        return packages
    legal = [
        package
        for package in packages
        if not package.exceeds_group_cap and (point_limit <= 0 or package.points <= point_limit)
    ]
    candidates = legal or packages
    ranked = sorted(candidates, key=_prompt_package_sort_key)
    visible = ranked[:max_rows]
    if len(visible) < max_rows:
        return visible

    visible_ids = {package.package_id for package in visible}
    combined_candidates = [
        package
        for package in ranked
        if package.combined_from_count > 1 and package.package_id not in visible_ids
    ]
    if not combined_candidates:
        return visible

    combined_slots = max(1, max_rows // 6)
    replacements = combined_candidates[:combined_slots]
    replaceable_indexes = [
        index
        for index in range(len(visible) - 1, -1, -1)
        if visible[index].combined_from_count == 1
    ][: len(replacements)]
    for index, replacement in zip(replaceable_indexes, replacements):
        visible[index] = replacement
    return sorted(visible, key=_prompt_package_sort_key)


def package_lookup(packages: list[AdvisorPackage]) -> dict[str, dict[str, Any]]:
    return {
        package.package_id: {
            "unit_id": package.unit_id,
            "unit_name": package.unit_name,
            "model_count": package.model_count,
            "combined_from_count": package.combined_from_count,
            "selected_upgrade_ids": package.selected_upgrade_ids,
        }
        for package in packages
    }


def _prompt_package_sort_key(package: AdvisorPackage) -> tuple[int, int, float, str, str]:
    role_priority = 0
    if "core" in package.role_tags:
        role_priority -= 2
    if "mobility" in package.role_tags:
        role_priority -= 2
    if "anti-tough" in package.role_tags:
        role_priority -= 1
    if "ranged" in package.role_tags:
        role_priority -= 1
    if "hero" in package.role_tags or package.caster_level:
        role_priority -= 1
    return (
        role_priority,
        package.points,
        -package.wounds_per_100pts_infantry,
        package.unit_name,
        package.package_id,
    )


def force_org_summary(point_limit: int) -> str:
    if point_limit <= 0:
        return "No force organization limits apply."
    hero_limit = force_org_hero_limit(point_limit)
    copy_limit = force_org_copy_limit(point_limit)
    group_limit = force_org_group_limit(point_limit)
    group_point_cap = force_org_group_point_cap(point_limit)
    return (
        f"Force organization: max heroes {hero_limit}, "
        f"max copies per unit {copy_limit}, "
        f"max effective units {group_limit}, "
        f"single unit/group cap {int(group_point_cap or 0)} pts."
    )


def _package_for_unit(
    *,
    unit: Unit,
    point_limit: int,
    spell_role_tags: tuple[str, ...] = (),
    selected_upgrade_ids: list[int] | None = None,
    upgrade_labels: list[str] | None = None,
    package_suffix: str = "base",
    upgrade_cost: int = 0,
    combined_from_count: int = 1,
) -> AdvisorPackage:
    model_count = _default_model_count(unit)
    points = unit_selection_points(
        unit=unit,
        model_count=model_count,
        upgrade_cost=upgrade_cost,
        combined_count=combined_from_count,
    )
    target_results = _target_scores(unit, model_count, points, combined_from_count)
    caster_level = _caster_level(unit.special_rules)
    return AdvisorPackage(
        package_id=_package_id(unit.id, package_suffix, combined_from_count),
        unit_id=unit.id,
        unit_name=unit.name,
        model_count=model_count,
        combined_from_count=combined_from_count,
        selected_upgrade_ids=selected_upgrade_ids or [],
        upgrade_labels=upgrade_labels or [],
        points=points,
        quality=unit.quality,
        defense=unit.defense,
        tough=unit.tough,
        max_ap=_max_ap(unit),
        ev_infantry=target_results["infantry"]["ev"],
        ev_elite=target_results["elite"]["ev"],
        ev_monster=target_results["monster"]["ev"],
        wounds_per_100pts_infantry=target_results["infantry"]["wounds_per_100_points"],
        role_tags=_role_tags(unit, points, point_limit, caster_level),
        aura_rules=_aura_rules(unit, selected_upgrade_ids or []),
        caster_level=caster_level,
        spell_role_tags=spell_role_tags if caster_level else (),
        can_embed_as_hero=_can_embed_as_hero(unit),
        can_host_embedded_hero=model_count > 1 and not is_hero(unit),
        exceeds_group_cap=point_limit > 0 and points > point_limit * 0.35,
    )


def _packages_for_unit_variant(
    *,
    unit: Unit,
    point_limit: int,
    spell_role_tags: tuple[str, ...],
    selected_upgrade_ids: list[int] | None = None,
    upgrade_labels: list[str] | None = None,
    package_suffix: str = "base",
    upgrade_cost: int = 0,
) -> list[AdvisorPackage]:
    base_package = _package_for_unit(
        unit=unit,
        point_limit=point_limit,
        spell_role_tags=spell_role_tags,
        selected_upgrade_ids=selected_upgrade_ids,
        upgrade_labels=upgrade_labels,
        package_suffix=package_suffix,
        upgrade_cost=upgrade_cost,
    )
    packages = [base_package]
    if not _can_build_combined_packages(unit, base_package.model_count, point_limit):
        return packages

    copy_limit = force_org_copy_limit(point_limit) or 1
    for combined_count in range(2, copy_limit + 1):
        combined_package = _package_for_unit(
            unit=unit,
            point_limit=point_limit,
            spell_role_tags=spell_role_tags,
            selected_upgrade_ids=selected_upgrade_ids,
            upgrade_labels=upgrade_labels,
            package_suffix=package_suffix,
            upgrade_cost=upgrade_cost,
            combined_from_count=combined_count,
        )
        if combined_package.exceeds_group_cap:
            continue
        if point_limit > 0 and combined_package.points > point_limit:
            continue
        packages.append(combined_package)
    return packages


def _can_build_combined_packages(unit: Unit, model_count: int, point_limit: int) -> bool:
    return point_limit > 0 and model_count > 1 and not is_hero(unit)


def _package_id(unit_id: int, package_suffix: str, combined_from_count: int) -> str:
    base_id = f"u{unit_id}-{package_suffix}"
    if combined_from_count <= 1:
        return base_id
    return f"{base_id}-c{combined_from_count}"


def _upgrade_options(unit: Unit) -> list[UnitUpgradeOption]:
    options: list[UnitUpgradeOption] = []
    for section in unit.upgrade_sections.all():
        options.extend(section.options.all())
    return options


def _default_model_count(unit: Unit) -> int:
    model_count = max(unit.min_models, unit.default_models)
    return min(model_count, effective_max_models(unit))


def _max_ap(unit: Unit) -> int:
    return max((slot.weapon.ap for slot in unit.weapon_slots.all() if slot.is_default), default=0)


def _target_scores(
    unit: Unit,
    model_count: int,
    points: int,
    combined_from_count: int = 1,
) -> dict[str, dict[str, float]]:
    targets = default_target_profiles()
    return {
        target.id: _target_score(unit, model_count, points, target, combined_from_count)
        for target in targets
    }


def _target_score(
    unit: Unit,
    model_count: int,
    points: int,
    target: TargetProfile,
    combined_from_count: int = 1,
) -> dict[str, float]:
    ev = 0.0
    for slot in unit.weapon_slots.all():
        if not slot.is_default:
            continue
        weapon = slot.weapon
        attacks = weapon.attacks * model_count * max(1, combined_from_count)
        special_rules = {**unit.special_rules, **weapon.special_rules}
        ev += calculate_ev(
            attacks,
            unit.quality,
            target.defense,
            weapon.ap,
            special_rules,
            target_special_rules=target.special_rules,
            combat_context=weapon_combat_context(weapon, model_count, target.tough),
        )
    return {
        "ev": round(ev, 6),
        "wounds_per_100_points": round((ev / points) * 100, 6) if points > 0 else 0,
    }


def _role_tags(unit: Unit, points: int, point_limit: int, caster_level: str = "") -> tuple[str, ...]:
    tags: list[str] = ["hero" if is_hero(unit) else "core"]
    if _has_any_rule(unit, ("Scout", "Fast", "Flying", "Strider", "Ambush")):
        tags.append("mobility")
    if any(slot.is_default and slot.weapon.range > 0 for slot in unit.weapon_slots.all()):
        tags.append("ranged")
    if (
        _max_ap(unit) >= 2
        or unit.tough >= 3
        or _has_disintegrate_weapon(unit)
        or _has_any_rule(unit, ("Melee Slayer", "Ranged Slayer"))
    ):
        tags.append("anti-tough")
    if point_limit > 0 and points <= point_limit * 0.12:
        tags.append("screen")
    if _has_any_rule(unit, ("Fearless", "Stealth", "Regeneration")):
        tags.append("support")
    if _has_any_rule(unit, ("Fearless",)):
        tags.append("morale")
    if caster_level:
        tags.extend(("caster", "support"))
    return tuple(dict.fromkeys(tags))


def _caster_level(special_rules: dict[str, Any] | None) -> str:
    if not special_rules:
        return ""
    for key, value in special_rules.items():
        normalized = key.strip().lower()
        if normalized == "caster":
            return str(value) if value not in (None, "", True, False) else "1"
        if normalized == "caster group" and value:
            return "group"
    return ""


def _faction_spell_role_tags(faction_id: int) -> tuple[str, ...]:
    roles: list[str] = []
    for effect in FactionSpell.objects.filter(faction_id=faction_id).values_list("effect", flat=True):
        roles.extend(spell_role_tags(effect))
    return tuple(dict.fromkeys(roles))


def spell_role_tags(effect: str) -> tuple[str, ...]:
    text = effect.lower()
    padded = f" {text} "
    tags: list[str] = []
    is_healing = any(
        marker in text
        for marker in (
            "remove d3 wounds",
            "remove one wound",
            "removes d3 wounds",
            "healing",
            "heal",
        )
    )
    if not is_healing and any(
        marker in text
        for marker in (
            " takes ",
            " hit",
            "wound",
            "ap(",
            "deadly",
            "poison",
            "damage",
        )
    ):
        tags.append("damage")
    if any(
        marker in text
        for marker in (
            "gets +",
            "gets disintegrate",
            "gets shred",
            "gets rending",
            "gets ap(",
            "gets regeneration",
        )
    ):
        tags.append("buff")
    if any(marker in text for marker in ("-1", "loses", "enemy unit loses", "debuff")):
        tags.append("debuff")
    if any(marker in text for marker in ("defense", "cover", "ignore", "shield")):
        tags.append("defense")
    if is_healing:
        tags.append("healing")
    if any(
        marker in padded
        for marker in (
            " move ",
            " moves ",
            " moving ",
            " placed anywhere ",
            " ambush ",
            " scout ",
            " advance ",
            " charge ",
        )
    ):
        tags.append("mobility")
    if any(marker in text for marker in ("morale", "fear", "discipline")):
        tags.append("morale")
    if any(marker in text for marker in ("terrain", "impassable", "blocking", "objective")):
        tags.append("control")
    return tuple(dict.fromkeys(tags))


def _aura_rules(unit: Unit, selected_upgrade_ids: list[int]) -> tuple[str, ...]:
    _normal_rules, unit_aura_rules = split_aura_rules(unit.special_rules)
    aura_rules = list(unit_aura_rules)
    selected = set(selected_upgrade_ids)
    for option in _upgrade_options(unit):
        if option.id in selected:
            aura_rules.extend(aura_rule_names_from_gains(option.gains))
    return tuple(dict.fromkeys(aura_rules))


def _can_embed_as_hero(unit: Unit) -> bool:
    return is_hero(unit) and unit.tough <= 6


def _embed_summary(package: AdvisorPackage) -> str:
    values: list[str] = []
    if package.can_embed_as_hero:
        values.append("hero")
    if package.can_host_embedded_hero:
        values.append("host")
    return ",".join(values) if values else "-"


def _has_any_rule(unit: Unit, names: tuple[str, ...]) -> bool:
    rules = unit.special_rules or {}
    normalized = {key.lower() for key, value in rules.items() if value}
    return any(name.lower() in normalized for name in names)


def _has_disintegrate_weapon(unit: Unit) -> bool:
    for slot in unit.weapon_slots.all():
        if not slot.is_default:
            continue
        rules = slot.weapon.special_rules or {}
        if any(key.lower() == "disintegrate" and bool(value) for key, value in rules.items()):
            return True
    return False


def _compact(value: str, max_length: int) -> str:
    clean = value.replace("|", "/")
    return clean if len(clean) <= max_length else clean[:max_length]
