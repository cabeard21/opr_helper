from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, TestCase, override_settings

from advisor.llm_service import (
    AdvisorLLMError,
    ListSuggestion,
    OpenAIAdvisorProvider,
    PackageListSuggestion,
    PackageSuggestedUnit,
    SuggestedUnit,
    package_suggestion_to_list_suggestion,
    get_advisor_provider,
    suggest_list,
)
from army_books.models import Faction, FactionSpell, Unit, UnitWeaponSlot, Weapon


class OpenAIAdvisorProviderTests(SimpleTestCase):
    @override_settings(OPENAI_MODEL="gpt-5.5")
    def test_calls_openai_responses_parse_with_configured_model(self):
        suggestion = ListSuggestion(
            units=[SuggestedUnit(unit_id=1, unit_name="Paladins", model_count=1, justification="Durable hammer.")],
            total_points=180,
            archetype="Offensive Elite",
            playstyle="Shove It In",
            activation_count=1,
            strategy_summary="Advance quickly and force favorable fights.",
            warnings=[],
        )
        client = Mock()
        client.responses.parse.return_value = SimpleNamespace(output_parsed=suggestion)
        provider = OpenAIAdvisorProvider(client=client)

        result = provider.suggest(
            system_prompt="Use doctrine.",
            user_context="Faction context.",
        )

        self.assertEqual(result, suggestion)
        client.responses.parse.assert_called_once()
        call_kwargs = client.responses.parse.call_args.kwargs
        self.assertEqual(call_kwargs["model"], "gpt-5.5")
        self.assertEqual(call_kwargs["text_format"], ListSuggestion)
        self.assertEqual(call_kwargs["instructions"], "Use doctrine.")
        self.assertEqual(call_kwargs["input"], "Faction context.")
        self.assertEqual(call_kwargs["max_output_tokens"], 8192)

    @override_settings(OPENAI_MODEL="gpt-5.5")
    def test_can_request_package_selection_schema(self):
        suggestion = PackageListSuggestion(
            units=[PackageSuggestedUnit(package_id="u1-base", justification="Durable scorer.")],
            total_points=180,
            archetype="Offensive Elite",
            playstyle="Shove It In",
            activation_count=1,
            strategy_summary="Advance quickly and force favorable fights.",
            warnings=[],
        )
        client = Mock()
        client.responses.parse.return_value = SimpleNamespace(output_parsed=suggestion)
        provider = OpenAIAdvisorProvider(client=client)

        result = provider.suggest(
            system_prompt="Use package ids.",
            user_context="Faction context.",
            text_format=PackageListSuggestion,
        )

        self.assertEqual(result, suggestion)
        self.assertEqual(client.responses.parse.call_args.kwargs["text_format"], PackageListSuggestion)

    def test_package_suggestion_converts_to_list_suggestion(self):
        package_suggestion = PackageListSuggestion(
            units=[
                PackageSuggestedUnit(package_id="u1-o10", justification="Adds AP to the main hammer."),
                PackageSuggestedUnit(
                    package_id="u2-base",
                    join_to_unit_index=0,
                    justification="Embeds aura support into the hammer.",
                ),
                PackageSuggestedUnit(package_id="missing", justification="Invalid package."),
            ],
            total_points=200,
            archetype="Offensive Elite",
            playstyle="Shove It In",
            activation_count=2,
            strategy_summary="Advance quickly and force favorable fights.",
            warnings=[],
        )

        result = package_suggestion_to_list_suggestion(
            package_suggestion,
            {
                "u1-o10": {
                    "unit_id": 1,
                    "unit_name": "Paladins",
                    "model_count": 1,
                    "combined_from_count": 1,
                    "selected_upgrade_ids": [10],
                    "selected_upgrade_selections": [{"option": 10, "quantity": 3}],
                },
                "u2-base": {
                    "unit_id": 2,
                    "unit_name": "Champion",
                    "model_count": 1,
                    "combined_from_count": 1,
                    "selected_upgrade_ids": [],
                    "selected_upgrade_selections": [],
                },
            },
        )

        self.assertEqual(result.units[0].unit_id, 1)
        self.assertEqual(result.units[0].selected_upgrade_ids, [10])
        self.assertEqual(
            [selection.model_dump() for selection in result.units[0].selected_upgrade_selections],
            [{"option": 10, "quantity": 3}],
        )
        self.assertEqual(result.units[0].combined_from_count, 1)
        self.assertIsNone(result.units[0].parent_unit_index)
        self.assertEqual(result.units[1].unit_id, 2)
        self.assertEqual(result.units[1].parent_unit_index, 0)
        self.assertIn("Unknown package id missing was skipped.", result.warnings)

    def test_package_suggestion_preserves_combined_count(self):
        package_suggestion = PackageListSuggestion(
            units=[PackageSuggestedUnit(package_id="u1-base-c2", justification="Forms a durable combined block.")],
            total_points=240,
            archetype="Board Control",
            playstyle="Hold the center.",
            activation_count=1,
            strategy_summary="Use one large block to anchor objectives.",
            warnings=[],
        )

        result = package_suggestion_to_list_suggestion(
            package_suggestion,
            {
                "u1-base-c2": {
                    "unit_id": 1,
                    "unit_name": "Shield Wall",
                    "model_count": 5,
                    "combined_from_count": 2,
                    "selected_upgrade_ids": [],
                },
            },
        )

        self.assertEqual(result.units[0].combined_from_count, 2)

    def test_retries_once_when_response_has_no_parsed_output(self):
        suggestion = PackageListSuggestion(
            units=[PackageSuggestedUnit(package_id="u1-base", justification="Durable scorer.")],
            total_points=180,
            archetype="Offensive Elite",
            playstyle="Shove It In",
            activation_count=1,
            strategy_summary="Advance quickly and force favorable fights.",
            warnings=[],
        )
        client = Mock()
        client.responses.parse.side_effect = [
            SimpleNamespace(output_parsed=None),
            SimpleNamespace(output_parsed=suggestion),
        ]
        provider = OpenAIAdvisorProvider(client=client)

        result = provider.suggest(
            system_prompt="Use package ids.",
            user_context="Faction context.",
            text_format=PackageListSuggestion,
        )

        self.assertEqual(result, suggestion)
        self.assertEqual(client.responses.parse.call_count, 2)
        retry_kwargs = client.responses.parse.call_args_list[1].kwargs
        self.assertEqual(retry_kwargs["max_output_tokens"], 8192)
        self.assertIn("Return complete valid JSON", retry_kwargs["instructions"])

    def test_raises_advisor_error_when_retry_response_has_no_parsed_output(self):
        client = Mock()
        client.responses.parse.side_effect = [
            SimpleNamespace(output_parsed=None),
            SimpleNamespace(output_parsed=None),
        ]
        provider = OpenAIAdvisorProvider(client=client)

        with self.assertRaisesMessage(AdvisorLLMError, "structured suggestion"):
            provider.suggest(system_prompt="Use doctrine.", user_context="Faction context.")

    def test_raises_advisor_error_when_structured_json_parse_fails(self):
        client = Mock()
        client.responses.parse.side_effect = lambda **_kwargs: PackageListSuggestion.model_validate_json(
            '{"units":[{"package_id":"u1-base","justification":"truncated'
        )
        provider = OpenAIAdvisorProvider(client=client)

        with self.assertRaisesMessage(AdvisorLLMError, "structured suggestion"):
            provider.suggest(
                system_prompt="Use package ids.",
                user_context="Faction context.",
                text_format=PackageListSuggestion,
            )

    @override_settings(OPENAI_MODEL="gpt-5.5")
    def test_retries_once_when_structured_json_parse_fails(self):
        suggestion = PackageListSuggestion(
            units=[PackageSuggestedUnit(package_id="u1-base", justification="Durable scorer.")],
            total_points=180,
            archetype="Offensive Elite",
            playstyle="Shove It In",
            activation_count=1,
            strategy_summary="Advance quickly and force favorable fights.",
            warnings=[],
        )
        client = Mock()
        try:
            PackageListSuggestion.model_validate_json('{"units":[{"package_id":"u1-base","justification":"truncated')
        except Exception as exc:
            parse_error = exc
        client.responses.parse.side_effect = [
            parse_error,
            SimpleNamespace(output_parsed=suggestion),
        ]
        provider = OpenAIAdvisorProvider(client=client)

        result = provider.suggest(
            system_prompt="Use package ids.",
            user_context="Faction context.",
            text_format=PackageListSuggestion,
        )

        self.assertEqual(result, suggestion)
        self.assertEqual(client.responses.parse.call_count, 2)
        retry_kwargs = client.responses.parse.call_args_list[1].kwargs
        self.assertEqual(retry_kwargs["max_output_tokens"], 8192)
        self.assertIn("Return complete valid JSON", retry_kwargs["instructions"])

    @override_settings(LLM_PROVIDER="openai")
    @patch("advisor.llm_service.OpenAIAdvisorProvider")
    def test_provider_factory_returns_configured_provider(self, provider_cls):
        provider = get_advisor_provider()

        self.assertEqual(provider, provider_cls.return_value)


