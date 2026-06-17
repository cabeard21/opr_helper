from django.test import TestCase

from army_books.models import Faction, Unit, UnitWeaponSlot, Weapon
from lists.models import ArmyList, ListUnit


class ListModelTests(TestCase):
    def test_army_list_defaults_relationships_and_string(self):
        faction = Faction.objects.create(name="Kingdom of Angels", version="3.5.1")
        army_list = ArmyList.objects.create(
            name="Tournament 2000",
            faction=faction,
            point_limit=2000,
        )

        self.assertEqual(str(army_list), "Tournament 2000 (2000 pts)")
        self.assertEqual(army_list.faction, faction)
        self.assertEqual(faction.army_lists.get(), army_list)
        self.assertIsNotNone(army_list.created_at)
        self.assertIsNotNone(army_list.updated_at)

    def test_list_unit_defaults_relationships_and_string(self):
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
        army_list = ArmyList.objects.create(
            name="Tournament 2000",
            faction=faction,
            point_limit=2000,
        )
        list_unit = ListUnit.objects.create(
            army_list=army_list,
            unit=unit,
            model_count=3,
            selected_weapon_slot=slot,
            notes="Hold center.",
        )

        self.assertEqual(str(list_unit), "3x Paladins")
        self.assertEqual(list_unit.army_list, army_list)
        self.assertEqual(list_unit.unit, unit)
        self.assertEqual(list_unit.selected_weapon_slot, slot)
        self.assertEqual(list_unit.notes, "Hold center.")
        self.assertEqual(army_list.units.get(), list_unit)

