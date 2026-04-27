import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from backend.app.services.automation_control_service import AutomationControlService
from backend.app.services.automation_state_repository import AutomationStateRepository
from backend.app.schemas.order import BrokerEnvironment, BrokerName, OrderRecord, OrderStatus, OrderType
from backend.app.services.broker_state_repository import BrokerStateRepository
from backend.app.services.brokers.alpaca_paper import AlpacaPaperBrokerAdapter
from backend.app.services.order_repository import OrderRepository
from backend.app.services.reconciliation_service import ReconciliationService


class ReconciliationServiceTest(unittest.TestCase):
    def test_sync_order_updates_last_synced_timestamp(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            order_repository = OrderRepository(base / "orders")
            broker_adapter = AlpacaPaperBrokerAdapter(BrokerStateRepository(base / "paper" / "state.json"))
            automation_service = AutomationControlService(
                AutomationStateRepository(base / "automation" / "state.json")
            )
            service = ReconciliationService(
                order_repository=order_repository,
                broker_adapter=broker_adapter,
                automation_control_service=automation_service,
            )
            order = OrderRecord(
                intent_id="intent-1",
                analysis_id="analysis-1",
                symbol="AAPL",
                broker_name=BrokerName.alpaca,
                broker_environment=BrokerEnvironment.paper,
                side="buy",
                order_type=OrderType.market,
                quantity=10,
                broker_order_id="sim-1",
                status=OrderStatus.filled,
                approval_required=False,
                submitted_at=datetime.now(timezone.utc),
                filled_at=datetime.now(timezone.utc),
            )
            order_repository.save(order)

            result = service.sync_order(order.id)

            self.assertEqual(len(result.synced_orders), 1)
            self.assertIsNotNone(result.synced_orders[0].last_synced_at)
            self.assertEqual(result.unmatched_local_symbols, ["AAPL"])
            self.assertTrue(automation_service.get_state().broker_sync_healthy)


if __name__ == "__main__":
    unittest.main()
