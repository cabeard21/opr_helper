from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from army_books.models import Faction, Unit, UnitWeaponSlot, Weapon
from army_books.opr_client import fetch_army_book, fetch_army_book_list
from army_books.parsers import parse_unit, parse_weapon


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

        summary = {"factions": 0, "units": 0, "weapons": 0, "slots": 0}
        for listed_book in books:
            uid = _source_uid(listed_book)
            if not uid:
                self.stdout.write(self.style.WARNING("Skipping army book without uid."))
                continue

            detail = fetch_army_book(uid, game_system_slug=game_system)
            if dry_run:
                summary["factions"] += 1
                summary["units"] += len(_units(detail))
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
                f"{summary['slots']} weapon slots."
            )
        )


def _sync_book(book: dict[str, Any], fallback: dict[str, Any]) -> dict[str, int]:
    merged_book = {**fallback, **book}
    faction = _upsert_faction(merged_book)
    summary = {"factions": 1, "units": 0, "weapons": 0, "slots": 0}

    for raw_unit in _units(merged_book):
        unit_kwargs = parse_unit(raw_unit)
        unit = _upsert_unit(faction, unit_kwargs)
        summary["units"] += 1

        for raw_weapon, is_default, upgrade_cost in _weapon_options(raw_unit):
            weapon_kwargs = parse_weapon(raw_weapon)
            weapon = _upsert_weapon(weapon_kwargs)
            UnitWeaponSlot.objects.update_or_create(
                unit=unit,
                weapon=weapon,
                defaults={"is_default": is_default, "upgrade_cost": upgrade_cost},
            )
            summary["weapons"] += 1
            summary["slots"] += 1

    return summary


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


def _source_uid(raw: dict[str, Any]) -> str | None:
    return raw.get("source_uid") or raw.get("uid") or raw.get("id")


def _units(book: dict[str, Any]) -> list[dict[str, Any]]:
    return book.get("units") or book.get("profiles") or []


def _weapons(unit: dict[str, Any]) -> list[dict[str, Any]]:
    return unit.get("weapons") or unit.get("loadout") or []


def _weapon_options(unit: dict[str, Any]) -> list[tuple[dict[str, Any], bool, int]]:
    options = [(weapon, True, 0) for weapon in _weapons(unit)]
    for upgrade in _upgrades(unit):
        upgrade_cost = _upgrade_cost(upgrade)
        for weapon in _weapons(upgrade):
            options.append((weapon, bool(upgrade.get("isDefault", False)), upgrade_cost))
    return options


def _upgrades(unit: dict[str, Any]) -> list[dict[str, Any]]:
    upgrades = unit.get("upgrades") or unit.get("upgradePackages") or unit.get("options") or []
    return [upgrade for upgrade in upgrades if isinstance(upgrade, dict)]


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
