from __future__ import annotations

from fastapi import APIRouter

from backend.app.core.config import get_settings
from backend.app.schemas.runtime import PlatformPreflightSummary
from backend.app.services.analysis_runtime_service import AnalysisRuntimeService
from backend.app.services.automation_control_service import AutomationControlService
from backend.app.services.automation_state_repository import AutomationStateRepository
from backend.app.services.broker_diagnostics_service import BrokerDiagnosticsService
from backend.app.services.broker_state_repository import BrokerStateRepository
from backend.app.services.brokers.factory import build_alpaca_broker_adapter
from backend.app.services.preflight_service import PlatformPreflightService

router = APIRouter(prefix="/diagnostics", tags=["diagnostics"])


def get_preflight_service() -> PlatformPreflightService:
    settings = get_settings()
    automation_service = AutomationControlService(
        repository=AutomationStateRepository(settings.automation_state_path)
    )
    broker_adapter = build_alpaca_broker_adapter(
        config=settings.alpaca,
        state_repository=BrokerStateRepository(settings.paper_broker_state_path),
    )
    broker_diagnostics = BrokerDiagnosticsService(
        alpaca_config=settings.alpaca,
        broker_adapter=broker_adapter,
        automation_control_service=automation_service,
    )
    return PlatformPreflightService(
        analysis_runtime_service=AnalysisRuntimeService(),
        broker_diagnostics_service=broker_diagnostics,
    )


@router.get("/preflight", response_model=PlatformPreflightSummary)
def get_preflight_summary() -> PlatformPreflightSummary:
    return get_preflight_service().get_summary()
