from django.test import TestCase

from advisor.llm_service import ListSuggestion, SuggestedUnit
from advisor.reconciliation import reconcile_suggestion
from advisor.suggestion_analysis import (
    analyze_reconciled_suggestion,
    build_metrics_correction_feedback,
)
from army_books.models import Faction, Unit, UnitWeaponSlot, Weapon


class SuggestionAnalysisTests(TestCase):
    def setUp(self):
        self.faction = Faction.objects.create(name="Kingdom of Angels", version="3.5.3")

    def test_low_activation_and_no_mobility_produces_actionable_feedback(self):
        guard = self._unit("Guard", 250)
        hammer = self._unit("Hammer", 250)
        suggestion = self._suggestion(
            SuggestedUnit(unit_id=guard.id, unit_name=guard.name, model_count=1, justification="Hold."),
            SuggestedUnit(unit_id=hammer.id, unit_name=hammer.name, model_count=1, justification="Hit."),
        )
        reconciled = reconcile_suggestion(
            faction=self.faction,
            point_limit=1000,
            suggestion=suggestion,
        )

        analysis = analyze_reconciled_suggestion(
            faction=self.faction,
            point_limit=1000,
            reconciled=reconciled,
        )
        feedback = build_metrics_correction_feedback(analysis)

        self.assertIn("activations 2", feedback)
        self.assertIn("mobility packages 0", feedback)
        self.assertIn("Improve activation count", feedback)
        self.assertIn("Add mobile objective play", feedback)

    def test_embedded_hero_points_count_toward_largest_group_share(self):
        host = self._unit("Shield Wall", 260, min_models=5, default_models=5)
        hero = self._unit("Champion", 90, special_rules={"Hero": True})
        suggestion = self._suggestion(
            SuggestedUnit(unit_id=host.id, unit_name=host.name, model_count=5, justification="Main block."),
            SuggestedUnit(
                unit_id=hero.id,
                unit_name=hero.name,
                model_count=1,
                parent_unit_index=0,
                justification="Aura support.",
            ),
        )
        reconciled = reconcile_suggestion(
            faction=self.faction,
            point_limit=1000,
            suggestion=suggestion,
        )

        analysis = analyze_reconciled_suggestion(
            faction=self.faction,
            point_limit=1000,
            reconciled=reconciled,
        )

        self.assertEqual(analysis.largest_group_points, 350)
        self.assertEqual(analysis.largest_group_share, 0.35)

    def test_balanced_list_produces_no_metrics_feedback(self):
        scouts = self._unit("Scouts", 150, special_rules={"Scout": True})
        flyers = self._unit("Flyers", 150, special_rules={"Flying": True})
        archers = self._unit("Archers", 150, weapon_range=24)
        slayers = self._unit("Slayers", 150, weapon_ap=3)
        spears = self._unit("Spears", 150)
        suggestion = self._suggestion(
            SuggestedUnit(unit_id=scouts.id, unit_name=scouts.name, model_count=1, justification="Scout."),
            SuggestedUnit(unit_id=flyers.id, unit_name=flyers.name, model_count=1, justification="Fly."),
            SuggestedUnit(unit_id=archers.id, unit_name=archers.name, model_count=1, justification="Shoot."),
            SuggestedUnit(unit_id=slayers.id, unit_name=slayers.name, model_count=1, justification="AP."),
            SuggestedUnit(unit_id=spears.id, unit_name=spears.name, model_count=1, justification="Score."),
        )
        reconciled = reconcile_suggestion(
            faction=self.faction,
            point_limit=750,
            suggestion=suggestion,
        )

        analysis = analyze_reconciled_suggestion(
            faction=self.faction,
            point_limit=750,
            reconciled=reconciled,
        )

        self.assertEqual(build_metrics_correction_feedback(analysis), "")

    def _suggestion(self, *units: SuggestedUnit) -> ListSuggestion:
        return ListSuggestion(
            units=list(units),
            total_points=sum(unit.model_count for unit in units),
            archetype="Balanced",
            playstyle="Board Control",
            activation_count=len(units),
            strategy_summary="Play objectives.",
            warnings=[],
        )

    def _unit(
        self,
        name: str,
        points: int,
        *,
        special_rules=None,
        weapon_range: int = 0,
        weapon_ap: int = 0,
        min_models: int = 1,
        default_models: int = 1,
    ) -> Unit:
        unit = Unit.objects.create(
            faction=self.faction,
            name=name,
            quality=4,
            defense=5,
            tough=1,
            points=points,
            min_models=min_models,
            max_models=default_models,
            default_models=default_models,
            special_rules=special_rules or {},
        )
        weapon = Weapon.objects.create(
            name=f"{name} Weapon",
            range=weapon_range,
            attacks=2,
            attacks_string="A2",
            ap=weapon_ap,
        )
        UnitWeaponSlot.objects.create(unit=unit, weapon=weapon, is_default=True)
        return unit
