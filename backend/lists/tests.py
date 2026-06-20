from django.test import TestCase

from army_books.models import Faction, Unit, UnitUpgradeOption, UnitUpgradeSection, UnitWeaponSlot, Weapon
from lists.analysis import TargetProfile, analyze_army_list
from lists.models import ArmyList, ListUnit, ListUnitUpgrade
from lists.validation import list_unit_points


class ListModelTests(TestCase):
    def test_army_list_defaults_relationships_and_string(self):
        faction = Faction.objects.create(name="Kingdom of Angels", version="3.5.1")
        army_list = ArmyList.objects.create(
            name="Tournament 2000",
            faction=faction,
            point_limit=2000,
            advisor_archetype="Offensive Elite",
            advisor_playstyle="Shove It In",
            advisor_strategy_summary="Push the center and score with support pieces.",
            advisor_prompt="Aggressive elite list.",
            advisor_warnings=["Low activation count."],
        )

        self.assertEqual(str(army_list), "Tournament 2000 (2000 pts)")
        self.assertEqual(army_list.faction, faction)
        self.assertEqual(faction.army_lists.get(), army_list)
        self.assertEqual(army_list.advisor_archetype, "Offensive Elite")
        self.assertEqual(army_list.advisor_warnings, ["Low activation count."])
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
            combined_from_count=2,
            notes="Hold center.",
        )

        self.assertEqual(str(list_unit), "3x Paladins")
        self.assertEqual(list_unit.army_list, army_list)
        self.assertEqual(list_unit.unit, unit)
        self.assertEqual(list_unit.selected_weapon_slot, slot)
        self.assertEqual(list_unit.combined_from_count, 2)
        self.assertEqual(list_unit.notes, "Hold center.")
        self.assertEqual(army_list.units.get(), list_unit)

    def test_list_unit_points_use_default_size_unit_cost_plus_upgrades(self):
        faction = Faction.objects.create(name="Disciples of War", version="3.5.3")
        unit = Unit.objects.create(
            faction=faction,
            name="Cultists",
            quality=5,
            defense=6,
            tough=1,
            points=65,
            min_models=10,
            max_models=20,
            default_models=10,
        )
        section = UnitUpgradeSection.objects.create(
            unit=unit,
            section_uid="cultist-weapons",
            label="Take Icon",
        )
        option = UnitUpgradeOption.objects.create(
            section=section,
            option_uid="icon",
            label="Icon",
            cost=10,
        )
        army_list = ArmyList.objects.create(name="750", faction=faction, point_limit=750)
        entry = ListUnit.objects.create(
            army_list=army_list,
            unit=unit,
            model_count=10,
            combined_from_count=2,
        )
        ListUnitUpgrade.objects.create(list_unit=entry, option=option)

        self.assertEqual(list_unit_points(entry), 150)

    def test_embedded_aura_applies_only_to_owner_and_host(self):
        faction = Faction.objects.create(name="Kingdom of Angels", version="3.5.3")
        weapon = Weapon.objects.create(
            name="Hand Weapon",
            range=0,
            attacks=1,
            attacks_string="A1",
            ap=0,
        )
        host_unit = Unit.objects.create(
            faction=faction,
            name="Guardians",
            quality=4,
            defense=5,
            tough=1,
            points=90,
            min_models=5,
            max_models=10,
            default_models=5,
        )
        other_unit = Unit.objects.create(
            faction=faction,
            name="Rangers",
            quality=4,
            defense=5,
            tough=1,
            points=90,
            min_models=5,
            max_models=10,
            default_models=5,
        )
        hero_unit = Unit.objects.create(
            faction=faction,
            name="Battle Captain",
            quality=4,
            defense=5,
            tough=1,
            points=75,
            special_rules={"Hero": True},
        )
        UnitWeaponSlot.objects.create(unit=host_unit, weapon=weapon, is_default=True)
        UnitWeaponSlot.objects.create(unit=other_unit, weapon=weapon, is_default=True)
        UnitWeaponSlot.objects.create(unit=hero_unit, weapon=weapon, is_default=True)
        section = UnitUpgradeSection.objects.create(
            unit=hero_unit,
            section_uid="captain-aura",
            label="Take Aura",
        )
        aura = UnitUpgradeOption.objects.create(
            section=section,
            option_uid="furious-aura",
            label="Furious Aura",
            cost=0,
            gains=[
                {
                    "content": [
                        {
                            "name": "Furious Aura",
                            "type": "ArmyBookRule",
                        }
                    ]
                }
            ],
        )
        army_list = ArmyList.objects.create(name="Aura Test", faction=faction, point_limit=2000)
        host = ListUnit.objects.create(army_list=army_list, unit=host_unit, model_count=5)
        other = ListUnit.objects.create(army_list=army_list, unit=other_unit, model_count=5)
        hero = ListUnit.objects.create(
            army_list=army_list,
            unit=hero_unit,
            model_count=1,
            parent_entry=host,
        )
        ListUnitUpgrade.objects.create(list_unit=hero, option=aura)

        analyzed = analyze_army_list(
            ArmyList.objects.prefetch_related(
                "units__unit__weapon_slots__weapon",
                "units__selected_upgrades__option__section",
                "units__selected_upgrades__option__weapons",
            ).get(id=army_list.id),
            [TargetProfile(id="test", name="Test", defense=5, tough=1)],
        )

        ev_by_name = {
            unit["unit_name"]: unit["target_results"][0]["ev"]
            for unit in analyzed["units"]
        }
        self.assertEqual(ev_by_name["Guardians"], 2.0)
        self.assertEqual(ev_by_name["Battle Captain"], 0.333333)
        self.assertEqual(ev_by_name["Rangers"], 1.666667)

