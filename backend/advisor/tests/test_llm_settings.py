from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from opr_helper.settings import _validate_llm_configuration


class AdvisorLLMSettingsTests(SimpleTestCase):
    def test_debug_mode_does_not_require_openai_api_key(self):
        _validate_llm_configuration(
            debug=True,
            provider="openai",
            openai_api_key="",
        )

    def test_openai_provider_requires_api_key_in_production(self):
        with self.assertRaisesMessage(
            ImproperlyConfigured,
            "OPENAI_API_KEY must be set",
        ):
            _validate_llm_configuration(
                debug=False,
                provider="openai",
                openai_api_key="",
            )

    def test_unsupported_provider_is_rejected_in_production(self):
        with self.assertRaisesMessage(
            ImproperlyConfigured,
            "Unsupported LLM_PROVIDER",
        ):
            _validate_llm_configuration(
                debug=False,
                provider="other",
                openai_api_key="test-key",
            )
