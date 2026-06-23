from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from army_books.models import (
    Faction,
    FactionSpell,
    Unit,
    UnitUpgradeOption,
    UnitUpgradeOptionWeapon,
    UnitUpgradeSection,
    UnitWeaponSlot,
    Weapon,
)
from army_books.opr_client import fetch_army_book, fetch_army_book_list
from army_books.parsers import parse_spell, parse_unit, parse_weapon


class Command(BaseCommand):
    help = "Fetch and cache OPR Age of Fantasy army books."

    def add_arguments(self, parser):
        parser.add_argument("--game-system", default="age-of-fantasy")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        game_system = options["game_system"]
        dry_run = options["dry_run"]

        books = fetch_army_book_list(game_system_slug=game_system)
        if not books:
            self.stdout.write(
                self.style.WARNING(
                    f"No army books returned for game system '{game_system}'."
                )
            )
            return

        summary = {"factions": 0, "units": 0, "weapons": 0, "slots": 0, "spells": 0}
        for listed_book in books:
            uid = _source_uid(listed_book)
            if not uid:
                self.stdout.write(self.style.WARNING("Skipping army book without uid."))
                continue

            detail = fetch_army_book(uid, game_system_slug=game_system)
            if dry_run:
                summary["factions"] += 1
                summary["units"] += len(_units(detail))
                summary["spells"] += len(_spells(detail))
                continue

            with transaction.atomic():
                book_summary = _sync_book(detail or listed_book, fallback=listed_book)
            for key, value in book_summary.items():
                summary[key] += value

        self.stdout.write(
            self.style.SUCCESS(
                "Synced "
                f"{summary['factions']} factions, "
                f"{summary['units']} units, "
                f"{summary['weapons']} weapons, "
                f"{summary['slots']} weapon slots, "
                f"{summary['spells']} spells."
            )
        )


def _sync_book(book: dict[str, Any], fallback: dict[str, Any]) -> dict[str, int]:
    merged_book = {**fallback, **book}
    faction = _upsert_faction(merged_book)
    summary = {"factions": 1, "units": 0, "weapons": 0, "slots": 0, "spells": 0}
    upgrade_packages = _upgrade_package_lookup(merged_book)
    summary["spells"] = _sync_spells(faction, merged_book)

    for raw_unit in _units(merged_book):
        unit_kwargs = parse_unit(raw_unit)
        unit = _upsert_unit(faction, unit_kwargs)
        summary["units"] += 1

        for raw_weapon, is_default, upgrade_cost, option_id, upgrade_id in _weapon_options(raw_unit):
            weapon_kwargs = parse_weapon(raw_weapon)
            weapon = _upsert_weapon(weapon_kwargs)
            UnitWeaponSlot.objects.update_or_create(
                unit=unit,
                weapon=weapon,
                defaults={
                    "is_default": is_default,
                    "upgrade_cost": upgrade_cost,
                    "option_id": option_id,
                    "upgrade_id": upgrade_id,
                },
            )
            summary["weapons"] += 1
            summary["slots"] += 1
        _sync_unit_upgrades(unit, raw_unit, upgrade_packages)

    return summary


def _sync_spells(faction: Faction, book: dict[str, Any]) -> int:
    seen_spell_ids: set[str] = set()
    for raw_spell in _spells(book):
        spell_kwargs = parse_spell(raw_spell)
        source_uid = spell_kwargs.pop("source_uid")
        seen_spell_ids.add(source_uid)
        FactionSpell.objects.update_or_create(
            faction=faction,
            source_uid=source_uid,
            defaults=spell_kwargs,
        )
    faction.spells.exclude(source_uid__in=seen_spell_ids).delete()
    return len(seen_spell_ids)


def _upsert_faction(book: dict[str, Any]) -> Faction:
    source_uid = _source_uid(book)
    defaults = {
        "name": book["name"],
        "version": str(book.get("versionString") or book.get("version") or ""),
        "last_fetched": timezone.now(),
        "source_slug": book.get("slug") or book.get("source_slug"),
    }
    faction, _created = Faction.objects.update_or_create(
        source_uid=source_uid,
        defaults=defaults,
    )
    return faction


