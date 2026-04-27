from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.app.core.config import get_settings
from backend.app.schemas.broker import AlpacaPaperReadiness, BrokerHealthCheckResult
from backend.app.services.automation_control_service import AutomationControlService
from backend.app.services.automation_state_repository import AutomationStateRepository
from backend.app.services.broker_diagnostics_service import BrokerDiagnosticsService
from backend.app.services.broker_state_repository import BrokerStateRepository
from backend.app.services.brokers.factory import build_alpaca_broker_adapter

router = APIRouter(prefix="/brokers", tags=["brokers"])


def build_broker_diagnostics_service() -> BrokerDiagnosticsService:
    settings = get_settings()
    automation_service = AutomationControlService(
        repository=AutomationStateRepository(settings.automation_state_path)
    )
    broker_adapter = build_alpaca_broker_adapter(
        config=settings.alpaca,
        state_repository=BrokerStateRepository(settings.paper_broker_state_path),
    )
    return BrokerDiagnosticsService(
        alpaca_config=settings.alpaca,
        broker_adapter=broker_adapter,
        automation_control_service=automation_service,
    )


@router.get("/alpaca/health", response_model=BrokerHealthCheckResult)
def get_alpaca_health() -> BrokerHealthCheckResult:
    return build_broker_diagnostics_service().get_alpaca_health()


@router.post("/alpaca/connect/test", response_model=BrokerHealthCheckResult)
def test_alpaca_connection() -> BrokerHealthCheckResult:
    result = build_broker_diagnostics_service().get_alpaca_health()
    if not result.configured:
        raise HTTPException(status_code=400, detail=result.message)
    if not result.connectivity_ok:
        raise HTTPException(status_code=502, detail=result.message)
    return result


@router.get("/alpaca/paper-readiness", response_model=AlpacaPaperReadiness)
def get_alpaca_paper_readiness() -> AlpacaPaperReadiness:
    return build_broker_diagnostics_service().get_alpaca_paper_readiness()
