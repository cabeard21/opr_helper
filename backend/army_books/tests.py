from django.test import TestCase

from army_books.models import Faction, Unit, UnitWeaponSlot, Weapon


class ArmyBookModelTests(TestCase):
    def test_faction_defaults_and_string(self):
        faction = Faction.objects.create(
            name="Kingdom of Angels",
            version="3.5.1",
            source_uid="aof-angels",
            source_slug="kingdom-of-angels",
        )

        self.assertEqual(str(faction), "Kingdom of Angels")
        self.assertIsNone(faction.last_fetched)
        self.assertEqual(faction.source_uid, "aof-angels")
        self.assertEqual(faction.source_slug, "kingdom-of-angels")

    def test_unit_defaults_relationships_and_string(self):
        faction = Faction.objects.create(name="Kingdom of Angels", version="3.5.1")
        unit = Unit.objects.create(
            faction=faction,
            name="Paladins",
            quality=3,
            defense=3,
            tough=3,
            points=180,
            source_uid="unit-paladins",
        )

        self.assertEqual(str(unit), "Paladins")
        self.assertEqual(unit.special_rules, {})
        self.assertEqual(unit.faction, faction)
        self.assertEqual(faction.units.get(), unit)
        self.assertEqual(unit.source_uid, "unit-paladins")

    def test_weapon_defaults_and_string(self):
        weapon = Weapon.objects.create(
            name="Great Weapon",
            range=0,
            attacks=2.0,
            attacks_string="A2",
            ap=2,
            special_rules={"Deadly": "3"},
            source_uid="weapon-great",
        )

        self.assertEqual(str(weapon), "Great Weapon")
        self.assertEqual(weapon.range, 0)
        self.assertEqual(weapon.attacks, 2.0)
        self.assertEqual(weapon.attacks_string, "A2")
        self.assertEqual(weapon.ap, 2)
        self.assertEqual(weapon.special_rules, {"Deadly": "3"})
        self.assertEqual(weapon.source_uid, "weapon-great")

    def test_unit_weapon_slot_defaults_relationships_and_string(self):
        faction = Faction.objects.create(name="Kingdom of Angels", version="3.5.1")
        unit = Unit.objects.create(
            faction=faction,
            name="Paladins",
            quality=3,
            defense=3,
            tough=3,
            points=180,
        )
        weapon = Weapon.objects.create(
            name="Great Weapon",
            range=0,
            attacks=2.0,
            attacks_string="A2",
            ap=2,
        )
        slot = UnitWeaponSlot.objects.create(unit=unit, weapon=weapon)

        self.assertTrue(slot.is_default)
        self.assertEqual(slot.upgrade_cost, 0)
        self.assertEqual(slot.unit, unit)
        self.assertEqual(slot.weapon, weapon)
        self.assertEqual(unit.weapon_slots.get(), slot)
        self.assertEqual(str(slot), "Paladins: Great Weapon")

