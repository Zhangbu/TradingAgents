from __future__ import annotations

from backend.app.schemas.runtime import (
    AnalysisRuntimeHealth,
    PlatformPreflightSummary,
    RuntimeHealthCheck,
    RuntimeHealthState,
    WorkflowPreflight,
)
from backend.app.services.analysis_runtime_service import AnalysisRuntimeService
from backend.app.services.broker_diagnostics_service import BrokerDiagnosticsService


class PlatformPreflightService:
    """Aggregate runtime, broker, and automation readiness into workflow preflight gates."""

    def __init__(
        self,
        *,
        analysis_runtime_service: AnalysisRuntimeService,
        broker_diagnostics_service: BrokerDiagnosticsService,
    ) -> None:
        self.analysis_runtime_service = analysis_runtime_service
        self.broker_diagnostics_service = broker_diagnostics_service

    def get_summary(self) -> PlatformPreflightSummary:
        runtime_health = self.analysis_runtime_service.get_health()
        paper_readiness = self.broker_diagnostics_service.get_alpaca_paper_readiness()

        analysis = self._build_analysis_preflight(runtime_health)
        paper_manual = self._build_manual_preflight(runtime_health, paper_readiness)
        paper_auto = self._build_auto_preflight(runtime_health, paper_readiness)

        return PlatformPreflightSummary(
            analysis=analysis,
            paper_manual=paper_manual,
            paper_auto=paper_auto,
        )

    def _build_analysis_preflight(
        self,
        runtime_health: AnalysisRuntimeHealth,
    ) -> WorkflowPreflight:
        checks = [
            runtime_health.llm,
            runtime_health.market_data,
        ]
        return self._compose_workflow("analysis", checks)

    def _build_manual_preflight(
        self,
        runtime_health: AnalysisRuntimeHealth,
        paper_readiness,
    ) -> WorkflowPreflight:
        checks = [
            runtime_health.llm,
            runtime_health.market_data,
            RuntimeHealthCheck(
                component="broker_connectivity",
                state=(
                    RuntimeHealthState.healthy
                    if paper_readiness.broker_health.connectivity_ok
                    else RuntimeHealthState.blocked
                ),
                configured=paper_readiness.broker_health.configured,
                healthy=paper_readiness.broker_health.connectivity_ok,
                message=paper_readiness.broker_health.message,
                recommended_action=(
                    None
                    if paper_readiness.broker_health.connectivity_ok
                    else "Restore Alpaca paper connectivity or switch back to simulator mode."
                ),
            ),
            RuntimeHealthCheck(
                component="kill_switch",
                state=(
                    RuntimeHealthState.blocked
                    if paper_readiness.automation_health.kill_switch_active
                    else RuntimeHealthState.healthy
                ),
                configured=True,
                healthy=not paper_readiness.automation_health.kill_switch_active,
                message=(
                    "Kill switch is active."
                    if paper_readiness.automation_health.kill_switch_active
                    else "Kill switch is released."
                ),
                recommended_action=(
                    "Release the kill switch before creating or approving paper orders."
                    if paper_readiness.automation_health.kill_switch_active
                    else None
                ),
            ),
            RuntimeHealthCheck(
                component="broker_sync",
                state=(
                    RuntimeHealthState.blocked
                    if not paper_readiness.automation_health.broker_sync_healthy
                    else (
                        RuntimeHealthState.warning
                        if paper_readiness.automation_health.broker_sync_stale
                        else RuntimeHealthState.healthy
                    )
                ),
                configured=True,
                healthy=paper_readiness.automation_health.broker_sync_healthy,
                message=paper_readiness.automation_health.status_summary,
                recommended_action=(
                    "Restore broker sync health before paper execution."
                    if not paper_readiness.automation_health.broker_sync_healthy
                    else (
                        "Record a fresh broker sync before paper execution if you want up-to-date broker state."
                        if paper_readiness.automation_health.broker_sync_stale
                        else None
                    )
                ),
            ),
        ]
        return self._compose_workflow("paper_manual", checks)

    def _build_auto_preflight(
        self,
        runtime_health: AnalysisRuntimeHealth,
        paper_readiness,
    ) -> WorkflowPreflight:
        manual = self._build_manual_preflight(runtime_health, paper_readiness)
        checks = list(manual.checks)
        checks.append(
            RuntimeHealthCheck(
                component="auto_trading",
                state=(
                    RuntimeHealthState.healthy
                    if paper_readiness.automation_health.effective_auto_trading_enabled
                    else RuntimeHealthState.blocked
                ),
                configured=True,
                healthy=paper_readiness.automation_health.effective_auto_trading_enabled,
                message=(
                    "Auto trading is enabled for paper workflows."
                    if paper_readiness.automation_health.effective_auto_trading_enabled
                    else "Auto trading is disabled or blocked by automation guardrails."
                ),
                recommended_action=(
                    None
                    if paper_readiness.automation_health.effective_auto_trading_enabled
                    else "Enable auto trading and clear automation blockers before launching paper_auto."
                ),
            )
        )
        return self._compose_workflow("paper_auto", checks)

    def _compose_workflow(
        self,
        workflow: str,
        checks: list[RuntimeHealthCheck],
    ) -> WorkflowPreflight:
        blocker_count = sum(1 for check in checks if check.state == RuntimeHealthState.blocked)
        warning_count = sum(1 for check in checks if check.state == RuntimeHealthState.warning)
        if blocker_count:
            state = RuntimeHealthState.blocked
        elif warning_count:
            state = RuntimeHealthState.warning
        else:
            state = RuntimeHealthState.healthy

        return WorkflowPreflight(
            workflow=workflow,
            ready=blocker_count == 0,
            state=state,
            checks=checks,
            blocker_count=blocker_count,
            warning_count=warning_count,
        )
