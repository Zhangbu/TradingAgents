import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from backend.app.schemas.broker import AlpacaBrokerConfig
from backend.app.services.analysis_runtime_service import AnalysisRuntimeService
from backend.app.services.automation_control_service import AutomationControlService
from backend.app.services.automation_state_repository import AutomationStateRepository
from backend.app.services.broker_diagnostics_service import BrokerDiagnosticsService
from backend.app.services.broker_state_repository import BrokerStateRepository
from backend.app.services.brokers.alpaca_paper import AlpacaPaperBrokerAdapter
from backend.app.services.preflight_service import PlatformPreflightService


class PlatformPreflightServiceTests(unittest.TestCase):
    def test_auto_workflow_blocked_when_auto_trading_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir, patch.dict(
            "os.environ",
            {
                "TRADINGAGENTS_LLM_PROVIDER": "deepseek",
                "DEEPSEEK_API_KEY": "test-key",
            },
            clear=False,
        ):
            base = Path(tmp_dir)
            automation_service = AutomationControlService(
                AutomationStateRepository(base / "automation" / "state.json")
            )
            broker_service = BrokerDiagnosticsService(
                alpaca_config=AlpacaBrokerConfig(enabled=False, paper_trading_mode="simulator"),
                broker_adapter=AlpacaPaperBrokerAdapter(BrokerStateRepository(base / "paper" / "state.json")),
                automation_control_service=automation_service,
            )
            service = PlatformPreflightService(
                analysis_runtime_service=AnalysisRuntimeService(),
                broker_diagnostics_service=broker_service,
            )

            summary = service.get_summary()

            self.assertTrue(summary.analysis.ready)
            self.assertTrue(summary.paper_manual.ready)
            self.assertEqual(summary.paper_manual.state, "warning")
            self.assertFalse(summary.paper_auto.ready)
            self.assertEqual(summary.paper_auto.state, "blocked")

    def test_manual_workflow_ready_when_sync_is_stale_but_healthy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir, patch.dict(
            "os.environ",
            {
                "TRADINGAGENTS_LLM_PROVIDER": "deepseek",
                "DEEPSEEK_API_KEY": "test-key",
            },
            clear=False,
        ):
            base = Path(tmp_dir)
            automation_service = AutomationControlService(
                AutomationStateRepository(base / "automation" / "state.json")
            )
            stale_time = datetime.now(timezone.utc) - timedelta(hours=1)
            automation_service.record_broker_sync(stale_time)
            broker_service = BrokerDiagnosticsService(
                alpaca_config=AlpacaBrokerConfig(enabled=False, paper_trading_mode="simulator"),
                broker_adapter=AlpacaPaperBrokerAdapter(BrokerStateRepository(base / "paper" / "state.json")),
                automation_control_service=automation_service,
            )
            service = PlatformPreflightService(
                analysis_runtime_service=AnalysisRuntimeService(),
                broker_diagnostics_service=broker_service,
            )

            summary = service.get_summary()

            self.assertTrue(summary.paper_manual.ready)
            self.assertEqual(summary.paper_manual.state, "warning")
            self.assertFalse(summary.paper_auto.ready)

    def test_manual_workflow_blocked_when_kill_switch_active(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir, patch.dict(
            "os.environ",
            {
                "TRADINGAGENTS_LLM_PROVIDER": "deepseek",
                "DEEPSEEK_API_KEY": "test-key",
            },
            clear=False,
        ):
            base = Path(tmp_dir)
            automation_service = AutomationControlService(
                AutomationStateRepository(base / "automation" / "state.json")
            )
            automation_service.activate_kill_switch("test")
            broker_service = BrokerDiagnosticsService(
                alpaca_config=AlpacaBrokerConfig(enabled=False, paper_trading_mode="simulator"),
                broker_adapter=AlpacaPaperBrokerAdapter(BrokerStateRepository(base / "paper" / "state.json")),
                automation_control_service=automation_service,
            )
            service = PlatformPreflightService(
                analysis_runtime_service=AnalysisRuntimeService(),
                broker_diagnostics_service=broker_service,
            )

            summary = service.get_summary()

            self.assertFalse(summary.paper_manual.ready)
            self.assertEqual(summary.paper_manual.state, "blocked")
