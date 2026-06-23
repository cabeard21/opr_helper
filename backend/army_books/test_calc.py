import math

import pytest

from army_books.calc.engine import calculate_distribution, calculate_ev
from army_books.calc.primitives import expected_wounds, p_fail_defense, p_hit


def test_base_probability_primitives():
    assert p_hit(4) == pytest.approx(0.5)
    assert p_hit(6, modifiers=1) == pytest.approx(1 / 6)
    assert p_hit(2, modifiers=-1) == pytest.approx(5 / 6)
    assert p_fail_defense(4, ap=0) == pytest.approx(0.5)
    assert p_fail_defense(4, ap=2) == pytest.approx(5 / 6)
    assert expected_wounds(attacks=3, quality=4, defense=4, ap=0) == pytest.approx(0.75)


def test_base_distribution_is_exact_and_sums_to_one():
    distribution = calculate_distribution(
        attacks=3,
        quality=4,
        defense=4,
        ap=0,
        special_rules={},
    )

    assert [point["wounds"] for point in distribution] == [0, 1, 2, 3]
    assert sum(point["probability"] for point in distribution) == pytest.approx(1)
    assert distribution[0]["probability"] == pytest.approx((3 / 4) ** 3)
    assert calculate_ev(3, 4, 4, 0, {}) == pytest.approx(0.75)


def test_reliable_attacks_use_quality_two_plus():
    assert calculate_ev(6, 5, 4, 0, {"Reliable": True}) == pytest.approx(6 * (5 / 6) * 0.5)


def test_reliable_still_respects_hit_penalties():
    assert calculate_ev(
        6,
        5,
        4,
        0,
        {"Reliable": True},
        modifiers={"stealth": True},
    ) == pytest.approx(6 * (4 / 6) * 0.5)


def test_reliable_keeps_natural_six_extra_hit_semantics():
    ev = calculate_ev(6, 5, 4, 0, {"Reliable": True, "Surge": True})

    assert ev == pytest.approx(6 * ((4 / 6) * 0.5 + (1 / 6) * 2 * 0.5))


def test_ap_and_deadly_increase_expected_wounds():
    assert calculate_ev(3, 4, 4, 2, {}) == pytest.approx(3 * 0.5 * (5 / 6))
    assert calculate_ev(3, 4, 4, 0, {"Deadly": 3}) == pytest.approx(2.25)

    distribution = calculate_distribution(1, 4, 4, 0, {"Deadly": 3})
    assert [point["wounds"] for point in distribution] == [0, 1, 2, 3]
    assert distribution[3]["probability"] == pytest.approx(0.25)
    assert distribution[1]["probability"] == pytest.approx(0)
    assert distribution[2]["probability"] == pytest.approx(0)


def test_poison_auto_wounds_on_natural_six():
    ev = calculate_ev(6, 4, 2, 0, {"Poison": True})

    # Per attack: 1/6 auto-wounds, rolls 4-5 hit normally and fail DE2 on 1/6.
    assert ev == pytest.approx(6 * ((1 / 6) + (2 / 6) * (1 / 6)))


def test_rending_uses_ap_six_on_natural_six():
    ev = calculate_ev(6, 4, 2, 0, {"Rending": True})

    # Per attack: natural 6 gets AP(+4), rolls 4-5 hit at normal AP.
    assert ev == pytest.approx(6 * ((1 / 6) * (5 / 6) + (2 / 6) * (1 / 6)))


def test_regeneration_target_ignores_one_third_of_wounds():
    ev = calculate_ev(6, 4, 4, 0, {}, target_special_rules={"Regeneration": True})

    assert ev == pytest.approx(6 * 0.5 * 0.5 * (2 / 3))

    distribution = calculate_distribution(
        1,
        4,
        4,
        0,
        {},
        target_special_rules={"Regeneration": True},
    )
    assert distribution[1]["probability"] == pytest.approx(0.25 * (2 / 3), abs=1e-6)


def test_regeneration_ignores_deadly_wound_before_multiplication():
    distribution = calculate_distribution(
        1,
        4,
        4,
        0,
        {"Deadly": 3},
        target_special_rules={"Regeneration": True},
    )

    assert distribution[3]["probability"] == pytest.approx(0.25 * (2 / 3), abs=1e-6)
    assert distribution[1]["probability"] == pytest.approx(0)
    assert distribution[2]["probability"] == pytest.approx(0)


def test_bane_ignores_target_regeneration():
    ev = calculate_ev(
        6,
        4,
        4,
        0,
        {"Bane": True},
        target_special_rules={"Regeneration": True},
    )

    assert ev == pytest.approx(6 * 0.5 * 0.5)


def test_disintegrate_ignores_target_regeneration_and_adds_ap_against_elite_defense():
    ev = calculate_ev(
        6,
        4,
        3,
        0,
        {"Disintegrate": True},
        target_special_rules={"Regeneration": True},
    )

    assert ev == pytest.approx(6 * 0.5 * (4 / 6))


