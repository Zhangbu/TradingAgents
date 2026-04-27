import tempfile
import unittest
from pathlib import Path

from backend.app.schemas.broker import InteractiveBrokersConfig
from backend.app.schemas.order import BrokerEnvironment, BrokerName, OrderRecord, OrderStatus, OrderType
from backend.app.services.broker_state_repository import BrokerStateRepository
from backend.app.services.brokers.interactive_brokers_paper import InteractiveBrokersPaperBrokerAdapter


class InteractiveBrokersPaperBrokerAdapterTest(unittest.TestCase):
    def test_buy_order_initially_partially_fills_and_sync_promotes_to_filled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            adapter = InteractiveBrokersPaperBrokerAdapter(
                config=InteractiveBrokersConfig(enabled=True),
                state_repository=BrokerStateRepository(Path(tmp_dir) / "ib.json"),
            )
            order = OrderRecord(
                intent_id="intent-1",
                analysis_id="analysis-1",
                symbol="MSFT",
                broker_name=BrokerName.interactive_brokers,
                broker_environment=BrokerEnvironment.paper,
                side="buy",
                order_type=OrderType.market,
                quantity=10,
                requested_price=100.0,
                status=OrderStatus.submitted,
                approval_required=False,
            )

            submitted = adapter.submit_order(order)
            self.assertEqual(submitted.status, OrderStatus.partially_filled)
            self.assertEqual(submitted.filled_quantity, 5)

            synced = adapter.sync_order(submitted)
            self.assertEqual(synced.status, OrderStatus.filled)
            self.assertEqual(synced.filled_quantity, 10)


if __name__ == "__main__":
    unittest.main()
