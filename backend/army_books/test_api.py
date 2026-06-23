from django.test import TestCase
from rest_framework.test import APIClient

from army_books.models import Faction, Unit, UnitWeaponSlot, Weapon


class ArmyBooksApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.faction = Faction.objects.create(
            name="Kingdom of Angels",
            version="3.5.3",
            source_uid="faction-angels",
        )
        self.unit = Unit.objects.create(
            faction=self.faction,
            name="Paladins",
            quality=3,
            defense=4,
            tough=3,
            points=180,
            special_rules={"Fearless": True},
            source_uid="unit-paladins",
        )
        self.weapon = Weapon.objects.create(
            name="Great Weapon",
            range=0,
            attacks=2,
            attacks_string="A2",
            ap=2,
            special_rules={"Deadly": 3},
            source_uid="weapon-great",
        )
        self.slot = UnitWeaponSlot.objects.create(unit=self.unit, weapon=self.weapon)

    def test_factions_endpoint_returns_enveloped_data(self):
        response = self.client.get("/api/factions/")

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["error"])
        self.assertEqual(response.json()["data"][0]["name"], "Kingdom of Angels")
        self.assertEqual(response.json()["data"][0]["unit_count"], 1)

    def test_faction_units_endpoint_returns_units_with_weapons(self):
        response = self.client.get(f"/api/factions/{self.faction.id}/units/")

        self.assertEqual(response.status_code, 200)
        unit = response.json()["data"][0]
        self.assertEqual(unit["name"], "Paladins")
        self.assertEqual(unit["weapon_slots"][0]["weapon"]["name"], "Great Weapon")
        self.assertEqual(unit["max_models"], 1)

    def test_unit_detail_endpoint_returns_single_unit(self):
        response = self.client.get(f"/api/units/{self.unit.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["id"], self.unit.id)
        self.assertEqual(response.json()["data"]["weapon_slots"][0]["id"], self.slot.id)

    def test_calc_endpoint_returns_ev_distribution_and_kill_stats(self):
        response = self.client.post(
            "/api/calc/ev/",
            {
                "unit_id": self.unit.id,
                "weapon_id": self.weapon.id,
                "target": {"defense": 4, "tough": 3},
            },
            format="json",
        )

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(payload["error"])
        self.assertEqual(payload["data"]["ev"], 3.333333)
        self.assertIn({"wounds": 0, "probability": 0.197531}, payload["data"]["distribution"])
        self.assertGreater(payload["data"]["p_kill_model"], 0)

    def test_calc_endpoint_applies_target_regeneration(self):
        response = self.client.post(
            "/api/calc/ev/",
            {
                "unit_id": self.unit.id,
                "weapon_id": self.weapon.id,
                "target": {
                    "defense": 4,
                    "tough": 3,
                    "special_rules": {"Regeneration": True},
                },
            },
            format="json",
        )

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["data"]["ev"], 2.222222)

    def test_calc_endpoint_accepts_combat_context(self):
        self.weapon.special_rules = {"Impact": 2, "Thrust": True}
        self.weapon.ap = 0
        self.weapon.save()

        response = self.client.post(
            "/api/calc/ev/",
            {
                "unit_id": self.unit.id,
                "weapon_id": self.weapon.id,
                "target": {"defense": 4, "tough": 3},
                "combat_context": {"charging": True},
            },
            format="json",
        )

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["data"]["ev"], 1.944444)

    def test_calc_endpoint_uses_target_tough_for_melee_slayer(self):
        self.weapon.special_rules = {}
        self.weapon.ap = 0
        self.weapon.save()
        self.unit.quality = 4
        self.unit.special_rules = {"Melee Slayer": True}
        self.unit.save()

        response = self.client.post(
            "/api/calc/ev/",
            {
                "unit_id": self.unit.id,
                "weapon_id": self.weapon.id,
                "target": {"defense": 4, "tough": 3},
                "combat_context": {"charging": True},
            },
            format="json",
        )

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["data"]["ev"], 0.833333)

    def test_calc_endpoint_validates_missing_records(self):
        response = self.client.post(
            "/api/calc/ev/",
            {
                "unit_id": 9999,
                "weapon_id": self.weapon.id,
                "target": {"defense": 4, "tough": 1},
            },
            format="json",
        )

        self.assertEqual(response.status_code, 404)
        self.assertIsNone(response.json()["data"])
        self.assertIn("Unit not found", response.json()["error"])

    def test_missing_faction_units_returns_error_envelope(self):
        response = self.client.get("/api/factions/9999/units/")

        self.assertEqual(response.status_code, 404)
        self.assertIsNone(response.json()["data"])
        self.assertIn("Faction not found", response.json()["error"])