def test_disintegrate_ap_bonus_applies_only_against_defense_two_or_three():
    assert calculate_ev(6, 4, 2, 0, {"Disintegrate": True}) == pytest.approx(6 * 0.5 * 0.5)
    assert calculate_ev(6, 4, 3, 0, {"Disintegrate": True}) == pytest.approx(6 * 0.5 * (4 / 6))
    assert calculate_ev(6, 4, 4, 0, {"Disintegrate": True}) == pytest.approx(6 * 0.5 * 0.5)


def test_disintegrate_composes_with_rending_without_double_counting_natural_six_ap():
    ev = calculate_ev(6, 4, 3, 0, {"Disintegrate": True, "Rending": True})

    expected_per_attack = (1 / 6) + (2 / 6) * (4 / 6)
    assert ev == pytest.approx(6 * expected_per_attack)


def test_disintegrate_ap_bonus_applies_to_blast():
    ev = calculate_ev(
        6,
        4,
        3,
        0,
        {"Blast": 3, "Disintegrate": True},
        combat_context={"target_unit_size": 3},
    )

    assert ev == pytest.approx(6 * 0.5 * 3 * (4 / 6))


def test_rending_ignores_regeneration_on_all_hits_and_adds_ap_on_natural_six():
    ev = calculate_ev(
        6,
        4,
        2,
        0,
        {"Rending": True},
        target_special_rules={"Regeneration": True},
    )

    expected_per_attack = (1 / 6) * (5 / 6) + ((2 / 6) * (1 / 6))
    assert ev == pytest.approx(6 * expected_per_attack)


def test_blast_multiplies_successful_hits_up_to_target_unit_size():
    assert calculate_ev(
        3,
        4,
        4,
        0,
        {"Blast": 2},
        combat_context={"target_unit_size": 10},
    ) == pytest.approx(3 * 0.5 * 2 * 0.5)
    assert calculate_ev(
        3,
        4,
        4,
        0,
        {"Blast": 3},
        combat_context={"target_unit_size": 2},
    ) == pytest.approx(3 * 0.5 * 2 * 0.5)
    assert calculate_ev(3, 4, 4, 0, {"Blast": 3}) == pytest.approx(3 * 0.5 * 0.5)


def test_blast_uses_hit_rolls_and_composes_with_reliable_and_rending():
    assert calculate_ev(
        3,
        4,
        4,
        0,
        {"Blast": 2},
        modifiers={"stealth": True},
        combat_context={"target_unit_size": 10},
    ) == pytest.approx(3 * (2 / 6) * 2 * 0.5)
    assert calculate_ev(
        3,
        5,
        4,
        0,
        {"Blast": 2, "Reliable": True},
        combat_context={"target_unit_size": 10},
    ) == pytest.approx(3 * (5 / 6) * 2 * 0.5)
    assert calculate_ev(
        6,
        4,
        2,
        0,
        {"Blast": 2, "Rending": True},
        combat_context={"target_unit_size": 10},
    ) == pytest.approx(6 * ((1 / 6) * 2 * (5 / 6) + (2 / 6) * 2 * (1 / 6)))


def test_blast_distribution_expands_wound_outcomes_and_sums_to_one():
    distribution = calculate_distribution(
        1,
        4,
        4,
        0,
        {"Blast": 3},
        combat_context={"target_unit_size": 10},
    )

    assert [point["wounds"] for point in distribution] == [0, 1, 2, 3]
    assert sum(point["probability"] for point in distribution) == pytest.approx(1)
    assert distribution[3]["probability"] == pytest.approx(0.5 * (0.5 ** 3))


def test_furious_requires_charge():
    assert calculate_ev(6, 4, 4, 0, {"Furious": True}) == pytest.approx(6 * 0.5 * 0.5)
    assert calculate_ev(
        6,
        4,
        4,
        0,
        {"Furious": True},
        combat_context={"charging": True},
    ) == pytest.approx(6 * ((2 / 6) * 0.5 + (1 / 6) * 2 * 0.5))


def test_surge_and_sergeant_add_extra_hits_on_natural_sixes():
    expected = 6 * ((2 / 6) * 0.5 + (1 / 6) * 2 * 0.5)

    assert calculate_ev(6, 4, 4, 0, {"Surge": True}) == pytest.approx(expected)
    assert calculate_ev(6, 4, 4, 0, {"Sergeant": True}) == pytest.approx(expected)


