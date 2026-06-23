from django.test import TestCase

from advisor.unit_scorer import score_faction_units
from army_books.models import Faction, Unit, UnitWeaponSlot, Weapon


class UnitScorerTests(TestCase):
    def setUp(self):
        self.faction = Faction.objects.create(name="Kingdom of Angels", version="3.5.3")
        self.paladins = Unit.objects.create(
            faction=self.faction,
            name="Paladins",
            quality=3,
            defense=4,
            tough=3,
            points=180,
            default_models=1,
            special_rules={"Fearless": True, "Scout": True},
        )
        self.weapon = Weapon.objects.create(
            name="Great Weapon",
            range=0,
            attacks=2,
            attacks_string="A2",
            ap=2,
            special_rules={"Deadly": 3},
        )
        self.slot = UnitWeaponSlot.objects.create(
            unit=self.paladins,
            weapon=self.weapon,
            is_default=True,
        )

    def test_scores_known_offensive_profile_against_default_targets(self):
        profiles = score_faction_units(self.faction.id)

        paladins = next(profile for profile in profiles if profile.unit_id == self.paladins.id)
        self.assertEqual(paladins.default_weapon_slot_id, self.slot.id)
        self.assertEqual(paladins.max_ap, 2)
        self.assertEqual(paladins.ev_infantry, 4.0)
        self.assertEqual(paladins.wounds_per_100pts_infantry, 2.222222)
        self.assertEqual(paladins.ev_elite, 2.666667)
        self.assertGreater(paladins.p_kill_infantry, 0)

    def test_units_without_weapon_slots_return_zero_offense(self):
        healer = Unit.objects.create(
            faction=self.faction,
            name="Healer",
            quality=4,
            defense=5,
            tough=1,
            points=55,
        )

        profiles = score_faction_units(self.faction.id)

        profile = next(profile for profile in profiles if profile.unit_id == healer.id)
        self.assertIsNone(profile.default_weapon_slot_id)
        self.assertEqual(profile.ev_infantry, 0)
        self.assertEqual(profile.ev_elite, 0)
        self.assertEqual(profile.ev_monster, 0)
        self.assertFalse(profile.is_ranged)

    def test_defensive_and_keyword_metadata_is_extracted(self):
        self.paladins.special_rules = {
            "Scout": True,
            "Fast": True,
            "Flying": True,
            "Fearless": True,
            "Stealth": True,
            "Regeneration": True,
        }
        self.paladins.save()

        profile = score_faction_units(self.faction.id)[0]

        self.assertEqual(profile.effective_health, 3)
        self.assertEqual(profile.resilience_score, 1.5)
        self.assertTrue(profile.has_scout)
        self.assertTrue(profile.has_fast)
        self.assertTrue(profile.has_flying)
        self.assertTrue(profile.has_fearless)
        self.assertTrue(profile.has_stealth)
        self.assertTrue(profile.has_regeneration)

    def test_returns_one_profile_per_unit_for_faction(self):
        Unit.objects.create(
            faction=self.faction,
            name="Guardians",
            quality=4,
            defense=5,
            tough=1,
            points=90,
        )

        profiles = score_faction_units(self.faction.id)

        self.assertEqual({profile.name for profile in profiles}, {"Guardians", "Paladins"})

    def test_scores_charge_context_for_melee_default_weapons_only(self):
        melee_weapon = Weapon.objects.create(
            name="Furious Claws",
            range=0,
            attacks=6,
            attacks_string="A6",
            ap=0,
            special_rules={"Furious": True},
        )
        ranged_weapon = Weapon.objects.create(
            name="Furious Bow",
            range=18,
            attacks=6,
            attacks_string="A6",
            ap=0,
            special_rules={"Furious": True},
        )
        melee_unit = Unit.objects.create(
            faction=self.faction,
            name="Furious Infantry",
            quality=4,
            defense=5,
            tough=1,
            points=100,
            default_models=1,
        )
        ranged_unit = Unit.objects.create(
            faction=self.faction,
            name="Furious Archers",
            quality=4,
            defense=5,
            tough=1,
            points=100,
            default_models=1,
        )
        UnitWeaponSlot.objects.create(unit=melee_unit, weapon=melee_weapon, is_default=True)
        UnitWeaponSlot.objects.create(unit=ranged_unit, weapon=ranged_weapon, is_default=True)

        profiles = {profile.name: profile for profile in score_faction_units(self.faction.id)}

        self.assertEqual(profiles["Furious Infantry"].ev_infantry, 2.666667)
        self.assertEqual(profiles["Furious Archers"].ev_infantry, 2.0)

    def test_scores_impact_and_thrust_with_melee_charge_context(self):
        self.weapon.special_rules = {"Impact": 2, "Thrust": True}
        self.weapon.ap = 0
        self.weapon.save()
        self.paladins.default_models = 3
        self.paladins.quality = 4
        self.paladins.save()

        profile = next(profile for profile in score_faction_units(self.faction.id) if profile.unit_id == self.paladins.id)

        self.assertEqual(profile.ev_infantry, 6.666667)

    def test_scores_disintegrate_against_elite_defense(self):
        self.weapon.special_rules = {"Disintegrate": True}
        self.weapon.ap = 0
        self.weapon.save()
        self.paladins.quality = 4
        self.paladins.save()

        profile = next(profile for profile in score_faction_units(self.faction.id) if profile.unit_id == self.paladins.id)

        self.assertEqual(profile.ev_infantry, 0.666667)
        self.assertEqual(profile.ev_elite, 0.666667)
        self.assertEqual(profile.ev_monster, 0.5)
