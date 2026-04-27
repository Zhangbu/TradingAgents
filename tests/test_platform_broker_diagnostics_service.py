import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from backend.app.schemas.broker import AlpacaBrokerConfig
from backend.app.services.automation_control_service import AutomationControlService
from backend.app.services.automation_state_repository import AutomationStateRepository
from backend.app.services.broker_diagnostics_service import BrokerDiagnosticsService
from backend.app.services.broker_state_repository import BrokerStateRepository
from backend.app.services.brokers.alpaca_api import AlpacaApiPaperBrokerAdapter
from backend.app.services.brokers.alpaca_paper import AlpacaPaperBrokerAdapter
from tests.test_platform_alpaca_api_adapter import FakeSession


class BrokerDiagnosticsServiceTest(unittest.TestCase):
    def test_simulator_mode_reports_local_health(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            automation_service = AutomationControlService(
                AutomationStateRepository(base / "automation" / "state.json")
            )
            service = BrokerDiagnosticsService(
                alpaca_config=AlpacaBrokerConfig(enabled=False, paper_trading_mode="simulator"),
                broker_adapter=AlpacaPaperBrokerAdapter(BrokerStateRepository(base / "paper" / "state.json")),
                automation_control_service=automation_service,
            )

            result = service.get_alpaca_health()

            self.assertTrue(result.connectivity_ok)
            self.assertEqual(result.integration_mode, "simulator")
            self.assertFalse(result.configured)

    def test_api_mode_reports_remote_connectivity_and_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            automation_service = AutomationControlService(
                AutomationStateRepository(base / "automation" / "state.json")
            )
            automation_service.record_broker_sync(datetime.now(timezone.utc))
            automation_service.set_auto_trading(True)
            adapter = AlpacaApiPaperBrokerAdapter(
                config=AlpacaBrokerConfig(
                    enabled=True,
                    paper_trading_mode="api",
                    api_key="key",
                    secret_key="secret",
                ),
                session=FakeSession(),
            )
            service = BrokerDiagnosticsService(
                alpaca_config=AlpacaBrokerConfig(
                    enabled=True,
                    paper_trading_mode="api",
                    api_key="key",
                    secret_key="secret",
                ),
                broker_adapter=adapter,
                automation_control_service=automation_service,
            )

            result = service.get_alpaca_paper_readiness()

            self.assertTrue(result.broker_health.connectivity_ok)
            self.assertTrue(result.manual_ready)
            self.assertTrue(result.auto_ready)
            self.assertIn("Auto Alpaca paper flow is ready.", result.checklist)


if __name__ == "__main__":
    unittest.main()