def _upsert_unit(faction: Faction, unit_kwargs: dict[str, Any]) -> Unit:
    source_uid = unit_kwargs.pop("source_uid")
    unit, _created = Unit.objects.update_or_create(
        source_uid=source_uid,
        defaults={**unit_kwargs, "faction": faction},
    )
    return unit


def _upsert_weapon(weapon_kwargs: dict[str, Any]) -> Weapon:
    source_uid = weapon_kwargs.pop("source_uid")
    weapon, _created = Weapon.objects.update_or_create(
        source_uid=source_uid,
        defaults=weapon_kwargs,
    )
    return weapon


def _sync_unit_upgrades(
    unit: Unit,
    raw_unit: dict[str, Any],
    upgrade_packages: dict[str, dict[str, Any]],
) -> None:
    seen_sections: set[str] = set()
    for package in _resolved_upgrade_packages(raw_unit, upgrade_packages):
        package_uid = str(_source_uid(package) or "")
        for raw_section in _upgrade_sections(package):
            section_uid = _upgrade_section_uid(raw_section)
            if not section_uid:
                continue
            seen_sections.add(section_uid)
            section, _created = UnitUpgradeSection.objects.update_or_create(
                unit=unit,
                section_uid=section_uid,
                defaults={
                    "package_uid": package_uid,
                    "label": str(raw_section.get("label") or ""),
                    "variant": str(raw_section.get("variant") or ""),
                    "targets": _upgrade_targets(raw_section),
                },
            )
            _sync_upgrade_options(section, raw_section, unit)

    unit.upgrade_sections.exclude(section_uid__in=seen_sections).delete()


def _sync_upgrade_options(
    section: UnitUpgradeSection,
    raw_section: dict[str, Any],
    unit: Unit,
) -> None:
    seen_options: set[str] = set()
    for raw_option in _upgrade_options(raw_section):
        option_uid = _upgrade_option_uid(raw_option)
        if not option_uid:
            continue
        seen_options.add(option_uid)
        option, _created = UnitUpgradeOption.objects.update_or_create(
            section=section,
            option_uid=option_uid,
            defaults={
                "label": str(raw_option.get("label") or ""),
                "cost": _option_cost(raw_option, unit.source_uid),
                "gains": _non_weapon_gains(raw_option),
            },
        )
        _sync_option_weapons(option, raw_option)
    section.options.exclude(option_uid__in=seen_options).delete()


def _sync_option_weapons(option: UnitUpgradeOption, raw_option: dict[str, Any]) -> None:
    seen_weapon_ids: set[int] = set()
    for raw_weapon in _gained_weapons(raw_option):
        weapon = _upsert_weapon(parse_weapon(raw_weapon))
        UnitUpgradeOptionWeapon.objects.update_or_create(option=option, weapon=weapon)
        seen_weapon_ids.add(weapon.id)
    option.option_weapons.exclude(weapon_id__in=seen_weapon_ids).delete()


def _source_uid(raw: dict[str, Any]) -> str | None:
    return raw.get("source_uid") or raw.get("uid") or raw.get("id")


def _units(book: dict[str, Any]) -> list[dict[str, Any]]:
    return book.get("units") or book.get("profiles") or []


def _spells(book: dict[str, Any]) -> list[dict[str, Any]]:
    spells = book.get("spells") or []
    return [spell for spell in spells if isinstance(spell, dict)]


def _weapons(unit: dict[str, Any]) -> list[dict[str, Any]]:
    return unit.get("weapons") or unit.get("loadout") or []


def _weapon_options(unit: dict[str, Any]) -> list[tuple[dict[str, Any], bool, int, str | None, str | None]]:
    options = [(weapon, True, 0, None, None) for weapon in _weapons(unit)]
    for upgrade in _upgrades(unit):
        upgrade_cost = _upgrade_cost(upgrade)
        option_id = _upgrade_option_id(upgrade)
        for weapon in _weapons(upgrade):
            options.append(
                (
                    weapon,
                    bool(upgrade.get("isDefault", False)),
                    upgrade_cost,
                    option_id,
                    _upgrade_id(upgrade, weapon),
                )
            )
    return options


def _upgrades(unit: dict[str, Any]) -> list[dict[str, Any]]:
    upgrades = unit.get("upgrades") or unit.get("upgradePackages") or unit.get("options") or []
    return [upgrade for upgrade in upgrades if isinstance(upgrade, dict)]


