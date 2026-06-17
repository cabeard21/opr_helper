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

    # Per attack: natural 6 wounds against AP6, rolls 4-5 hit at normal AP.
    assert ev == pytest.approx(6 * ((1 / 6) * 1 + (2 / 6) * (1 / 6)))


def test_blast_skips_hit_rolls_and_furious_adds_expected_attacks():
    assert calculate_ev(3, 4, 4, 0, {"Blast": 2}) == pytest.approx(2 * 0.5)
    assert calculate_ev(6, 4, 4, 0, {"Furious": True}) == pytest.approx(7 * 0.5 * 0.5)


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
