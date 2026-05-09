from contextlib import redirect_stdout
from io import StringIO
import unittest
from unittest.mock import patch

from tradingagents.dataflows.alpha_vantage_common import (
    AlphaVantagePremiumEndpointError,
    _filter_csv_by_date_range,
    _make_api_request,
)
from backend.app.services.analysis_service import AnalysisService


class _FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text

    def raise_for_status(self) -> None:
        return None


class AlphaVantageCommonTests(unittest.TestCase):
    def test_make_api_request_raises_premium_endpoint_error(self) -> None:
        payload = (
            '{"Information": "Thank you for using Alpha Vantage! This is a premium '
            'endpoint. You may subscribe to any of the premium plans."}'
        )
        with patch(
            "tradingagents.dataflows.alpha_vantage_common.get_api_key",
            return_value="demo",
        ), patch(
            "tradingagents.dataflows.alpha_vantage_common.requests.get",
            return_value=_FakeResponse(payload),
        ):
            with self.assertRaises(AlphaVantagePremiumEndpointError):
                _make_api_request("TIME_SERIES_DAILY_ADJUSTED", {"symbol": "AAPL"})

    def test_filter_csv_by_date_range_rejects_non_market_schema(self) -> None:
        bad_csv = '"Information","Value"\n"premium endpoint","upgrade required"\n'

        with redirect_stdout(StringIO()):
            filtered = _filter_csv_by_date_range(bad_csv, "2026-05-01", "2026-05-09")

        self.assertEqual(filtered, bad_csv)

    def test_analysis_service_normalizes_premium_endpoint_error(self) -> None:
        service = AnalysisService(repository=None, runner=object())

        message, details = service._normalize_failure(
            "Alpha Vantage rejected the request because this endpoint requires a premium plan"
        )

        self.assertEqual(
            message,
            "Alpha Vantage rejected the market data request because the selected endpoint is only available on a premium plan.",
        )
        self.assertEqual(details.code, "market_data_premium_endpoint")