def test_relentless_adds_extra_hits_when_shooting_over_nine_inches():
    expected = 6 * ((2 / 6) * 0.5 + (1 / 6) * 2 * 0.5)

    assert calculate_ev(6, 4, 4, 0, {"Relentless": True}) == pytest.approx(6 * 0.5 * 0.5)
    assert calculate_ev(
        6,
        4,
        4,
        0,
        {"Relentless": True},
        combat_context={"target_over_9": True, "is_melee": False},
    ) == pytest.approx(expected)
    assert calculate_ev(
        6,
        4,
        4,
        0,
        {"Relentless": True},
        combat_context={"target_over_9": True, "is_melee": True},
    ) == pytest.approx(6 * 0.5 * 0.5)


def test_extra_hits_do_not_inherit_natural_six_rending_ap():
    ev = calculate_ev(6, 4, 2, 0, {"Surge": True, "Rending": True})

    expected_per_attack = (2 / 6) * (1 / 6) + (1 / 6) * ((5 / 6) + (1 / 6))
    assert ev == pytest.approx(6 * expected_per_attack)


def test_thrust_applies_only_on_charging_melee():
    baseline = calculate_ev(6, 4, 4, 0, {"Thrust": True})
    ranged_charge = calculate_ev(
        6,
        4,
        4,
        0,
        {"Thrust": True},
        combat_context={"charging": True, "is_melee": False},
    )
    melee_charge = calculate_ev(
        6,
        4,
        4,
        0,
        {"Thrust": True},
        combat_context={"charging": True, "is_melee": True},
    )

    assert baseline == pytest.approx(6 * 0.5 * 0.5)
    assert ranged_charge == pytest.approx(baseline)
    assert melee_charge == pytest.approx(6 * (4 / 6) * (4 / 6))


def test_melee_slayer_adds_ap_against_tough_targets_only_on_charge():
    baseline = calculate_ev(
        6,
        4,
        4,
        0,
        {"Melee Slayer": True},
        combat_context={"charging": True, "is_melee": True, "target_tough": 1},
    )
    not_charging = calculate_ev(
        6,
        4,
        4,
        0,
        {"Melee Slayer": True},
        combat_context={"charging": False, "is_melee": True, "target_tough": 3},
    )
    charging_tough_target = calculate_ev(
        6,
        4,
        4,
        0,
        {"Melee Slayer": True},
        combat_context={"charging": True, "is_melee": True, "target_tough": 3},
    )

    assert baseline == pytest.approx(6 * 0.5 * 0.5)
    assert not_charging == pytest.approx(baseline)
    assert charging_tough_target == pytest.approx(6 * 0.5 * (5 / 6))


def test_ranged_slayer_adds_ap_against_tough_targets_only_when_shooting():
    baseline = calculate_ev(
        6,
        4,
        4,
        0,
        {"Ranged Slayer": True},
        combat_context={"is_melee": False, "target_tough": 1},
    )
    melee_attack = calculate_ev(
        6,
        4,
        4,
        0,
        {"Ranged Slayer": True},
        combat_context={"charging": True, "is_melee": True, "target_tough": 3},
    )
    shooting_tough_target = calculate_ev(
        6,
        4,
        4,
        0,
        {"Ranged Slayer": True},
        combat_context={"is_melee": False, "target_tough": 3},
    )

    assert baseline == pytest.approx(6 * 0.5 * 0.5)
    assert melee_attack == pytest.approx(baseline)
    assert shooting_tough_target == pytest.approx(6 * 0.5 * (5 / 6))


def test_impact_adds_charge_hits_without_weapon_specials():
    ev = calculate_ev(
        0,
        4,
        4,
        0,
        {"Impact": 2, "Deadly": 3},
        combat_context={"charging": True, "attacking_models": 3},
    )

    assert ev == pytest.approx(6 * (5 / 6) * 0.5)
    assert calculate_ev(0, 4, 4, 0, {"Impact": 2}) == pytest.approx(0)


def test_unstoppable_ignores_regeneration_and_negative_modifiers():
    ev = calculate_ev(
        6,
        4,
        4,
        0,
        {"Unstoppable": True},
        modifiers={"stealth": True, "indirect": True},
        target_special_rules={"Regeneration": True},
    )

    assert ev == pytest.approx(6 * 0.5 * 0.5)


def test_stealth_and_indirect_apply_hit_penalties():
    assert calculate_ev(6, 4, 4, 0, {}, modifiers={"stealth": True}) == pytest.approx(6 * (2 / 6) * 0.5)
    assert calculate_ev(6, 4, 4, 0, {}, modifiers={"indirect": True}) == pytest.approx(6 * (2 / 6) * 0.5)
    assert calculate_ev(
        6,
        4,
        4,
        0,
        {},
        modifiers={"stealth": True, "indirect": True},
    ) == pytest.approx(6 * (1 / 6) * 0.5)


def test_distribution_supports_kill_probability_thresholds():
    distribution = calculate_distribution(3, 4, 4, 0, {})
    p_at_least_one = sum(point["probability"] for point in distribution if point["wounds"] >= 1)

    assert math.isclose(p_at_least_one, 1 - ((3 / 4) ** 3))
