from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from army_books.models import Unit, UnitUpgradeOption
from lists.loadouts import aura_rule_names_from_gains, split_aura_rules
from lists.validation import effective_max_models, is_hero, unit_selection_points


@dataclass(frozen=True)
class AdvisorPackage:
    package_id: str
    unit_id: int
    unit_name: str
    model_count: int
    selected_upgrade_ids: list[int]
    upgrade_labels: list[str]
    points: int
    quality: int
    defense: int
    tough: int
    max_ap: int
    role_tags: tuple[str, ...]
    aura_rules: tuple[str, ...]
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
    for unit in units:
        packages.append(_package_for_unit(unit=unit, point_limit=point_limit))
        for option in _upgrade_options(unit):
            if option.cost <= 0:
                continue
            packages.append(
                _package_for_unit(
                    unit=unit,
                    point_limit=point_limit,
                    selected_upgrade_ids=[option.id],
                    upgrade_labels=[option.label],
                    package_suffix=f"o{option.id}",
                    upgrade_cost=option.cost,
                )
            )
    return packages


def build_package_table(packages: list[AdvisorPackage]) -> str:
    lines = [
        "| Package | Unit | Pts | Models | Q | Def | T | AP | Upgrades | Roles | Aura | Embed | Legal |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for package in packages:
        lines.append(
            "| {package_id} | {unit} | {points} | {models} | {quality}+ | {defense}+ | "
            "{tough} | {ap} | {upgrades} | {roles} | {aura} | {embed} | {legal} |".format(
                package_id=package.package_id,
                unit=_compact(package.unit_name, 36),
                points=package.points,
                models=package.model_count,
                quality=package.quality,
                defense=package.defense,
                tough=package.tough,
                ap=package.max_ap,
                upgrades=_compact(", ".join(package.upgrade_labels), 60) if package.upgrade_labels else "-",
                roles=", ".join(package.role_tags),
                aura=_compact(", ".join(package.aura_rules), 48) if package.aura_rules else "-",
                embed=_embed_summary(package),
                legal="over 35% cap" if package.exceeds_group_cap else "ok",
            )
        )
    return "\n".join(lines)


def package_lookup(packages: list[AdvisorPackage]) -> dict[str, dict[str, Any]]:
    return {
        package.package_id: {
            "unit_id": package.unit_id,
            "unit_name": package.unit_name,
            "model_count": package.model_count,
            "selected_upgrade_ids": package.selected_upgrade_ids,
        }
        for package in packages
    }


def force_org_summary(point_limit: int) -> str:
    if point_limit <= 0:
        return "No force organization limits apply."
    return (
        f"Force organization: max heroes {max(1, point_limit // 500)}, "
        f"max copies per unit {1 + point_limit // 750}, "
        f"max effective units {point_limit // 150}, "
        f"single unit/group cap {int(point_limit * 0.35)} pts."
    )


def _package_for_unit(
    *,
    unit: Unit,
    point_limit: int,
    selected_upgrade_ids: list[int] | None = None,
    upgrade_labels: list[str] | None = None,
    package_suffix: str = "base",
    upgrade_cost: int = 0,
) -> AdvisorPackage:
    model_count = _default_model_count(unit)
    points = unit_selection_points(unit=unit, model_count=model_count, upgrade_cost=upgrade_cost)
    return AdvisorPackage(
        package_id=f"u{unit.id}-{package_suffix}",
        unit_id=unit.id,
        unit_name=unit.name,
        model_count=model_count,
        selected_upgrade_ids=selected_upgrade_ids or [],
        upgrade_labels=upgrade_labels or [],
        points=points,
        quality=unit.quality,
        defense=unit.defense,
        tough=unit.tough,
        max_ap=_max_ap(unit),
        role_tags=_role_tags(unit, points, point_limit),
        aura_rules=_aura_rules(unit, selected_upgrade_ids or []),
        can_embed_as_hero=_can_embed_as_hero(unit),
        can_host_embedded_hero=model_count > 1 and not is_hero(unit),
        exceeds_group_cap=point_limit > 0 and points > point_limit * 0.35,
    )


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


def _role_tags(unit: Unit, points: int, point_limit: int) -> tuple[str, ...]:
    tags: list[str] = ["hero" if is_hero(unit) else "core"]
    if _has_any_rule(unit, ("Scout", "Fast", "Flying", "Strider", "Ambush")):
        tags.append("mobility")
    if any(slot.is_default and slot.weapon.range > 0 for slot in unit.weapon_slots.all()):
        tags.append("ranged")
    if _max_ap(unit) >= 2 or unit.tough >= 3:
        tags.append("anti-tough")
    if point_limit > 0 and points <= point_limit * 0.12:
        tags.append("screen")
    if _has_any_rule(unit, ("Fearless", "Stealth", "Regeneration")):
        tags.append("support")
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


def _compact(value: str, max_length: int) -> str:
    clean = value.replace("|", "/")
    return clean if len(clean) <= max_length else clean[:max_length]
