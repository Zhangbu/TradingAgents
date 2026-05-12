from __future__ import annotations

from backend.app.schemas.analysis import FailureDetails
from backend.app.schemas.audit import AuditEventType
from backend.app.schemas.order import BrokerSyncResult, OrderStatus, ReconciliationDiff
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
            failure_details = self._build_failure_details(
                code="broker_sync_failed",
                component="reconciliation",
                category="broker",
                retryable=True,
                message=f"Broker sync failed: {exc}",
                recommended_action=(
                    "Retry sync after checking broker connectivity, then review the "
                    "order trail if the failure persists."
                ),
                raw_message=str(exc),
            )
            failed_order = order.model_copy(deep=True)
            failed_order.failure_details = failure_details
            failed_order.status_reason = failure_details.message
            self.order_repository.save(failed_order)
            self._mark_sync_failure(failure_details.message)
            raise ValueError(f"Broker sync failed: {exc}") from exc

        order_diffs = self._build_order_diffs([synced])
        position_diffs = self._build_position_diffs(snapshot)
        account_diffs = self._build_account_diffs(snapshot)
        result = BrokerSyncResult(
            synced_orders=[synced],
            account_snapshot=snapshot,
            matched_positions=snapshot.positions,
            unmatched_local_symbols=self._find_unmatched_local_symbols(snapshot),
            unmatched_broker_symbols=self._find_unmatched_broker_symbols(snapshot),
            order_diffs=order_diffs,
            position_diffs=position_diffs,
            account_diffs=account_diffs,
            cash_diff=0.0,
            equity_diff=0.0,
            requires_operator_review=bool(
                self._find_unmatched_local_symbols(snapshot)
                or self._find_unmatched_broker_symbols(snapshot)
                or order_diffs
                or account_diffs
            ),
            summary_message=self._build_summary_message(snapshot),
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

        order_diffs = self._build_order_diffs(synced_orders)
        position_diffs = self._build_position_diffs(snapshot)
        account_diffs = self._build_account_diffs(snapshot)
        result = BrokerSyncResult(
            synced_orders=synced_orders,
            account_snapshot=snapshot,
            matched_positions=snapshot.positions,
            unmatched_local_symbols=self._find_unmatched_local_symbols(snapshot),
            unmatched_broker_symbols=self._find_unmatched_broker_symbols(snapshot),
            order_diffs=order_diffs,
            position_diffs=position_diffs,
            account_diffs=account_diffs,
            cash_diff=0.0,
            equity_diff=0.0,
            requires_operator_review=bool(
                self._find_unmatched_local_symbols(snapshot)
                or self._find_unmatched_broker_symbols(snapshot)
                or order_diffs
                or account_diffs
            ),
            summary_message=self._build_summary_message(snapshot),
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

    def _build_summary_message(self, snapshot) -> str:
        unmatched_local = self._find_unmatched_local_symbols(snapshot)
        unmatched_broker = self._find_unmatched_broker_symbols(snapshot)
        if unmatched_local or unmatched_broker:
            return (
                "Reconciliation completed with mismatches. Review unmatched local and "
                "broker symbols before trusting the account state."
            )
        return "Reconciliation completed without symbol mismatches."

    def _build_order_diffs(self, orders) -> list[ReconciliationDiff]:
        diffs: list[ReconciliationDiff] = []
        for order in orders:
            if order.failure_details is not None:
                diffs.append(
                    ReconciliationDiff(
                        category="order",
                        field="failure_details",
                        severity="critical",
                        local_value=order.status.value,
                        broker_value=order.broker_status_raw,
                        message=order.failure_details.message,
                    )
                )
            elif order.broker_status_raw and order.status.value != order.broker_status_raw:
                diffs.append(
                    ReconciliationDiff(
                        category="order",
                        field="status",
                        severity="warning",
                        local_value=order.status.value,
                        broker_value=order.broker_status_raw,
                        message=(
                            f"Local order status is {order.status.value} while the broker "
                            f"reports {order.broker_status_raw}."
                        ),
                    )
                )
        return diffs

    def _build_position_diffs(self, snapshot) -> list[ReconciliationDiff]:
        diffs: list[ReconciliationDiff] = []
        for symbol in self._find_unmatched_local_symbols(snapshot):
            diffs.append(
                ReconciliationDiff(
                    category="position",
                    field="symbol",
                    severity="warning",
                    local_value=symbol,
                    broker_value=None,
                    message=f"{symbol} exists in local order history but not in broker positions.",
                )
            )
        for symbol in self._find_unmatched_broker_symbols(snapshot):
            diffs.append(
                ReconciliationDiff(
                    category="position",
                    field="symbol",
                    severity="warning",
                    local_value=None,
                    broker_value=symbol,
                    message=f"{symbol} exists in broker positions but not in local order history.",
                )
            )
        return diffs

    def _build_account_diffs(self, snapshot) -> list[ReconciliationDiff]:
        diffs: list[ReconciliationDiff] = []
        if snapshot.cash < 0:
            diffs.append(
                ReconciliationDiff(
                    category="account",
                    field="cash",
                    severity="warning",
                    local_value=snapshot.cash,
                    broker_value=snapshot.cash,
                    message="Account cash is negative after sync and should be reviewed.",
                )
            )
        if snapshot.buying_power < 0:
            diffs.append(
                ReconciliationDiff(
                    category="account",
                    field="buying_power",
                    severity="warning",
                    local_value=snapshot.buying_power,
                    broker_value=snapshot.buying_power,
                    message="Buying power is negative after sync and should be reviewed.",
                )
            )
        return diffs

    def _build_failure_details(
        self,
        *,
        code: str,
        component: str,
        category: str,
        retryable: bool,
        message: str,
        recommended_action: str,
        raw_message: str,
    ) -> FailureDetails:
        return FailureDetails(
            code=code,
            component=component,
            category=category,
            retryable=retryable,
            message=message,
            recommended_action=recommended_action,
            raw_message=raw_message,
        )

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
