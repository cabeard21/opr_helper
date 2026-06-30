from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from army_books.models import (
    Faction,
    FactionSpell,
    Unit,
    UnitUpgradeOption,
    UnitUpgradeSection,
    UnitWeaponSlot,
    Weapon,
)


BOOK_LIST = [
    {
        "uid": "faction-angels",
        "name": "Kingdom of Angels",
        "versionString": "3.5.3",
    }
]

BOOK_DETAIL = {
    "uid": "faction-angels",
    "name": "Kingdom of Angels",
    "versionString": "3.5.3",
    "spells": [
        {
            "id": "spell-shield",
            "name": "Shield Wall",
            "type": 1,
            "effect": 'Pick one friendly unit within 12", which gets +1 to Defense rolls.',
            "threshold": 2,
            "spellbookId": "angel-book",
        }
    ],
    "units": [
        {
            "id": "unit-paladins",
            "name": "Paladins",
            "quality": 3,
            "defense": 4,
            "cost": 180,
            "rules": [
                {"id": "rule-fearless", "name": "Fearless", "label": "Fearless"},
                {"id": "rule-tough", "name": "Tough", "rating": 3, "label": "Tough(3)"},
            ],
            "weapons": [
                {
                    "id": "weapon-great",
                    "name": "Great Weapon",
                    "range": 0,
                    "attacks": 2,
                    "specialRules": [
                        {"id": "rule-ap", "name": "AP", "rating": 2, "label": "AP(2)"},
                        {
                            "id": "rule-deadly",
                            "name": "Deadly",
                            "rating": 3,
                            "label": "Deadly(3)",
                        },
                    ],
                }
            ],
            "upgrades": [
                {
                    "optionId": "option-blessed-weapons",
                    "cost": 25,
                    "weapons": [
                        {
                            "id": "weapon-blessed-great",
                            "upgradeId": "upgrade-blessed-great",
                            "name": "Blessed Great Weapon",
                            "range": 0,
                            "attacks": 2,
                            "specialRules": [
                                {"id": "rule-ap", "name": "AP", "rating": 3, "label": "AP(3)"}
                            ],
                        }
                    ],
                }
            ],
        }
    ],
}

BULL_BOOK_DETAIL = {
    "uid": "faction-havoc-dwarves",
    "name": "Havoc Dwarves",
    "versionString": "3.5.3",
    "units": [
        {
            "id": "bOv6BGK",
            "name": "Bull Construct",
            "quality": 4,
            "defense": 2,
            "cost": 235,
            "size": 1,
            "rules": [{"name": "Tough", "rating": 9}],
            "weapons": [
                {
                    "id": "BTEKkW8x",
                    "name": "Heavy Great Weapon",
                    "range": 0,
                    "attacks": 6,
                    "specialRules": [{"name": "AP", "rating": 4}],
                },
                {
                    "id": "qSPHZX1J",
                    "name": "Stomp",
                    "range": 0,
                    "attacks": 3,
                    "specialRules": [{"name": "AP", "rating": 1}],
                },
            ],
            "upgrades": ["X2LU7GIa"],
        }
    ],
    "upgradePackages": [
        {
            "uid": "X2LU7GIa",
            "hint": "Bull Construct",
            "sections": [
                {
                    "id": "MoFv9P0",
                    "uid": "m5Fl4_I9XF",
                    "label": "Replace Heavy Great Weapon",
                    "variant": "replace",
                    "targets": ["Heavy Great Weapon"],
                    "options": [
                        {
                            "uid": "2-liYIN7tu",
                            "id": "2-liYIN7tu",
                            "costs": [{"cost": 35, "unitId": "bOv6BGK"}],
                            "label": 'Twin Arm-Flamethrowers (12", A3, AP(1), Blast(3), Reliable)',
                            "gains": [
                                {
                                    "id": None,
                                    "name": "Twin Arm-Flamethrowers",
                                    "type": "ArmyBookWeapon",
                                    "range": 12,
                                    "attacks": 3,
                                    "weaponId": "3fOjuT5u",
                                    "specialRules": [
                                        {"name": "AP", "rating": 1},
                                        {"name": "Blast", "rating": 3},
                                        {"name": "Reliable"},
                                    ],
                                }
                            ],
                        }
                    ],
                }
            ],
        }
    ],
}

