from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Any

from army_books.calc.weapon_scoring import weapon_ev_profile, weapon_has_limited_rule
from army_books.models import FactionSpell, Unit, UnitUpgradeOption
from army_books.upgrade_matching import weapon_matches_upgrade_target
from army_books.upgrade_resolution import resolve_unit_upgrade_options
from lists.analysis import TargetProfile, default_target_profiles, weapon_combat_context
from lists.loadouts import (
    aura_rule_names_from_gains,
    split_aura_rules,
    weapon_attack_count,
    weapon_count,
    weapon_with_count,
)
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
    selected_upgrade_selections: list[dict[str, int]]
    upgrade_labels: list[str]
    points: int
    quality: int
    defense: int
    tough: int
    max_ap: int
    ev_infantry: float
    ev_elite: float
    ev_monster: float
    burst_ev_infantry: float
    burst_ev_elite: float
    burst_ev_monster: float
    ranged_ev_infantry: float
    melee_ev_infantry: float
    wounds_per_100pts_infantry: float
    limited_weapon_names: tuple[str, ...]
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
    seen_package_keys: set[tuple[int, tuple[tuple[int, int], ...]]] = set()
    spell_role_tags = _faction_spell_role_tags(faction_id)
    for unit in units:
        packages.extend(
            _packages_for_unit_variant(
                unit=unit,
                point_limit=point_limit,
                spell_role_tags=spell_role_tags,
            )
        )
        seen_package_keys.add((unit.id, ()))
        upgrade_options = [option for option in _upgrade_options(unit) if option.cost > 0]
        replace_any_options = [option for option in upgrade_options if _is_replace_any_section(option.section)]
        normal_options = [option for option in upgrade_options if not _is_replace_any_section(option.section)]
        upgrade_selections = [
            *([option] for option in normal_options),
            *_upgrade_option_combinations(_advisor_relevant_upgrade_options(normal_options)),
        ]
        replace_any_selections = [
            ([option], {option.id: target_count})
            for option in replace_any_options
            if (target_count := _replace_any_target_count(unit, option.section)) > 0
        ]
        for selection, quantities in [
            *((selection, None) for selection in upgrade_selections),
            *replace_any_selections,
        ]:
            package_data = _resolved_upgrade_package_data(unit, selection, quantities_by_option=quantities)
            if package_data is None:
                continue
            package_key = (unit.id, _selection_key(package_data["selected_upgrade_selections"]))
            if package_key in seen_package_keys:
                continue
            seen_package_keys.add(package_key)
            packages.extend(
                _packages_for_unit_variant(
                    unit=unit,
                    point_limit=point_limit,
                    spell_role_tags=spell_role_tags,
                    selected_upgrade_ids=package_data["selected_upgrade_ids"],
                    selected_upgrade_selections=package_data["selected_upgrade_selections"],
                    upgrade_labels=package_data["upgrade_labels"],
                    package_suffix=_upgrade_package_suffix(package_data["selected_upgrade_ids"]),
                    upgrade_cost=package_data["upgrade_cost"],
                )
            )
    return packages


