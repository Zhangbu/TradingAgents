import unittest

from backend.app.schemas.analysis import PlatformMode
from backend.app.schemas.trade_intent import (
    EntryType,
    TimeHorizon,
    TradeIntentRecord,
    TradeIntentStatus,
    TradeRating,
    TradeSide,
)
from backend.app.services.risk_service import RiskService


def build_intent(**overrides) -> TradeIntentRecord:
    payload = {
        "analysis_id": "analysis_1",
        "symbol": "AAPL",
        "trade_date": "2026-04-25",
        "mode": PlatformMode.paper_auto,
        "rating": TradeRating.buy,
        "side": TradeSide.buy,
        "confidence": 0.78,
        "entry_type": EntryType.market,
        "time_horizon": TimeHorizon.swing,
        "max_position_pct": 0.08,
        "max_loss_pct": 0.03,
        "take_profit_pct": 0.09,
        "thesis_summary": "Constructive momentum and supportive fundamentals.",
        "source_signal": "BUY",
        "risk_flags": [],
    }
    payload.update(overrides)
    return TradeIntentRecord(**payload)


class RiskServiceTest(unittest.TestCase):
    def test_paper_auto_ready_when_all_phase_two_checks_pass(self) -> None:
        intent = build_intent(mode=PlatformMode.paper_auto)

        evaluated = RiskService().evaluate(intent)

        self.assertEqual(evaluated.status, TradeIntentStatus.ready)
        assert evaluated.risk_summary is not None
        self.assertEqual(evaluated.risk_summary.outcome, TradeIntentStatus.ready)

    def test_manual_mode_requires_operator_approval(self) -> None:
        intent = build_intent(mode=PlatformMode.paper_manual)

        evaluated = RiskService().evaluate(intent)

        self.assertEqual(evaluated.status, TradeIntentStatus.approval_required)
        assert evaluated.risk_summary is not None
        rule_codes = [check.rule_code for check in evaluated.risk_summary.checks]
        self.assertIn("mode.manual_approval", rule_codes)

    def test_analysis_only_mode_blocks_order_path(self) -> None:
        intent = build_intent(mode=PlatformMode.analysis_only)

        evaluated = RiskService().evaluate(intent)

        self.assertEqual(evaluated.status, TradeIntentStatus.blocked)
        assert evaluated.risk_summary is not None
        rule_codes = [check.rule_code for check in evaluated.risk_summary.checks]
        self.assertIn("mode.analysis_only", rule_codes)

    def test_live_auto_is_hard_blocked(self) -> None:
        intent = build_intent(mode=PlatformMode.live_auto)

        evaluated = RiskService().evaluate(intent)

        self.assertEqual(evaluated.status, TradeIntentStatus.blocked)
        assert evaluated.risk_summary is not None
        rule_codes = [check.rule_code for check in evaluated.risk_summary.checks]
        self.assertIn("mode.live_auto_disabled", rule_codes)


if __name__ == "__main__":
    unittest.main()
