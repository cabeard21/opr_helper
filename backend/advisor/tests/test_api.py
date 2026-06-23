from unittest.mock import patch
from unittest.mock import call

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from advisor.llm_service import AdvisorLLMError, ListSuggestion, SuggestedUnit
from army_books.models import Faction, Unit, UnitUpgradeOption, UnitUpgradeSection, UnitWeaponSlot, Weapon
from lists.models import ArmyList, ListUnit, ListUnitUpgrade


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
        self.upgrade_section = UnitUpgradeSection.objects.create(
            unit=self.unit,
            section_uid="paladin-upgrades",
            label="Paladin Upgrades",
        )
        self.upgrade_option = UnitUpgradeOption.objects.create(
            section=self.upgrade_section,
            option_uid="blessed-weapons",
            label="Blessed Weapons",
            cost=20,
        )
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
        self.assertEqual(suggest_list.call_count, 2)
        self.assertEqual(suggest_list.call_args_list[0], call(self.faction.id, 2000, "Aggressive elite list."))
        feedback = suggest_list.call_args.kwargs["correction_feedback"]
        self.assertIn("Spend closer to 2000 points; the prior legal total was 180.", feedback)
        self.assertIn("List health metrics", feedback)

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
        self.assertEqual(
            payload["data"]["army_list"]["name"],
            "Kingdom of Angels - Offensive Elite (2000 pts)",
        )
        self.assertEqual(payload["data"]["army_list"]["advisor_archetype"], "Offensive Elite")
        self.assertEqual(payload["data"]["army_list"]["advisor_playstyle"], "Shove It In")
        self.assertEqual(
            payload["data"]["army_list"]["advisor_strategy_summary"],
            "Push with Paladins and contest central objectives.",
        )
        self.assertEqual(payload["data"]["army_list"]["advisor_prompt"], "Aggressive elite list.")
        self.assertEqual(payload["data"]["computed_total_points"], 180)

    @patch("advisor.views.suggest_list")
    def test_suggest_endpoint_persists_combined_units(self, suggest_list):
        shield_wall = Unit.objects.create(
            faction=self.faction,
            name="Shield Wall",
            quality=4,
            defense=5,
            tough=1,
            points=120,
            min_models=5,
            max_models=10,
            default_models=5,
        )
        UnitWeaponSlot.objects.create(unit=shield_wall, weapon=self.weapon)
        suggest_list.return_value = self.suggestion.model_copy(
            update={
                "units": [
                    SuggestedUnit(
                        unit_id=shield_wall.id,
                        unit_name="Shield Wall",
                        model_count=5,
                        combined_from_count=2,
                        justification="Combined center block.",
                    )
                ],
                "total_points": 240,
            }
        )

        response = self.client.post(
            "/api/advisor/suggest/",
            {
                "faction": self.faction.id,
                "point_limit": 750,
                "prompt": "Durable center block.",
                "dry_run": False,
            },
            format="json",
        )

        payload = response.json()
        entry = ListUnit.objects.get(unit=shield_wall)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(entry.combined_from_count, 2)
        self.assertEqual(payload["data"]["army_list"]["units"][0]["combined_from_count"], 2)
        self.assertEqual(payload["data"]["computed_total_points"], 240)

    @patch("advisor.views.suggest_list")
    def test_suggest_endpoint_creates_from_preview_payload_without_recalling_llm(self, suggest_list):
        response = self.client.post(
            "/api/advisor/suggest/",
            {
                "faction": self.faction.id,
                "point_limit": 2000,
                "prompt": "Aggressive elite list.",
                "dry_run": False,
                "suggestion": self.suggestion.model_dump(),
            },
            format="json",
        )

        payload = response.json()
        self.assertEqual(response.status_code, 201)
        suggest_list.assert_not_called()
        self.assertEqual(ArmyList.objects.count(), 1)
        self.assertEqual(ListUnit.objects.count(), 1)
        self.assertEqual(
            payload["data"]["army_list"]["name"],
            "Kingdom of Angels - Offensive Elite (2000 pts)",
        )
        self.assertEqual(payload["data"]["army_list"]["units"][0]["unit_name"], "Paladins")

    @patch("advisor.views.suggest_list")
    def test_suggest_endpoint_persists_advisor_embedded_hero(self, suggest_list):
        host = Unit.objects.create(
            faction=self.faction,
            name="Guardians",
            quality=4,
            defense=5,
            tough=1,
            points=90,
            min_models=5,
            max_models=10,
            default_models=5,
        )
        UnitWeaponSlot.objects.create(unit=host, weapon=self.weapon, is_default=True)
        hero = Unit.objects.create(
            faction=self.faction,
            name="Champion",
            quality=3,
            defense=4,
            tough=3,
            points=95,
            special_rules={"Hero": True},
        )
        UnitWeaponSlot.objects.create(unit=hero, weapon=self.weapon, is_default=True)
        suggestion = self.suggestion.model_copy(
            update={
                "units": [
                    SuggestedUnit(
                        unit_id=host.id,
                        unit_name="Guardians",
                        model_count=5,
                        justification="Main scoring block.",
                    ),
                    SuggestedUnit(
                        unit_id=hero.id,
                        unit_name="Champion",
                        model_count=1,
                        parent_unit_index=0,
                        justification="Embedded aura support.",
                    ),
                ]
            }
        )

        response = self.client.post(
            "/api/advisor/suggest/",
            {
                "faction": self.faction.id,
                "point_limit": 2000,
                "prompt": "Use an aura hero in the main block.",
                "dry_run": False,
                "suggestion": suggestion.model_dump(),
            },
            format="json",
        )

        payload = response.json()
        self.assertEqual(response.status_code, 201)
        suggest_list.assert_not_called()
        host_payload = next(unit for unit in payload["data"]["army_list"]["units"] if unit["unit_name"] == "Guardians")
        hero_payload = next(unit for unit in payload["data"]["army_list"]["units"] if unit["unit_name"] == "Champion")
        self.assertIsNone(host_payload["parent_entry"])
        self.assertEqual(hero_payload["parent_entry"], host_payload["id"])
        self.assertEqual(payload["data"]["suggestion"]["units"][1]["parent_unit_index"], 0)

    @patch("advisor.views.suggest_list")
    def test_suggest_endpoint_uses_fallback_name_for_blank_archetype(self, suggest_list):
        suggestion = self.suggestion.model_copy(update={"archetype": "   "})

        response = self.client.post(
            "/api/advisor/suggest/",
            {
                "faction": self.faction.id,
                "point_limit": 750,
                "prompt": "Make a flexible list.",
                "dry_run": False,
                "suggestion": suggestion.model_dump(),
            },
            format="json",
        )

        payload = response.json()
        self.assertEqual(response.status_code, 201)
        suggest_list.assert_not_called()
        self.assertEqual(
            payload["data"]["army_list"]["name"],
            "Kingdom of Angels - Advisor List (750 pts)",
        )

    @patch("advisor.views.suggest_list")
    def test_suggest_endpoint_persists_reconciled_selected_upgrades(self, suggest_list):
        suggestion = self.suggestion.model_copy(
            update={
                "units": [
                    self.suggestion.units[0].model_copy(
                        update={"selected_upgrade_ids": [self.upgrade_option.id]}
                    )
                ],
            }
        )

        response = self.client.post(
            "/api/advisor/suggest/",
            {
                "faction": self.faction.id,
                "point_limit": 2000,
                "prompt": "Aggressive elite list.",
                "dry_run": False,
                "suggestion": suggestion.model_dump(),
            },
            format="json",
        )

        payload = response.json()
        self.assertEqual(response.status_code, 201)
        suggest_list.assert_not_called()
        self.assertEqual(payload["data"]["computed_total_points"], 200)
        self.assertEqual(payload["data"]["army_list"]["total_points"], 200)
        self.assertEqual(payload["data"]["army_list"]["validation"]["errors"], [])
        self.assertEqual(payload["data"]["army_list"]["units"][0]["selected_upgrades"], [self.upgrade_option.id])
        self.assertEqual(ListUnitUpgrade.objects.get().option, self.upgrade_option)

    @patch("advisor.views.suggest_list")
    def test_suggest_endpoint_creates_repaired_underfilled_preview_payload(self, suggest_list):
        guard = self._unit_with_default_weapon("Guardians", 90)
        scouts = self._unit_with_default_weapon("Scouts", 120, {"Scout": True})
        archers = self._unit_with_default_weapon("Archers", 150, {"Fast": True})
        gargoyles = self._unit_with_default_weapon("Gargoyles", 240, {"Flying": True})
        suggestion = ListSuggestion(
            units=[
                SuggestedUnit(
                    unit_id=self.unit.id,
                    unit_name="Paladins",
                    model_count=1,
                    justification="Durable center.",
                ),
                SuggestedUnit(
                    unit_id=guard.id,
                    unit_name="Guardians",
                    model_count=1,
                    justification="Objective unit one.",
                ),
                SuggestedUnit(
                    unit_id=guard.id,
                    unit_name="Guardians",
                    model_count=1,
                    justification="Objective unit two.",
                ),
                SuggestedUnit(
                    unit_id=scouts.id,
                    unit_name="Scouts",
                    model_count=1,
                    justification="Early mobility.",
                ),
                SuggestedUnit(
                    unit_id=archers.id,
                    unit_name="Archers",
                    model_count=1,
                    justification="Fast support.",
                ),
            ],
            total_points=630,
            archetype="Offensive Elite",
            playstyle="Shove It In",
            activation_count=5,
            strategy_summary="Push forward with mobile support.",
            warnings=[],
        )

        response = self.client.post(
            "/api/advisor/suggest/",
            {
                "faction": self.faction.id,
                "point_limit": 750,
                "prompt": "Aggressive elite list.",
                "dry_run": False,
                "suggestion": suggestion.model_dump(),
            },
            format="json",
        )

        payload = response.json()
        created_names = [unit["unit_name"] for unit in payload["data"]["army_list"]["units"]]
        self.assertEqual(response.status_code, 201)
        suggest_list.assert_not_called()
        self.assertEqual(payload["data"]["computed_total_points"], 740)
        self.assertEqual(payload["data"]["point_delta"], 10)
        self.assertIn(gargoyles.name, created_names)
        self.assertNotIn(archers.name, created_names)
        self.assertEqual(payload["data"]["army_list"]["validation"]["errors"], [])
        self.assertIn(
            "Gargoyles replaced Archers to use remaining points.",
            payload["data"]["reconciliation_warnings"],
        )
        self.assertIn(
            "Added Blessed Weapons to Paladins to use remaining points.",
            payload["data"]["reconciliation_warnings"],
        )

    def test_suggest_endpoint_rejects_invalid_preview_payload(self):
        response = self.client.post(
            "/api/advisor/suggest/",
            {
                "faction": self.faction.id,
                "point_limit": 2000,
                "prompt": "Aggressive elite list.",
                "dry_run": False,
                "suggestion": {"units": [{"unit_id": self.unit.id}]},
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("suggestion", str(response.json()["error"]).lower())

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

    @patch("advisor.views.suggest_list")
    def test_suggest_endpoint_retries_once_for_avoidable_reconciliation_changes(self, suggest_list):
        guard = self._unit_with_default_weapon("Guardians", 90)
        first = ListSuggestion(
            units=[
                SuggestedUnit(
                    unit_id=99999,
                    unit_name="Missing",
                    model_count=1,
                    justification="Bad package.",
                )
            ],
            total_points=100,
            archetype="Broken Draft",
            playstyle="Invalid",
            activation_count=1,
            strategy_summary="This should be corrected.",
            warnings=[],
        )
        corrected = ListSuggestion(
            units=[
                SuggestedUnit(
                    unit_id=guard.id,
                    unit_name="Guardians",
                    model_count=1,
                    justification="Legal scoring unit.",
                )
            ],
            total_points=90,
            archetype="Objective Control",
            playstyle="Board Play",
            activation_count=1,
            strategy_summary="Hold objectives with legal units.",
            warnings=[],
        )
        suggest_list.side_effect = [first, corrected]

        response = self.client.post(
            "/api/advisor/suggest/",
            {
                "faction": self.faction.id,
                "point_limit": 750,
                "prompt": "Make a legal list.",
            },
            format="json",
        )

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(suggest_list.call_count, 2)
        self.assertIn("unknown unit id", suggest_list.call_args.kwargs["correction_feedback"].lower())
        self.assertEqual(payload["data"]["suggestion"]["archetype"], "Objective Control")
        self.assertEqual(payload["data"]["suggestion"]["units"][0]["unit_name"], "Guardians")

    @patch("advisor.views.suggest_list")
    def test_suggest_endpoint_retries_once_for_actionable_metrics_feedback(self, suggest_list):
        first_units = [
            self._unit_with_default_weapon(f"Line Unit {index}", 150)
            for index in range(1, 6)
        ]
        corrected_units = [
            self._unit_with_default_weapon("Scouts", 150, {"Scout": True}),
            self._unit_with_default_weapon("Flyers", 150, {"Flying": True}),
            self._unit_with_default_weapon("Archers", 150, weapon_range=24),
            self._unit_with_default_weapon("Slayers", 150, weapon_ap=3),
            self._unit_with_default_weapon("Spears", 150),
        ]
        first = ListSuggestion(
            units=[
                SuggestedUnit(
                    unit_id=unit.id,
                    unit_name=unit.name,
                    model_count=1,
                    justification="Static line unit.",
                )
                for unit in first_units
            ],
            total_points=750,
            archetype="Static Line",
            playstyle="Stand and fight",
            activation_count=5,
            strategy_summary="Hold the center.",
            warnings=["Low mobility."],
        )
        corrected = ListSuggestion(
            units=[
                SuggestedUnit(
                    unit_id=unit.id,
                    unit_name=unit.name,
                    model_count=1,
                    justification="Covers a needed role.",
                )
                for unit in corrected_units
            ],
            total_points=750,
            archetype="Objective Control",
            playstyle="Mobile Board Play",
            activation_count=5,
            strategy_summary="Use mobile units to contest objectives.",
            warnings=[],
        )
        suggest_list.side_effect = [first, corrected]

        response = self.client.post(
            "/api/advisor/suggest/",
            {
                "faction": self.faction.id,
                "point_limit": 750,
                "prompt": "Make a mobile objective list.",
            },
            format="json",
        )

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(suggest_list.call_count, 2)
        feedback = suggest_list.call_args.kwargs["correction_feedback"]
        self.assertIn("List health metrics", feedback)
        self.assertIn("mobility packages 0", feedback)
        self.assertEqual(payload["data"]["suggestion"]["archetype"], "Objective Control")

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

    def _unit_with_default_weapon(self, name, points, special_rules=None, weapon_range=None, weapon_ap=None):
        unit = Unit.objects.create(
            faction=self.faction,
            name=name,
            quality=4,
            defense=5,
            tough=1,
            points=points,
            default_models=1,
            min_models=1,
            max_models=1,
            special_rules=special_rules or {},
        )
        weapon = self.weapon
        if weapon_range is not None or weapon_ap is not None:
            weapon = Weapon.objects.create(
                name=f"{name} Weapon",
                range=self.weapon.range if weapon_range is None else weapon_range,
                attacks=self.weapon.attacks,
                attacks_string=self.weapon.attacks_string,
                ap=self.weapon.ap if weapon_ap is None else weapon_ap,
            )
        UnitWeaponSlot.objects.create(unit=unit, weapon=weapon, is_default=True)
        return unit
