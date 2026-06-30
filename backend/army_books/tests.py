from django.test import TestCase

from army_books.models import Faction, Unit, UnitUpgradeOption, UnitUpgradeSection, UnitWeaponSlot, Weapon
from army_books.upgrade_resolution import resolve_unit_upgrade_options


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
        self.assertEqual(unit.min_models, 1)
        self.assertIsNone(unit.max_models)
        self.assertEqual(unit.default_models, 1)
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


class UpgradeResolutionTests(TestCase):
    def setUp(self):
        self.faction = Faction.objects.create(name="Eternal Wardens", version="3.5.3")
        self.unit = Unit.objects.create(
            faction=self.faction,
            name="Winged Wardens",
            quality=4,
            defense=4,
            tough=1,
            points=100,
        )
        self.hand_weapon = Weapon.objects.create(
            name="Hand Weapon",
            range=0,
            attacks=1,
            attacks_string="A1",
            ap=0,
        )
        self.javelin = Weapon.objects.create(
            name="Javelin",
            range=12,
            attacks=1,
            attacks_string="A1",
            ap=0,
        )
        self.storm_trident = Weapon.objects.create(
            name="Storm Trident",
            range=18,
            attacks=1,
            attacks_string="A1",
            ap=2,
        )
        UnitWeaponSlot.objects.create(unit=self.unit, weapon=self.hand_weapon, is_default=True)
        self.javelin_section = UnitUpgradeSection.objects.create(
            unit=self.unit,
            section_uid="winged-warden-javelins",
            label="Take Javelins",
            variant="upgrade",
        )
        self.javelins = UnitUpgradeOption.objects.create(
            section=self.javelin_section,
            option_uid="javelins",
            label="Javelins",
            cost=10,
        )
        self.javelins.weapons.add(self.javelin)
        self.trident_section = UnitUpgradeSection.objects.create(
            unit=self.unit,
            section_uid="winged-warden-trident",
            label="Replace one Javelin",
            variant="replace",
            targets=["Javelins"],
        )
        self.trident = UnitUpgradeOption.objects.create(
            section=self.trident_section,
            option_uid="storm-trident",
            label="Storm Trident",
            cost=15,
        )
        self.trident.weapons.add(self.storm_trident)

    def test_dependent_replace_upgrade_adds_prerequisite_option(self):
        resolution = resolve_unit_upgrade_options(
            self.unit,
            [self.trident],
            warn_on_added_prerequisites=True,
        )

        self.assertTrue(resolution.is_valid)
        self.assertEqual(resolution.option_ids, [self.javelins.id, self.trident.id])
        self.assertEqual(
            resolution.warnings,
            ["Winged Wardens added Javelins because Storm Trident requires it."],
        )

    def test_dependent_replace_upgrade_rejects_conflicting_prerequisite_section(self):
        darts = UnitUpgradeOption.objects.create(
            section=self.javelin_section,
            option_uid="darts",
            label="Darts",
            cost=5,
        )

        resolution = resolve_unit_upgrade_options(self.unit, [darts, self.trident])

        self.assertFalse(resolution.is_valid)
        self.assertIn("Storm Trident requires a weapon matching Javelins.", resolution.errors)