def _upgrade_package_lookup(book: dict[str, Any]) -> dict[str, dict[str, Any]]:
    packages = book.get("upgradePackages") or []
    lookup: dict[str, dict[str, Any]] = {}
    for package in packages:
        if not isinstance(package, dict):
            continue
        for key in (_source_uid(package), package.get("uid"), package.get("id")):
            if key:
                lookup[str(key)] = package
    return lookup


def _resolved_upgrade_packages(
    unit: dict[str, Any],
    upgrade_packages: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    raw_upgrades = unit.get("upgrades") or unit.get("upgradePackages") or unit.get("options") or []
    packages: list[dict[str, Any]] = []
    for raw_upgrade in raw_upgrades:
        if isinstance(raw_upgrade, dict):
            packages.append(raw_upgrade)
        elif str(raw_upgrade) in upgrade_packages:
            packages.append(upgrade_packages[str(raw_upgrade)])
    return packages


def _upgrade_sections(package: dict[str, Any]) -> list[dict[str, Any]]:
    sections = package.get("sections")
    if isinstance(sections, list):
        return [section for section in sections if isinstance(section, dict)]
    if "options" in package:
        return [package]
    return []


def _upgrade_section_uid(section: dict[str, Any]) -> str | None:
    value = section.get("uid") or section.get("sectionUid") or section.get("sectionId") or section.get("id")
    return str(value) if value else None


def _upgrade_targets(section: dict[str, Any]) -> list[str]:
    targets = section.get("targets") or []
    if not isinstance(targets, list):
        return []
    return [str(target) for target in targets]


def _upgrade_options(section: dict[str, Any]) -> list[dict[str, Any]]:
    options = section.get("options") or []
    return [option for option in options if isinstance(option, dict)]


def _upgrade_option_uid(option: dict[str, Any]) -> str | None:
    value = option.get("uid") or option.get("optionUid") or option.get("optionId") or option.get("id")
    return str(value) if value else None


def _option_cost(option: dict[str, Any], unit_uid: str | None) -> int:
    costs = option.get("costs")
    if isinstance(costs, list):
        for raw_cost in costs:
            if not isinstance(raw_cost, dict):
                continue
            if str(raw_cost.get("unitId")) == str(unit_uid):
                return _safe_int(raw_cost.get("cost"))
    return _upgrade_cost(option)


def _gained_weapons(option: dict[str, Any]) -> list[dict[str, Any]]:
    gains = option.get("gains") or option.get("weapons") or []
    if not isinstance(gains, list):
        return []
    return [
        gain
        for gain in gains
        if isinstance(gain, dict) and str(gain.get("type") or "").lower().endswith("weapon")
    ]


def _non_weapon_gains(option: dict[str, Any]) -> list[dict[str, Any]]:
    gains = option.get("gains") or []
    if not isinstance(gains, list):
        return []
    return [
        gain
        for gain in gains
        if isinstance(gain, dict) and not str(gain.get("type") or "").lower().endswith("weapon")
    ]


def _upgrade_cost(upgrade: dict[str, Any]) -> int:
    raw_cost = (
        upgrade.get("upgrade_cost")
        or upgrade.get("upgradeCost")
        or upgrade.get("cost")
        or upgrade.get("points")
        or 0
    )
    try:
        return int(raw_cost)
    except (TypeError, ValueError):
        return 0


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _upgrade_option_id(upgrade: dict[str, Any]) -> str | None:
    return (
        upgrade.get("optionId")
        or upgrade.get("option_id")
        or upgrade.get("optionUID")
        or upgrade.get("optionUid")
        or upgrade.get("uid")
        or upgrade.get("id")
        or upgrade.get("source_uid")
    )


def _upgrade_id(upgrade: dict[str, Any], weapon: dict[str, Any]) -> str | None:
    return (
        weapon.get("upgradeId")
        or weapon.get("upgrade_id")
        or weapon.get("upgradeUID")
        or weapon.get("upgradeUid")
        or upgrade.get("upgradeId")
        or upgrade.get("upgrade_id")
        or weapon.get("uid")
        or weapon.get("id")
        or weapon.get("source_uid")
    )