RATMEN_WEAPON_TEAMS_BOOK_DETAIL = {
    "uid": "faction-ratmen",
    "name": "Ratmen",
    "versionString": "3.5.3",
    "units": [
        {
            "id": "wXtqtYK",
            "name": "Weapon Teams",
            "quality": 5,
            "defense": 5,
            "cost": 110,
            "size": 3,
            "rules": [{"name": "Tough", "rating": 3}],
            "weapons": [
                {
                    "id": "4DJN0QXy",
                    "weaponId": "5bdTXzzH",
                    "name": "Crew",
                    "count": 3,
                    "range": 0,
                    "attacks": 1,
                    "specialRules": [],
                },
                {
                    "id": "xpLVuWlR",
                    "weaponId": "ESfMmujC",
                    "name": "Heavy Drill",
                    "count": 3,
                    "range": 0,
                    "attacks": 1,
                    "specialRules": [
                        {"name": "AP", "rating": 4},
                        {"name": "Deadly", "rating": 3},
                    ],
                },
            ],
            "upgrades": ["F1"],
        }
    ],
    "upgradePackages": [
        {
            "uid": "F1",
            "sections": [
                {
                    "uid": "MwsXsbn",
                    "label": "Replace any Heavy Drill",
                    "variant": "replace",
                    "affects": {"type": "any"},
                    "targets": ["Heavy Drill"],
                    "options": [
                        {
                            "uid": "VurkaS1",
                            "costs": [{"cost": 5, "unitId": "wXtqtYK"}],
                            "label": 'Gatling Gun (18", A4, AP(1))',
                            "gains": [
                                {
                                    "weaponId": "xpLVuWlR",
                                    "name": "Gatling Gun",
                                    "count": 1,
                                    "range": 18,
                                    "attacks": 4,
                                    "type": "ArmyBookWeapon",
                                    "specialRules": [{"name": "AP", "rating": 1}],
                                }
                            ],
                        }
                    ],
                }
            ],
        }
    ],
}


