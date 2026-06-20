from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings

from advisor.llm_service import (
    AdvisorLLMError,
    ListSuggestion,
    OpenAIAdvisorProvider,
    PackageListSuggestion,
    PackageSuggestedUnit,
    SuggestedUnit,
    package_suggestion_to_list_suggestion,
    get_advisor_provider,
)


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
        self.assertEqual(call_kwargs["max_output_tokens"], 2048)

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
                    "selected_upgrade_ids": [10],
                },
                "u2-base": {
                    "unit_id": 2,
                    "unit_name": "Champion",
                    "model_count": 1,
                    "selected_upgrade_ids": [],
                },
            },
        )

        self.assertEqual(result.units[0].unit_id, 1)
        self.assertEqual(result.units[0].selected_upgrade_ids, [10])
        self.assertIsNone(result.units[0].parent_unit_index)
        self.assertEqual(result.units[1].unit_id, 2)
        self.assertEqual(result.units[1].parent_unit_index, 0)
        self.assertIn("Unknown package id missing was skipped.", result.warnings)

    def test_raises_advisor_error_when_response_has_no_parsed_output(self):
        client = Mock()
        client.responses.parse.return_value = SimpleNamespace(output_parsed=None)
        provider = OpenAIAdvisorProvider(client=client)

        with self.assertRaisesMessage(AdvisorLLMError, "structured suggestion"):
            provider.suggest(system_prompt="Use doctrine.", user_context="Faction context.")

    @override_settings(LLM_PROVIDER="openai")
    @patch("advisor.llm_service.OpenAIAdvisorProvider")
    def test_provider_factory_returns_configured_provider(self, provider_cls):
        provider = get_advisor_provider()

        self.assertEqual(provider, provider_cls.return_value)
