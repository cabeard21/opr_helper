from django.test import TestCase

from advisor.llm_service import ListSuggestion, SuggestedUnit
from advisor.reconciliation import reconcile_suggestion
from army_books.models import Faction, Unit, UnitUpgradeOption, UnitUpgradeSection, UnitWeaponSlot, Weapon


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
        self.guard = Unit.objects.create(
            faction=self.faction,
            name="Guardians",
            quality=4,
            defense=5,
            tough=1,
            points=90,
            min_models=1,
            max_models=1,
            default_models=1,
        )
        self.hero = Unit.objects.create(
            faction=self.faction,
            name="Champion",
            quality=3,
            defense=4,
            tough=3,
            points=95,
            special_rules={"Hero": True},
        )
        weapon = Weapon.objects.create(
            name="Great Weapon",
            range=0,
            attacks=2,
            attacks_string="A2",
            ap=2,
        )
        UnitWeaponSlot.objects.create(unit=self.unit, weapon=weapon, is_default=True)
        UnitWeaponSlot.objects.create(unit=self.guard, weapon=weapon, is_default=True)
        UnitWeaponSlot.objects.create(unit=self.hero, weapon=weapon, is_default=True)
        self.scouts = self._unit_with_default_weapon(
            name="Scouts",
            points=120,
            special_rules={"Scout": True},
        )
        self.archers = self._unit_with_default_weapon(
            name="Archers",
            points=150,
            special_rules={"Fast": True},
        )
        self.gargoyles = self._unit_with_default_weapon(
            name="Gargoyles",
            points=240,
            special_rules={"Flying": True},
        )
        self.bull_construct = self._unit_with_default_weapon(
            name="Bull Construct",
            points=300,
            tough=12,
        )

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

    def test_synced_default_size_unit_cost_is_not_multiplied_by_minimum_models(self):
        cultists = self._unit_with_default_weapon(
            name="Cultists",
            points=65,
            min_models=10,
            max_models=20,
            default_models=10,
        )
        suggestion = self._suggestion(
            SuggestedUnit(
                unit_id=cultists.id,
                unit_name="Cultists",
                model_count=1,
                justification="Cheap activation.",
            )
        )

        result = reconcile_suggestion(
            faction=self.faction,
            point_limit=750,
            suggestion=suggestion,
        )

        self.assertEqual(result.suggestion.units[0].model_count, 10)
        self.assertEqual(result.computed_total_points, 65)
        self.assertNotIn("35% force organization unit cap", "\n".join(result.warnings))

    def test_fixed_default_size_unit_with_upgrade_is_clamped_before_points(self):
        immortals = self._unit_with_default_weapon(
            name="Immortals",
            points=90,
            min_models=5,
            max_models=None,
            default_models=5,
        )
        banner = self._upgrade_option(immortals, "Banner", 10)
        suggestion = self._suggestion(
            SuggestedUnit(
                unit_id=immortals.id,
                unit_name="Immortals",
                model_count=10,
                selected_upgrade_ids=[banner.id],
                justification="Reliable melee scoring unit.",
            )
        )

        result = reconcile_suggestion(
            faction=self.faction,
            point_limit=750,
            suggestion=suggestion,
        )

        self.assertEqual(result.suggestion.units[0].model_count, 5)
        self.assertEqual(result.suggestion.units[0].selected_upgrade_ids, [banner.id])
        self.assertEqual(result.computed_total_points, 100)
        self.assertIn("Immortals model count was reduced to the maximum of 5.", result.warnings)

    def test_minimum_model_units_do_not_false_trip_force_org_point_share(self):
        cultists = self._unit_with_default_weapon("Cultists", 65, min_models=10, max_models=20, default_models=10)
        shooters = self._unit_with_default_weapon("Shooters", 95, min_models=10, max_models=20, default_models=10)
        infernal_shooters = self._unit_with_default_weapon(
            "Infernal Shooters",
            120,
            min_models=10,
            max_models=20,
            default_models=10,
        )
        berserkers = self._unit_with_default_weapon("Berserkers", 150, min_models=10, max_models=20, default_models=10)
        suggestion = self._suggestion(
            SuggestedUnit(unit_id=cultists.id, unit_name="Cultists", model_count=10, justification="Screen."),
            SuggestedUnit(unit_id=shooters.id, unit_name="Shooters", model_count=10, justification="Ranged."),
            SuggestedUnit(
                unit_id=infernal_shooters.id,
                unit_name="Infernal Shooters",
                model_count=10,
                justification="Ranged AP.",
            ),
            SuggestedUnit(unit_id=berserkers.id, unit_name="Berserkers", model_count=10, justification="Melee."),
        )

        result = reconcile_suggestion(
            faction=self.faction,
            point_limit=750,
            suggestion=suggestion,
        )

        self.assertEqual(
            [unit.unit_name for unit in result.suggestion.units],
            ["Cultists", "Shooters", "Infernal Shooters", "Berserkers"],
        )
        self.assertEqual(result.computed_total_points, 430)
        self.assertNotIn("35% force organization unit cap", "\n".join(result.warnings))

    def test_invalid_or_wrong_unit_selected_upgrade_ids_are_ignored_with_warnings(self):
        option = self._upgrade_option(self.unit, "Blessed Weapons", 20)
        wrong_unit_option = self._upgrade_option(self.guard, "Guardian Banner", 15)
        suggestion = self._suggestion(
            SuggestedUnit(
                unit_id=self.unit.id,
                unit_name="Paladins",
                model_count=1,
                selected_upgrade_ids=[option.id, wrong_unit_option.id, 99999],
                justification="Durable high-AP unit.",
            )
        )

        result = reconcile_suggestion(
            faction=self.faction,
            point_limit=750,
            suggestion=suggestion,
        )

        self.assertEqual(result.suggestion.units[0].selected_upgrade_ids, [option.id])
        self.assertEqual(result.computed_total_points, 200)
        self.assertIn(f"Paladins ignored invalid upgrade id {wrong_unit_option.id}.", result.warnings)
        self.assertIn("Paladins ignored invalid upgrade id 99999.", result.warnings)

    def test_repair_can_add_legal_upgrade_to_reduce_point_delta(self):
        unit_a = self._unit_with_default_weapon("Line Guard", 100)
        unit_b = self._unit_with_default_weapon("Rangers", 130)
        unit_c = self._unit_with_default_weapon("Lancers", 120)
        option = self._upgrade_option(unit_a, "Blessed Weapons", 60)
        suggestion = self._suggestion(
            SuggestedUnit(unit_id=unit_a.id, unit_name="Line Guard", model_count=1, justification="Center."),
            SuggestedUnit(unit_id=unit_b.id, unit_name="Rangers", model_count=1, justification="Ranged."),
            SuggestedUnit(unit_id=unit_c.id, unit_name="Lancers", model_count=1, justification="Flank."),
            total_points=350,
        )

        result = reconcile_suggestion(
            faction=self.faction,
            point_limit=460,
            suggestion=suggestion,
        )

        self.assertGreater(result.computed_total_points, 350)
        self.assertLessEqual(result.computed_total_points, 460)
        upgraded = next(unit for unit in result.suggestion.units if unit.unit_id == unit_a.id)
        self.assertEqual(upgraded.selected_upgrade_ids, [option.id])
        self.assertIn("Added Blessed Weapons to Line Guard to use remaining points.", result.warnings)

    def test_upgrade_repair_respects_point_limit_and_force_org_cap(self):
        unit_a = self._unit_with_default_weapon("Line Guard", 100)
        unit_b = self._unit_with_default_weapon("Rangers", 130)
        unit_c = self._unit_with_default_weapon("Lancers", 120)
        self._upgrade_option(unit_a, "Too Expensive", 200)
        suggestion = self._suggestion(
            SuggestedUnit(unit_id=unit_a.id, unit_name="Line Guard", model_count=1, justification="Center."),
            SuggestedUnit(unit_id=unit_b.id, unit_name="Rangers", model_count=1, justification="Ranged."),
            SuggestedUnit(unit_id=unit_c.id, unit_name="Lancers", model_count=1, justification="Flank."),
            total_points=350,
        )

        result = reconcile_suggestion(
            faction=self.faction,
            point_limit=460,
            suggestion=suggestion,
        )

        remaining_unit_a = [unit for unit in result.suggestion.units if unit.unit_id == unit_a.id]
        if remaining_unit_a:
            self.assertEqual(remaining_unit_a[0].selected_upgrade_ids, [])
        self.assertGreaterEqual(result.computed_total_points, 350)
        self.assertNotIn("Too Expensive", "\n".join(result.warnings))

    def test_trims_suggestion_to_force_org_and_point_limit(self):
        suggestion = self._suggestion(
            SuggestedUnit(unit_id=self.hero.id, unit_name="Champion", model_count=1, justification="Hero one."),
            SuggestedUnit(unit_id=self.hero.id, unit_name="Champion", model_count=1, justification="Hero two."),
            SuggestedUnit(unit_id=self.guard.id, unit_name="Guardians", model_count=1, justification="Score one."),
            SuggestedUnit(unit_id=self.guard.id, unit_name="Guardians", model_count=1, justification="Score two."),
            SuggestedUnit(unit_id=self.guard.id, unit_name="Guardians", model_count=1, justification="Score three."),
            SuggestedUnit(unit_id=self.guard.id, unit_name="Guardians", model_count=1, justification="Score four."),
        )

        result = reconcile_suggestion(
            faction=self.faction,
            point_limit=750,
            suggestion=suggestion,
        )

        self.assertLessEqual(result.computed_total_points, 750)
        self.assertEqual([unit.unit_name for unit in result.suggestion.units], ["Champion", "Guardians", "Guardians"])
        self.assertIn("Champion was skipped because force organization allows at most 1 heroes.", result.warnings)
        self.assertIn("Guardians was skipped because force organization allows at most 2 copies.", result.warnings)

    def test_preserves_legal_embedded_hero_parent_index(self):
        host = self._unit_with_default_weapon(
            "Shield Wall",
            120,
            min_models=5,
            max_models=10,
            default_models=5,
        )
        suggestion = self._suggestion(
            SuggestedUnit(unit_id=host.id, unit_name="Shield Wall", model_count=5, justification="Main block."),
            SuggestedUnit(
                unit_id=self.hero.id,
                unit_name="Champion",
                model_count=1,
                parent_unit_index=0,
                justification="Aura support for the block.",
            ),
        )

        result = reconcile_suggestion(
            faction=self.faction,
            point_limit=1000,
            suggestion=suggestion,
        )

        self.assertEqual(result.computed_total_points, 215)
        self.assertEqual(result.suggestion.activation_count, 1)
        self.assertIsNone(result.suggestion.units[0].parent_unit_index)
        self.assertEqual(result.suggestion.units[1].parent_unit_index, 0)
        self.assertEqual(result.warnings, [])

    def test_invalid_embedded_hero_parent_index_degrades_to_standalone(self):
        suggestion = self._suggestion(
            SuggestedUnit(
                unit_id=self.hero.id,
                unit_name="Champion",
                model_count=1,
                parent_unit_index=4,
                justification="Bad parent.",
            )
        )

        result = reconcile_suggestion(
            faction=self.faction,
            point_limit=1000,
            suggestion=suggestion,
        )

        self.assertIsNone(result.suggestion.units[0].parent_unit_index)
        self.assertIn("Champion ignored invalid embedded host index 4.", result.warnings)

    def test_repairs_full_force_org_underfill_by_swapping_legal_higher_value_unit(self):
        suggestion = self._suggestion(
            SuggestedUnit(unit_id=self.unit.id, unit_name="Paladins", model_count=1, justification="Durable center."),
            SuggestedUnit(unit_id=self.guard.id, unit_name="Guardians", model_count=1, justification="Objective unit one."),
            SuggestedUnit(unit_id=self.guard.id, unit_name="Guardians", model_count=1, justification="Objective unit two."),
            SuggestedUnit(unit_id=self.scouts.id, unit_name="Scouts", model_count=1, justification="Early mobility."),
            SuggestedUnit(unit_id=self.archers.id, unit_name="Archers", model_count=1, justification="Fast support."),
            total_points=630,
        )

        result = reconcile_suggestion(
            faction=self.faction,
            point_limit=750,
            suggestion=suggestion,
        )

        self.assertEqual(result.computed_total_points, 750)
        self.assertEqual(result.point_delta, 0)
        self.assertEqual(len(result.suggestion.units), 5)
        self.assertIn("Gargoyles", [unit.unit_name for unit in result.suggestion.units])
        self.assertNotIn("Scouts", [unit.unit_name for unit in result.suggestion.units])
        self.assertIn("Gargoyles replaced Scouts to use remaining points.", result.warnings)
        self.assertNotIn(
            "Gargoyles was skipped because force organization allows at most 5 units.",
            result.warnings,
        )

    def test_repair_does_not_use_candidates_over_force_org_point_share(self):
        suggestion = self._suggestion(
            SuggestedUnit(unit_id=self.unit.id, unit_name="Paladins", model_count=1, justification="Durable center."),
            SuggestedUnit(unit_id=self.guard.id, unit_name="Guardians", model_count=1, justification="Objective unit one."),
            SuggestedUnit(unit_id=self.guard.id, unit_name="Guardians", model_count=1, justification="Objective unit two."),
            SuggestedUnit(unit_id=self.scouts.id, unit_name="Scouts", model_count=1, justification="Early mobility."),
            SuggestedUnit(unit_id=self.archers.id, unit_name="Archers", model_count=1, justification="Fast support."),
            total_points=630,
        )

        result = reconcile_suggestion(
            faction=self.faction,
            point_limit=750,
            suggestion=suggestion,
        )

        self.assertNotIn("Bull Construct", [unit.unit_name for unit in result.suggestion.units])
        self.assertNotIn("Bull Construct replaced", "\n".join(result.warnings))

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

    def _unit_with_default_weapon(
        self,
        name: str,
        points: int,
        tough: int = 1,
        special_rules=None,
        min_models: int = 1,
        max_models: int | None = 1,
        default_models: int = 1,
    ):
        unit = Unit.objects.create(
            faction=self.faction,
            name=name,
            quality=4,
            defense=5,
            tough=tough,
            points=points,
            min_models=min_models,
            max_models=max_models,
            default_models=default_models,
            special_rules=special_rules or {},
        )
        weapon = Weapon.objects.create(
            name=f"{name} Weapon",
            range=0,
            attacks=2,
            attacks_string="A2",
            ap=1,
        )
        UnitWeaponSlot.objects.create(unit=unit, weapon=weapon, is_default=True)
        return unit

    def _upgrade_option(self, unit: Unit, label: str, cost: int) -> UnitUpgradeOption:
        section = UnitUpgradeSection.objects.create(
            unit=unit,
            section_uid=f"{unit.id}-{label}",
            label=f"{unit.name} Upgrades",
        )
        return UnitUpgradeOption.objects.create(
            section=section,
            option_uid=label,
            label=label,
            cost=cost,
        )
