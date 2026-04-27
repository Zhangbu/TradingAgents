from __future__ import annotations

from datetime import datetime, timezone

from backend.app.schemas.broker import BrokerPosition
from backend.app.schemas.order import AccountSnapshot, OrderRecord, OrderStatus, PositionRecord
from backend.app.services.broker_state_repository import BrokerStateRepository


class AlpacaPaperBrokerAdapter:
    """Deterministic Alpaca paper adapter used for local closed-loop testing."""

    def __init__(self, state_repository: BrokerStateRepository) -> None:
        self.state_repository = state_repository

    def submit_order(self, order: OrderRecord) -> OrderRecord:
        state = self.state_repository.load()
        fill_price = order.requested_price or 100.0
        notional = fill_price * order.quantity

        if order.side == "buy":
            if notional > state.buying_power:
                order.status = OrderStatus.failed
                order.status_reason = "Insufficient buying power in Alpaca paper account."
                order.updated_at = datetime.now(timezone.utc)
                return order

            state.cash -= notional
            position = state.positions.get(order.symbol)
            if position is None:
                state.positions[order.symbol] = BrokerPosition(
                    symbol=order.symbol,
                    quantity=order.quantity,
                    average_price=fill_price,
                )
            else:
                new_quantity = position.quantity + order.quantity
                average_price = ((position.quantity * position.average_price) + notional) / new_quantity
                state.positions[order.symbol] = BrokerPosition(
                    symbol=order.symbol,
                    quantity=new_quantity,
                    average_price=average_price,
                )
        else:
            position = state.positions.get(order.symbol)
            if position is None or position.quantity < order.quantity:
                order.status = OrderStatus.failed
                order.status_reason = "Insufficient position quantity for sell order."
                order.updated_at = datetime.now(timezone.utc)
                return order

            state.cash += notional
            remaining = position.quantity - order.quantity
            if remaining == 0:
                state.positions.pop(order.symbol, None)
            else:
                state.positions[order.symbol] = BrokerPosition(
                    symbol=order.symbol,
                    quantity=remaining,
                    average_price=position.average_price,
                )

        state.equity = self._calculate_equity(state)
        state.buying_power = state.cash
        self.state_repository.save(state)

        order.status = OrderStatus.filled
        order.filled_price = fill_price
        order.broker_order_id = order.broker_order_id or f"sim-{order.id}"
        order.submitted_at = order.submitted_at or datetime.now(timezone.utc)
        order.filled_at = datetime.now(timezone.utc)
        order.last_synced_at = datetime.now(timezone.utc)
        order.updated_at = datetime.now(timezone.utc)
        return order

    def get_account_snapshot(self) -> AccountSnapshot:
        state = self.state_repository.load()
        positions = [
            PositionRecord(
                symbol=position.symbol,
                quantity=position.quantity,
                average_price=position.average_price,
                market_value=position.quantity * position.average_price,
            )
            for position in sorted(state.positions.values(), key=lambda item: item.symbol)
        ]
        return AccountSnapshot(
            cash=state.cash,
            equity=state.equity,
            buying_power=state.buying_power,
            positions=positions,
        )

    def _calculate_equity(self, state) -> float:
        return state.cash + sum(
            position.quantity * position.average_price for position in state.positions.values()
        )

    def sync_order(self, order: OrderRecord) -> OrderRecord:
        order.last_synced_at = datetime.now(timezone.utc)
        order.updated_at = datetime.now(timezone.utc)
        order.filled_quantity = order.quantity if order.status == OrderStatus.filled else order.filled_quantity
        order.broker_status_raw = "filled" if order.status == OrderStatus.filled else order.broker_status_raw
        return order

    def get_broker_name(self) -> str:
        return "alpaca"

    def cancel_order(self, order: OrderRecord) -> OrderRecord:
        order.status = OrderStatus.canceled
        order.canceled_at = datetime.now(timezone.utc)
        order.updated_at = datetime.now(timezone.utc)
        order.broker_status_raw = "canceled"
        return order

    def replace_order(self, order: OrderRecord, *, quantity: int | None, limit_price: float | None) -> OrderRecord:
        if quantity is not None:
            order.quantity = quantity
            order.remaining_quantity = max(order.quantity - order.filled_quantity, 0)
        if limit_price is not None:
            order.requested_price = limit_price
        order.status = OrderStatus.replaced
        order.updated_at = datetime.now(timezone.utc)
        order.broker_status_raw = "replaced"
        return order
