from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from backend.app.core.config import get_settings
from backend.app.schemas.order import (
    AccountSnapshot,
    ApprovalRequest,
    BrokerSyncResult,
    OrderCancelRequest,
    OrderCreateRequest,
    OrderListResponse,
    OrderRecord,
    OrderReplaceRequest,
)
from backend.app.services.broker_state_repository import BrokerStateRepository
from backend.app.services.automation_control_service import AutomationControlService
from backend.app.services.automation_state_repository import AutomationStateRepository
from backend.app.services.audit_log_repository import AuditLogRepository
from backend.app.services.audit_log_service import AuditLogService
from backend.app.services.brokers.factory import build_alpaca_broker_adapter, build_interactive_brokers_adapter
from backend.app.services.execution_service import ExecutionService
from backend.app.services.order_repository import OrderRepository
from backend.app.services.reconciliation_service import ReconciliationService
from backend.app.services.trade_intent_repository import TradeIntentRepository

router = APIRouter(prefix="/orders", tags=["orders"])

def get_repositories():
    settings = get_settings()
    trade_intent_repository = TradeIntentRepository(settings.trade_intents_dir)
    order_repository = OrderRepository(settings.orders_dir)
    return settings, trade_intent_repository, order_repository


def build_active_broker_adapter(*, broker_name: str, settings, alpaca_state_repository, ib_state_repository):
    if broker_name == "interactive_brokers":
        return build_interactive_brokers_adapter(
            config=settings.interactive_brokers,
            state_repository=ib_state_repository,
        )
    return build_alpaca_broker_adapter(
        config=settings.alpaca,
        state_repository=alpaca_state_repository,
    )


def build_execution_service(*, broker_name: str) -> ExecutionService:
    settings, trade_intent_repository, order_repository = get_repositories()
    alpaca_state_repository = BrokerStateRepository(settings.paper_broker_state_path)
    ib_state_repository = BrokerStateRepository(settings.data_dir / "paper_broker" / "ib_state.json")
    automation_repository = AutomationStateRepository(settings.automation_state_path)
    automation_service = AutomationControlService(repository=automation_repository)
    audit_service = AuditLogService(AuditLogRepository(settings.audit_logs_dir))
    broker_adapter = build_active_broker_adapter(
        broker_name=broker_name,
        settings=settings,
        alpaca_state_repository=alpaca_state_repository,
        ib_state_repository=ib_state_repository,
    )
    return ExecutionService(
        trade_intent_repository=trade_intent_repository,
        order_repository=order_repository,
        broker_adapter=broker_adapter,
        automation_control_service=automation_service,
        audit_log_service=audit_service,
    )


def build_reconciliation_service(*, broker_name: str) -> ReconciliationService:
    settings, _, order_repository = get_repositories()
    alpaca_state_repository = BrokerStateRepository(settings.paper_broker_state_path)
    ib_state_repository = BrokerStateRepository(settings.data_dir / "paper_broker" / "ib_state.json")
    automation_repository = AutomationStateRepository(settings.automation_state_path)
    automation_service = AutomationControlService(repository=automation_repository)
    audit_service = AuditLogService(AuditLogRepository(settings.audit_logs_dir))
    broker_adapter = build_active_broker_adapter(
        broker_name=broker_name,
        settings=settings,
        alpaca_state_repository=alpaca_state_repository,
        ib_state_repository=ib_state_repository,
    )
    return ReconciliationService(
        order_repository=order_repository,
        broker_adapter=broker_adapter,
        automation_control_service=automation_service,
        audit_log_service=audit_service,
    )


@router.post("", response_model=OrderRecord)
def create_order(request: OrderCreateRequest) -> OrderRecord:
    try:
        return build_execution_service(broker_name=request.broker_name.value).create_order(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{order_id}/approve", response_model=OrderRecord)
def approve_order(order_id: str, request: ApprovalRequest) -> OrderRecord:
    if request.order_id != order_id:
        raise HTTPException(status_code=400, detail="Path order_id must match request body.")
    try:
        _, _, order_repository = get_repositories()
        order = order_repository.get(order_id)
        if order is None:
            raise HTTPException(status_code=404, detail="Order not found")
        return build_execution_service(broker_name=order.broker_name.value).approve_order(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{order_id}/reject", response_model=OrderRecord)
def reject_order(order_id: str, request: ApprovalRequest) -> OrderRecord:
    if request.order_id != order_id:
        raise HTTPException(status_code=400, detail="Path order_id must match request body.")
    try:
        _, _, order_repository = get_repositories()
        order = order_repository.get(order_id)
        if order is None:
            raise HTTPException(status_code=404, detail="Order not found")
        return build_execution_service(broker_name=order.broker_name.value).reject_order(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{order_id}/cancel", response_model=OrderRecord)
def cancel_order(order_id: str, request: OrderCancelRequest) -> OrderRecord:
    try:
        _, _, order_repository = get_repositories()
        order = order_repository.get(order_id)
        if order is None:
            raise HTTPException(status_code=404, detail="Order not found")
        return build_execution_service(broker_name=order.broker_name.value).cancel_order(order_id, request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{order_id}/replace", response_model=OrderRecord)
def replace_order(order_id: str, request: OrderReplaceRequest) -> OrderRecord:
    try:
        _, _, order_repository = get_repositories()
        order = order_repository.get(order_id)
        if order is None:
            raise HTTPException(status_code=404, detail="Order not found")
        return build_execution_service(broker_name=order.broker_name.value).replace_order(order_id, request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("", response_model=OrderListResponse)
def list_orders(limit: int = Query(default=20, ge=1, le=200)) -> OrderListResponse:
    _, _, order_repository = get_repositories()
    return OrderListResponse(items=order_repository.list_orders(limit=limit))


@router.get("/accounts/paper", response_model=AccountSnapshot)
def get_paper_account(broker_name: str = Query(default="alpaca")) -> AccountSnapshot:
    try:
        return build_execution_service(broker_name=broker_name).get_account_snapshot()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/sync/all", response_model=BrokerSyncResult)
def sync_all_orders(broker_name: str = Query(default="alpaca")) -> BrokerSyncResult:
    try:
        return build_reconciliation_service(broker_name=broker_name).sync_all_orders()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/{order_id}/sync", response_model=BrokerSyncResult)
def sync_order(order_id: str) -> BrokerSyncResult:
    try:
        _, _, order_repository = get_repositories()
        order = order_repository.get(order_id)
        if order is None:
            raise HTTPException(status_code=404, detail="Order not found")
        return build_reconciliation_service(broker_name=order.broker_name.value).sync_order(order_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{order_id}", response_model=OrderRecord)
def get_order(order_id: str) -> OrderRecord:
    _, _, order_repository = get_repositories()
    order = order_repository.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return order
