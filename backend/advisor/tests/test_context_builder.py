from django.test import SimpleTestCase

from advisor.context_builder import build_system_prompt, build_unit_table, build_user_context
from advisor.unit_scorer import UnitProfile


def profile(index: int = 1) -> UnitProfile:
    return UnitProfile(
        unit_id=index,
        name=f"Unit {index}",
        points=100,
        quality=4,
        defense=5,
        tough=1,
        default_models=1,
        default_weapon_slot_id=index,
        default_weapon_name="Sword",
        max_ap=1,
        ev_infantry=1.25,
        ev_elite=0.75,
        ev_monster=0.25,
        wounds_per_100pts_infantry=1.25,
        p_kill_infantry=0.45,
        effective_health=1,
        resilience_score=0.5,
        has_scout=index % 2 == 0,
        has_fast=False,
        has_flying=False,
        has_fearless=True,
        has_stealth=False,
        has_regeneration=False,
        is_ranged=False,
    )


class ContextBuilderTests(SimpleTestCase):
    def test_unit_table_renders_expected_columns_and_rows(self):
        table = build_unit_table([profile(1), profile(2)])

        self.assertIn("| ID | Name | Pts | Q | Def | T | AP | EV_inf | EV_eli | EV_mon | W100 | Scout | Fast | Fear | Rng |", table)
        self.assertIn("| 1 | Unit 1 | 100 | 4+ | 5+ | 1 | 1 | 1.25 | 0.75 | 0.25 | 1.25 | no | no | yes | no |", table)
        self.assertEqual(len([line for line in table.splitlines() if line.startswith("| ")]), 4)

    def test_system_prompt_contains_core_doctrine_terms(self):
        prompt = build_system_prompt(game="AoF")

        for term in ("activation", "AP", "mobility", "Scout", "Fearless", "25%", "archetype"):
            self.assertIn(term, prompt)

    def test_user_context_stays_bounded_for_typical_faction(self):
        unit_table = build_unit_table([profile(index) for index in range(1, 41)])

        context = build_user_context(
            faction_name="Kingdom of Angels",
            point_limit=2000,
            unit_table=unit_table,
            user_prompt="Build an aggressive mobile list.",
        )

        self.assertLess(len(context), 6000)
        self.assertIn("Kingdom of Angels", context)
        self.assertIn("Build an aggressive mobile list.", context)
