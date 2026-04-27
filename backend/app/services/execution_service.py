from __future__ import annotations

from datetime import datetime, timezone

from backend.app.schemas.order import (
    AccountSnapshot,
    ApprovalRequest,
    OrderCancelRequest,
    BrokerEnvironment,
    BrokerName,
    OrderCreateRequest,
    OrderReplaceRequest,
    OrderRecord,
    OrderStatus,
    OrderType,
)
from backend.app.schemas.analysis import PlatformMode
from backend.app.schemas.trade_intent import TradeIntentRecord, TradeIntentStatus
from backend.app.services.order_repository import OrderRepository
from backend.app.services.trade_intent_repository import TradeIntentRepository
from backend.app.services.automation_control_service import AutomationControlService
from backend.app.services.audit_log_service import AuditLogService
from backend.app.services.brokers.base import BrokerAdapter


class ExecutionService:
    """Creates paper orders from approved trade intents and manages lifecycle transitions."""

    def __init__(
        self,
        trade_intent_repository: TradeIntentRepository,
        order_repository: OrderRepository,
        broker_adapter: BrokerAdapter,
        automation_control_service: AutomationControlService | None = None,
        audit_log_service: AuditLogService | None = None,
    ) -> None:
        self.trade_intent_repository = trade_intent_repository
        self.order_repository = order_repository
        self.broker_adapter = broker_adapter
        self.automation_control_service = automation_control_service
        self.audit_log_service = audit_log_service

    def create_order(self, request: OrderCreateRequest) -> OrderRecord:
        intent = self.trade_intent_repository.get(request.intent_id)
        if intent is None:
            raise ValueError("Trade intent not found.")
        if intent.status == TradeIntentStatus.blocked:
            raise ValueError("Blocked trade intents cannot produce orders.")
        if intent.side == "hold":
            raise ValueError("Hold trade intents cannot produce executable orders.")
        if request.broker_environment == BrokerEnvironment.live and intent.mode != PlatformMode.live_manual:
            raise ValueError("Live execution requires a live_manual intent mode.")

        order = self._build_order(intent, request)
        self._assert_execution_allowed(
            is_auto=not order.approval_required,
            is_live=request.broker_environment == BrokerEnvironment.live,
            action_label="Order creation",
        )
        self.order_repository.save(order)

        if not order.approval_required:
            order = self._submit_order(order)

        saved = self.order_repository.save(order)
        self._log_event("order_created", saved.id, "system", after=saved)
        return saved

    def approve_order(self, approval: ApprovalRequest) -> OrderRecord:
        order = self.order_repository.get(approval.order_id)
        if order is None:
            raise ValueError("Order not found.")
        if order.status != OrderStatus.pending_approval:
            raise ValueError("Only pending approval orders can be approved.")

        before = order.model_copy(deep=True)
        self._assert_execution_allowed(
            is_auto=False,
            is_live=order.broker_environment == BrokerEnvironment.live,
            action_label="Order approval",
        )
        order.status = OrderStatus.approved
        order.status_reason = f"Approved by {approval.reviewer}"
        order.updated_at = datetime.now(timezone.utc)
        saved = self.order_repository.save(self._submit_order(order))
        self._log_event("order_approved", saved.id, approval.reviewer, before=before, after=saved)
        return saved

    def reject_order(self, approval: ApprovalRequest) -> OrderRecord:
        order = self.order_repository.get(approval.order_id)
        if order is None:
            raise ValueError("Order not found.")
        if order.status != OrderStatus.pending_approval:
            raise ValueError("Only pending approval orders can be rejected.")

        before = order.model_copy(deep=True)
        order.status = OrderStatus.rejected
        order.status_reason = self._build_rejection_reason(approval)
        order.updated_at = datetime.now(timezone.utc)
        saved = self.order_repository.save(order)
        self._log_event("order_rejected", saved.id, approval.reviewer, before=before, after=saved)
        return saved

    def cancel_order(self, order_id: str, request: OrderCancelRequest) -> OrderRecord:
        order = self.order_repository.get(order_id)
        if order is None:
            raise ValueError("Order not found.")
        if order.status not in {
            OrderStatus.submitted,
            OrderStatus.partially_filled,
            OrderStatus.filled,
            OrderStatus.approved,
            OrderStatus.replaced,
        }:
            raise ValueError("Only active orders can be canceled.")

        before = order.model_copy(deep=True)
        order.status = OrderStatus.cancel_requested
        order.cancel_requested_at = datetime.now(timezone.utc)
        order.updated_at = datetime.now(timezone.utc)
        try:
            canceled = self.broker_adapter.cancel_order(order)
        except Exception as exc:
            self._record_broker_failure(f"Broker cancel failed: {exc}")
            raise ValueError(f"Broker cancel failed: {exc}") from exc
        saved = self.order_repository.save(canceled)
        self._log_event("order_canceled", saved.id, request.reviewer, before=before, after=saved, metadata={"note": request.note or ""})
        return saved

    def replace_order(self, order_id: str, request: OrderReplaceRequest) -> OrderRecord:
        order = self.order_repository.get(order_id)
        if order is None:
            raise ValueError("Order not found.")
        if order.status not in {
            OrderStatus.submitted,
            OrderStatus.partially_filled,
            OrderStatus.filled,
            OrderStatus.approved,
            OrderStatus.replaced,
        }:
            raise ValueError("Only active orders can be replaced.")

        before = order.model_copy(deep=True)
        order.status = OrderStatus.replace_requested
        order.updated_at = datetime.now(timezone.utc)
        try:
            replaced = self.broker_adapter.replace_order(order, quantity=request.quantity, limit_price=request.limit_price)
        except Exception as exc:
            self._record_broker_failure(f"Broker replace failed: {exc}")
            raise ValueError(f"Broker replace failed: {exc}") from exc
        saved = self.order_repository.save(replaced)
        self._log_event("order_replaced", saved.id, request.reviewer, before=before, after=saved, metadata={"note": request.note or ""})
        return saved

    def get_order(self, order_id: str) -> OrderRecord | None:
        return self.order_repository.get(order_id)

    def list_orders(self, limit: int = 50) -> list[OrderRecord]:
        return self.order_repository.list_orders(limit=limit)

    def get_account_snapshot(self) -> AccountSnapshot:
        return self.broker_adapter.get_account_snapshot()

    def _build_order(self, intent: TradeIntentRecord, request: OrderCreateRequest) -> OrderRecord:
        quantity = max(int((100000.0 * intent.max_position_pct) / request.reference_price), 1)
        approval_required = intent.status == TradeIntentStatus.approval_required
        order_type = OrderType.limit if request.limit_price is not None else OrderType.market
        requested_price = request.limit_price or request.reference_price

        return OrderRecord(
            intent_id=intent.id,
            analysis_id=intent.analysis_id,
            symbol=intent.symbol,
            broker_name=request.broker_name,
            broker_environment=request.broker_environment,
            side=intent.side.value,
            order_type=order_type,
            quantity=quantity,
            remaining_quantity=quantity,
            requested_price=requested_price,
            status=OrderStatus.pending_approval if approval_required else OrderStatus.submitted,
            approval_required=approval_required,
            status_reason="Awaiting operator approval." if approval_required else "Submitted to broker.",
        )

    def _submit_order(self, order: OrderRecord) -> OrderRecord:
        order.status = OrderStatus.submitted
        order.submitted_at = datetime.now(timezone.utc)
        order.updated_at = datetime.now(timezone.utc)
        try:
            submitted = self.broker_adapter.submit_order(order)
        except Exception as exc:
            failed = order.model_copy(deep=True)
            failed.status = OrderStatus.failed
            failed.status_reason = f"Broker submission failed: {exc}"
            failed.last_synced_at = datetime.now(timezone.utc)
            failed.updated_at = datetime.now(timezone.utc)
            self._record_broker_failure(failed.status_reason)
            return self.order_repository.save(failed)
        if submitted.remaining_quantity is None:
            submitted.remaining_quantity = max(submitted.quantity - submitted.filled_quantity, 0)
        if submitted.filled_price is not None:
            submitted.average_fill_price = submitted.filled_price

        if submitted.status == OrderStatus.failed:
            self._record_broker_failure(submitted.status_reason or "Broker submission failed.")
        else:
            self._record_broker_success()

        return submitted

    def _build_rejection_reason(self, approval: ApprovalRequest) -> str:
        note = f": {approval.note}" if approval.note else ""
        return f"Rejected by {approval.reviewer}{note}"

    def _assert_execution_allowed(self, *, is_auto: bool, is_live: bool, action_label: str) -> None:
        if self.automation_control_service is None:
            return
        self.automation_control_service.assert_submission_allowed(
            is_auto=is_auto,
            is_live=is_live,
            action_label=action_label,
        )

    def _log_event(self, event_type: str, entity_id: str, actor: str, before=None, after=None, metadata=None) -> None:
        if self.audit_log_service is None:
            return
        from backend.app.schemas.audit import AuditEventType

        self.audit_log_service.log(
            event_type=AuditEventType(event_type),
            entity_type="order",
            entity_id=entity_id,
            actor=actor,
            before=before,
            after=after,
            metadata=metadata or {},
        )

    def _record_broker_failure(self, reason: str) -> None:
        if self.automation_control_service is None:
            return
        self.automation_control_service.record_broker_failure(reason)

    def _record_broker_success(self) -> None:
        if self.automation_control_service is None:
            return
        self.automation_control_service.record_broker_success()
