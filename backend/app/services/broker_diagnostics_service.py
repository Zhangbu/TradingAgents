from __future__ import annotations

from backend.app.schemas.broker import AlpacaBrokerConfig, AlpacaPaperReadiness, BrokerHealthCheckResult
from backend.app.services.automation_control_service import AutomationControlService
from backend.app.services.brokers.base import BrokerAdapter


class BrokerDiagnosticsService:
    """Computes broker connectivity and paper workflow readiness snapshots."""

    def __init__(
        self,
        *,
        alpaca_config: AlpacaBrokerConfig,
        broker_adapter: BrokerAdapter,
        automation_control_service: AutomationControlService,
    ) -> None:
        self.alpaca_config = alpaca_config
        self.broker_adapter = broker_adapter
        self.automation_control_service = automation_control_service

    def get_alpaca_health(self) -> BrokerHealthCheckResult:
        credentials_present = bool(self.alpaca_config.api_key and self.alpaca_config.secret_key)
        if not self.alpaca_config.enabled or self.alpaca_config.paper_trading_mode != "api":
            return BrokerHealthCheckResult(
                broker_name="alpaca",
                environment="paper",
                integration_mode=self.alpaca_config.paper_trading_mode,
                configured=False,
                credentials_present=credentials_present,
                connectivity_ok=True,
                message="Alpaca paper simulator mode is active. Remote API connectivity is not required.",
                base_url=self.alpaca_config.base_url,
            )

        if not credentials_present:
            return BrokerHealthCheckResult(
                broker_name="alpaca",
                environment="paper",
                integration_mode="api",
                configured=False,
                credentials_present=False,
                connectivity_ok=False,
                message="Alpaca API mode is enabled, but credentials are missing.",
                base_url=self.alpaca_config.base_url,
            )

        try:
            account_snapshot = self.broker_adapter.get_account_snapshot()
        except Exception as exc:
            return BrokerHealthCheckResult(
                broker_name="alpaca",
                environment="paper",
                integration_mode="api",
                configured=True,
                credentials_present=True,
                connectivity_ok=False,
                message=f"Alpaca paper connectivity check failed: {exc}",
                base_url=self.alpaca_config.base_url,
            )

        return BrokerHealthCheckResult(
            broker_name="alpaca",
            environment="paper",
            integration_mode="api",
            configured=True,
            credentials_present=True,
            connectivity_ok=True,
            message="Alpaca paper connectivity check succeeded.",
            base_url=self.alpaca_config.base_url,
            account_snapshot=account_snapshot,
        )

    def get_alpaca_paper_readiness(self) -> AlpacaPaperReadiness:
        broker_health = self.get_alpaca_health()
        automation_health = self.automation_control_service.get_health_snapshot()

        checklist: list[str] = []
        if not broker_health.connectivity_ok:
            checklist.append("Fix Alpaca paper connectivity or switch back to simulator mode.")
        if automation_health.kill_switch_active:
            checklist.append("Release the kill switch before creating or approving Alpaca paper orders.")
        if not automation_health.broker_sync_healthy:
            checklist.append("Restore broker sync health before using paper execution.")
        if automation_health.broker_sync_stale:
            checklist.append("Record a fresh broker sync for a more up-to-date broker snapshot.")
        if not automation_health.auto_trading_enabled:
            checklist.append("Enable auto trading if you want the paper_auto flow to submit automatically.")

        manual_ready = (
            broker_health.connectivity_ok
            and not automation_health.kill_switch_active
            and automation_health.broker_sync_healthy
        )
        auto_ready = manual_ready and automation_health.effective_auto_trading_enabled

        if manual_ready and not checklist:
            checklist.append("Manual Alpaca paper flow is ready.")
        if auto_ready:
            checklist.append("Auto Alpaca paper flow is ready.")

        return AlpacaPaperReadiness(
            broker_health=broker_health,
            automation_health=automation_health,
            manual_ready=manual_ready,
            auto_ready=auto_ready,
            checklist=checklist,
        )