class SuggestListContextTests(TestCase):
    @patch("advisor.llm_service.get_advisor_provider")
    @override_settings(ADVISOR_PACKAGE_TABLE_MAX_ROWS=60)
    def test_suggest_list_includes_synced_spell_context(self, provider_factory):
        faction = Faction.objects.create(name="Saurians", version="3.5.3")
        caster = Unit.objects.create(
            faction=faction,
            name="Frog Mage",
            quality=4,
            defense=5,
            tough=3,
            points=205,
            special_rules={"Caster": 3, "Hero": True},
        )
        weapon = Weapon.objects.create(name="Staff", range=0, attacks=1, attacks_string="A1")
        UnitWeaponSlot.objects.create(unit=caster, weapon=weapon, is_default=True)
        FactionSpell.objects.create(
            faction=faction,
            source_uid="spell-healing-swarm",
            name="Healing Swarm",
            threshold=2,
            effect='Pick one friendly unit within 12", which removes D3 wounds.',
        )
        provider = provider_factory.return_value
        provider.suggest.return_value = PackageListSuggestion(
            units=[],
            total_points=0,
            archetype="Magic Support",
            playstyle="Control objectives with spells.",
            activation_count=0,
            strategy_summary="Use spell support to preserve the army.",
            warnings=[],
        )

        suggest_list(faction.id, 750, "Build around useful magic.")

        user_context = provider.suggest.call_args.kwargs["user_context"]
        self.assertIn("Faction spells:", user_context)
        self.assertIn("Healing Swarm", user_context)
        self.assertIn("healing", user_context)
        self.assertIn("| Frog Mage |", user_context)
        self.assertIn("| 3 | healing |", user_context)

    @override_settings(ADVISOR_PACKAGE_TABLE_MAX_ROWS=1)
    @patch("advisor.llm_service.get_advisor_provider")
    def test_suggest_list_uses_only_visible_prompt_packages_for_lookup(self, provider_factory):
        faction = Faction.objects.create(name="Beastmen", version="3.5.3")
        legal = Unit.objects.create(
            faction=faction,
            name="Raiders",
            quality=4,
            defense=5,
            tough=1,
            points=90,
            min_models=1,
            max_models=1,
            default_models=1,
        )
        over_cap = Unit.objects.create(
            faction=faction,
            name="Mountain Giant",
            quality=4,
            defense=2,
            tough=12,
            points=400,
            min_models=1,
            max_models=1,
            default_models=1,
        )
        weapon = Weapon.objects.create(name="Club", range=0, attacks=2, attacks_string="A2")
        UnitWeaponSlot.objects.create(unit=legal, weapon=weapon, is_default=True)
        UnitWeaponSlot.objects.create(unit=over_cap, weapon=weapon, is_default=True)
        provider = provider_factory.return_value
        provider.suggest.return_value = PackageListSuggestion(
            units=[PackageSuggestedUnit(package_id=f"u{legal.id}-base", justification="Legal scorer.")],
            total_points=90,
            archetype="Board Control",
            playstyle="Objective play",
            activation_count=1,
            strategy_summary="Use the legal scoring unit.",
            warnings=[],
        )

        result = suggest_list(faction.id, 750, "Build a legal list.")

        user_context = provider.suggest.call_args.kwargs["user_context"]
        self.assertIn(f"u{legal.id}-base", user_context)
        self.assertNotIn(f"u{over_cap.id}-base", user_context)
        self.assertEqual(result.units[0].unit_id, legal.id)
