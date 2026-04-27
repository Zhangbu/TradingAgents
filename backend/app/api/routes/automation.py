from __future__ import annotations

from fastapi import APIRouter

from backend.app.core.config import get_settings
from backend.app.schemas.automation import (
    AutoTradingRequest,
    LiveTradingConfirmRequest,
    LiveTradingRequest,
    AutomationHealthSnapshot,
    AutomationState,
    BrokerSyncRequest,
    KillSwitchRequest,
    SchedulerUpdateRequest,
)
from backend.app.services.automation_control_service import AutomationControlService
from backend.app.services.automation_state_repository import AutomationStateRepository

router = APIRouter(prefix="/automation", tags=["automation"])


def get_automation_service() -> AutomationControlService:
    settings = get_settings()
    repository = AutomationStateRepository(settings.automation_state_path)
    return AutomationControlService(repository=repository)


@router.get("/state", response_model=AutomationState)
def get_automation_state() -> AutomationState:
    return get_automation_service().get_state()


@router.get("/health", response_model=AutomationHealthSnapshot)
def get_automation_health() -> AutomationHealthSnapshot:
    return get_automation_service().get_health_snapshot()


@router.post("/kill-switch/activate", response_model=AutomationState)
def activate_kill_switch(request: KillSwitchRequest) -> AutomationState:
    return get_automation_service().activate_kill_switch(request.reason)


@router.post("/kill-switch/release", response_model=AutomationState)
def release_kill_switch() -> AutomationState:
    return get_automation_service().release_kill_switch()


@router.post("/auto-trading", response_model=AutomationState)
def set_auto_trading(request: AutoTradingRequest) -> AutomationState:
    return get_automation_service().set_auto_trading(request.enabled)


@router.post("/live-trading", response_model=AutomationState)
def set_live_trading(request: LiveTradingRequest) -> AutomationState:
    return get_automation_service().set_live_trading(request)


@router.post("/live-trading/confirm", response_model=AutomationState)
def confirm_live_trading(request: LiveTradingConfirmRequest) -> AutomationState:
    return get_automation_service().confirm_live_trading(request)


@router.post("/broker-sync", response_model=AutomationState)
def record_broker_sync(request: BrokerSyncRequest) -> AutomationState:
    return get_automation_service().record_broker_sync(request.synced_at)


@router.post("/scheduler", response_model=AutomationState)
def update_scheduler(request: SchedulerUpdateRequest) -> AutomationState:
    return get_automation_service().update_scheduler(request)
