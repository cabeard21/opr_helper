from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from advisor.llm_service import ListSuggestion, SuggestedUnit, AdvisorLLMError
from army_books.models import Faction, Unit, UnitWeaponSlot, Weapon
from lists.models import ArmyList, ListUnit


class AdvisorApiTests(TestCase):
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
            default_models=1,
        )
        self.weapon = Weapon.objects.create(
            name="Great Weapon",
            range=0,
            attacks=2,
            attacks_string="A2",
            ap=2,
        )
        self.slot = UnitWeaponSlot.objects.create(unit=self.unit, weapon=self.weapon)
        self.suggestion = ListSuggestion(
            units=[
                SuggestedUnit(
                    unit_id=self.unit.id,
                    unit_name="Paladins",
                    model_count=1,
                    justification="Durable high-AP unit.",
                )
            ],
            total_points=180,
            archetype="Offensive Elite",
            playstyle="Shove It In",
            activation_count=1,
            strategy_summary="Push with Paladins and contest central objectives.",
            warnings=[],
        )

    @patch("advisor.views.suggest_list")
    def test_suggest_endpoint_returns_dry_run_suggestion(self, suggest_list):
        suggest_list.return_value = self.suggestion

        response = self.client.post(
            "/api/advisor/suggest/",
            {
                "faction": self.faction.id,
                "point_limit": 2000,
                "prompt": "Aggressive elite list.",
            },
            format="json",
        )

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(payload["error"])
        self.assertEqual(payload["data"]["suggestion"]["archetype"], "Offensive Elite")
        self.assertEqual(payload["data"]["computed_total_points"], 180)
        self.assertEqual(payload["data"]["point_delta"], 1820)
        self.assertEqual(payload["data"]["reconciliation_warnings"], [])
        self.assertIsNone(payload["data"]["army_list"])
        suggest_list.assert_called_once_with(self.faction.id, 2000, "Aggressive elite list.")

    def test_suggest_endpoint_rejects_missing_faction(self):
        response = self.client.post(
            "/api/advisor/suggest/",
            {"point_limit": 2000, "prompt": "Aggressive elite list."},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("faction", str(response.json()["error"]).lower())

    def test_suggest_endpoint_rejects_unknown_faction(self):
        response = self.client.post(
            "/api/advisor/suggest/",
            {"faction": 9999, "point_limit": 2000, "prompt": "Aggressive elite list."},
            format="json",
        )

        self.assertEqual(response.status_code, 404)
        self.assertIn("Faction not found", response.json()["error"])

    def test_suggest_endpoint_rejects_invalid_prompt(self):
        response = self.client.post(
            "/api/advisor/suggest/",
            {"faction": self.faction.id, "point_limit": 2000, "prompt": ""},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("prompt", str(response.json()["error"]).lower())

    @patch("advisor.views.suggest_list")
    def test_suggest_endpoint_maps_llm_error_to_bad_gateway(self, suggest_list):
        suggest_list.side_effect = AdvisorLLMError("provider unavailable")

        response = self.client.post(
            "/api/advisor/suggest/",
            {
                "faction": self.faction.id,
                "point_limit": 2000,
                "prompt": "Aggressive elite list.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["error"], "Advisor provider unavailable.")

    @patch("advisor.views.suggest_list")
    def test_suggest_endpoint_can_create_army_list(self, suggest_list):
        suggest_list.return_value = self.suggestion

        response = self.client.post(
            "/api/advisor/suggest/",
            {
                "faction": self.faction.id,
                "point_limit": 2000,
                "prompt": "Aggressive elite list.",
                "dry_run": False,
            },
            format="json",
        )

        payload = response.json()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(ArmyList.objects.count(), 1)
        self.assertEqual(ListUnit.objects.count(), 1)
        self.assertEqual(payload["data"]["army_list"]["units"][0]["unit_name"], "Paladins")
        self.assertEqual(payload["data"]["army_list"]["validation"]["errors"], [])
        self.assertEqual(payload["data"]["computed_total_points"], 180)

    @patch("advisor.views.suggest_list")
    def test_suggest_endpoint_accepts_false_string_for_list_creation(self, suggest_list):
        suggest_list.return_value = self.suggestion

        response = self.client.post(
            "/api/advisor/suggest/",
            {
                "faction": self.faction.id,
                "point_limit": 2000,
                "prompt": "Aggressive elite list.",
                "dry_run": "false",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(ArmyList.objects.count(), 1)

    @patch("advisor.views.suggest_list")
    def test_suggest_endpoint_rejects_list_creation_when_no_units_survive_reconciliation(self, suggest_list):
        suggest_list.return_value = ListSuggestion(
            units=[
                SuggestedUnit(
                    unit_id=99999,
                    unit_name="Missing",
                    model_count=1,
                    justification="Unknown unit.",
                )
            ],
            total_points=100,
            archetype="Offensive Elite",
            playstyle="Shove It In",
            activation_count=1,
            strategy_summary="Push forward.",
            warnings=[],
        )

        response = self.client.post(
            "/api/advisor/suggest/",
            {
                "faction": self.faction.id,
                "point_limit": 2000,
                "prompt": "Aggressive elite list.",
                "dry_run": False,
            },
            format="json",
        )

        payload = response.json()
        self.assertEqual(response.status_code, 422)
        self.assertEqual(ArmyList.objects.count(), 0)
        self.assertIn("No valid suggested units", payload["error"])
        self.assertIn("unknown unit id", payload["data"]["reconciliation_warnings"][0])

    @override_settings(ADVISOR_RATE_LIMIT_REQUESTS=5, ADVISOR_RATE_LIMIT_WINDOW_SECONDS=60)
    @patch("advisor.views.suggest_list")
    def test_suggest_endpoint_rate_limits_expensive_requests(self, suggest_list):
        suggest_list.return_value = self.suggestion

        for _index in range(5):
            self.client.post(
                "/api/advisor/suggest/",
                {
                    "faction": self.faction.id,
                    "point_limit": 2000,
                    "prompt": "Aggressive elite list.",
                },
                format="json",
                REMOTE_ADDR="203.0.113.10",
            )

        response = self.client.post(
            "/api/advisor/suggest/",
            {
                "faction": self.faction.id,
                "point_limit": 2000,
                "prompt": "Aggressive elite list.",
            },
            format="json",
            REMOTE_ADDR="203.0.113.10",
        )

        self.assertEqual(response.status_code, 429)
        self.assertIn("Too many advisor requests", response.json()["error"])
