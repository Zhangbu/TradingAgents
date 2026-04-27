import tempfile
import unittest
from pathlib import Path

from backend.app.schemas.analysis import (
    AnalysisArtifacts,
    AnalysisRunRecord,
    AnalysisStatus,
    PlatformMode,
)
from backend.app.schemas.trade_intent import TradeIntentStatus
from backend.app.services.analysis_repository import AnalysisRepository
from backend.app.services.signal_service import SignalService
from backend.app.services.risk_service import RiskService
from backend.app.services.trade_intent_repository import TradeIntentRepository
from backend.app.services.trade_intent_service import TradeIntentService


class TradeIntentServiceTest(unittest.TestCase):
    def test_create_from_analysis_and_evaluate_risk(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_path = Path(tmp_dir)
            analysis_repository = AnalysisRepository(base_path / "analysis")
            trade_intent_repository = TradeIntentRepository(base_path / "intents")
            service = TradeIntentService(
                analysis_repository=analysis_repository,
                trade_intent_repository=trade_intent_repository,
                signal_service=SignalService(),
                risk_service=RiskService(),
            )

            analysis = AnalysisRunRecord(
                symbol="AAPL",
                trade_date="2026-04-25",
                selected_analysts=["market", "news"],
                mode=PlatformMode.paper_manual,
                status=AnalysisStatus.completed,
                artifacts=AnalysisArtifacts(
                    final_trade_decision="Buy the stock, but earnings volatility makes timing sensitive.",
                    processed_signal="BUY",
                ),
            )
            analysis_repository.save(analysis)

            intent = service.create_from_analysis(analysis.id)
            evaluated = service.evaluate_risk(intent.id)

            self.assertEqual(intent.analysis_id, analysis.id)
            self.assertEqual(evaluated.status, TradeIntentStatus.approval_required)
            assert evaluated.risk_summary is not None
            self.assertGreaterEqual(len(evaluated.risk_summary.checks), 2)


if __name__ == "__main__":
    unittest.main()
