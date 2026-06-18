from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from army_books.models import Faction, Unit, UnitWeaponSlot, Weapon


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
                    "cost": 25,
                    "weapons": [
                        {
                            "id": "weapon-blessed-great",
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
        upgrade = UnitWeaponSlot.objects.get(unit=unit, weapon__source_uid="weapon-blessed-great")
        self.assertFalse(upgrade.is_default)
        self.assertEqual(upgrade.upgrade_cost, 25)

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
