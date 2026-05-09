import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from backend.app.schemas.analysis import PlatformMode
from backend.app.schemas.automation import AutomationState
from backend.app.schemas.order import (
    ApprovalRequest,
    BrokerEnvironment,
    BrokerName,
    OrderCreateRequest,
)
from backend.app.schemas.trade_intent import (
    EntryType,
    TimeHorizon,
    TradeIntentRecord,
    TradeIntentStatus,
    TradeRating,
    TradeSide,
)
from backend.app.services.automation_control_service import AutomationControlService
from backend.app.services.automation_state_repository import AutomationStateRepository
from backend.app.services.broker_state_repository import BrokerStateRepository
from backend.app.services.brokers.alpaca_paper import AlpacaPaperBrokerAdapter
from backend.app.services.execution_service import ExecutionService
from backend.app.services.order_repository import OrderRepository
from backend.app.services.trade_intent_repository import TradeIntentRepository


def build_intent(**overrides) -> TradeIntentRecord:
    payload = {
        "analysis_id": "analysis_1",
        "symbol": "AAPL",
        "trade_date": "2026-04-25",
        "mode": PlatformMode.paper_auto,
        "rating": TradeRating.buy,
        "side": TradeSide.buy,
        "status": TradeIntentStatus.ready,
        "confidence": 0.78,
        "entry_type": EntryType.market,
        "time_horizon": TimeHorizon.swing,
        "max_position_pct": 0.08,
        "max_loss_pct": 0.03,
        "take_profit_pct": 0.09,
        "thesis_summary": "Constructive setup.",
        "source_signal": "BUY",
        "risk_flags": [],
    }
    payload.update(overrides)
    return TradeIntentRecord(**payload)


class ExecutionGuardrailsTest(unittest.TestCase):
    def test_manual_order_allowed_when_sync_is_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            intent_repository = TradeIntentRepository(base / "intents")
            order_repository = OrderRepository(base / "orders")
            automation_service = AutomationControlService(
                AutomationStateRepository(base / "automation" / "state.json")
            )
            stale_time = datetime.now(timezone.utc) - timedelta(hours=1)
            automation_service.record_broker_sync(stale_time)
            broker_adapter = AlpacaPaperBrokerAdapter(BrokerStateRepository(base / "paper" / "state.json"))
            service = ExecutionService(
                intent_repository,
                order_repository,
                broker_adapter,
                automation_control_service=automation_service,
            )

            intent = build_intent(mode=PlatformMode.paper_manual, status=TradeIntentStatus.approval_required)
            intent_repository.save(intent)

            order = service.create_order(
                OrderCreateRequest(
                    intent_id=intent.id,
                    broker_name=BrokerName.alpaca,
                    broker_environment=BrokerEnvironment.paper,
                    reference_price=100,
                )
            )

            self.assertEqual(order.status.value, "pending_approval")

    def test_auto_order_blocked_when_auto_trading_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            intent_repository = TradeIntentRepository(base / "intents")
            order_repository = OrderRepository(base / "orders")
            automation_service = AutomationControlService(
                AutomationStateRepository(base / "automation" / "state.json")
            )
            automation_service.record_broker_sync(datetime.now(timezone.utc))
            broker_adapter = AlpacaPaperBrokerAdapter(BrokerStateRepository(base / "paper" / "state.json"))
            service = ExecutionService(
                intent_repository,
                order_repository,
                broker_adapter,
                automation_control_service=automation_service,
            )

            intent = build_intent()
            intent_repository.save(intent)

            with self.assertRaisesRegex(ValueError, "auto trading is disabled"):
                service.create_order(
                    OrderCreateRequest(
                        intent_id=intent.id,
                        broker_name=BrokerName.alpaca,
                        broker_environment=BrokerEnvironment.paper,
                        reference_price=100,
                    )
                )

    def test_auto_order_blocked_when_sync_is_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            intent_repository = TradeIntentRepository(base / "intents")
            order_repository = OrderRepository(base / "orders")
            automation_service = AutomationControlService(
                AutomationStateRepository(base / "automation" / "state.json")
            )
            automation_service.set_auto_trading(True)
            stale_time = datetime.now(timezone.utc) - timedelta(hours=1)
            automation_service.record_broker_sync(stale_time)
            broker_adapter = AlpacaPaperBrokerAdapter(BrokerStateRepository(base / "paper" / "state.json"))
            service = ExecutionService(
                intent_repository,
                order_repository,
                broker_adapter,
                automation_control_service=automation_service,
            )

            intent = build_intent()
            intent_repository.save(intent)

            with self.assertRaisesRegex(ValueError, "broker sync is stale"):
                service.create_order(
                    OrderCreateRequest(
                        intent_id=intent.id,
                        broker_name=BrokerName.alpaca,
                        broker_environment=BrokerEnvironment.paper,
                        reference_price=100,
                    )
                )

    def test_kill_switch_blocks_manual_approval_submission(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            intent_repository = TradeIntentRepository(base / "intents")
            order_repository = OrderRepository(base / "orders")
            automation_service = AutomationControlService(
                AutomationStateRepository(base / "automation" / "state.json")
            )
            automation_service.record_broker_sync(datetime.now(timezone.utc))
            automation_service.activate_kill_switch("manual stop")
            broker_adapter = AlpacaPaperBrokerAdapter(BrokerStateRepository(base / "paper" / "state.json"))
            service = ExecutionService(
                intent_repository,
                order_repository,
                broker_adapter,
                automation_control_service=automation_service,
            )

            intent = build_intent(mode=PlatformMode.paper_manual, status=TradeIntentStatus.approval_required)
            intent_repository.save(intent)

            with self.assertRaisesRegex(ValueError, "kill switch is active"):
                service.create_order(
                    OrderCreateRequest(
                        intent_id=intent.id,
                        broker_name=BrokerName.alpaca,
                        broker_environment=BrokerEnvironment.paper,
                        reference_price=100,
                    )
                )

    def test_failed_submissions_increment_broker_failures(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            intent_repository = TradeIntentRepository(base / "intents")
            order_repository = OrderRepository(base / "orders")
            automation_repository = AutomationStateRepository(base / "automation" / "state.json")
            automation_service = AutomationControlService(automation_repository)
            automation_service.set_auto_trading(True)
            automation_service.record_broker_sync(datetime.now(timezone.utc))
            broker_adapter = AlpacaPaperBrokerAdapter(BrokerStateRepository(base / "paper" / "state.json"))
            service = ExecutionService(
                intent_repository,
                order_repository,
                broker_adapter,
                automation_control_service=automation_service,
            )

            intent = build_intent(
                side=TradeSide.sell,
                rating=TradeRating.sell,
                source_signal="SELL",
            )
            intent_repository.save(intent)

            order = service.create_order(
                OrderCreateRequest(
                    intent_id=intent.id,
                    broker_name=BrokerName.alpaca,
                    broker_environment=BrokerEnvironment.paper,
                    reference_price=100,
                )
            )

            self.assertEqual(order.status.value, "failed")
            state = automation_service.get_state()
            self.assertEqual(state.consecutive_broker_failures, 1)


if __name__ == "__main__":
    unittest.main()
