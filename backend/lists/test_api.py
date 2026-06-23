from django.test import TestCase
from rest_framework.test import APIClient

from army_books.models import (
    Faction,
    Unit,
    UnitUpgradeOption,
    UnitUpgradeOptionWeapon,
    UnitUpgradeSection,
    UnitWeaponSlot,
    Weapon,
)
from lists.models import ArmyList, ListUnit, ListUnitUpgrade


class ListsApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.faction = Faction.objects.create(
            name="Kingdom of Angels",
            version="3.5.3",
            source_uid="army-angels",
        )
        self.unit = Unit.objects.create(
            faction=self.faction,
            name="Paladins",
            quality=3,
            defense=4,
            tough=3,
            points=180,
            max_models=4,
            source_uid="unit-paladins",
        )
        self.hero = Unit.objects.create(
            faction=self.faction,
            name="Champion",
            quality=3,
            defense=4,
            tough=3,
            points=95,
            special_rules={"Hero": True},
            source_uid="unit-champion",
        )
        self.guard = Unit.objects.create(
            faction=self.faction,
            name="Guardians",
            quality=4,
            defense=5,
            tough=1,
            points=90,
            min_models=5,
            max_models=20,
            default_models=10,
            source_uid="unit-guardians",
        )
        self.weapon = Weapon.objects.create(
            name="Great Weapon",
            range=0,
            attacks=2,
            attacks_string="A2",
            ap=2,
        )
        self.slot = UnitWeaponSlot.objects.create(unit=self.unit, weapon=self.weapon)
        self.hero_slot = UnitWeaponSlot.objects.create(unit=self.hero, weapon=self.weapon)
        self.guard_slot = UnitWeaponSlot.objects.create(unit=self.guard, weapon=self.weapon)
        self.upgrade_weapon = Weapon.objects.create(
            name="Blessed Great Weapon",
            range=0,
            attacks=2,
            attacks_string="A2",
            ap=3,
        )
        self.upgrade_slot = UnitWeaponSlot.objects.create(
            unit=self.unit,
            weapon=self.upgrade_weapon,
            is_default=False,
            upgrade_cost=25,
            option_id="option-blessed-weapons",
            upgrade_id="upgrade-blessed-great",
        )
        self.bull = Unit.objects.create(
            faction=self.faction,
            name="Bull Construct",
            quality=4,
            defense=2,
            tough=9,
            points=235,
            source_uid="bOv6BGK",
        )
        self.heavy_great_weapon = Weapon.objects.create(
            name="Heavy Great Weapon",
            range=0,
            attacks=6,
            attacks_string="A6",
            ap=4,
            source_uid="BTEKkW8x",
        )
        self.stomp = Weapon.objects.create(
            name="Stomp",
            range=0,
            attacks=3,
            attacks_string="A3",
            ap=1,
            source_uid="qSPHZX1J",
        )
        UnitWeaponSlot.objects.create(unit=self.bull, weapon=self.heavy_great_weapon, is_default=True)
        UnitWeaponSlot.objects.create(unit=self.bull, weapon=self.stomp, is_default=True)
        self.flamer = Weapon.objects.create(
            name="Twin Arm-Flamethrowers",
            range=12,
            attacks=3,
            attacks_string="A3",
            ap=1,
            special_rules={"Blast": 3, "Reliable": True},
            source_uid="3fOjuT5u",
        )
        self.bull_upgrade_section = UnitUpgradeSection.objects.create(
            unit=self.bull,
            package_uid="X2LU7GIa",
            section_uid="m5Fl4_I9XF",
            label="Replace Heavy Great Weapon",
            variant="replace",
            targets=["Heavy Great Weapon"],
        )
        self.bull_upgrade_option = UnitUpgradeOption.objects.create(
            section=self.bull_upgrade_section,
            option_uid="2-liYIN7tu",
            label="Twin Arm-Flamethrowers",
            cost=35,
        )
        UnitUpgradeOptionWeapon.objects.create(option=self.bull_upgrade_option, weapon=self.flamer)

    def test_create_list_and_read_detail(self):
        create_response = self.client.post(
            "/api/lists/",
            {"name": "Tournament 2000", "faction": self.faction.id, "point_limit": 2000},
            format="json",
        )

        self.assertEqual(create_response.status_code, 201)
        army_list_id = create_response.json()["data"]["id"]

        detail_response = self.client.get(f"/api/lists/{army_list_id}/")
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.json()["data"]["name"], "Tournament 2000")
        self.assertEqual(detail_response.json()["data"]["total_points"], 0)

    def test_patch_list(self):
        army_list = ArmyList.objects.create(
            name="Draft",
            faction=self.faction,
            point_limit=1000,
        )

        response = self.client.patch(
            f"/api/lists/{army_list.id}/",
            {"point_limit": 2000},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["point_limit"], 2000)

    def test_add_and_remove_list_unit(self):
        army_list = ArmyList.objects.create(
            name="Tournament 2000",
            faction=self.faction,
            point_limit=2000,
        )

        add_response = self.client.post(
            f"/api/lists/{army_list.id}/units/",
            {
                "unit": self.unit.id,
                "model_count": 2,
                "selected_weapon_slot": self.slot.id,
                "notes": "Hold center.",
            },
            format="json",
        )

        self.assertEqual(add_response.status_code, 201)
        self.assertEqual(add_response.json()["data"]["total_points"], 360)
        list_unit_id = add_response.json()["data"]["units"][0]["id"]

        delete_response = self.client.delete(f"/api/lists/{army_list.id}/units/{list_unit_id}/")

        self.assertEqual(delete_response.status_code, 200)
        self.assertEqual(delete_response.json()["data"]["total_points"], 0)
        self.assertEqual(ListUnit.objects.count(), 0)

    def test_update_list_unit_model_count_and_notes(self):
        army_list = ArmyList.objects.create(
            name="Tournament 2000",
            faction=self.faction,
            point_limit=2000,
        )
        list_unit = ListUnit.objects.create(
            army_list=army_list,
            unit=self.unit,
            model_count=1,
            selected_weapon_slot=self.slot,
            notes="Screen flank.",
        )

        response = self.client.patch(
            f"/api/lists/{army_list.id}/units/{list_unit.id}/",
            {"model_count": 3, "notes": "Hold center."},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertEqual(payload["total_points"], 540)
        self.assertEqual(payload["units"][0]["model_count"], 3)
        self.assertEqual(payload["units"][0]["notes"], "Hold center.")

    def test_selected_weapon_upgrade_cost_is_included_in_totals(self):
        army_list = ArmyList.objects.create(
            name="Tournament 2000",
            faction=self.faction,
            point_limit=2000,
        )

        response = self.client.post(
            f"/api/lists/{army_list.id}/units/",
            {
                "unit": self.unit.id,
                "model_count": 2,
                "selected_weapon_slot": self.upgrade_slot.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()["data"]
        self.assertEqual(payload["total_points"], 385)
        self.assertEqual(payload["units"][0]["total_points"], 385)
        self.assertEqual(payload["units"][0]["selected_weapon_name"], "Blessed Great Weapon")

    def test_selected_native_upgrade_replaces_only_targeted_default_weapon(self):
        army_list = ArmyList.objects.create(
            name="Tournament 2000",
            faction=self.faction,
            point_limit=2000,
        )

        response = self.client.post(
            f"/api/lists/{army_list.id}/units/",
            {
                "unit": self.bull.id,
                "model_count": 1,
                "selected_upgrades": [self.bull_upgrade_option.id],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()["data"]
        unit_payload = payload["units"][0]
        self.assertEqual(payload["total_points"], 270)
        self.assertEqual(unit_payload["total_points"], 270)
        self.assertEqual(unit_payload["selected_upgrades"], [self.bull_upgrade_option.id])
        self.assertEqual(
            unit_payload["loadout_weapon_names"],
            ["Stomp", "Twin Arm-Flamethrowers"],
        )
        self.assertEqual(unit_payload["loadout_summary"], "Stomp + Twin Arm-Flamethrowers")

    def test_default_multi_weapon_loadout_is_preserved(self):
        army_list = ArmyList.objects.create(
            name="Tournament 2000",
            faction=self.faction,
            point_limit=2000,
        )

        response = self.client.post(
            f"/api/lists/{army_list.id}/units/",
            {"unit": self.bull.id, "model_count": 1},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        unit_payload = response.json()["data"]["units"][0]
        self.assertEqual(unit_payload["total_points"], 235)
        self.assertEqual(
            unit_payload["loadout_weapon_names"],
            ["Heavy Great Weapon", "Stomp"],
        )

    def test_model_count_must_respect_known_unit_bounds(self):
        self.unit.min_models = 2
        self.unit.max_models = 4
        self.unit.default_models = 2
        self.unit.save()
        army_list = ArmyList.objects.create(
            name="Tournament 2000",
            faction=self.faction,
            point_limit=6000,
        )

        response = self.client.post(
            f"/api/lists/{army_list.id}/units/",
            {"unit": self.unit.id, "model_count": 5, "selected_weapon_slot": self.slot.id},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIsNone(response.json()["data"])
        self.assertIn("at most 4", str(response.json()["error"]))

    def test_model_count_without_explicit_max_is_fixed_at_default_size(self):
        fixed_unit = Unit.objects.create(
            faction=self.faction,
            name="Immortals",
            quality=3,
            defense=4,
            tough=1,
            points=90,
            min_models=5,
            default_models=5,
        )
        UnitWeaponSlot.objects.create(unit=fixed_unit, weapon=self.weapon, is_default=True)
        army_list = ArmyList.objects.create(
            name="Tournament 750",
            faction=self.faction,
            point_limit=750,
        )

        response = self.client.post(
            f"/api/lists/{army_list.id}/units/",
            {"unit": fixed_unit.id, "model_count": 10},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIsNone(response.json()["data"])
        self.assertIn("at most 5", str(response.json()["error"]))

    def test_add_list_unit_rejects_malformed_unit_without_server_error(self):
        army_list = ArmyList.objects.create(
            name="Tournament 2000",
            faction=self.faction,
            point_limit=2000,
        )

        response = self.client.post(
            f"/api/lists/{army_list.id}/units/",
            {"unit": "not-a-unit", "model_count": 1, "selected_weapon_slot": self.slot.id},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIsNone(response.json()["data"])
        self.assertIn("unit", str(response.json()["error"]).lower())

    def test_list_response_includes_validation_messages(self):
        army_list = ArmyList.objects.create(
            name="Tournament 2000",
            faction=self.faction,
            point_limit=300,
        )
        ListUnit.objects.create(
            army_list=army_list,
            unit=self.unit,
            model_count=2,
            selected_weapon_slot=self.upgrade_slot,
        )

        response = self.client.get(f"/api/lists/{army_list.id}/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertEqual(payload["total_points"], 385)
        self.assertEqual(payload["validation"]["errors"][0]["code"], "over_point_limit")

    def test_list_response_includes_advisor_summary_fields(self):
        army_list = ArmyList.objects.create(
            name="Advisor Suggestion - Kingdom of Angels",
            faction=self.faction,
            point_limit=2000,
            advisor_archetype="Offensive Elite",
            advisor_playstyle="Shove It In",
            advisor_strategy_summary="Push through the center.",
            advisor_prompt="Aggressive elite list.",
            advisor_warnings=["Low activation count."],
        )

        response = self.client.get(f"/api/lists/{army_list.id}/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertEqual(payload["advisor_archetype"], "Offensive Elite")
        self.assertEqual(payload["advisor_playstyle"], "Shove It In")
        self.assertEqual(payload["advisor_strategy_summary"], "Push through the center.")
        self.assertEqual(payload["advisor_prompt"], "Aggressive elite list.")
        self.assertEqual(payload["advisor_warnings"], ["Low activation count."])

    def test_patch_list_unit_can_combine_units_and_attach_hero(self):
        army_list = ArmyList.objects.create(
            name="Tournament 2000",
            faction=self.faction,
            point_limit=6000,
        )
        host = ListUnit.objects.create(
            army_list=army_list,
            unit=self.guard,
            model_count=10,
            selected_weapon_slot=self.guard_slot,
            combined_from_count=2,
        )
        hero_entry = ListUnit.objects.create(
            army_list=army_list,
            unit=self.hero,
            model_count=1,
            selected_weapon_slot=self.hero_slot,
        )

        response = self.client.patch(
            f"/api/lists/{army_list.id}/units/{hero_entry.id}/",
            {"parent_entry": host.id},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        units = response.json()["data"]["units"]
        host_payload = next(unit for unit in units if unit["id"] == host.id)
        hero_payload = next(unit for unit in units if unit["id"] == hero_entry.id)
        self.assertEqual(host_payload["combined_from_count"], 2)
        self.assertIsNone(host_payload["parent_entry"])
        self.assertEqual(hero_payload["parent_entry"], host.id)
        self.assertEqual(response.json()["data"]["validation"]["errors"], [])

    def test_force_org_validation_flags_duplicate_heroes_and_large_unit_groups(self):
        army_list = ArmyList.objects.create(
            name="Tournament 1000",
            faction=self.faction,
            point_limit=1000,
        )
        for index in range(4):
            ListUnit.objects.create(
                army_list=army_list,
                unit=self.hero,
                model_count=1,
                selected_weapon_slot=self.hero_slot,
                notes=f"Hero {index}",
            )
        ListUnit.objects.create(
            army_list=army_list,
            unit=self.unit,
            model_count=3,
            selected_weapon_slot=self.slot,
        )

        response = self.client.get(f"/api/lists/{army_list.id}/")

        self.assertEqual(response.status_code, 200)
        codes = {message["code"] for message in response.json()["data"]["validation"]["errors"]}
        self.assertIn("too_many_heroes", codes)
        self.assertIn("too_many_unit_copies", codes)
        self.assertIn("unit_group_over_point_share", codes)

    def test_force_org_allows_two_heroes_at_750_points(self):
        army_list = ArmyList.objects.create(
            name="Tournament 750",
            faction=self.faction,
            point_limit=750,
        )
        for index in range(2):
            ListUnit.objects.create(
                army_list=army_list,
                unit=self.hero,
                model_count=1,
                selected_weapon_slot=self.hero_slot,
                notes=f"Hero {index}",
            )

        response = self.client.get(f"/api/lists/{army_list.id}/")

        self.assertEqual(response.status_code, 200)
        codes = {message["code"] for message in response.json()["data"]["validation"]["errors"]}
        self.assertNotIn("too_many_heroes", codes)

        ListUnit.objects.create(
            army_list=army_list,
            unit=self.hero,
            model_count=1,
            selected_weapon_slot=self.hero_slot,
            notes="Hero 2",
        )

        response = self.client.get(f"/api/lists/{army_list.id}/")

        self.assertEqual(response.status_code, 200)
        codes = {message["code"] for message in response.json()["data"]["validation"]["errors"]}
        self.assertIn("too_many_heroes", codes)

    def test_rejects_illegal_hero_attachment_to_single_model_unit(self):
        army_list = ArmyList.objects.create(
            name="Tournament 2000",
            faction=self.faction,
            point_limit=2000,
        )
        host = ListUnit.objects.create(
            army_list=army_list,
            unit=self.unit,
            model_count=1,
            selected_weapon_slot=self.slot,
        )
        hero_entry = ListUnit.objects.create(
            army_list=army_list,
            unit=self.hero,
            model_count=1,
            selected_weapon_slot=self.hero_slot,
        )

        response = self.client.patch(
            f"/api/lists/{army_list.id}/units/{hero_entry.id}/",
            {"parent_entry": host.id},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("multi-model", str(response.json()["error"]))

    def test_army_forge_export_returns_native_save_json(self):
        army_list = ArmyList.objects.create(
            name="Kingdom of Angels - Offensive Elite (2000 pts)",
            faction=self.faction,
            point_limit=2000,
        )
        host = ListUnit.objects.create(
            army_list=army_list,
            unit=self.guard,
            model_count=10,
            selected_weapon_slot=self.guard_slot,
            combined_from_count=2,
        )
        ListUnit.objects.create(
            army_list=army_list,
            unit=self.hero,
            model_count=1,
            selected_weapon_slot=self.hero_slot,
            parent_entry=host,
            notes="Lead the block.",
        )

        response = self.client.get(f"/api/lists/{army_list.id}/export/army-forge/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertEqual(payload["armyId"], "army-angels")
        self.assertEqual(payload["armyIds"], ["army-angels"])
        self.assertEqual(payload["armyName"], "Kingdom of Angels")
        self.assertEqual(payload["gameSystem"], "aof")
        self.assertEqual(payload["listPoints"], 275)
        self.assertEqual(payload["saveVersion"], 3)
        self.assertEqual(payload["armyVersions"], [{"armyId": "army-angels", "version": "3.5.3"}])
        self.assertEqual(payload["list"]["name"], "Kingdom of Angels - Offensive Elite (2000 pts)")
        self.assertEqual(payload["list"]["pointsLimit"], 2000)
        self.assertEqual(payload["list"]["modelCount"], 21)
        self.assertEqual(payload["list"]["activationCount"], 1)
        self.assertTrue(payload["list"]["forceOrg"])
        self.assertFalse(payload["list"]["isCloud"])
        self.assertFalse(payload["list"]["simpleMode"])
        self.assertEqual(len(payload["list"]["units"]), 3)
        host_rows = [unit for unit in payload["list"]["units"] if unit["id"] == "unit-guardians"]
        hero_rows = [unit for unit in payload["list"]["units"] if unit["id"] == "unit-champion"]
        self.assertEqual(len(host_rows), 2)
        self.assertTrue(all(unit["combined"] for unit in host_rows))
        self.assertIsNone(host_rows[0]["joinToUnit"])
        self.assertEqual(host_rows[1]["joinToUnit"], host_rows[0]["selectionId"])
        self.assertEqual(hero_rows[0]["joinToUnit"], host_rows[0]["selectionId"])
        self.assertEqual(hero_rows[0]["notes"], "Lead the block.")
        self.assertEqual(hero_rows[0]["xp"], 0)
        self.assertEqual(hero_rows[0]["traits"], [])
        self.assertEqual(hero_rows[0]["selectedUpgrades"], [])

    def test_army_forge_export_includes_selected_upgrade_identifiers(self):
        army_list = ArmyList.objects.create(
            name="Tournament 2000",
            faction=self.faction,
            point_limit=2000,
        )
        ListUnit.objects.create(
            army_list=army_list,
            unit=self.unit,
            model_count=1,
            selected_weapon_slot=self.upgrade_slot,
        )

        response = self.client.get(f"/api/lists/{army_list.id}/export/army-forge/")

        self.assertEqual(response.status_code, 200)
        exported_unit = response.json()["data"]["list"]["units"][0]
        self.assertEqual(exported_unit["id"], "unit-paladins")
        self.assertEqual(exported_unit["armyId"], "army-angels")
        self.assertEqual(
            exported_unit["selectedUpgrades"],
            [
                {
                    "optionId": "option-blessed-weapons",
                    "upgradeId": "upgrade-blessed-great",
                    "instanceId": exported_unit["selectedUpgrades"][0]["instanceId"],
                }
            ],
        )

    def test_army_forge_export_includes_native_selected_upgrade_identifiers(self):
        army_list = ArmyList.objects.create(
            name="Tournament 2000",
            faction=self.faction,
            point_limit=2000,
        )
        entry = ListUnit.objects.create(
            army_list=army_list,
            unit=self.bull,
            model_count=1,
        )
        ListUnitUpgrade.objects.create(list_unit=entry, option=self.bull_upgrade_option)

        response = self.client.get(f"/api/lists/{army_list.id}/export/army-forge/")

        self.assertEqual(response.status_code, 200)
        exported_unit = response.json()["data"]["list"]["units"][0]
        self.assertEqual(exported_unit["id"], "bOv6BGK")
        self.assertEqual(response.json()["data"]["listPoints"], 270)
        self.assertEqual(
            exported_unit["selectedUpgrades"],
            [
                {
                    "optionId": "2-liYIN7tu",
                    "upgradeId": "m5Fl4_I9XF",
                    "instanceId": exported_unit["selectedUpgrades"][0]["instanceId"],
                }
            ],
        )

    def test_army_forge_export_rejects_missing_native_selected_upgrade_ids(self):
        self.bull_upgrade_option.option_uid = ""
        self.bull_upgrade_option.save()
        army_list = ArmyList.objects.create(
            name="Tournament 2000",
            faction=self.faction,
            point_limit=2000,
        )
        entry = ListUnit.objects.create(
            army_list=army_list,
            unit=self.bull,
            model_count=1,
        )
        ListUnitUpgrade.objects.create(list_unit=entry, option=self.bull_upgrade_option)

        response = self.client.get(f"/api/lists/{army_list.id}/export/army-forge/")

        self.assertEqual(response.status_code, 422)
        self.assertIsNone(response.json()["data"])
        self.assertIn("re-sync army books", response.json()["error"].lower())

    def test_army_forge_export_rejects_missing_native_faction_id(self):
        self.faction.source_uid = ""
        self.faction.save()
        army_list = ArmyList.objects.create(
            name="Tournament 2000",
            faction=self.faction,
            point_limit=2000,
        )
        ListUnit.objects.create(
            army_list=army_list,
            unit=self.unit,
            model_count=1,
            selected_weapon_slot=self.slot,
        )

        response = self.client.get(f"/api/lists/{army_list.id}/export/army-forge/")

        self.assertEqual(response.status_code, 422)
        self.assertIsNone(response.json()["data"])
        self.assertIn("faction", response.json()["error"].lower())

    def test_army_forge_export_rejects_missing_native_unit_id(self):
        self.unit.source_uid = ""
        self.unit.save()
        army_list = ArmyList.objects.create(
            name="Tournament 2000",
            faction=self.faction,
            point_limit=2000,
        )
        ListUnit.objects.create(
            army_list=army_list,
            unit=self.unit,
            model_count=1,
            selected_weapon_slot=self.slot,
        )

        response = self.client.get(f"/api/lists/{army_list.id}/export/army-forge/")

        self.assertEqual(response.status_code, 422)
        self.assertIsNone(response.json()["data"])
        self.assertIn("unit", response.json()["error"].lower())

    def test_army_forge_export_rejects_missing_selected_upgrade_ids(self):
        self.upgrade_slot.option_id = ""
        self.upgrade_slot.save()
        army_list = ArmyList.objects.create(
            name="Tournament 2000",
            faction=self.faction,
            point_limit=2000,
        )
        ListUnit.objects.create(
            army_list=army_list,
            unit=self.unit,
            model_count=1,
            selected_weapon_slot=self.upgrade_slot,
        )

        response = self.client.get(f"/api/lists/{army_list.id}/export/army-forge/")

        self.assertEqual(response.status_code, 422)
        self.assertIsNone(response.json()["data"])
        self.assertIn("re-sync army books", response.json()["error"].lower())

    def test_update_list_unit_rejects_weapon_slot_from_other_unit(self):
        other_unit = Unit.objects.create(
            faction=self.faction,
            name="Guardians",
            quality=4,
            defense=5,
            tough=1,
            points=90,
        )
        other_weapon = Weapon.objects.create(
            name="Longbow",
            range=30,
            attacks=1,
            attacks_string="A1",
            ap=0,
        )
        other_slot = UnitWeaponSlot.objects.create(unit=other_unit, weapon=other_weapon)
        army_list = ArmyList.objects.create(
            name="Tournament 2000",
            faction=self.faction,
            point_limit=2000,
        )
        list_unit = ListUnit.objects.create(
            army_list=army_list,
            unit=self.unit,
            model_count=1,
            selected_weapon_slot=self.slot,
        )

        response = self.client.patch(
            f"/api/lists/{army_list.id}/units/{list_unit.id}/",
            {"selected_weapon_slot": other_slot.id},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIsNone(response.json()["data"])
        self.assertIn("Selected weapon slot", str(response.json()["error"]))

    def test_update_missing_list_unit_returns_error_envelope(self):
        army_list = ArmyList.objects.create(
            name="Tournament 2000",
            faction=self.faction,
            point_limit=2000,
        )

        response = self.client.patch(
            f"/api/lists/{army_list.id}/units/9999/",
            {"model_count": 2},
            format="json",
        )

        self.assertEqual(response.status_code, 404)
        self.assertIsNone(response.json()["data"])
        self.assertIn("List unit not found", response.json()["error"])

    def test_rejects_unit_from_wrong_faction(self):
        other_faction = Faction.objects.create(name="Beastmen", version="3.5.3")
        other_unit = Unit.objects.create(
            faction=other_faction,
            name="Brute",
            quality=4,
            defense=4,
            tough=1,
            points=80,
        )
        army_list = ArmyList.objects.create(
            name="Tournament 2000",
            faction=self.faction,
            point_limit=2000,
        )

        response = self.client.post(
            f"/api/lists/{army_list.id}/units/",
            {"unit": other_unit.id, "model_count": 1},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIsNone(response.json()["data"])
        self.assertIn("same faction", response.json()["error"])

    def test_missing_list_returns_error_envelope(self):
        response = self.client.get("/api/lists/9999/")

        self.assertEqual(response.status_code, 404)
        self.assertIsNone(response.json()["data"])
        self.assertIn("Army list not found", response.json()["error"])

    def test_analyze_list_returns_unit_and_total_results(self):
        army_list = ArmyList.objects.create(
            name="Tournament 2000",
            faction=self.faction,
            point_limit=2000,
        )
        ListUnit.objects.create(
            army_list=army_list,
            unit=self.unit,
            model_count=2,
            selected_weapon_slot=self.slot,
        )

        response = self.client.post(
            f"/api/lists/{army_list.id}/analysis/",
            {
                "targets": [
                    {"id": "infantry", "name": "Infantry", "defense": 5, "tough": 1},
                    {"id": "elite", "name": "Elite", "defense": 3, "tough": 3},
                ]
            },
            format="json",
        )

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(payload["error"])
        self.assertEqual(payload["data"]["list_id"], army_list.id)
        self.assertEqual(len(payload["data"]["targets"]), 2)
        unit_result = payload["data"]["units"][0]
        self.assertEqual(unit_result["unit_name"], "Paladins")
        self.assertEqual(unit_result["model_count"], 2)
        self.assertEqual(unit_result["points"], 360)
        self.assertEqual(unit_result["effective_wounds"], 12.0)
        self.assertEqual(unit_result["effective_wounds_per_100_points"], 3.333333)
        self.assertEqual(unit_result["weapon_name"], "Great Weapon")
        infantry_result = unit_result["target_results"][0]
        self.assertEqual(infantry_result["target_id"], "infantry")
        self.assertEqual(infantry_result["ev"], 2.666667)
        self.assertEqual(infantry_result["ranged_ev"], 0)
        self.assertEqual(infantry_result["melee_ev"], 2.666667)
        self.assertEqual(infantry_result["wounds_per_100_points"], 0.740741)
        self.assertEqual(infantry_result["ranged_wounds_per_100_points"], 0)
        self.assertEqual(infantry_result["melee_wounds_per_100_points"], 0.740741)
        self.assertGreater(infantry_result["p_kill_model"], 0)
        self.assertEqual(payload["data"]["totals"][0]["ev"], 2.666667)
        self.assertEqual(payload["data"]["totals"][0]["ranged_ev"], 0)
        self.assertEqual(payload["data"]["totals"][0]["melee_ev"], 2.666667)

    def test_analyze_list_counts_regeneration_as_extra_effective_wounds(self):
        self.unit.special_rules = {"Regeneration": True}
        self.unit.save()
        army_list = ArmyList.objects.create(
            name="Tournament 2000",
            faction=self.faction,
            point_limit=2000,
        )
        ListUnit.objects.create(
            army_list=army_list,
            unit=self.unit,
            model_count=2,
            selected_weapon_slot=self.slot,
        )

        response = self.client.post(
            f"/api/lists/{army_list.id}/analysis/",
            {"targets": [{"id": "infantry", "name": "Infantry", "defense": 5, "tough": 1}]},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        unit_result = response.json()["data"]["units"][0]
        self.assertEqual(unit_result["effective_wounds"], 18.0)
        self.assertEqual(unit_result["effective_wounds_per_100_points"], 5.0)

    def test_analyze_list_applies_disintegrate_against_elite_defense(self):
        self.weapon.ap = 0
        self.weapon.special_rules = {"Disintegrate": True}
        self.weapon.save()
        army_list = ArmyList.objects.create(
            name="Tournament 2000",
            faction=self.faction,
            point_limit=2000,
        )
        ListUnit.objects.create(
            army_list=army_list,
            unit=self.unit,
            model_count=1,
            selected_weapon_slot=self.slot,
        )

        response = self.client.post(
            f"/api/lists/{army_list.id}/analysis/",
            {"targets": [{"id": "elite", "name": "Elite", "defense": 3, "tough": 3}]},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        target_result = response.json()["data"]["units"][0]["target_results"][0]
        self.assertEqual(target_result["ev"], 0.888889)
        self.assertEqual(target_result["wounds_per_100_points"], round((0.888889 / 180) * 100, 6))

    def test_analyze_list_applies_blast_to_infantry_and_elite_targets_only(self):
        self.unit.quality = 4
        self.unit.save()
        self.weapon.attacks = 3
        self.weapon.ap = 0
        self.weapon.special_rules = {"Blast": 3}
        self.weapon.save()
        army_list = ArmyList.objects.create(
            name="Tournament 2000",
            faction=self.faction,
            point_limit=2000,
        )
        ListUnit.objects.create(
            army_list=army_list,
            unit=self.unit,
            model_count=1,
            selected_weapon_slot=self.slot,
        )

        response = self.client.post(
            f"/api/lists/{army_list.id}/analysis/",
            {
                "targets": [
                    {"id": "infantry", "name": "Infantry", "defense": 4, "tough": 1},
                    {"id": "elite", "name": "Elite", "defense": 4, "tough": 3},
                    {"id": "monster", "name": "Monster", "defense": 4, "tough": 10},
                ]
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        results = {
            result["target_id"]: result
            for result in response.json()["data"]["units"][0]["target_results"]
        }
        self.assertEqual(results["infantry"]["ev"], 2.25)
        self.assertEqual(results["elite"]["ev"], 2.25)
        self.assertEqual(results["monster"]["ev"], 0.75)

    def test_analyze_list_uses_upgrade_cost_for_efficiency(self):
        army_list = ArmyList.objects.create(
            name="Tournament 2000",
            faction=self.faction,
            point_limit=2000,
        )
        ListUnit.objects.create(
            army_list=army_list,
            unit=self.unit,
            model_count=2,
            selected_weapon_slot=self.upgrade_slot,
        )

        response = self.client.post(
            f"/api/lists/{army_list.id}/analysis/",
            {"targets": [{"id": "infantry", "name": "Infantry", "defense": 5, "tough": 1}]},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        unit_result = response.json()["data"]["units"][0]
        self.assertEqual(unit_result["points"], 385)
        target_result = unit_result["target_results"][0]
        self.assertEqual(target_result["wounds_per_100_points"], round((target_result["ev"] / 385) * 100, 6))

    def test_analyze_list_falls_back_to_default_weapon_slot(self):
        army_list = ArmyList.objects.create(
            name="Tournament 2000",
            faction=self.faction,
            point_limit=2000,
        )
        ListUnit.objects.create(
            army_list=army_list,
            unit=self.unit,
            model_count=1,
            selected_weapon_slot=None,
        )

        response = self.client.post(
            f"/api/lists/{army_list.id}/analysis/",
            {"targets": [{"id": "infantry", "name": "Infantry", "defense": 5, "tough": 1}]},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        unit_result = response.json()["data"]["units"][0]
        self.assertEqual(unit_result["weapon_id"], self.weapon.id)
        self.assertEqual(unit_result["weapon_name"], "Great Weapon")

    def test_analyze_list_sums_effective_multi_weapon_loadout(self):
        army_list = ArmyList.objects.create(
            name="Tournament 2000",
            faction=self.faction,
            point_limit=2000,
        )
        entry = ListUnit.objects.create(
            army_list=army_list,
            unit=self.bull,
            model_count=1,
        )
        ListUnitUpgrade.objects.create(list_unit=entry, option=self.bull_upgrade_option)

        response = self.client.post(
            f"/api/lists/{army_list.id}/analysis/",
            {"targets": [{"id": "monster", "name": "Monster", "defense": 2, "tough": 10}]},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        unit_result = response.json()["data"]["units"][0]
        self.assertEqual(unit_result["points"], 270)
        self.assertEqual(unit_result["weapon_name"], "Stomp + Twin Arm-Flamethrowers")
        self.assertEqual(unit_result["weapon_names"], ["Stomp", "Twin Arm-Flamethrowers"])
        target_result = unit_result["target_results"][0]
        self.assertEqual(target_result["ev"], 1.333333)
        self.assertEqual(target_result["ranged_ev"], 0.833333)
        self.assertEqual(target_result["melee_ev"], 0.5)
        self.assertEqual(target_result["activation_ev"], 0.833333)
        self.assertEqual(
            target_result["ev"],
            round(target_result["ranged_ev"] + target_result["melee_ev"], 6),
        )
        self.assertEqual(target_result["ranged_wounds_per_100_points"], round((0.833333 / 270) * 100, 6))
        self.assertEqual(target_result["melee_wounds_per_100_points"], round((0.5 / 270) * 100, 6))
        self.assertEqual(target_result["activation_wounds_per_100_points"], round((0.833333 / 270) * 100, 6))
        self.assertEqual(response.json()["data"]["totals"][0]["ranged_ev"], 0.833333)
        self.assertEqual(response.json()["data"]["totals"][0]["melee_ev"], 0.5)
        self.assertEqual(response.json()["data"]["totals"][0]["activation_ev"], 0.833333)

    def test_analyze_list_default_monster_target_has_regeneration(self):
        army_list = ArmyList.objects.create(
            name="Tournament 2000",
            faction=self.faction,
            point_limit=2000,
        )
        ListUnit.objects.create(
            army_list=army_list,
            unit=self.unit,
            model_count=1,
            selected_weapon_slot=self.slot,
        )

        response = self.client.post(f"/api/lists/{army_list.id}/analysis/", {"targets": []}, format="json")

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        monster_target = next(target for target in payload["targets"] if target["id"] == "monster")
        self.assertEqual(monster_target["special_rules"], {"Regeneration": True})
        monster_result = next(
            result for result in payload["units"][0]["target_results"] if result["target_id"] == "monster"
        )
        self.assertEqual(monster_result["ev"], 0.444444)

    def test_analyze_list_uses_charge_context_for_melee_only(self):
        melee_weapon = Weapon.objects.create(
            name="Furious Claws",
            range=0,
            attacks=6,
            attacks_string="A6",
            ap=0,
            special_rules={"Furious": True},
        )
        ranged_weapon = Weapon.objects.create(
            name="Furious Bow",
            range=18,
            attacks=6,
            attacks_string="A6",
            ap=0,
            special_rules={"Furious": True},
        )
        melee_unit = Unit.objects.create(
            faction=self.faction,
            name="Charging Claws",
            quality=3,
            defense=5,
            tough=1,
            points=100,
        )
        ranged_unit = Unit.objects.create(
            faction=self.faction,
            name="Furious Archers",
            quality=3,
            defense=5,
            tough=1,
            points=100,
        )
        melee_slot = UnitWeaponSlot.objects.create(unit=melee_unit, weapon=melee_weapon, is_default=True)
        ranged_slot = UnitWeaponSlot.objects.create(unit=ranged_unit, weapon=ranged_weapon, is_default=True)
        army_list = ArmyList.objects.create(
            name="Tournament 2000",
            faction=self.faction,
            point_limit=2000,
        )
        ListUnit.objects.create(army_list=army_list, unit=melee_unit, model_count=1, selected_weapon_slot=melee_slot)
        ListUnit.objects.create(army_list=army_list, unit=ranged_unit, model_count=1, selected_weapon_slot=ranged_slot)

        response = self.client.post(
            f"/api/lists/{army_list.id}/analysis/",
            {"targets": [{"id": "infantry", "name": "Infantry", "defense": 4, "tough": 1}]},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        results = {unit["unit_name"]: unit["target_results"][0] for unit in response.json()["data"]["units"]}
        self.assertEqual(results["Charging Claws"]["ev"], 2.5)
        self.assertEqual(results["Furious Archers"]["ev"], 2.0)

    def test_analyze_list_applies_slayer_against_tough_targets_by_attack_type(self):
        melee_weapon = Weapon.objects.create(
            name="Monster Hunting Spear",
            range=0,
            attacks=2,
            attacks_string="A2",
            ap=0,
        )
        ranged_weapon = Weapon.objects.create(
            name="Monster Hunter Bow",
            range=24,
            attacks=2,
            attacks_string="A2",
            ap=0,
        )
        melee_unit = Unit.objects.create(
            faction=self.faction,
            name="Quest Knights",
            quality=4,
            defense=4,
            tough=1,
            points=100,
            special_rules={"Melee Slayer": True},
        )
        ranged_unit = Unit.objects.create(
            faction=self.faction,
            name="Monster Hunters",
            quality=4,
            defense=5,
            tough=1,
            points=100,
            special_rules={"Ranged Slayer": True},
        )
        melee_slot = UnitWeaponSlot.objects.create(unit=melee_unit, weapon=melee_weapon, is_default=True)
        ranged_slot = UnitWeaponSlot.objects.create(unit=ranged_unit, weapon=ranged_weapon, is_default=True)
        army_list = ArmyList.objects.create(
            name="Tournament 2000",
            faction=self.faction,
            point_limit=2000,
        )
        ListUnit.objects.create(army_list=army_list, unit=melee_unit, model_count=1, selected_weapon_slot=melee_slot)
        ListUnit.objects.create(army_list=army_list, unit=ranged_unit, model_count=1, selected_weapon_slot=ranged_slot)

        response = self.client.post(
            f"/api/lists/{army_list.id}/analysis/",
            {
                "targets": [
                    {"id": "infantry", "name": "Infantry", "defense": 5, "tough": 1},
                    {"id": "elite", "name": "Elite", "defense": 3, "tough": 3},
                ]
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        results = {
            unit["unit_name"]: {
                target["target_id"]: target
                for target in unit["target_results"]
            }
            for unit in response.json()["data"]["units"]
        }
        self.assertEqual(results["Quest Knights"]["infantry"]["melee_ev"], 0.666667)
        self.assertEqual(results["Quest Knights"]["elite"]["melee_ev"], 0.666667)
        self.assertEqual(results["Monster Hunters"]["infantry"]["ranged_ev"], 0.666667)
        self.assertEqual(results["Monster Hunters"]["elite"]["ranged_ev"], 0.666667)

    def test_analyze_missing_list_returns_error_envelope(self):
        response = self.client.post(
            "/api/lists/9999/analysis/",
            {"targets": [{"id": "infantry", "name": "Infantry", "defense": 5, "tough": 1}]},
            format="json",
        )

        self.assertEqual(response.status_code, 404)
        self.assertIsNone(response.json()["data"])
        self.assertIn("Army list not found", response.json()["error"])

    def test_analyze_list_rejects_invalid_target(self):
        army_list = ArmyList.objects.create(
            name="Tournament 2000",
            faction=self.faction,
            point_limit=2000,
        )

        response = self.client.post(
            f"/api/lists/{army_list.id}/analysis/",
            {"targets": [{"id": "bad", "name": "Bad", "defense": 7, "tough": 0}]},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIsNone(response.json()["data"])
        self.assertIn("defense", str(response.json()["error"]).lower())
