import tempfile
import unittest
from pathlib import Path

from backend.app.schemas.broker import AlpacaBrokerConfig, InteractiveBrokersConfig
from backend.app.services.broker_state_repository import BrokerStateRepository
from backend.app.services.brokers.factory import build_alpaca_broker_adapter, build_interactive_brokers_adapter


class BrokerFactoryTest(unittest.TestCase):
    def test_build_interactive_brokers_adapter_returns_simulator(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            adapter = build_interactive_brokers_adapter(
                config=InteractiveBrokersConfig(enabled=True),
                state_repository=BrokerStateRepository(Path(tmp_dir) / "ib.json"),
            )

            self.assertEqual(adapter.get_broker_name(), "interactive_brokers")

    def test_build_alpaca_adapter_defaults_to_simulator(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            adapter = build_alpaca_broker_adapter(
                config=AlpacaBrokerConfig(enabled=False),
                state_repository=BrokerStateRepository(Path(tmp_dir) / "alpaca.json"),
            )

            self.assertEqual(adapter.get_broker_name(), "alpaca")


if __name__ == "__main__":
    unittest.main()
