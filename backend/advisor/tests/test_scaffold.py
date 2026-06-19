from django.test import TestCase
from rest_framework.test import APIClient

from advisor.apps import AdvisorConfig


class AdvisorScaffoldTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_advisor_root_endpoint_returns_provider_status(self):
        response = self.client.get("/api/advisor/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIsNone(payload["error"])
        self.assertEqual(payload["data"]["status"], "advisor-ready")
        self.assertEqual(payload["data"]["provider"], "openai")
        self.assertEqual(payload["data"]["model"], "gpt-5.5")

    def test_advisor_app_config_uses_expected_name(self):
        self.assertEqual(AdvisorConfig.name, "advisor")
