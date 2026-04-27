import unittest

from backend.app.schemas.analysis import (
    AnalysisArtifacts,
    AnalysisRunRecord,
    AnalysisStatus,
    PlatformMode,
)
from backend.app.services.signal_service import SignalService


class SignalServiceTest(unittest.TestCase):
    def test_build_from_analysis_maps_buy_signal_to_structured_intent(self) -> None:
        record = AnalysisRunRecord(
            symbol="AAPL",
            trade_date="2026-04-25",
            selected_analysts=["market", "news"],
            mode=PlatformMode.paper_manual,
            status=AnalysisStatus.completed,
            artifacts=AnalysisArtifacts(
                final_trade_decision="Buy the stock, but note earnings volatility next week.",
                processed_signal="BUY",
            ),
        )

        intent = SignalService().build_from_analysis(record)

        self.assertEqual(intent.symbol, "AAPL")
        self.assertEqual(intent.rating.value, "BUY")
        self.assertEqual(intent.side.value, "buy")
        self.assertAlmostEqual(intent.max_position_pct, 0.08)
        self.assertIn("earnings_risk", intent.risk_flags)
        self.assertIn("high_volatility", intent.risk_flags)

    def test_build_from_analysis_uses_hold_defaults_when_signal_missing(self) -> None:
        record = AnalysisRunRecord(
            symbol="MSFT",
            trade_date="2026-04-25",
            selected_analysts=["market"],
            mode=PlatformMode.analysis_only,
            status=AnalysisStatus.completed,
            artifacts=AnalysisArtifacts(final_trade_decision="Mixed setup and unclear direction."),
        )

        intent = SignalService().build_from_analysis(record)

        self.assertEqual(intent.rating.value, "HOLD")
        self.assertEqual(intent.side.value, "hold")
        self.assertEqual(intent.entry_type.value, "none")
        self.assertEqual(intent.max_loss_pct, 0.0)


if __name__ == "__main__":
    unittest.main()
