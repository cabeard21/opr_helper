from django.test import TestCase
from rest_framework.test import APIClient

from army_books.models import Faction, Unit, UnitWeaponSlot, Weapon
from lists.models import ArmyList, ListUnit


class ListsApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.faction = Faction.objects.create(name="Kingdom of Angels", version="3.5.3")
        self.unit = Unit.objects.create(
            faction=self.faction,
            name="Paladins",
            quality=3,
            defense=4,
            tough=3,
            points=180,
        )
        self.weapon = Weapon.objects.create(
            name="Great Weapon",
            range=0,
            attacks=2,
            attacks_string="A2",
            ap=2,
        )
        self.slot = UnitWeaponSlot.objects.create(unit=self.unit, weapon=self.weapon)

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
