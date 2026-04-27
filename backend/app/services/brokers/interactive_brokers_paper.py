from __future__ import annotations

from datetime import datetime, timezone

from backend.app.schemas.broker import BrokerPosition, InteractiveBrokersConfig
from backend.app.schemas.order import AccountSnapshot, OrderRecord, OrderStatus, PositionRecord
from backend.app.services.broker_state_repository import BrokerStateRepository


class InteractiveBrokersPaperBrokerAdapter:
    """Deterministic IB paper adapter for local testing until a live gateway client is added."""

    def __init__(
        self,
        config: InteractiveBrokersConfig,
        state_repository: BrokerStateRepository,
    ) -> None:
        self.config = config
        self.state_repository = state_repository

    def submit_order(self, order: OrderRecord) -> OrderRecord:
        state = self.state_repository.load()
        fill_price = order.requested_price or 100.0
        notional = fill_price * order.quantity

        if order.side == "buy":
            if notional > state.buying_power:
                order.status = OrderStatus.failed
                order.status_reason = "Insufficient buying power in IB paper account."
                order.updated_at = datetime.now(timezone.utc)
                order.broker_status_raw = "Rejected"
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

            order.status = OrderStatus.partially_filled if order.quantity > 1 else OrderStatus.filled
            order.filled_quantity = order.quantity // 2 if order.status == OrderStatus.partially_filled else order.quantity
        else:
            position = state.positions.get(order.symbol)
            if position is None or position.quantity < order.quantity:
                order.status = OrderStatus.failed
                order.status_reason = "Insufficient position quantity for IB sell order."
                order.updated_at = datetime.now(timezone.utc)
                order.broker_status_raw = "Rejected"
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
            order.status = OrderStatus.filled
            order.filled_quantity = order.quantity

        state.equity = state.cash + sum(
            item.quantity * item.average_price for item in state.positions.values()
        )
        state.buying_power = state.cash
        self.state_repository.save(state)

        order.broker_order_id = order.broker_order_id or f"ib-sim-{order.id}"
        order.filled_price = fill_price
        order.submitted_at = order.submitted_at or datetime.now(timezone.utc)
        if order.status == OrderStatus.filled:
            order.filled_at = datetime.now(timezone.utc)
        order.last_synced_at = datetime.now(timezone.utc)
        order.updated_at = datetime.now(timezone.utc)
        order.broker_status_raw = "Submitted" if order.status == OrderStatus.partially_filled else "Filled"
        return order

    def get_account_snapshot(self) -> AccountSnapshot:
        state = self.state_repository.load()
        return AccountSnapshot(
            cash=state.cash,
            equity=state.equity,
            buying_power=state.buying_power,
            positions=[
                PositionRecord(
                    symbol=position.symbol,
                    quantity=position.quantity,
                    average_price=position.average_price,
                    market_value=position.quantity * position.average_price,
                )
                for position in sorted(state.positions.values(), key=lambda item: item.symbol)
            ],
        )

    def sync_order(self, order: OrderRecord) -> OrderRecord:
        order.last_synced_at = datetime.now(timezone.utc)
        order.updated_at = datetime.now(timezone.utc)
        if order.status == OrderStatus.partially_filled:
            order.status = OrderStatus.filled
            order.filled_quantity = order.quantity
            order.filled_at = datetime.now(timezone.utc)
            order.broker_status_raw = "Filled"
        return order

    def get_broker_name(self) -> str:
        return "interactive_brokers"

    def cancel_order(self, order: OrderRecord) -> OrderRecord:
        order.status = OrderStatus.canceled
        order.canceled_at = datetime.now(timezone.utc)
        order.updated_at = datetime.now(timezone.utc)
        order.broker_status_raw = "Cancelled"
        return order

    def replace_order(self, order: OrderRecord, *, quantity: int | None, limit_price: float | None) -> OrderRecord:
        if quantity is not None:
            order.quantity = quantity
            order.remaining_quantity = max(order.quantity - order.filled_quantity, 0)
        if limit_price is not None:
            order.requested_price = limit_price
        order.status = OrderStatus.replaced
        order.updated_at = datetime.now(timezone.utc)
        order.broker_status_raw = "Replaced"
        return order
