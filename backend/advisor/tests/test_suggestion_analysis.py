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
        scouts = self._unit("Scouts", 150, special_rules={"Scout": True}, weapon_attacks=10, weapon_ap=2)
        flyers = self._unit("Flyers", 150, special_rules={"Flying": True}, weapon_attacks=10, weapon_ap=2)
        archers = self._unit("Archers", 150, weapon_range=24, weapon_attacks=10, weapon_ap=2)
        slayers = self._unit("Slayers", 150, weapon_attacks=10, weapon_ap=3)
        spears = self._unit("Spears", 150, weapon_attacks=10, weapon_ap=2)
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

    def test_low_damage_output_produces_bounded_feedback(self):
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
        feedback = build_metrics_correction_feedback(analysis)

        self.assertLess(analysis.damage_output_score, 45)
        self.assertIn("Improve total damage output", feedback)
        self.assertIn("Current totals:", feedback)
        self.assertIn("expected around 25.00 / 12.00 / 8.00 at 750 pts", feedback)

    def test_damage_output_benchmarks_scale_by_point_limit(self):
        hitters = [
            self._unit(f"Hitter {index}", 300, weapon_attacks=10, weapon_ap=2)
            for index in range(1, 6)
        ]
        suggestion = self._suggestion(
            *[
                SuggestedUnit(unit_id=unit.id, unit_name=unit.name, model_count=1, justification="Damage.")
                for unit in hitters
            ]
        )
        reconciled = reconcile_suggestion(
            faction=self.faction,
            point_limit=1500,
            suggestion=suggestion,
        )

        analysis = analyze_reconciled_suggestion(
            faction=self.faction,
            point_limit=1500,
            reconciled=reconciled,
        )

        self.assertEqual(analysis.damage_output_benchmarks["infantry"], 50)
        self.assertEqual(analysis.damage_output_benchmarks["elite"], 24)
        self.assertEqual(analysis.damage_output_benchmarks["monster"], 16)

    def test_selected_damage_upgrades_contribute_to_damage_output(self):
        unit = self._unit("Spears", 200, weapon_attacks=1)
        upgrade_weapon = Weapon.objects.create(
            name="Heavy Spear",
            range=0,
            attacks=20,
            attacks_string="A20",
            ap=3,
        )
        option = unit.upgrade_sections.create(
            section_uid="spears-weapons",
            label="Weapons",
        ).options.create(
            option_uid="heavy-spears",
            label="Heavy Spears",
            cost=0,
        )
        option.weapons.add(upgrade_weapon)
        suggestion = self._suggestion(
            SuggestedUnit(
                unit_id=unit.id,
                unit_name=unit.name,
                model_count=1,
                selected_upgrade_ids=[option.id],
                justification="Upgrade damage.",
            )
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

        self.assertGreater(analysis.target_ev["infantry"], 1)

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
        weapon_attacks: int = 2,
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
            attacks=weapon_attacks,
            attacks_string=f"A{weapon_attacks}",
            ap=weapon_ap,
        )
        UnitWeaponSlot.objects.create(unit=unit, weapon=weapon, is_default=True)
        return unit
