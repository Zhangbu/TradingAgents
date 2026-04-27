import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from backend.app.schemas.automation import SchedulerUpdateRequest
from backend.app.services.automation_control_service import AutomationControlService
from backend.app.services.automation_state_repository import AutomationStateRepository


class AutomationControlServiceTest(unittest.TestCase):
    def test_health_snapshot_reports_effective_auto_when_healthy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            service = AutomationControlService(
                AutomationStateRepository(Path(tmp_dir) / "automation.json")
            )
            service.set_auto_trading(True)
            service.record_broker_sync(datetime.now(timezone.utc))

            snapshot = service.get_health_snapshot()

            self.assertTrue(snapshot.effective_auto_trading_enabled)
            self.assertFalse(snapshot.kill_switch_active)

    def test_stale_sync_disables_effective_auto_trading(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            service = AutomationControlService(
                AutomationStateRepository(Path(tmp_dir) / "automation.json")
            )
            service.set_auto_trading(True)
            stale_time = datetime.now(timezone.utc) - timedelta(hours=1)
            service.record_broker_sync(stale_time)

            snapshot = service.get_health_snapshot(now=datetime.now(timezone.utc))

            self.assertTrue(snapshot.broker_sync_stale)
            self.assertFalse(snapshot.effective_auto_trading_enabled)

    def test_broker_failures_activate_kill_switch_after_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            service = AutomationControlService(
                AutomationStateRepository(Path(tmp_dir) / "automation.json")
            )

            service.record_broker_failure("failure 1")
            service.record_broker_failure("failure 2")
            state = service.record_broker_failure("failure 3")

            self.assertTrue(state.kill_switch_active)
            self.assertEqual(state.kill_switch_reason, "failure 3")

    def test_scheduler_update_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            service = AutomationControlService(
                AutomationStateRepository(Path(tmp_dir) / "automation.json")
            )

            state = service.update_scheduler(
                SchedulerUpdateRequest(enabled=True, interval_minutes=15, target_mode="paper_auto")
            )

            self.assertTrue(state.scheduler.enabled)
            self.assertEqual(state.scheduler.interval_minutes, 15)

    def test_live_trading_requires_enable_then_confirm(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            service = AutomationControlService(
                AutomationStateRepository(Path(tmp_dir) / "automation.json")
            )
            service.record_broker_sync(datetime.now(timezone.utc))
            service.set_live_trading(
                type("Req", (), {"enabled": True, "actor": "alice", "reason": "manual live readiness"})()
            )
            state = service.confirm_live_trading(
                type("Req", (), {"actor": "alice"})()
            )
            snapshot = service.get_health_snapshot()

            self.assertTrue(state.live_trading_enabled)
            self.assertTrue(state.live_trading_double_confirmed)
            self.assertTrue(snapshot.effective_live_trading_enabled)


if __name__ == "__main__":
    unittest.main()
