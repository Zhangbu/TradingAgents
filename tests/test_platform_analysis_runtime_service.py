import os
import unittest
from unittest.mock import patch

from backend.app.services.analysis_runtime_service import AnalysisRuntimeService


class AnalysisRuntimeServiceTests(unittest.TestCase):
    def test_reports_blocked_llm_when_active_provider_key_is_missing(self) -> None:
        with patch.dict(
            os.environ,
            {
                "TRADINGAGENTS_LLM_PROVIDER": "deepseek",
                "DEEPSEEK_API_KEY": "",
            },
            clear=False,
        ):
            health = AnalysisRuntimeService().get_health()

        self.assertEqual(health.profile.llm_provider, "deepseek")
        self.assertEqual(health.llm.state, "blocked")
        self.assertFalse(health.llm.healthy)

    def test_reports_blocked_market_data_when_alpha_vantage_key_is_missing(self) -> None:
        with patch.dict(
            os.environ,
            {
                "TRADINGAGENTS_CORE_STOCK_VENDOR": "alpha_vantage",
                "TRADINGAGENTS_TECHNICAL_VENDOR": "alpha_vantage",
                "TRADINGAGENTS_FUNDAMENTAL_VENDOR": "alpha_vantage",
                "TRADINGAGENTS_NEWS_VENDOR": "alpha_vantage",
                "ALPHA_VANTAGE_API_KEY": "",
            },
            clear=False,
        ):
            health = AnalysisRuntimeService().get_health()

        self.assertEqual(health.market_data.state, "blocked")
        self.assertFalse(health.market_data.healthy)

    def test_reports_nvidia_provider_key_presence_in_profile(self) -> None:
        with patch.dict(
            os.environ,
            {
                "TRADINGAGENTS_LLM_PROVIDER": "nvidia",
                "NVIDIA_API_KEY": "nv-key",
            },
            clear=False,
        ):
            profile = AnalysisRuntimeService().get_profile()

        self.assertEqual(profile.llm_provider, "nvidia")
        self.assertTrue(profile.api_keys_present["nvidia"])

    def test_runtime_catalog_includes_provider_models_and_vendor_categories(self) -> None:
        catalog = AnalysisRuntimeService().get_catalog()

        self.assertIn("nvidia", catalog.providers)
        self.assertTrue(
            any(option.value == "z-ai/glm4.7" for option in catalog.providers["nvidia"].quick_models)
        )
        self.assertTrue(
            any(category.category == "core_stock_apis" for category in catalog.data_vendor_categories)
        )
