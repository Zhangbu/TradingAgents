from __future__ import annotations

from typing import Protocol

from backend.app.schemas.order import AccountSnapshot, OrderRecord


class BrokerAdapter(Protocol):
    """Protocol for broker adapters used by the execution layer."""

    def submit_order(self, order: OrderRecord) -> OrderRecord:
        ...

    def get_account_snapshot(self) -> AccountSnapshot:
        ...

    def sync_order(self, order: OrderRecord) -> OrderRecord:
        ...

    def get_broker_name(self) -> str:
        ...

    def cancel_order(self, order: OrderRecord) -> OrderRecord:
        ...

    def replace_order(self, order: OrderRecord, *, quantity: int | None, limit_price: float | None) -> OrderRecord:
        ...
