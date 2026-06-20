from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase, override_settings

from advisor.context_builder import build_reference_material, build_system_prompt, build_unit_table, build_user_context
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
        upgrade_options=("10: Banner (+20) replaces Sword",) if index == 1 else (),
    )


class ContextBuilderTests(SimpleTestCase):
    def test_unit_table_renders_expected_columns_and_rows(self):
        table = build_unit_table([profile(1), profile(2)])

        self.assertIn("| ID | Name | Pts | Q | Def | T | AP | EV_inf | EV_eli | EV_mon | W100 | Scout | Fast | Fly | Fear | Rng | Upgrades |", table)
        self.assertIn("| 1 | Unit 1 | 100 | 4+ | 5+ | 1 | 1 | 1.25 | 0.75 | 0.25 | 1.25 | no | no | no | yes | no | 10: Banner (+20) replaces Sword |", table)
        self.assertEqual(len([line for line in table.splitlines() if line.startswith("| ")]), 4)

    def test_system_prompt_contains_core_doctrine_terms(self):
        prompt = build_system_prompt(game="AoF")

        for term in ("activation", "AP", "mobility", "Scout", "Fearless", "25%", "archetype", "close to the point limit"):
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

    def test_reference_material_loads_markdown_in_deterministic_order(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "b.md").write_text("Second reference", encoding="utf-8")
            (root / "a.md").write_text("First reference", encoding="utf-8")
            (root / "skip.txt").write_text("Ignored", encoding="utf-8")

            with override_settings(ADVISOR_REFERENCE_DIR=root, ADVISOR_REFERENCE_MAX_CHARS=200):
                material = build_reference_material()

        self.assertIn("## a.md\nFirst reference", material)
        self.assertIn("## b.md\nSecond reference", material)
        self.assertNotIn("Ignored", material)
        self.assertLess(material.index("First reference"), material.index("Second reference"))
