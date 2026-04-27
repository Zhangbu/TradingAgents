from __future__ import annotations

from backend.app.schemas.audit import AuditEventType
from backend.app.schemas.order import BrokerSyncResult, OrderStatus
from backend.app.services.audit_log_service import AuditLogService
from backend.app.services.automation_control_service import AutomationControlService
from backend.app.services.order_repository import OrderRepository
from backend.app.services.brokers.base import BrokerAdapter


class ReconciliationService:
    """Syncs local orders and account state with the currently active broker adapter."""

    def __init__(
        self,
        order_repository: OrderRepository,
        broker_adapter: BrokerAdapter,
        automation_control_service: AutomationControlService | None = None,
        audit_log_service: AuditLogService | None = None,
    ) -> None:
        self.order_repository = order_repository
        self.broker_adapter = broker_adapter
        self.automation_control_service = automation_control_service
        self.audit_log_service = audit_log_service

    def sync_order(self, order_id: str) -> BrokerSyncResult:
        order = self.order_repository.get(order_id)
        if order is None:
            raise ValueError("Order not found.")

        try:
            synced = self.broker_adapter.sync_order(order)
            self.order_repository.save(synced)
            snapshot = self.broker_adapter.get_account_snapshot()
        except Exception as exc:
            self._mark_sync_failure(f"Broker sync failed: {exc}")
            raise ValueError(f"Broker sync failed: {exc}") from exc

        result = BrokerSyncResult(
            synced_orders=[synced],
            account_snapshot=snapshot,
            matched_positions=snapshot.positions,
            unmatched_local_symbols=self._find_unmatched_local_symbols(snapshot),
            unmatched_broker_symbols=self._find_unmatched_broker_symbols(snapshot),
            cash_diff=0.0,
            equity_diff=0.0,
            requires_operator_review=bool(self._find_unmatched_local_symbols(snapshot) or self._find_unmatched_broker_symbols(snapshot)),
        )
        self._mark_sync_success()
        self._log_sync_events(order_id=order_id, result=result)
        return result

    def sync_all_orders(self, limit: int = 100) -> BrokerSyncResult:
        synced_orders = []
        try:
            for order in self.order_repository.list_orders(limit=limit):
                if order.status in {
                    OrderStatus.submitted,
                    OrderStatus.partially_filled,
                    OrderStatus.filled,
                    OrderStatus.cancel_requested,
                    OrderStatus.replace_requested,
                    OrderStatus.failed,
                }:
                    synced = self.broker_adapter.sync_order(order)
                    self.order_repository.save(synced)
                    synced_orders.append(synced)

            snapshot = self.broker_adapter.get_account_snapshot()
        except Exception as exc:
            self._mark_sync_failure(f"Broker sync failed: {exc}")
            raise ValueError(f"Broker sync failed: {exc}") from exc

        result = BrokerSyncResult(
            synced_orders=synced_orders,
            account_snapshot=snapshot,
            matched_positions=snapshot.positions,
            unmatched_local_symbols=self._find_unmatched_local_symbols(snapshot),
            unmatched_broker_symbols=self._find_unmatched_broker_symbols(snapshot),
            cash_diff=0.0,
            equity_diff=0.0,
            requires_operator_review=bool(self._find_unmatched_local_symbols(snapshot) or self._find_unmatched_broker_symbols(snapshot)),
        )
        self._mark_sync_success()
        self._log_sync_events(order_id="all", result=result)
        return result

    def _find_unmatched_local_symbols(self, snapshot) -> list[str]:
        local_symbols = {order.symbol for order in self.order_repository.list_orders(limit=500)}
        broker_symbols = {position.symbol for position in snapshot.positions}
        return sorted(local_symbols - broker_symbols)

    def _find_unmatched_broker_symbols(self, snapshot) -> list[str]:
        local_symbols = {order.symbol for order in self.order_repository.list_orders(limit=500)}
        broker_symbols = {position.symbol for position in snapshot.positions}
        return sorted(broker_symbols - local_symbols)

    def _mark_sync_failure(self, reason: str) -> None:
        if self.automation_control_service is not None:
            self.automation_control_service.mark_broker_sync_unhealthy(reason)

    def _mark_sync_success(self) -> None:
        if self.automation_control_service is not None:
            self.automation_control_service.record_broker_sync()
            self.automation_control_service.record_broker_success()

    def _log_sync_events(self, *, order_id: str, result: BrokerSyncResult) -> None:
        if self.audit_log_service is None:
            return

        self.audit_log_service.log(
            event_type=AuditEventType.broker_synced,
            entity_type="broker_sync",
            entity_id=order_id,
            actor="system",
            after=result,
            metadata={"synced_order_count": len(result.synced_orders)},
        )
        self.audit_log_service.log(
            event_type=AuditEventType.reconciliation_completed,
            entity_type="broker_sync",
            entity_id=order_id,
            actor="system",
            after=result,
            metadata={"requires_operator_review": result.requires_operator_review},
        )
