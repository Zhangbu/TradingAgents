import tempfile
import unittest
from pathlib import Path

from backend.app.schemas.analysis import PlatformMode
from backend.app.schemas.order import (
    AccountSnapshot,
    ApprovalRequest,
    BrokerEnvironment,
    BrokerName,
    OrderCreateRequest,
    OrderStatus,
)
from backend.app.schemas.trade_intent import (
    EntryType,
    TimeHorizon,
    TradeIntentRecord,
    TradeIntentStatus,
    TradeRating,
    TradeSide,
)
from backend.app.services.broker_state_repository import BrokerStateRepository
from backend.app.services.audit_log_repository import AuditLogRepository
from backend.app.services.audit_log_service import AuditLogService
from backend.app.services.brokers.alpaca_paper import AlpacaPaperBrokerAdapter
from backend.app.services.execution_service import ExecutionService
from backend.app.services.order_repository import OrderRepository
from backend.app.services.trade_intent_repository import TradeIntentRepository


def build_intent(**overrides) -> TradeIntentRecord:
    payload = {
        "analysis_id": "analysis_1",
        "symbol": "AAPL",
        "trade_date": "2026-04-25",
        "mode": PlatformMode.paper_manual,
        "rating": TradeRating.buy,
        "side": TradeSide.buy,
        "status": TradeIntentStatus.approval_required,
        "confidence": 0.78,
        "entry_type": EntryType.market,
        "time_horizon": TimeHorizon.swing,
        "max_position_pct": 0.08,
        "max_loss_pct": 0.03,
        "take_profit_pct": 0.09,
        "thesis_summary": "Constructive momentum and supportive fundamentals.",
        "source_signal": "BUY",
        "risk_flags": ["earnings_risk"],
    }
    payload.update(overrides)
    return TradeIntentRecord(**payload)


