import os
import unittest
from unittest.mock import patch

from tradingagents.default_config import build_default_config


class TradingAgentsDataVendorConfigTests(unittest.TestCase):
    def test_uses_env_data_vendor_overrides(self) -> None:
        with patch.dict(
            os.environ,
            {
                "TRADINGAGENTS_CORE_STOCK_VENDOR": "alpha_vantage",
                "TRADINGAGENTS_TECHNICAL_VENDOR": "alpha_vantage",
                "TRADINGAGENTS_FUNDAMENTAL_VENDOR": "alpha_vantage",
                "TRADINGAGENTS_NEWS_VENDOR": "alpha_vantage",
            },
            clear=False,
        ):
            config = build_default_config()

        self.assertEqual(
            config["data_vendors"],
            {
                "core_stock_apis": "alpha_vantage",
                "technical_indicators": "alpha_vantage",
                "fundamental_data": "alpha_vantage",
                "news_data": "alpha_vantage",
            },
        )