def build_package_table(packages: list[AdvisorPackage]) -> str:
    lines = [
        "| Package | Unit | Pts | Models | Combined | Q | Def | T | AP | Act_inf | Burst_inf | Rng_inf | Mel_inf | Act_eli | Act_mon | W100 | Limited | Upgrades | Roles | Caster | Spell Roles | Aura | Embed | Legal |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for package in packages:
        lines.append(
            "| {package_id} | {unit} | {points} | {models} | {combined} | {quality}+ | {defense}+ | "
            "{tough} | {ap} | {ev_inf:.2f} | {burst_inf:.2f} | {rng_inf:.2f} | {mel_inf:.2f} | {ev_eli:.2f} | {ev_mon:.2f} | {w100:.2f} | "
            "{limited} | {upgrades} | {roles} | {caster} | {spell_roles} | {aura} | {embed} | {legal} |".format(
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
                burst_inf=package.burst_ev_infantry,
                rng_inf=package.ranged_ev_infantry,
                mel_inf=package.melee_ev_infantry,
                ev_eli=package.ev_elite,
                ev_mon=package.ev_monster,
                w100=package.wounds_per_100pts_infantry,
                limited=_compact(", ".join(package.limited_weapon_names), 48) if package.limited_weapon_names else "-",
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
            "selected_upgrade_selections": package.selected_upgrade_selections,
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
    selected_upgrade_selections: list[dict[str, int]] | None = None,
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
    selected_ids = selected_upgrade_ids or []
    selected_selections = selected_upgrade_selections or _selected_upgrade_selections_from_ids(selected_ids)
    weapons, extra_rules = _variant_weapons_and_rules(unit, selected_ids, selected_selections)
    caster_level = _caster_level({**(unit.special_rules or {}), **extra_rules})
    target_results = _target_scores(unit, model_count, points, combined_from_count, weapons, extra_rules)
    return AdvisorPackage(
        package_id=_package_id(unit.id, package_suffix, combined_from_count),
        unit_id=unit.id,
        unit_name=unit.name,
        model_count=model_count,
        combined_from_count=combined_from_count,
        selected_upgrade_ids=selected_upgrade_ids or [],
        selected_upgrade_selections=selected_selections,
        upgrade_labels=upgrade_labels or [],
        points=points,
        quality=unit.quality,
        defense=unit.defense,
        tough=unit.tough,
        max_ap=_max_ap(weapons),
        ev_infantry=target_results["infantry"]["ev"],
        ev_elite=target_results["elite"]["ev"],
        ev_monster=target_results["monster"]["ev"],
        burst_ev_infantry=target_results["infantry"]["burst_ev"],
        burst_ev_elite=target_results["elite"]["burst_ev"],
        burst_ev_monster=target_results["monster"]["burst_ev"],
        ranged_ev_infantry=target_results["infantry"]["ranged_ev"],
        melee_ev_infantry=target_results["infantry"]["melee_ev"],
        wounds_per_100pts_infantry=target_results["infantry"]["wounds_per_100_points"],
        limited_weapon_names=tuple(
            weapon.name for weapon in weapons if weapon_has_limited_rule(weapon)
        ),
        role_tags=_role_tags(unit, points, point_limit, caster_level, weapons, extra_rules),
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
    selected_upgrade_selections: list[dict[str, int]] | None = None,
    upgrade_labels: list[str] | None = None,
    package_suffix: str = "base",
    upgrade_cost: int = 0,
) -> list[AdvisorPackage]:
    base_package = _package_for_unit(
        unit=unit,
        point_limit=point_limit,
        spell_role_tags=spell_role_tags,
        selected_upgrade_ids=selected_upgrade_ids,
        selected_upgrade_selections=selected_upgrade_selections,
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
            selected_upgrade_selections=selected_upgrade_selections,
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


def _upgrade_package_suffix(option_ids: list[int]) -> str:
    return "o" + "-".join(str(option_id) for option_id in option_ids)


def _resolved_upgrade_package_data(
    unit: Unit,
    selected_options: list[UnitUpgradeOption],
    *,
    quantities_by_option: dict[int, int] | None = None,
) -> dict[str, Any] | None:
    resolution = resolve_unit_upgrade_options(unit, selected_options)
    if not resolution.is_valid:
        return None
    quantities = quantities_by_option or {}
    selections = [
        {"option": option.id, "quantity": max(1, int(quantities.get(option.id, 1)))}
        for option in resolution.options
    ]
    return {
        "selected_upgrade_ids": resolution.option_ids,
        "selected_upgrade_selections": selections,
        "upgrade_labels": [
            _upgrade_label(option, _quantity_for_option(option.id, selections))
            for option in resolution.options
        ],
        "upgrade_cost": sum(option.cost * _quantity_for_option(option.id, selections) for option in resolution.options),
    }


def _upgrade_label(option: UnitUpgradeOption, quantity: int) -> str:
    return f"{option.label} x{quantity}" if quantity > 1 else option.label


def _quantity_for_option(option_id: int, selections: list[dict[str, int]]) -> int:
    for selection in selections:
        if selection["option"] == option_id:
            return max(1, int(selection.get("quantity", 1)))
    return 1


def _selection_key(selections: list[dict[str, int]]) -> tuple[tuple[int, int], ...]:
    return tuple((selection["option"], max(1, int(selection.get("quantity", 1)))) for selection in selections)


def _advisor_relevant_upgrade_options(options: list[UnitUpgradeOption]) -> list[UnitUpgradeOption]:
    return [option for option in options if _upgrade_option_is_advisor_relevant(option)]


def _upgrade_option_combinations(
    options: list[UnitUpgradeOption],
    *,
    max_selected: int = 2,
) -> list[list[UnitUpgradeOption]]:
    selections: list[list[UnitUpgradeOption]] = []
    for size in range(2, max_selected + 1):
        for selected in combinations(options, size):
            if _has_conflicting_upgrade_sections(list(selected)):
                continue
            selections.append(list(selected))
    return selections


def _has_conflicting_upgrade_sections(options: list[UnitUpgradeOption]) -> bool:
    seen_section_ids: set[int] = set()
    for option in options:
        if option.section_id in seen_section_ids and not _is_replace_any_section(option.section):
            return True
        seen_section_ids.add(option.section_id)
    return False


def _upgrade_option_is_advisor_relevant(option: UnitUpgradeOption) -> bool:
    if option.weapons.exists():
        return True
    return bool(_advisor_relevant_gain_rules(option.gains))


def _advisor_relevant_gain_rules(gains: list[dict[str, Any]]) -> tuple[str, ...]:
    relevant_rules = {
        "ambush",
        "ap",
        "caster",
        "caster group",
        "deadly",
        "defense",
        "disintegrate",
        "fast",
        "fearless",
        "flying",
        "furious",
        "impact",
        "melee slayer",
        "poison",
        "ranged slayer",
        "regeneration",
        "reliable",
        "rending",
        "scout",
        "sergeant",
        "stealth",
        "strider",
        "support",
        "surge",
        "tough",
        "unstoppable",
    }
    return tuple(
        rule
        for rule, _rating in _gain_rules(gains)
        if rule.strip().lower() in relevant_rules or "aura" in rule.strip().lower()
    )


def _upgrade_options(unit: Unit) -> list[UnitUpgradeOption]:
    options: list[UnitUpgradeOption] = []
    for section in unit.upgrade_sections.all():
        options.extend(section.options.all())
    return options


def _default_model_count(unit: Unit) -> int:
    model_count = max(unit.min_models, unit.default_models)
    return min(model_count, effective_max_models(unit))


def _max_ap(weapons: list[Any]) -> int:
    return max((weapon.ap for weapon in weapons), default=0)


def _target_scores(
    unit: Unit,
    model_count: int,
    points: int,
    combined_from_count: int = 1,
    weapons: list[Any] | None = None,
    extra_rules: dict[str, Any] | None = None,
) -> dict[str, dict[str, float]]:
    targets = default_target_profiles()
    selected_weapons = weapons if weapons is not None else _variant_weapons_and_rules(unit)[0]
    selected_extra_rules = extra_rules or {}
    return {
        target.id: _target_score(unit, model_count, points, target, combined_from_count, selected_weapons, selected_extra_rules)
        for target in targets
    }


def _target_score(
    unit: Unit,
    model_count: int,
    points: int,
    target: TargetProfile,
    combined_from_count: int = 1,
    weapons: list[Any] | None = None,
    extra_rules: dict[str, Any] | None = None,
) -> dict[str, float]:
    weapons = weapons if weapons is not None else _variant_weapons_and_rules(unit)[0]
    extra_rules = extra_rules or {}
    ev = 0.0
    ranged_ev = 0.0
    melee_ev = 0.0
    burst_ev = 0.0
    burst_ranged_ev = 0.0
    burst_melee_ev = 0.0
    for weapon in weapons:
        attacks = weapon.attacks * weapon_attack_count(weapon, model_count) * max(1, combined_from_count)
        special_rules = {**unit.special_rules, **extra_rules, **weapon.special_rules}
        weapon_profile = weapon_ev_profile(
            weapon=weapon,
            attacks=attacks,
            quality=unit.quality,
            defense=target.defense,
            special_rules=special_rules,
            target_special_rules=target.special_rules,
            combat_context=weapon_combat_context(weapon, model_count, target.tough, target.unit_size),
        )
        ev += weapon_profile.sustained_ev
        burst_ev += weapon_profile.burst_ev
        if weapon.range > 0:
            ranged_ev += weapon_profile.sustained_ev
            burst_ranged_ev += weapon_profile.burst_ev
        else:
            melee_ev += weapon_profile.sustained_ev
            burst_melee_ev += weapon_profile.burst_ev
    activation_ev = max(ranged_ev, melee_ev)
    return {
        "ev": round(activation_ev, 6),
        "summed_ev": round(ev, 6),
        "ranged_ev": round(ranged_ev, 6),
        "melee_ev": round(melee_ev, 6),
        "burst_ev": round(max(burst_ranged_ev, burst_melee_ev), 6),
        "burst_summed_ev": round(burst_ev, 6),
        "burst_ranged_ev": round(burst_ranged_ev, 6),
        "burst_melee_ev": round(burst_melee_ev, 6),
        "wounds_per_100_points": round((activation_ev / points) * 100, 6) if points > 0 else 0,
    }


def _role_tags(
    unit: Unit,
    points: int,
    point_limit: int,
    caster_level: str = "",
    weapons: list[Any] | None = None,
    extra_rules: dict[str, Any] | None = None,
) -> tuple[str, ...]:
    tags: list[str] = ["hero" if is_hero(unit) else "core"]
    weapons = weapons if weapons is not None else _variant_weapons_and_rules(unit)[0]
    combined_rules = {**(unit.special_rules or {}), **(extra_rules or {})}
    ranged_ev = _lane_ev(unit, weapons, combined_rules, ranged=True)
    melee_ev = _lane_ev(unit, weapons, combined_rules, ranged=False)
    if _has_any_rule_from(combined_rules, ("Scout", "Fast", "Flying", "Strider", "Ambush")):
        tags.append("mobility")
    if any(weapon.range > 0 for weapon in weapons):
        tags.append("ranged")
    if ranged_ev > 0 and ranged_ev >= melee_ev:
        tags.append("ranged-pressure")
    if melee_ev > 0 and melee_ev >= ranged_ev:
        tags.append("melee-threat")
    weaker_lane = min(value for value in (ranged_ev, melee_ev) if value > 0) if ranged_ev > 0 and melee_ev > 0 else 0
    stronger_lane = max(ranged_ev, melee_ev)
    if weaker_lane > 0 and stronger_lane > 0:
        if weaker_lane >= stronger_lane * 0.5:
            tags.append("hybrid-flex")
        elif ranged_ev < melee_ev and ranged_ev <= melee_ev * 0.35:
            tags.append("ranged-tax-risk")
    if (
        _max_ap(weapons) >= 2
        or unit.tough >= 3
        or _has_disintegrate_weapon(weapons)
        or _has_any_rule_from(combined_rules, ("Melee Slayer", "Ranged Slayer"))
    ):
        tags.append("anti-tough")
    if point_limit > 0 and points <= point_limit * 0.12:
        tags.append("screen")
    if _has_any_rule_from(combined_rules, ("Fearless", "Stealth", "Regeneration")):
        tags.append("support")
    if _has_any_rule_from(combined_rules, ("Fearless",)):
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
    for option in _resolved_upgrade_options(unit, selected_upgrade_ids):
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


def _variant_weapons_and_rules(
    unit: Unit,
    selected_upgrade_ids: list[int] | None = None,
    selected_upgrade_selections: list[dict[str, int]] | None = None,
) -> tuple[list[Any], dict[str, Any]]:
    weapons = [weapon_with_count(slot.weapon, slot.count) for slot in unit.weapon_slots.all() if slot.is_default]
    if not weapons:
        weapons = [weapon_with_count(slot.weapon, slot.count) for slot in unit.weapon_slots.all()[:1]]
    extra_rules: dict[str, Any] = {}
    selected = set(selected_upgrade_ids or [])
    if not selected:
        return weapons, extra_rules

    quantities = {
        int(selection["option"]): max(1, int(selection.get("quantity", 1)))
        for selection in selected_upgrade_selections or []
        if selection.get("option") is not None
    }
    for option in _resolved_upgrade_options(unit, selected_upgrade_ids or []):
        option_quantity = quantities.get(option.id, 1)
        if option.section.variant.lower() == "replace":
            quantity = option_quantity if _is_replace_any_section(option.section) else None
            weapons = _remove_target_weapons(weapons, option.section.targets, quantity=quantity)
        weapons = [*weapons, *_option_weapons(option, option_quantity)]
        gained_rules, _aura_rules = split_aura_rules(dict(_gain_rules(option.gains)))
        extra_rules = {**extra_rules, **gained_rules}
    return weapons, extra_rules


def _option_weapons(option: UnitUpgradeOption, quantity: int = 1) -> list[Any]:
    links = list(option.option_weapons.select_related("weapon").all())
    if links:
        return [
            weapon_with_count(link.weapon, link.count * quantity if link.count else None)
            for link in links
        ]
    return [weapon_with_count(weapon, quantity) for weapon in option.weapons.all()]


def _remove_target_weapons(
    weapons: list[Any],
    targets: list[str],
    *,
    quantity: int | None,
) -> list[Any]:
    if quantity is None:
        return [
            weapon
            for weapon in weapons
            if not weapon_matches_upgrade_target(weapon.name, targets)
        ]
    remaining = quantity
    kept: list[Any] = []
    for weapon in weapons:
        if remaining <= 0 or not weapon_matches_upgrade_target(weapon.name, targets):
            kept.append(weapon)
            continue
        count = weapon_count(weapon)
        if count is None:
            remaining -= 1
            continue
        removed = min(count, remaining)
        remaining -= removed
        if count > removed:
            kept.append(weapon_with_count(weapon, count - removed))
    return kept


def _is_replace_any_section(section: Any) -> bool:
    affects = getattr(section, "affects", None) or {}
    return section.variant.lower() == "replace" and str(affects.get("type") or "").lower() == "any"


def _replace_any_target_count(unit: Unit, section: Any) -> int:
    count = 0
    for slot in unit.weapon_slots.all():
        if not slot.is_default or not weapon_matches_upgrade_target(slot.weapon.name, section.targets):
            continue
        count += slot.count or 1
    return count


def _selected_upgrade_selections_from_ids(option_ids: list[int]) -> list[dict[str, int]]:
    return [{"option": option_id, "quantity": 1} for option_id in option_ids]


def _resolved_upgrade_options(unit: Unit, selected_upgrade_ids: list[int]) -> list[UnitUpgradeOption]:
    selected_options = [option for option in _upgrade_options(unit) if option.id in set(selected_upgrade_ids)]
    option_order = {option_id: index for index, option_id in enumerate(selected_upgrade_ids)}
    selected_options = sorted(selected_options, key=lambda option: option_order[option.id])
    resolution = resolve_unit_upgrade_options(unit, selected_options)
    return resolution.options if resolution.is_valid else selected_options


def _gain_rules(gains: list[dict[str, Any]]):
    for gain in gains:
        if not isinstance(gain, dict):
            continue
        content = gain.get("content")
        if not isinstance(content, list):
            continue
        for rule in content:
            if not isinstance(rule, dict):
                continue
            name = rule.get("name")
            if name:
                yield str(name), rule.get("rating", True)


def _lane_ev(unit: Unit, weapons: list[Any], extra_rules: dict[str, Any], *, ranged: bool) -> float:
    target = default_target_profiles()[0]
    ev = 0.0
    for weapon in weapons:
        if (weapon.range > 0) != ranged:
            continue
        attacks = weapon.attacks * weapon_attack_count(weapon, _default_model_count(unit))
        special_rules = {**(unit.special_rules or {}), **extra_rules, **(weapon.special_rules or {})}
        ev += weapon_ev_profile(
            weapon=weapon,
            attacks=attacks,
            quality=unit.quality,
            defense=target.defense,
            special_rules=special_rules,
            target_special_rules=target.special_rules,
            combat_context=weapon_combat_context(weapon, _default_model_count(unit), target.tough, target.unit_size),
        ).sustained_ev
    return ev


def _has_disintegrate_weapon(weapons: list[Any]) -> bool:
    for weapon in weapons:
        rules = weapon.special_rules or {}
        if any(key.lower() == "disintegrate" and bool(value) for key, value in rules.items()):
            return True
    return False


def _has_any_rule_from(rules: dict[str, Any], names: tuple[str, ...]) -> bool:
    normalized = {key.lower() for key, value in rules.items() if value}
    return any(name.lower() in normalized for name in names)


def _compact(value: str, max_length: int) -> str:
    clean = value.replace("|", "/")
    return clean if len(clean) <= max_length else clean[:max_length]
