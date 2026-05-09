import unittest
import sys
import types
from unittest.mock import patch

if "requests" not in sys.modules:
    sys.modules["requests"] = types.ModuleType("requests")

if "pandas" not in sys.modules:
    pandas_stub = types.ModuleType("pandas")
    pandas_stub.DataFrame = object
    pandas_stub.read_csv = lambda *_args, **_kwargs: None
    sys.modules["pandas"] = pandas_stub

if "yfinance" not in sys.modules:
    yfinance_stub = types.ModuleType("yfinance")
    yfinance_stub.Ticker = object
    yfinance_stub.Search = object
    yfinance_stub.download = lambda *_args, **_kwargs: None
    sys.modules["yfinance"] = yfinance_stub

if "yfinance.exceptions" not in sys.modules:
    yfinance_exceptions_stub = types.ModuleType("yfinance.exceptions")
    yfinance_exceptions_stub.YFRateLimitError = type("YFRateLimitError", (Exception,), {})
    sys.modules["yfinance.exceptions"] = yfinance_exceptions_stub

if "stockstats" not in sys.modules:
    stockstats_stub = types.ModuleType("stockstats")
    stockstats_stub.wrap = lambda data: data
    sys.modules["stockstats"] = stockstats_stub

from tradingagents.dataflows.interface import (
    AlphaVantagePremiumEndpointError,
    AlphaVantageRateLimitError,
    route_to_vendor,
)


class DataVendorRoutingTests(unittest.TestCase):
    def test_single_vendor_config_does_not_fallback_to_yfinance(self) -> None:
        with patch("tradingagents.dataflows.interface.get_category_for_method", return_value="core_stock_apis"), patch(
            "tradingagents.dataflows.interface.get_vendor",
            return_value="alpha_vantage",
        ), patch.dict(
            "tradingagents.dataflows.interface.VENDOR_METHODS",
            {
                "get_stock_data": {
                    "alpha_vantage": lambda *_args, **_kwargs: (_ for _ in ()).throw(
                        AlphaVantageRateLimitError("rate limit")
                    ),
                    "yfinance": lambda *_args, **_kwargs: "should not be used",
                }
            },
            clear=False,
        ):
            with self.assertRaises(AlphaVantageRateLimitError):
                route_to_vendor("get_stock_data", "AAPL", "2026-04-20", "2026-04-26")

    def test_explicit_multi_vendor_config_can_fallback(self) -> None:
        with patch("tradingagents.dataflows.interface.get_category_for_method", return_value="core_stock_apis"), patch(
            "tradingagents.dataflows.interface.get_vendor",
            return_value="alpha_vantage,yfinance",
        ), patch.dict(
            "tradingagents.dataflows.interface.VENDOR_METHODS",
            {
                "get_stock_data": {
                    "alpha_vantage": lambda *_args, **_kwargs: (_ for _ in ()).throw(
                        AlphaVantageRateLimitError("rate limit")
                    ),
                    "yfinance": lambda *_args, **_kwargs: "fallback used",
                }
            },
            clear=False,
        ):
            result = route_to_vendor("get_stock_data", "AAPL", "2026-04-20", "2026-04-26")

        self.assertEqual(result, "fallback used")

    def test_explicit_multi_vendor_config_can_fallback_on_premium_endpoint(self) -> None:
        with patch("tradingagents.dataflows.interface.get_category_for_method", return_value="core_stock_apis"), patch(
            "tradingagents.dataflows.interface.get_vendor",
            return_value="alpha_vantage,yfinance",
        ), patch.dict(
            "tradingagents.dataflows.interface.VENDOR_METHODS",
            {
                "get_stock_data": {
                    "alpha_vantage": lambda *_args, **_kwargs: (_ for _ in ()).throw(
                        AlphaVantagePremiumEndpointError("premium endpoint")
                    ),
                    "yfinance": lambda *_args, **_kwargs: "fallback used",
                }
            },
            clear=False,
        ):
            result = route_to_vendor("get_stock_data", "AAPL", "2026-04-20", "2026-04-26")

        self.assertEqual(result, "fallback used")
