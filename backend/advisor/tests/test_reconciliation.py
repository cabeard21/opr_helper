from django.test import TestCase

from advisor.llm_service import ListSuggestion, SuggestedUnit
from advisor.reconciliation import reconcile_suggestion
from army_books.models import Faction, Unit, UnitWeaponSlot, Weapon


class SuggestionReconciliationTests(TestCase):
    def setUp(self):
        self.faction = Faction.objects.create(name="Kingdom of Angels", version="3.5.3")
        self.other_faction = Faction.objects.create(name="Beastmen", version="3.5.3")
        self.unit = Unit.objects.create(
            faction=self.faction,
            name="Paladins",
            quality=3,
            defense=4,
            tough=3,
            points=180,
            min_models=1,
            max_models=2,
            default_models=1,
        )
        self.other_unit = Unit.objects.create(
            faction=self.other_faction,
            name="Raiders",
            quality=4,
            defense=5,
            tough=1,
            points=90,
        )
        weapon = Weapon.objects.create(
            name="Great Weapon",
            range=0,
            attacks=2,
            attacks_string="A2",
            ap=2,
        )
        UnitWeaponSlot.objects.create(unit=self.unit, weapon=weapon, is_default=True)

    def test_recomputes_total_points_from_database_units(self):
        suggestion = self._suggestion(
            SuggestedUnit(
                unit_id=self.unit.id,
                unit_name="Paladins",
                model_count=2,
                justification="Durable high-AP unit.",
            ),
            total_points=1,
        )

        result = reconcile_suggestion(
            faction=self.faction,
            point_limit=2000,
            suggestion=suggestion,
        )

        self.assertEqual(result.computed_total_points, 360)
        self.assertEqual(result.point_delta, 1640)
        self.assertEqual(result.suggestion.total_points, 360)
        self.assertEqual(result.warnings, [])

    def test_skips_wrong_faction_and_unknown_units_with_warnings(self):
        suggestion = self._suggestion(
            SuggestedUnit(
                unit_id=self.other_unit.id,
                unit_name="Raiders",
                model_count=1,
                justification="Not from this faction.",
            ),
            SuggestedUnit(
                unit_id=99999,
                unit_name="Missing",
                model_count=1,
                justification="Unknown unit.",
            ),
        )

        result = reconcile_suggestion(
            faction=self.faction,
            point_limit=2000,
            suggestion=suggestion,
        )

        self.assertEqual(result.suggestion.units, [])
        self.assertEqual(result.computed_total_points, 0)
        self.assertIn("Raiders is not available to Kingdom of Angels.", result.warnings)
        self.assertIn("Missing references an unknown unit id and was skipped.", result.warnings)

    def test_clamps_model_count_to_unit_bounds(self):
        suggestion = self._suggestion(
            SuggestedUnit(
                unit_id=self.unit.id,
                unit_name="Paladins",
                model_count=9,
                justification="Too many models.",
            )
        )

        result = reconcile_suggestion(
            faction=self.faction,
            point_limit=2000,
            suggestion=suggestion,
        )

        self.assertEqual(result.suggestion.units[0].model_count, 2)
        self.assertEqual(result.computed_total_points, 360)
        self.assertIn("Paladins model count was reduced to the maximum of 2.", result.warnings)

    def _suggestion(self, *units: SuggestedUnit, total_points=0):
        return ListSuggestion(
            units=list(units),
            total_points=total_points,
            archetype="Offensive Elite",
            playstyle="Shove It In",
            activation_count=len(units),
            strategy_summary="Push the center.",
            warnings=[],
        )
