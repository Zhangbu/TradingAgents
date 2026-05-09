import unittest

from backend.app.schemas.broker import AlpacaBrokerConfig
from backend.app.schemas.order import BrokerEnvironment, BrokerName, OrderRecord, OrderStatus, OrderType
from backend.app.services.brokers.alpaca_api import AlpacaApiPaperBrokerAdapter


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload
        self.status_code = 200
        self.text = ""

    def raise_for_status(self):
        return None

    def json(self):
        if self._payload is None:
            raise ValueError("No JSON body")
        return self._payload


class FakeSession:
    def __init__(self):
        self.calls = []

    def request(self, method, url, headers=None, timeout=None, **kwargs):
        self.calls.append((method, url, headers, kwargs))
        if method == "POST" and url.endswith("/orders"):
            return FakeResponse(
                {
                    "id": "broker-order-1",
                    "status": "filled",
                    "filled_avg_price": "101.5",
                    "submitted_at": "2026-04-25T10:00:00Z",
                    "filled_at": "2026-04-25T10:00:01Z",
                }
            )
        if method == "GET" and url.endswith("/account"):
            return FakeResponse(
                {
                    "cash": "92000",
                    "equity": "100500",
                    "buying_power": "92000",
                }
            )
        if method == "GET" and url.endswith("/positions"):
            return FakeResponse(
                [
                    {
                        "symbol": "AAPL",
                        "qty": "80",
                        "avg_entry_price": "100.0",
                        "market_value": "8120.0",
                    }
                ]
            )
        if method == "GET" and url.endswith("/orders/broker-order-1"):
            return FakeResponse(
                {
                    "id": "broker-order-1",
                    "status": "partially_filled",
                    "filled_avg_price": "101.5",
                    "filled_qty": "5",
                    "submitted_at": "2026-04-25T10:00:00Z",
                    "updated_at": "2026-04-25T10:00:02Z",
                }
            )
        if method == "DELETE" and url.endswith("/orders/broker-order-1"):
            return FakeResponse(None)
        raise AssertionError(f"Unexpected request: {method} {url}")


class FailingSession:
    def request(self, method, url, headers=None, timeout=None, **kwargs):
        raise RuntimeError("TLS connect error")


class AlpacaApiPaperBrokerAdapterTest(unittest.TestCase):
    def build_adapter(self):
        config = AlpacaBrokerConfig(
            enabled=True,
            paper_trading_mode="api",
            api_key="key",
            secret_key="secret",
        )
        session = FakeSession()
        return AlpacaApiPaperBrokerAdapter(config=config, session=session), session

    def test_submit_order_maps_remote_payload(self):
        adapter, session = self.build_adapter()
        order = OrderRecord(
            intent_id="intent-1",
            analysis_id="analysis-1",
            symbol="AAPL",
            broker_name=BrokerName.alpaca,
            broker_environment=BrokerEnvironment.paper,
            side="buy",
            order_type=OrderType.market,
            quantity=10,
            requested_price=100.0,
            status=OrderStatus.submitted,
            approval_required=False,
        )

        submitted = adapter.submit_order(order)

        self.assertEqual(submitted.broker_order_id, "broker-order-1")
        self.assertEqual(submitted.status, OrderStatus.filled)
        self.assertAlmostEqual(submitted.filled_price or 0.0, 101.5)
        self.assertTrue(session.calls)

    def test_get_account_snapshot_uses_remote_account_and_positions(self):
        adapter, _ = self.build_adapter()

        snapshot = adapter.get_account_snapshot()

        self.assertEqual(snapshot.cash, 92000.0)
        self.assertEqual(snapshot.positions[0].symbol, "AAPL")
        self.assertEqual(snapshot.positions[0].quantity, 80)

    def test_sync_order_maps_partial_fill_status_and_remaining_quantity(self):
        adapter, _ = self.build_adapter()
        order = OrderRecord(
            intent_id="intent-1",
            analysis_id="analysis-1",
            symbol="AAPL",
            broker_name=BrokerName.alpaca,
            broker_environment=BrokerEnvironment.paper,
            side="buy",
            order_type=OrderType.market,
            quantity=10,
            requested_price=100.0,
            broker_order_id="broker-order-1",
            status=OrderStatus.submitted,
            approval_required=False,
        )

        synced = adapter.sync_order(order)

        self.assertEqual(synced.status, OrderStatus.partially_filled)
        self.assertEqual(synced.filled_quantity, 5)
        self.assertEqual(synced.remaining_quantity, 5)
        self.assertEqual(synced.average_fill_price, 101.5)

    def test_cancel_order_handles_empty_delete_response(self):
        adapter, _ = self.build_adapter()
        order = OrderRecord(
            intent_id="intent-1",
            analysis_id="analysis-1",
            symbol="AAPL",
            broker_name=BrokerName.alpaca,
            broker_environment=BrokerEnvironment.paper,
            side="buy",
            order_type=OrderType.market,
            quantity=10,
            requested_price=100.0,
            broker_order_id="broker-order-1",
            status=OrderStatus.submitted,
            approval_required=False,
        )

        canceled = adapter.cancel_order(order)

        self.assertEqual(canceled.status, OrderStatus.canceled)
        self.assertIsNotNone(canceled.canceled_at)

    def test_get_account_snapshot_surfaces_transport_error_as_value_error(self):
        config = AlpacaBrokerConfig(
            enabled=True,
            paper_trading_mode="api",
            api_key="key",
            secret_key="secret",
        )
        adapter = AlpacaApiPaperBrokerAdapter(config=config, session=FailingSession())

        with self.assertRaisesRegex(ValueError, "TLS/SSL setup"):
            adapter.get_account_snapshot()


if __name__ == "__main__":
    unittest.main()
