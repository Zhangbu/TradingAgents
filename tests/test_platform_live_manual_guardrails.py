import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from backend.app.schemas.analysis import PlatformMode
from backend.app.schemas.automation import LiveTradingConfirmRequest, LiveTradingRequest
from backend.app.schemas.order import BrokerEnvironment, BrokerName, OrderCreateRequest
from backend.app.schemas.trade_intent import EntryType, TimeHorizon, TradeIntentRecord, TradeIntentStatus, TradeRating, TradeSide
from backend.app.services.automation_control_service import AutomationControlService
from backend.app.services.automation_state_repository import AutomationStateRepository
from backend.app.services.broker_state_repository import BrokerStateRepository
from backend.app.services.brokers.alpaca_paper import AlpacaPaperBrokerAdapter
from backend.app.services.execution_service import ExecutionService
from backend.app.services.order_repository import OrderRepository
from backend.app.services.trade_intent_repository import TradeIntentRepository


def build_live_intent(**overrides) -> TradeIntentRecord:
    payload = {
        "analysis_id": "analysis-live",
        "symbol": "AAPL",
        "trade_date": "2026-04-25",
        "mode": PlatformMode.live_manual,
        "rating": TradeRating.buy,
        "side": TradeSide.buy,
        "status": TradeIntentStatus.approval_required,
        "confidence": 0.8,
        "entry_type": EntryType.market,
        "time_horizon": TimeHorizon.swing,
        "max_position_pct": 0.05,
        "max_loss_pct": 0.03,
        "take_profit_pct": 0.08,
        "thesis_summary": "live manual test",
        "risk_flags": [],
    }
    payload.update(overrides)
    return TradeIntentRecord(**payload)


class LiveManualGuardrailsTest(unittest.TestCase):
    def test_live_order_requires_live_controls_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            intent_repository = TradeIntentRepository(base / "intents")
            order_repository = OrderRepository(base / "orders")
            automation = AutomationControlService(AutomationStateRepository(base / "automation" / "state.json"))
            automation.record_broker_sync(datetime.now(timezone.utc))
            broker = AlpacaPaperBrokerAdapter(BrokerStateRepository(base / "paper" / "state.json"))
            service = ExecutionService(intent_repository, order_repository, broker, automation_control_service=automation)
            intent = build_live_intent()
            intent_repository.save(intent)

            with self.assertRaisesRegex(ValueError, "live trading is not fully enabled"):
                service.create_order(
                    OrderCreateRequest(
                        intent_id=intent.id,
                        broker_name=BrokerName.alpaca,
                        broker_environment=BrokerEnvironment.live,
                        reference_price=100,
                    )
                )

            automation.set_live_trading(LiveTradingRequest(enabled=True, actor="alice", reason="ready"))
            automation.confirm_live_trading(LiveTradingConfirmRequest(actor="alice"))

            order = service.create_order(
                OrderCreateRequest(
                    intent_id=intent.id,
                    broker_name=BrokerName.alpaca,
                    broker_environment=BrokerEnvironment.live,
                    reference_price=100,
                )
            )
            self.assertEqual(order.status.value, "pending_approval")


if __name__ == "__main__":
    unittest.main()
