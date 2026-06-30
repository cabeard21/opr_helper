import pytest

from army_books.parsers import (
    parse_attacks_value,
    parse_spell,
    parse_special_rules,
    parse_stat_target,
    parse_unit,
    parse_weapon,
)


def test_parse_stat_target_accepts_plus_strings_and_numbers():
    assert parse_stat_target("4+") == 4
    assert parse_stat_target(3) == 3
    assert parse_stat_target(" 2+ ") == 2


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("A2", 2.0),
        ("2", 2.0),
        (3, 3.0),
        ("2d6", 7.0),
        ("d6", 3.5),
    ],
)
def test_parse_attacks_value_keeps_expected_value_for_fixed_and_dice_attacks(
    raw_value,
    expected,
):
    assert parse_attacks_value(raw_value) == expected


def test_parse_special_rules_normalizes_names_and_values():
    assert parse_special_rules(["Poison", "Deadly(3)", {"name": "Rending"}]) == {
        "Poison": True,
        "Deadly": 3,
        "Rending": True,
    }


def test_parse_special_rules_uses_army_forge_rating_values():
    raw_rules = [
        {"id": "rule-furious", "name": "Furious", "label": "Furious"},
        {"id": "rule-tough", "name": "Tough", "rating": 6, "label": "Tough(6)"},
    ]

    assert parse_special_rules(raw_rules) == {
        "Furious": True,
        "Tough": 6,
    }


def test_parse_unit_maps_opr_fixture_to_model_kwargs():
    raw_unit = {
        "id": "unit-paladins",
        "name": "Paladins",
        "quality": "3+",
        "defense": "4+",
        "tough": "3",
        "cost": 180,
        "rules": ["Fearless", "Regeneration(5)"],
    }

    assert parse_unit(raw_unit) == {
        "source_uid": "unit-paladins",
        "name": "Paladins",
        "quality": 3,
        "defense": 4,
        "tough": 3,
        "points": 180,
        "min_models": 1,
        "max_models": None,
        "default_models": 1,
        "special_rules": {"Fearless": True, "Regeneration": 5},
    }


def test_parse_unit_maps_roster_model_count_bounds():
    raw_unit = {
        "id": "unit-guard",
        "name": "Guard",
        "quality": "4+",
        "defense": "5+",
        "cost": 90,
        "size": 10,
        "minSize": 5,
        "maxSize": 20,
        "rules": [],
    }

    parsed = parse_unit(raw_unit)

    assert parsed["default_models"] == 10
    assert parsed["min_models"] == 5
    assert parsed["max_models"] == 20


def test_parse_unit_maps_current_army_forge_rule_objects_to_model_kwargs():
    raw_unit = {
        "id": "unit-brute-boss",
        "name": "Kemba Brute Boss",
        "quality": 3,
        "defense": 3,
        "cost": 130,
        "rules": [
            {"id": "rule-furious", "name": "Furious", "label": "Furious"},
            {"id": "rule-tough", "name": "Tough", "rating": 6, "label": "Tough(6)"},
        ],
    }

    assert parse_unit(raw_unit) == {
        "source_uid": "unit-brute-boss",
        "name": "Kemba Brute Boss",
        "quality": 3,
        "defense": 3,
        "tough": 6,
        "points": 130,
        "min_models": 1,
        "max_models": None,
        "default_models": 1,
        "special_rules": {"Furious": True, "Tough": 6},
    }


def test_parse_weapon_maps_opr_fixture_to_model_kwargs():
    raw_weapon = {
        "id": "weapon-great",
        "name": "Great Weapon",
        "range": "0",
        "attacks": "A2",
        "ap": "AP(2)",
        "rules": ["Deadly(3)"],
    }

    assert parse_weapon(raw_weapon) == {
        "source_uid": "weapon-great",
        "name": "Great Weapon",
        "range": 0,
        "attacks": 2.0,
        "attacks_string": "A2",
        "ap": 2,
        "special_rules": {"Deadly": 3},
    }


def test_parse_weapon_maps_current_army_forge_weapon_shape():
    raw_weapon = {
        "id": "weapon-heavy-hand",
        "name": "Heavy Hand Weapon",
        "range": 0,
        "attacks": 6,
        "specialRules": [
            {
                "id": "rule-ap",
                "name": "AP",
                "rating": 2,
                "label": "AP(2)",
            },
            {
                "id": "rule-rending",
                "name": "Rending",
                "label": "Rending",
            },
        ],
    }

    assert parse_weapon(raw_weapon) == {
        "source_uid": "weapon-heavy-hand",
        "name": "Heavy Hand Weapon",
        "range": 0,
        "attacks": 6.0,
        "attacks_string": "A6",
        "ap": 2,
        "special_rules": {"Rending": True},
    }


def test_parse_weapon_keeps_limited_special_rule():
    raw_weapon = {
        "id": "weapon-grenade",
        "name": "Grenade",
        "range": 12,
        "attacks": 4,
        "specialRules": [
            {"name": "AP", "rating": 1, "label": "AP(1)"},
            {"name": "Limited", "label": "Limited"},
        ],
    }

    parsed = parse_weapon(raw_weapon)

    assert parsed["ap"] == 1
    assert parsed["special_rules"] == {"Limited": True}


def test_parse_spell_maps_army_forge_spell_shape():
    raw_spell = {
        "id": "spell-poison-mist",
        "name": "Poison Mist",
        "type": 2,
        "effect": 'Pick one enemy unit within 18", which friendly units gets Shred.',
        "threshold": 1,
        "spellbookId": "book-saurians",
        "generation": {"effect": {"id": "generated-effect"}},
    }

    assert parse_spell(raw_spell) == {
        "source_uid": "spell-poison-mist",
        "name": "Poison Mist",
        "threshold": 1,
        "effect": 'Pick one enemy unit within 18", which friendly units gets Shred.',
        "spellbook_id": "book-saurians",
        "spell_type": 2,
        "raw_data": raw_spell,
    }