class ExecutionServiceTest(unittest.TestCase):
    def test_broker_submission_failure_returns_failed_order(self) -> None:
        class FailingBroker:
            def submit_order(self, order):
                raise RuntimeError("alpaca unavailable")

            def get_account_snapshot(self):
                return AccountSnapshot(cash=100000, equity=100000, buying_power=100000, positions=[])

            def sync_order(self, order):
                return order

            def get_broker_name(self):
                return "alpaca"

            def cancel_order(self, order):
                return order

            def replace_order(self, order, *, quantity, limit_price):
                return order

        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            intent_repository = TradeIntentRepository(base / "intents")
            order_repository = OrderRepository(base / "orders")
            service = ExecutionService(intent_repository, order_repository, FailingBroker())

            intent = build_intent(mode=PlatformMode.paper_auto, status=TradeIntentStatus.ready)
            intent_repository.save(intent)

            order = service.create_order(
                OrderCreateRequest(
                    intent_id=intent.id,
                    broker_name=BrokerName.alpaca,
                    broker_environment=BrokerEnvironment.paper,
                    reference_price=100,
                )
            )

            self.assertEqual(order.status, OrderStatus.failed)
            self.assertIn("alpaca unavailable", order.status_reason or "")

    def test_manual_order_requires_approval_before_fill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            intent_repository = TradeIntentRepository(base / "intents")
            order_repository = OrderRepository(base / "orders")
            broker_adapter = AlpacaPaperBrokerAdapter(BrokerStateRepository(base / "paper" / "state.json"))
            audit_service = AuditLogService(AuditLogRepository(base / "audit"))
            service = ExecutionService(intent_repository, order_repository, broker_adapter, audit_log_service=audit_service)

            intent = build_intent(mode=PlatformMode.paper_manual)
            intent_repository.save(intent)

            order = service.create_order(
                OrderCreateRequest(
                    intent_id=intent.id,
                    broker_name=BrokerName.alpaca,
                    broker_environment=BrokerEnvironment.paper,
                    reference_price=100,
                )
            )

            self.assertEqual(order.status, OrderStatus.pending_approval)

            approved = service.approve_order(
                ApprovalRequest(order_id=order.id, reviewer="alice", note="Looks good")
            )

            self.assertEqual(approved.status, OrderStatus.filled)
            snapshot = service.get_account_snapshot()
            self.assertEqual(snapshot.positions[0].symbol, "AAPL")
            self.assertEqual(snapshot.positions[0].quantity, 80)

    def test_ready_paper_auto_order_fills_immediately(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            intent_repository = TradeIntentRepository(base / "intents")
            order_repository = OrderRepository(base / "orders")
            broker_adapter = AlpacaPaperBrokerAdapter(BrokerStateRepository(base / "paper" / "state.json"))
            service = ExecutionService(intent_repository, order_repository, broker_adapter)

            intent = build_intent(mode=PlatformMode.paper_auto, status=TradeIntentStatus.ready)
            intent_repository.save(intent)

            order = service.create_order(
                OrderCreateRequest(
                    intent_id=intent.id,
                    broker_name=BrokerName.alpaca,
                    broker_environment=BrokerEnvironment.paper,
                    reference_price=100,
                )
            )

            self.assertEqual(order.status, OrderStatus.filled)
            self.assertFalse(order.approval_required)

    def test_blocked_trade_intent_cannot_create_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            intent_repository = TradeIntentRepository(base / "intents")
            order_repository = OrderRepository(base / "orders")
            broker_adapter = AlpacaPaperBrokerAdapter(BrokerStateRepository(base / "paper" / "state.json"))
            service = ExecutionService(intent_repository, order_repository, broker_adapter)

            intent = build_intent(status=TradeIntentStatus.blocked)
            intent_repository.save(intent)

            with self.assertRaisesRegex(ValueError, "Blocked trade intents"):
                service.create_order(
                    OrderCreateRequest(
                        intent_id=intent.id,
                        broker_name=BrokerName.alpaca,
                        broker_environment=BrokerEnvironment.paper,
                        reference_price=100,
                    )
                )

    def test_reject_order_stops_submission(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            intent_repository = TradeIntentRepository(base / "intents")
            order_repository = OrderRepository(base / "orders")
            broker_adapter = AlpacaPaperBrokerAdapter(BrokerStateRepository(base / "paper" / "state.json"))
            service = ExecutionService(intent_repository, order_repository, broker_adapter)

            intent = build_intent()
            intent_repository.save(intent)
            order = service.create_order(
                OrderCreateRequest(
                    intent_id=intent.id,
                    broker_name=BrokerName.alpaca,
                    broker_environment=BrokerEnvironment.paper,
                    reference_price=100,
                )
            )

            rejected = service.reject_order(
                ApprovalRequest(order_id=order.id, reviewer="bob", note="Skip this setup")
            )

            self.assertEqual(rejected.status, OrderStatus.rejected)
            snapshot = service.get_account_snapshot()
            self.assertIsInstance(snapshot, AccountSnapshot)
            self.assertEqual(snapshot.positions, [])

    def test_cancel_and_replace_update_order_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            intent_repository = TradeIntentRepository(base / "intents")
            order_repository = OrderRepository(base / "orders")
            broker_adapter = AlpacaPaperBrokerAdapter(BrokerStateRepository(base / "paper" / "state.json"))
            service = ExecutionService(intent_repository, order_repository, broker_adapter)

            intent = build_intent(mode=PlatformMode.paper_auto, status=TradeIntentStatus.ready)
            intent_repository.save(intent)
            order = service.create_order(
                OrderCreateRequest(
                    intent_id=intent.id,
                    broker_name=BrokerName.alpaca,
                    broker_environment=BrokerEnvironment.paper,
                    reference_price=100,
                )
            )

            replaced = service.replace_order(
                order.id,
                type("Req", (), {"reviewer": "alice", "quantity": 40, "limit_price": 95.0, "note": "tighten"})(),
            )
            self.assertEqual(replaced.status, OrderStatus.replaced)
            self.assertEqual(replaced.quantity, 40)

            canceled = service.cancel_order(
                order.id,
                type("Req", (), {"reviewer": "alice", "note": "stop trade"})(),
            )
            self.assertEqual(canceled.status, OrderStatus.canceled)


if __name__ == "__main__":
    unittest.main()