class SyncArmyBooksCommandTests(TestCase):
    @patch("army_books.management.commands.sync_army_books.fetch_army_book")
    @patch("army_books.management.commands.sync_army_books.fetch_army_book_list")
    def test_sync_creates_faction_units_weapons_and_slots(
        self,
        mock_fetch_list,
        mock_fetch_book,
    ):
        mock_fetch_list.return_value = BOOK_LIST
        mock_fetch_book.return_value = BOOK_DETAIL

        call_command("sync_army_books")

        faction = Faction.objects.get(source_uid="faction-angels")
        unit = Unit.objects.get(source_uid="unit-paladins")
        weapon = Weapon.objects.get(source_uid="weapon-great")
        slot = UnitWeaponSlot.objects.get(unit=unit, weapon=weapon)

        self.assertEqual(faction.name, "Kingdom of Angels")
        self.assertEqual(faction.version, "3.5.3")
        self.assertEqual(unit.faction, faction)
        self.assertEqual(unit.quality, 3)
        self.assertEqual(unit.tough, 3)
        self.assertEqual(weapon.ap, 2)
        self.assertEqual(weapon.special_rules, {"Deadly": 3})
        self.assertTrue(slot.is_default)
        spell = FactionSpell.objects.get(faction=faction, source_uid="spell-shield")
        self.assertEqual(spell.name, "Shield Wall")
        self.assertEqual(spell.threshold, 2)
        self.assertEqual(spell.spellbook_id, "angel-book")
        upgrade = UnitWeaponSlot.objects.get(unit=unit, weapon__source_uid="weapon-blessed-great")
        self.assertFalse(upgrade.is_default)
        self.assertEqual(upgrade.upgrade_cost, 25)
        self.assertEqual(upgrade.option_id, "option-blessed-weapons")
        self.assertEqual(upgrade.upgrade_id, "upgrade-blessed-great")

    @patch("army_books.management.commands.sync_army_books.fetch_army_book")
    @patch("army_books.management.commands.sync_army_books.fetch_army_book_list")
    def test_sync_is_idempotent(self, mock_fetch_list, mock_fetch_book):
        mock_fetch_list.return_value = BOOK_LIST
        mock_fetch_book.return_value = BOOK_DETAIL

        call_command("sync_army_books")
        call_command("sync_army_books")

        self.assertEqual(Faction.objects.count(), 1)
        self.assertEqual(Unit.objects.count(), 1)
        self.assertEqual(Weapon.objects.count(), 2)
        self.assertEqual(UnitWeaponSlot.objects.count(), 2)

    @patch("army_books.management.commands.sync_army_books.fetch_army_book")
    @patch("army_books.management.commands.sync_army_books.fetch_army_book_list")
    def test_sync_resolves_referenced_upgrade_packages(self, mock_fetch_list, mock_fetch_book):
        mock_fetch_list.return_value = [
            {
                "uid": "faction-havoc-dwarves",
                "name": "Havoc Dwarves",
                "versionString": "3.5.3",
            }
        ]
        mock_fetch_book.return_value = BULL_BOOK_DETAIL

        call_command("sync_army_books")

        bull = Unit.objects.get(source_uid="bOv6BGK")
        default_weapons = list(
            bull.weapon_slots.filter(is_default=True)
            .order_by("weapon__name")
            .values_list("weapon__name", flat=True)
        )
        self.assertEqual(default_weapons, ["Heavy Great Weapon", "Stomp"])

        section = UnitUpgradeSection.objects.get(unit=bull)
        self.assertEqual(section.package_uid, "X2LU7GIa")
        self.assertEqual(section.section_uid, "m5Fl4_I9XF")
        self.assertEqual(section.label, "Replace Heavy Great Weapon")
        self.assertEqual(section.variant, "replace")
        self.assertEqual(section.targets, ["Heavy Great Weapon"])

        option = UnitUpgradeOption.objects.get(section=section)
        self.assertEqual(option.option_uid, "2-liYIN7tu")
        self.assertEqual(option.cost, 35)
        self.assertEqual(option.gains, [])
        self.assertEqual(
            list(option.weapons.values_list("name", flat=True)),
            ["Twin Arm-Flamethrowers"],
        )

    @patch("army_books.management.commands.sync_army_books.fetch_army_book")
    @patch("army_books.management.commands.sync_army_books.fetch_army_book_list")
    def test_sync_preserves_weapon_ids_counts_and_replace_any_metadata(
        self,
        mock_fetch_list,
        mock_fetch_book,
    ):
        mock_fetch_list.return_value = [
            {
                "uid": "faction-ratmen",
                "name": "Ratmen",
                "versionString": "3.5.3",
            }
        ]
        mock_fetch_book.return_value = RATMEN_WEAPON_TEAMS_BOOK_DETAIL

        call_command("sync_army_books")

        unit = Unit.objects.get(source_uid="wXtqtYK")
        slots = {
            slot.weapon.name: slot
            for slot in unit.weapon_slots.select_related("weapon").order_by("weapon__name")
        }
        self.assertEqual(set(slots), {"Crew", "Heavy Drill"})
        self.assertEqual(slots["Heavy Drill"].weapon.source_uid, "ESfMmujC")
        self.assertEqual(slots["Heavy Drill"].count, 3)

        section = UnitUpgradeSection.objects.get(unit=unit)
        self.assertEqual(section.affects, {"type": "any"})
        option = UnitUpgradeOption.objects.get(section=section)
        option_link = option.option_weapons.select_related("weapon").get()
        self.assertEqual(option_link.weapon.name, "Gatling Gun")
        self.assertEqual(option_link.weapon.source_uid, "xpLVuWlR")
        self.assertEqual(option_link.count, 1)

    @patch("army_books.management.commands.sync_army_books.fetch_army_book")
    @patch("army_books.management.commands.sync_army_books.fetch_army_book_list")
    def test_re_sync_removes_stale_weapon_slots(self, mock_fetch_list, mock_fetch_book):
        mock_fetch_list.return_value = BOOK_LIST
        mock_fetch_book.return_value = BOOK_DETAIL

        call_command("sync_army_books")
        updated = {
            **BOOK_DETAIL,
            "units": [{**BOOK_DETAIL["units"][0], "weapons": [], "upgrades": []}],
        }
        mock_fetch_book.return_value = updated
        call_command("sync_army_books")

        self.assertEqual(UnitWeaponSlot.objects.count(), 0)

    @patch("army_books.management.commands.sync_army_books.fetch_army_book")
    @patch("army_books.management.commands.sync_army_books.fetch_army_book_list")
    def test_re_sync_removes_stale_upgrade_metadata(self, mock_fetch_list, mock_fetch_book):
        mock_fetch_list.return_value = [
            {
                "uid": "faction-havoc-dwarves",
                "name": "Havoc Dwarves",
                "versionString": "3.5.3",
            }
        ]
        mock_fetch_book.return_value = BULL_BOOK_DETAIL

        call_command("sync_army_books")
        updated = {**BULL_BOOK_DETAIL, "upgradePackages": []}
        updated["units"] = [{**BULL_BOOK_DETAIL["units"][0], "upgrades": []}]
        mock_fetch_book.return_value = updated
        call_command("sync_army_books")

        self.assertEqual(UnitUpgradeSection.objects.count(), 0)
        self.assertEqual(UnitUpgradeOption.objects.count(), 0)

    @patch("army_books.management.commands.sync_army_books.fetch_army_book")
    @patch("army_books.management.commands.sync_army_books.fetch_army_book_list")
    def test_re_sync_removes_stale_spell_metadata(self, mock_fetch_list, mock_fetch_book):
        mock_fetch_list.return_value = BOOK_LIST
        mock_fetch_book.return_value = BOOK_DETAIL

        call_command("sync_army_books")
        updated = {**BOOK_DETAIL, "spells": []}
        mock_fetch_book.return_value = updated
        call_command("sync_army_books")

        self.assertEqual(FactionSpell.objects.count(), 0)

    @patch("army_books.management.commands.sync_army_books.fetch_army_book")
    @patch("army_books.management.commands.sync_army_books.fetch_army_book_list")
    def test_dry_run_does_not_write_records(self, mock_fetch_list, mock_fetch_book):
        mock_fetch_list.return_value = BOOK_LIST
        mock_fetch_book.return_value = BOOK_DETAIL

        call_command("sync_army_books", dry_run=True)

        self.assertEqual(Faction.objects.count(), 0)
        self.assertEqual(Unit.objects.count(), 0)
        self.assertEqual(Weapon.objects.count(), 0)
        self.assertEqual(UnitWeaponSlot.objects.count(), 0)

    @patch("army_books.management.commands.sync_army_books.fetch_army_book_list")
    def test_empty_book_list_exits_without_error(self, mock_fetch_list):
        mock_fetch_list.return_value = []

        call_command("sync_army_books")

        self.assertEqual(Faction.objects.count(), 0)
