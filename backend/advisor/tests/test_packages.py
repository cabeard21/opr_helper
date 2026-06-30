from django.test import TestCase

from advisor.packages import build_advisor_packages, build_package_table, force_org_summary, prompt_packages
from army_books.models import (
    Faction,
    FactionSpell,
    Unit,
    UnitUpgradeOption,
    UnitUpgradeOptionWeapon,
    UnitUpgradeSection,
    UnitWeaponSlot,
    Weapon,
)


class AdvisorPackageTests(TestCase):
    def setUp(self):
        self.faction = Faction.objects.create(name="Kingdom of Angels", version="3.5.3")
        self.weapon = Weapon.objects.create(
            name="Great Weapon",
            range=0,
            attacks=2,
            attacks_string="A2",
            ap=2,
        )

    def test_builds_default_size_package_with_roles_and_force_org_hints(self):
        unit = self._unit(
            name="Sky Guard",
            points=120,
            min_models=5,
            max_models=10,
            default_models=5,
            special_rules={"Scout": True, "Flying": True},
        )

        packages = build_advisor_packages(self.faction.id, point_limit=750)

        package = next(candidate for candidate in packages if candidate.unit_id == unit.id)
        self.assertEqual(package.package_id, f"u{unit.id}-base")
        self.assertEqual(package.model_count, 5)
        self.assertEqual(package.points, 120)
        self.assertEqual(package.ev_infantry, 5.0)
        self.assertEqual(package.ev_elite, 3.333333)
        self.assertEqual(package.ev_monster, 1.666667)
        self.assertEqual(package.wounds_per_100pts_infantry, 4.166667)
        self.assertEqual(package.selected_upgrade_ids, [])
        self.assertIn("mobility", package.role_tags)
        self.assertIn("core", package.role_tags)
        self.assertFalse(package.exceeds_group_cap)

    def test_builds_upgrade_packages_with_computed_points(self):
        unit = self._unit(name="Paladins", points=180, tough=3)
        section = UnitUpgradeSection.objects.create(
            unit=unit,
            section_uid="paladin-upgrades",
            label="Paladin Upgrades",
        )
        option = UnitUpgradeOption.objects.create(
            section=section,
            option_uid="blessed-weapons",
            label="Blessed Weapons",
            cost=20,
        )

        packages = build_advisor_packages(self.faction.id, point_limit=750)

        upgrade_package = next(
            candidate for candidate in packages if candidate.selected_upgrade_ids == [option.id]
        )
        self.assertEqual(upgrade_package.package_id, f"u{unit.id}-o{option.id}")
        self.assertEqual(upgrade_package.points, 200)
        self.assertIn("anti-tough", upgrade_package.role_tags)

    def test_replace_upgrade_package_matches_plural_target_to_singular_weapon(self):
        dual_weapons = Weapon.objects.create(
            name="Dual Hand Weapons",
            range=0,
            attacks=2,
            attacks_string="A2",
            ap=0,
        )
        unit = self._unit(name="War Gore Reavers", points=100)
        section = UnitUpgradeSection.objects.create(
            unit=unit,
            section_uid="war-gore-weapons",
            label="Replace all Great Weapons",
            variant="replace",
            targets=["Great Weapons"],
        )
        option = UnitUpgradeOption.objects.create(
            section=section,
            option_uid="dual-hand-weapons",
            label="Dual Hand Weapons (A2)",
            cost=10,
        )
        option.weapons.add(dual_weapons)

        packages = build_advisor_packages(self.faction.id, point_limit=750)

        upgrade_package = next(
            candidate for candidate in packages if candidate.selected_upgrade_ids == [option.id]
        )
        self.assertEqual(upgrade_package.max_ap, 0)
        table = build_package_table([upgrade_package])
        self.assertIn(f"| u{unit.id}-o{option.id} | War Gore Reavers | 110 |", table)
        self.assertIn("| 0 |", table)
        self.assertNotIn("| 2 |", table)

    def test_dependent_replace_upgrade_package_includes_prerequisite_upgrade(self):
        javelin = Weapon.objects.create(
            name="Javelin",
            range=12,
            attacks=1,
            attacks_string="A1",
            ap=0,
        )
        storm_trident = Weapon.objects.create(
            name="Storm Trident",
            range=18,
            attacks=1,
            attacks_string="A1",
            ap=2,
        )
        unit = self._unit(name="Winged Wardens", points=100)
        javelin_section = UnitUpgradeSection.objects.create(
            unit=unit,
            section_uid="winged-warden-javelins",
            label="Take Javelins",
            variant="upgrade",
        )
        javelins = UnitUpgradeOption.objects.create(
            section=javelin_section,
            option_uid="javelins",
            label="Javelins",
            cost=10,
        )
        javelins.weapons.add(javelin)
        trident_section = UnitUpgradeSection.objects.create(
            unit=unit,
            section_uid="winged-warden-trident",
            label="Replace one Javelin",
            variant="replace",
            targets=["Javelins"],
        )
        trident = UnitUpgradeOption.objects.create(
            section=trident_section,
            option_uid="storm-trident",
            label="Storm Trident",
            cost=15,
        )
        trident.weapons.add(storm_trident)

        packages = build_advisor_packages(self.faction.id, point_limit=750)

        self.assertNotIn([trident.id], [package.selected_upgrade_ids for package in packages])
        package = next(
            candidate for candidate in packages if candidate.selected_upgrade_ids == [javelins.id, trident.id]
        )
        self.assertEqual(package.points, 125)
        self.assertEqual(package.upgrade_labels, ["Javelins", "Storm Trident"])
        self.assertEqual(package.max_ap, 2)

    def test_replace_any_weapon_team_package_uses_full_replacement_quantity(self):
        crew = Weapon.objects.create(name="Crew", range=0, attacks=1, attacks_string="A1")
        heavy_drill = Weapon.objects.create(
            name="Heavy Drill",
            range=0,
            attacks=1,
            attacks_string="A1",
            ap=4,
            special_rules={"Deadly": 3},
        )
        gatling = Weapon.objects.create(
            name="Gatling Gun",
            range=18,
            attacks=4,
            attacks_string="A4",
            ap=1,
        )
        mortar = Weapon.objects.create(
            name="Toxin Mortar",
            range=24,
            attacks=2,
            attacks_string="A2",
            ap=1,
            special_rules={"Poison": True},
        )
        unit = self._unit(
            name="Weapon Teams",
            points=110,
            tough=3,
            min_models=3,
            max_models=3,
            default_models=3,
            weapon=crew,
        )
        UnitWeaponSlot.objects.create(unit=unit, weapon=heavy_drill, is_default=True, count=3)
        unit.weapon_slots.filter(weapon=crew).update(count=3)
        section = UnitUpgradeSection.objects.create(
            unit=unit,
            section_uid="weapon-team-drills",
            label="Replace any Heavy Drill",
            variant="replace",
            targets=["Heavy Drill"],
            affects={"type": "any"},
        )
        option = UnitUpgradeOption.objects.create(
            section=section,
            option_uid="gatling-gun",
            label='Gatling Gun (18", A4, AP(1))',
            cost=5,
        )
        UnitUpgradeOptionWeapon.objects.create(option=option, weapon=gatling, count=1)
        mortar_option = UnitUpgradeOption.objects.create(
            section=section,
            option_uid="toxin-mortar",
            label='Toxin Mortar (24", A2, AP(1), Poison)',
            cost=5,
        )
        UnitUpgradeOptionWeapon.objects.create(option=mortar_option, weapon=mortar, count=1)

        packages = build_advisor_packages(self.faction.id, point_limit=750)

        base_package = next(candidate for candidate in packages if candidate.package_id == f"u{unit.id}-base")
        self.assertNotIn("ranged", base_package.role_tags)
        self.assertEqual(base_package.ranged_ev_infantry, 0)
        package = next(candidate for candidate in packages if candidate.selected_upgrade_ids == [option.id])
        self.assertIn("ranged", package.role_tags)
        self.assertEqual(package.selected_upgrade_selections, [{"option": option.id, "quantity": 3}])
        self.assertEqual(package.upgrade_labels, ['Gatling Gun (18", A4, AP(1)) x3'])
        self.assertEqual(package.max_ap, 1)
        self.assertGreater(package.ranged_ev_infantry, 0)
        self.assertEqual(package.points, 125)
        self.assertNotIn(
            [option.id, mortar_option.id],
            [candidate.selected_upgrade_ids for candidate in packages],
        )

    def test_builds_legal_combined_packages_for_multi_model_units(self):
        unit = self._unit(
            name="Shield Wall",
            points=120,
            min_models=5,
            max_models=10,
            default_models=5,
        )
        single_model = self._unit(name="Lone Hunter", points=95)

        packages = build_advisor_packages(self.faction.id, point_limit=750)

        combined = next(candidate for candidate in packages if candidate.package_id == f"u{unit.id}-base-c2")
        self.assertEqual(combined.combined_from_count, 2)
        self.assertEqual(combined.model_count, 5)
        self.assertEqual(combined.points, 240)
        self.assertFalse(combined.exceeds_group_cap)
        self.assertNotIn(f"u{single_model.id}-base-c2", [package.package_id for package in packages])

    def test_combined_packages_respect_copy_limit_and_force_org_cap(self):
        unit = self._unit(
            name="Expensive Guard",
            points=140,
            min_models=5,
            max_models=10,
            default_models=5,
        )

        packages = build_advisor_packages(self.faction.id, point_limit=750)

        self.assertNotIn(f"u{unit.id}-base-c2", [package.package_id for package in packages])
        self.assertNotIn(f"u{unit.id}-base-c3", [package.package_id for package in packages])

    def test_package_table_renders_package_ids_constraints_and_roles(self):
        self._unit(name="Rangers", points=100, special_rules={"Fast": True})

        table = build_package_table(build_advisor_packages(self.faction.id, point_limit=750))

        self.assertIn(
            "| Package | Unit | Pts | Models | Combined | Q | Def | T | AP | Act_inf | Burst_inf | Rng_inf | Mel_inf | Act_eli | Act_mon | W100 | Limited | Upgrades | Roles | Caster | Spell Roles | Aura | Embed | Legal |",
            table,
        )
        self.assertIn("u", table)
        self.assertIn("| 1.00 | 0.00 | 1.00 | 0.67 | 0.33 | 1.00 |", table)
        self.assertIn("mobility", table)
        self.assertIn("ok", table)

    def test_force_org_summary_uses_aof_hero_limit(self):
        self.assertIn("max heroes 2", force_org_summary(750))

    def test_packages_surface_caster_level_and_faction_spell_roles(self):
        caster = self._unit(name="Frog Mage", points=205, special_rules={"Caster": 3, "Hero": True})
        FactionSpell.objects.create(
            faction=self.faction,
            source_uid="spell-heal",
            name="Healing Swarm",
            threshold=2,
            effect='Pick one friendly unit within 12", which removes D3 wounds.',
        )
        FactionSpell.objects.create(
            faction=self.faction,
            source_uid="spell-bolt",
            name="Lightning Bolt",
            threshold=1,
            effect='Pick one enemy unit within 18", which takes 2 hits with AP(2).',
        )

        packages = build_advisor_packages(self.faction.id, point_limit=750)

        package = next(candidate for candidate in packages if candidate.unit_id == caster.id)
        self.assertEqual(package.caster_level, "3")
        self.assertIn("caster", package.role_tags)
        self.assertEqual(package.spell_role_tags, ("damage", "healing"))

    def test_caster_group_is_marked_without_numeric_level(self):
        unit = self._unit(name="Mage Council", points=170, special_rules={"Caster Group": True})

        package = next(
            candidate for candidate in build_advisor_packages(self.faction.id, point_limit=750)
            if candidate.unit_id == unit.id
        )

        self.assertEqual(package.caster_level, "group")
        self.assertIn("caster", package.role_tags)

    def test_caster_upgrade_surfaces_spell_support_roles(self):
        unit = self._unit(name="Apprentice Circle", points=120)
        section = UnitUpgradeSection.objects.create(
            unit=unit,
            section_uid="apprentice-circle-magic",
            label="Take Magic",
            variant="upgrade",
        )
        option = UnitUpgradeOption.objects.create(
            section=section,
            option_uid="caster-training",
            label="Caster Training",
            cost=25,
            gains=[{"content": [{"name": "Caster", "rating": 1, "type": "ArmyBookRule"}]}],
        )
        FactionSpell.objects.create(
            faction=self.faction,
            source_uid="spell-bolt",
            name="Lightning Bolt",
            threshold=1,
            effect='Pick one enemy unit within 18", which takes 2 hits with AP(2).',
        )

        package = next(
            candidate
            for candidate in build_advisor_packages(self.faction.id, point_limit=750)
            if candidate.selected_upgrade_ids == [option.id]
        )

        self.assertEqual(package.caster_level, "1")
        self.assertIn("caster", package.role_tags)
        self.assertEqual(package.spell_role_tags, ("damage",))

    def test_package_offense_uses_melee_charge_context(self):
        melee_weapon = Weapon.objects.create(
            name="Furious Claws",
            range=0,
            attacks=6,
            attacks_string="A6",
            ap=0,
            special_rules={"Furious": True, "Impact": 2},
        )
        ranged_weapon = Weapon.objects.create(
            name="Furious Bow",
            range=18,
            attacks=6,
            attacks_string="A6",
            ap=0,
            special_rules={"Furious": True, "Impact": 2},
        )
        melee_unit = self._unit(name="Furious Infantry", points=100, weapon=melee_weapon)
        ranged_unit = self._unit(name="Furious Archers", points=100, weapon=ranged_weapon)

        packages = {package.unit_id: package for package in build_advisor_packages(self.faction.id, point_limit=750)}

        self.assertEqual(packages[melee_unit.id].ev_infantry, 3.777778)
        self.assertEqual(packages[ranged_unit.id].ev_infantry, 2.0)

    def test_package_hybrid_upgrade_uses_best_activation_lane_not_sum(self):
        unit = self._unit(name="Quest Knights", points=100)
        bow = Weapon.objects.create(
            name="Short Bow",
            range=18,
            attacks=1,
            attacks_string="A1",
            ap=0,
        )
        section = UnitUpgradeSection.objects.create(
            unit=unit,
            section_uid="quest-knight-bow",
            label="Take Bows",
            variant="upgrade",
        )
        option = UnitUpgradeOption.objects.create(
            section=section,
            option_uid="short-bow",
            label="Short Bows",
            cost=15,
        )
        option.weapons.add(bow)

        package = next(
            candidate for candidate in build_advisor_packages(self.faction.id, point_limit=750)
            if candidate.selected_upgrade_ids == [option.id]
        )

        self.assertEqual(package.ranged_ev_infantry, 0.333333)
        self.assertEqual(package.melee_ev_infantry, 1.0)
        self.assertEqual(package.ev_infantry, 1.0)
        self.assertEqual(package.wounds_per_100pts_infantry, round((1.0 / 115) * 100, 6))
        self.assertIn("melee-threat", package.role_tags)
        self.assertIn("ranged-tax-risk", package.role_tags)

    def test_package_support_hybrid_marks_meaningful_ranged_flex(self):
        staff = Weapon.objects.create(
            name="Staff",
            range=0,
            attacks=1,
            attacks_string="A1",
            ap=0,
        )
        unit = self._unit(name="Battle Mage", points=100, special_rules={"Caster": 1}, weapon=staff)
        bolt = Weapon.objects.create(
            name="Magic Bolt",
            range=18,
            attacks=1,
            attacks_string="A1",
            ap=0,
        )
        section = UnitUpgradeSection.objects.create(
            unit=unit,
            section_uid="battle-mage-bolt",
            label="Take Bolt",
            variant="upgrade",
        )
        option = UnitUpgradeOption.objects.create(
            section=section,
            option_uid="magic-bolt",
            label="Magic Bolt",
            cost=5,
        )
        option.weapons.add(bolt)

        package = next(
            candidate for candidate in build_advisor_packages(self.faction.id, point_limit=750)
            if candidate.selected_upgrade_ids == [option.id]
        )

        self.assertEqual(package.ranged_ev_infantry, 0.333333)
        self.assertEqual(package.melee_ev_infantry, 0.333333)
        self.assertEqual(package.ev_infantry, 0.333333)
        self.assertIn("hybrid-flex", package.role_tags)
        self.assertIn("support", package.role_tags)

    def test_limited_weapon_package_uses_sustained_score_and_surfaces_burst(self):
        unit = self._unit(name="Bombardiers", points=100, weapon=Weapon.objects.create(
            name="Hand Weapon",
            range=0,
            attacks=1,
            attacks_string="A1",
            ap=0,
        ))
        bomb = Weapon.objects.create(
            name="Fire Bomb",
            range=12,
            attacks=4,
            attacks_string="A4",
            ap=0,
            special_rules={"Limited": True},
        )
        section = UnitUpgradeSection.objects.create(
            unit=unit,
            section_uid="bombardier-bombs",
            label="Take Bombs",
            variant="upgrade",
        )
        option = UnitUpgradeOption.objects.create(
            section=section,
            option_uid="fire-bomb",
            label="Fire Bomb",
            cost=10,
        )
        option.weapons.add(bomb)

        package = next(
            candidate for candidate in build_advisor_packages(self.faction.id, point_limit=750)
            if candidate.selected_upgrade_ids == [option.id]
        )

        self.assertEqual(package.ranged_ev_infantry, 0.333333)
        self.assertEqual(package.burst_ev_infantry, 1.333333)
        self.assertEqual(package.ev_infantry, 0.333333)
        self.assertEqual(package.wounds_per_100pts_infantry, round((0.333333 / 110) * 100, 6))
        self.assertEqual(package.limited_weapon_names, ("Fire Bomb",))
        table = build_package_table([package])
        self.assertIn("Burst_inf", table)
        self.assertIn("Fire Bomb", table)

    def test_package_offense_and_roles_value_disintegrate_against_elite_defense(self):
        hex_weapon = Weapon.objects.create(
            name="Hex Rifle",
            range=18,
            attacks=2,
            attacks_string="A2",
            ap=0,
            special_rules={"Disintegrate": True},
        )
        unit = self._unit(name="Hex Shooters", points=100, weapon=hex_weapon)

        package = next(
            candidate for candidate in build_advisor_packages(self.faction.id, point_limit=750)
            if candidate.unit_id == unit.id
        )

        self.assertEqual(package.ev_infantry, 0.666667)
        self.assertEqual(package.ev_elite, 0.666667)
        self.assertEqual(package.ev_monster, 0.5)
        self.assertIn("anti-tough", package.role_tags)

    def test_package_monster_ev_uses_regenerating_default_target(self):
        unit = self._unit(name="Monster Hunters", points=100)

        package = next(
            candidate for candidate in build_advisor_packages(self.faction.id, point_limit=750)
            if candidate.unit_id == unit.id
        )

        self.assertEqual(package.ev_monster, 0.333333)

    def test_package_regeneration_bypass_rules_keep_full_monster_ev(self):
        expected_ev = {
            "Bane": 0.166667,
            "Disintegrate": 0.5,
            "Unstoppable": 0.166667,
            "Rending": 0.388889,
        }
        for rule, expected in expected_ev.items():
            with self.subTest(rule=rule):
                weapon = Weapon.objects.create(
                    name=f"{rule} Spear",
                    range=0,
                    attacks=2,
                    attacks_string="A2",
                    ap=0,
                    special_rules={rule: True},
                )
                unit = self._unit(name=f"{rule} Hunters", points=100, weapon=weapon)

                package = next(
                    candidate for candidate in build_advisor_packages(self.faction.id, point_limit=750)
                    if candidate.unit_id == unit.id
                )

                self.assertEqual(package.ev_monster, expected)

    def test_package_offense_and_roles_value_melee_slayer_against_tough_targets(self):
        slayer_weapon = Weapon.objects.create(
            name="Monster Hunting Spear",
            range=0,
            attacks=2,
            attacks_string="A2",
            ap=0,
        )
        unit = self._unit(
            name="Quest Knights",
            points=100,
            special_rules={"Melee Slayer": True, "Fearless": True},
            weapon=slayer_weapon,
        )

        package = next(
            candidate for candidate in build_advisor_packages(self.faction.id, point_limit=750)
            if candidate.unit_id == unit.id
        )

        self.assertEqual(package.ev_infantry, 0.666667)
        self.assertEqual(package.ev_elite, 0.666667)
        self.assertEqual(package.ev_monster, 0.333333)
        self.assertIn("anti-tough", package.role_tags)
        self.assertIn("morale", package.role_tags)

    def test_package_offense_and_roles_value_ranged_slayer_against_tough_targets(self):
        slayer_weapon = Weapon.objects.create(
            name="Monster Hunter Bow",
            range=24,
            attacks=2,
            attacks_string="A2",
            ap=0,
        )
        unit = self._unit(
            name="Monster Hunters",
            points=100,
            special_rules={"Ranged Slayer": True},
            weapon=slayer_weapon,
        )

        package = next(
            candidate for candidate in build_advisor_packages(self.faction.id, point_limit=750)
            if candidate.unit_id == unit.id
        )

        self.assertEqual(package.ev_infantry, 0.666667)
        self.assertEqual(package.ev_elite, 0.666667)
        self.assertEqual(package.ev_monster, 0.333333)
        self.assertIn("anti-tough", package.role_tags)

    def test_prompt_packages_are_bounded_and_legal_first(self):
        self._unit(name="Giant", points=400, tough=12)
        for index in range(6):
            self._unit(name=f"Scout {index}", points=80 + index, special_rules={"Scout": True})

        packages = build_advisor_packages(self.faction.id, point_limit=750)
        visible = prompt_packages(packages, point_limit=750, max_rows=3)

        self.assertEqual(len(visible), 3)
        self.assertTrue(all(not package.exceeds_group_cap for package in visible))
        self.assertNotIn("Giant", [package.unit_name for package in visible])

    def test_packages_mark_aura_upgrades_and_embedding_roles(self):
        host = self._unit(
            name="Guardians",
            points=90,
            min_models=5,
            max_models=10,
            default_models=5,
        )
        hero = self._unit(
            name="Champion",
            points=75,
            special_rules={"Hero": True},
        )
        section = UnitUpgradeSection.objects.create(
            unit=hero,
            section_uid="champion-aura",
            label="Take Aura",
        )
        option = UnitUpgradeOption.objects.create(
            section=section,
            option_uid="swift-aura",
            label="Swift Aura",
            cost=10,
            gains=[{"content": [{"name": "Swift Aura", "type": "ArmyBookRule"}]}],
        )

        packages = build_advisor_packages(self.faction.id, point_limit=750)

        host_package = next(package for package in packages if package.unit_id == host.id)
        hero_package = next(package for package in packages if package.selected_upgrade_ids == [option.id])
        self.assertTrue(host_package.can_host_embedded_hero)
        self.assertFalse(host_package.can_embed_as_hero)
        self.assertTrue(hero_package.can_embed_as_hero)
        self.assertFalse(hero_package.can_host_embedded_hero)
        self.assertEqual(hero_package.aura_rules, ("Swift Aura",))

    def test_builds_relevant_multi_upgrade_combo_packages(self):
        unit = self._unit(name="Household Guard", points=100)
        bow = Weapon.objects.create(
            name="Long Bow",
            range=24,
            attacks=1,
            attacks_string="A1",
            ap=1,
        )
        weapon_section = UnitUpgradeSection.objects.create(
            unit=unit,
            section_uid="household-guard-weapons",
            label="Take Bows",
            variant="upgrade",
        )
        bows = UnitUpgradeOption.objects.create(
            section=weapon_section,
            option_uid="long-bows",
            label="Long Bows",
            cost=10,
        )
        bows.weapons.add(bow)
        banner_section = UnitUpgradeSection.objects.create(
            unit=unit,
            section_uid="household-guard-banner",
            label="Take Banner",
            variant="upgrade",
        )
        banner = UnitUpgradeOption.objects.create(
            section=banner_section,
            option_uid="war-banner",
            label="War Banner",
            cost=15,
            gains=[{"content": [{"name": "Fearless", "type": "ArmyBookRule"}]}],
        )

        packages = build_advisor_packages(self.faction.id, point_limit=750)
        selected_ids = [package.selected_upgrade_ids for package in packages]

        self.assertIn([bows.id], selected_ids)
        self.assertIn([banner.id], selected_ids)
        combo = next(
            package
            for package in packages
            if set(package.selected_upgrade_ids) == {bows.id, banner.id}
        )
        expected_suffix = "-".join(str(option_id) for option_id in combo.selected_upgrade_ids)
        self.assertEqual(combo.package_id, f"u{unit.id}-o{expected_suffix}")
        self.assertEqual(combo.points, 125)
        self.assertEqual(set(combo.upgrade_labels), {"Long Bows", "War Banner"})
        self.assertEqual(combo.max_ap, 2)
        self.assertIn("ranged", combo.role_tags)
        self.assertIn("morale", combo.role_tags)

    def test_multi_upgrade_combos_skip_irrelevant_and_same_section_options(self):
        unit = self._unit(name="City Militia", points=100)
        sword = Weapon.objects.create(
            name="Fine Sword",
            range=0,
            attacks=2,
            attacks_string="A2",
            ap=1,
        )
        weapon_section = UnitUpgradeSection.objects.create(
            unit=unit,
            section_uid="city-militia-weapons",
            label="Weapon Options",
            variant="upgrade",
        )
        sword_option = UnitUpgradeOption.objects.create(
            section=weapon_section,
            option_uid="fine-sword",
            label="Fine Sword",
            cost=10,
        )
        sword_option.weapons.add(sword)
        axe_option = UnitUpgradeOption.objects.create(
            section=weapon_section,
            option_uid="fine-axe",
            label="Fine Axe",
            cost=12,
        )
        armor_section = UnitUpgradeSection.objects.create(
            unit=unit,
            section_uid="city-militia-armor",
            label="Armor Options",
            variant="upgrade",
        )
        polish = UnitUpgradeOption.objects.create(
            section=armor_section,
            option_uid="polished-armor",
            label="Polished Armor",
            cost=5,
        )

        packages = build_advisor_packages(self.faction.id, point_limit=750)
        selected_ids = [package.selected_upgrade_ids for package in packages]

        self.assertNotIn([sword_option.id, axe_option.id], selected_ids)
        self.assertNotIn([sword_option.id, polish.id], selected_ids)

    def test_multi_upgrade_combo_includes_resolved_prerequisites(self):
        javelin = Weapon.objects.create(
            name="Javelin",
            range=12,
            attacks=1,
            attacks_string="A1",
            ap=0,
        )
        storm_trident = Weapon.objects.create(
            name="Storm Trident",
            range=18,
            attacks=1,
            attacks_string="A1",
            ap=2,
        )
        unit = self._unit(name="Winged Veterans", points=100)
        javelin_section = UnitUpgradeSection.objects.create(
            unit=unit,
            section_uid="winged-veteran-javelins",
            label="Take Javelins",
            variant="upgrade",
        )
        javelins = UnitUpgradeOption.objects.create(
            section=javelin_section,
            option_uid="javelins",
            label="Javelins",
            cost=10,
        )
        javelins.weapons.add(javelin)
        trident_section = UnitUpgradeSection.objects.create(
            unit=unit,
            section_uid="winged-veteran-trident",
            label="Replace one Javelin",
            variant="replace",
            targets=["Javelins"],
        )
        trident = UnitUpgradeOption.objects.create(
            section=trident_section,
            option_uid="storm-trident",
            label="Storm Trident",
            cost=15,
        )
        trident.weapons.add(storm_trident)
        banner_section = UnitUpgradeSection.objects.create(
            unit=unit,
            section_uid="winged-veteran-banner",
            label="Take Banner",
            variant="upgrade",
        )
        banner = UnitUpgradeOption.objects.create(
            section=banner_section,
            option_uid="swift-banner",
            label="Swift Banner",
            cost=20,
            gains=[{"content": [{"name": "Scout", "type": "ArmyBookRule"}]}],
        )

        packages = build_advisor_packages(self.faction.id, point_limit=750)

        combo = next(
            package
            for package in packages
            if package.selected_upgrade_ids == [javelins.id, trident.id, banner.id]
        )
        self.assertEqual(combo.points, 145)
        self.assertEqual(combo.upgrade_labels, ["Javelins", "Storm Trident", "Swift Banner"])
        self.assertIn("mobility", combo.role_tags)

    def _unit(
        self,
        *,
        name: str,
        points: int,
        tough: int = 1,
        min_models: int = 1,
        max_models: int | None = 1,
        default_models: int = 1,
        special_rules=None,
        weapon: Weapon | None = None,
    ) -> Unit:
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
        UnitWeaponSlot.objects.create(unit=unit, weapon=weapon or self.weapon, is_default=True)
        return unit
