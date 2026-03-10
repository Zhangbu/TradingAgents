"""Paper trading exchange implementation for testing."""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List, Callable, Awaitable
import asyncio

from tradingagents.execution.base_exchange import (
    BaseExchange,
    Order,
    OrderRequest,
    Position,
    Ticker,
    Balance,
    AccountInfo,
    OrderType,
    OrderSide,
    OrderStatus,
    TimeInForce,
    ExchangeError,
    InsufficientFundsError,
)


class PaperExchange(BaseExchange):
    """Paper trading exchange for testing without real money.
    
    Simulates order execution with configurable slippage and latency.
    Useful for strategy testing and development.
    """
    
    def __init__(
        self,
        initial_balance: float = 100000.0,
        balance_currency: str = "USDT",
        slippage_percent: float = 0.01,
        latency_ms: int = 100,
        fee_percent: float = 0.001,  # 0.1% default fee
        callback: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None,
    ):
        """Initialize paper exchange.
        
        Args:
            initial_balance: Starting balance in base currency
            balance_currency: Base currency symbol
            slippage_percent: Simulated slippage percentage (default 0.01%)
            latency_ms: Simulated execution latency in milliseconds
            fee_percent: Trading fee percentage (default 0.1%)
            callback: Optional async callback for events
        """
        super().__init__("paper", callback)
        
        self.initial_balance = initial_balance
        self.balance_currency = balance_currency
        self.slippage_percent = slippage_percent
        self.latency_ms = latency_ms
        self.fee_percent = fee_percent
        
        # Simulated state
        self._balances: Dict[str, Balance] = {
            balance_currency: Balance(
                asset=balance_currency,
                free=initial_balance,
                used=0.0,
                total=initial_balance,
            )
        }
        self._orders: Dict[str, Order] = {}
        self._positions: Dict[str, Position] = {}
        self._prices: Dict[str, float] = {}
        self._order_counter = 0
    
    async def connect(self) -> bool:
        """Connect to the paper exchange (always succeeds)."""
        self._connected = True
        await self._emit_callback("connected", {"status": "connected"})
        return True
    
    async def disconnect(self) -> None:
        """Disconnect from the paper exchange."""
        self._connected = False
        await self._emit_callback("disconnected", {"status": "disconnected"})
    
    def set_price(self, symbol: str, price: float) -> None:
        """Set the current price for a symbol.
        
        This is used to simulate price updates for paper trading.
        
        Args:
            symbol: Trading pair symbol
            price: Current price
        """
        self._prices[symbol] = price
    
    def update_price(self, symbol: str, price: float) -> None:
        """Update price and recalculate position PnL.
        
        Args:
            symbol: Trading pair symbol
            price: New price
        """
        self._prices[symbol] = price
        
        # Update position PnL if exists
        if symbol in self._positions:
            position = self._positions[symbol]
            position.current_price = price
            if position.side == "long":
                position.unrealized_pnl = (price - position.entry_price) * position.quantity
                position.unrealized_pnl_percent = ((price - position.entry_price) / position.entry_price) * 100
            else:
                position.unrealized_pnl = (position.entry_price - price) * position.quantity
                position.unrealized_pnl_percent = ((position.entry_price - price) / position.entry_price) * 100
    
    async def get_account_info(self) -> AccountInfo:
        """Get account information."""
        balances = list(self._balances.values())
        
        # Calculate total equity including unrealized PnL
        total_equity = self._balances.get(self.balance_currency, Balance(self.balance_currency, 0, 0, 0)).total
        unrealized_pnl = sum(p.unrealized_pnl for p in self._positions.values())
        total_equity += unrealized_pnl
        
        margin_used = sum(p.quantity * p.entry_price for p in self._positions.values())
        available_margin = total_equity - margin_used
        
        return AccountInfo(
            balances=balances,
            total_equity=total_equity,
            available_margin=available_margin,
            margin_used=margin_used,
            unrealized_pnl=unrealized_pnl,
            realized_pnl=total_equity - self.initial_balance,
        )
    
    async def get_ticker(self, symbol: str) -> Ticker:
        """Get ticker for a symbol."""
        price = self._prices.get(symbol, 100.0)  # Default price if not set
        
        return Ticker(
            symbol=symbol,
            last_price=price,
            bid_price=price * (1 - self.slippage_percent / 100),
            ask_price=price * (1 + self.slippage_percent / 100),
            high_24h=price * 1.05,
            low_24h=price * 0.95,
            volume_24h=1000000,
        )
    
    async def get_positions(self) -> List[Position]:
        """Get all open positions."""
        return list(self._positions.values())
    
    async def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for a specific symbol."""
        return self._positions.get(symbol)
    
    async def place_order(self, request: OrderRequest) -> Order:
        """Place an order.
        
        For paper trading, market orders are immediately filled with simulated
        slippage. Limit orders remain open until filled manually or cancelled.
        """
        if not self._connected:
            raise ExchangeError("Exchange not connected")
        
        # Simulate latency
        await asyncio.sleep(self.latency_ms / 1000)
        
        # Generate order ID
        self._order_counter += 1
        order_id = f"paper_{self._order_counter}_{uuid.uuid4().hex[:8]}"
        
        # Get current price
        current_price = self._prices.get(request.symbol, 100.0)
        
        # Calculate fill price with slippage
        if request.order_type == OrderType.MARKET:
            slippage = self.slippage_percent / 100
            if request.side == OrderSide.BUY:
                fill_price = current_price * (1 + slippage)
            else:
                fill_price = current_price * (1 - slippage)
            
            # Check balance for buy orders
            if request.side == OrderSide.BUY:
                required = request.quantity * fill_price
                balance = self._balances.get(self.balance_currency)
                if not balance or balance.free < required:
                    raise InsufficientFundsError(
                        f"Insufficient {self.balance_currency}. Required: {required}, Available: {balance.free if balance else 0}"
                    )
                
                # Deduct balance
                balance.free -= required
                balance.used += required
                
                # Add to asset balance
                asset = request.symbol.split("/")[0] if "/" in request.symbol else request.symbol
                if asset not in self._balances:
                    self._balances[asset] = Balance(asset=asset, free=0, used=0, total=0)
                self._balances[asset].free += request.quantity
                self._balances[asset].total += request.quantity
            
            else:  # SELL
                asset = request.symbol.split("/")[0] if "/" in request.symbol else request.symbol
                asset_balance = self._balances.get(asset)
                if not asset_balance or asset_balance.free < request.quantity:
                    raise InsufficientFundsError(
                        f"Insufficient {asset}. Required: {request.quantity}, Available: {asset_balance.free if asset_balance else 0}"
                    )
                
                # Deduct asset
                asset_balance.free -= request.quantity
                asset_balance.total -= request.quantity
                
                # Add to base currency
                proceeds = request.quantity * fill_price
                self._balances[self.balance_currency].free += proceeds
                self._balances[self.balance_currency].total += proceeds
            
            # Calculate fees
            fees = request.quantity * fill_price * self.fee_percent
            
            # Create filled order
            order = Order(
                id=order_id,
                symbol=request.symbol,
                side=request.side,
                quantity=request.quantity,
                order_type=request.order_type,
                status=OrderStatus.FILLED,
                price=fill_price,
                filled_quantity=request.quantity,
                average_fill_price=fill_price,
                fees=fees,
                client_order_id=request.client_order_id,
                exchange_order_id=order_id,
                time_in_force=request.time_in_force,
                metadata=request.metadata,
            )
            
            # Update or create position
            await self._update_position(request.symbol, request.side, request.quantity, fill_price)
            
        else:  # LIMIT order
            # Create open order
            order = Order(
                id=order_id,
                symbol=request.symbol,
                side=request.side,
                quantity=request.quantity,
                order_type=request.order_type,
                status=OrderStatus.OPEN,
                price=request.price,
                client_order_id=request.client_order_id,
                exchange_order_id=order_id,
                time_in_force=request.time_in_force,
                metadata=request.metadata,
            )
        
        self._orders[order_id] = order
        
        # Emit callback
        await self._emit_callback("order_update", {
            "order_id": order_id,
            "status": order.status.value,
            "filled_quantity": order.filled_quantity,
            "average_price": order.average_fill_price,
        })
        
        return order
    
    async def _update_position(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        price: float,
    ) -> None:
        """Update position after order fill."""
        position = self._positions.get(symbol)
        
        if position:
            if side == OrderSide.BUY:
                # Add to position
                new_quantity = position.quantity + quantity
                new_entry = (position.entry_price * position.quantity + price * quantity) / new_quantity
                position.quantity = new_quantity
                position.entry_price = new_entry
            else:
                # Reduce position
                position.quantity -= quantity
                if position.quantity <= 0:
                    del self._positions[symbol]
        else:
            # Create new position
            position_side = "long" if side == OrderSide.BUY else "short"
            self._positions[symbol] = Position(
                symbol=symbol,
                side=position_side,
                quantity=quantity,
                entry_price=price,
                current_price=price,
            )
        
        await self._emit_callback("position_update", {
            "symbol": symbol,
            "side": position.side if position else None,
            "quantity": position.quantity if position else 0,
        })
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order."""
        order = self._orders.get(order_id)
        if not order:
            return False
        
        if order.status not in [OrderStatus.OPEN, OrderStatus.PENDING]:
            return False
        
        order.status = OrderStatus.CANCELLED
        order.updated_at = datetime.utcnow()
        
        await self._emit_callback("order_update", {
            "order_id": order_id,
            "status": "cancelled",
        })
        
        return True
    
    async def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID."""
        return self._orders.get(order_id)
    
    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """Get all open orders."""
        orders = [
            order for order in self._orders.values()
            if order.status in [OrderStatus.OPEN, OrderStatus.PENDING]
        ]
        if symbol:
            orders = [o for o in orders if o.symbol == symbol]
        return orders
    
    def reset(self) -> None:
        """Reset paper exchange to initial state."""
        self._balances = {
            self.balance_currency: Balance(
                asset=self.balance_currency,
                free=self.initial_balance,
                used=0.0,
                total=self.initial_balance,
            )
        }
        self._orders = {}
        self._positions = {}
        self._prices = {}
        self._order_counter = 0
    
    def get_trade_summary(self) -> Dict[str, Any]:
        """Get summary of all paper trading activity."""
        account = asyncio.run(self.get_account_info())
        
        total_trades = len([o for o in self._orders.values() if o.status == OrderStatus.FILLED])
        winning_trades = len([p for p in self._positions.values() if p.unrealized_pnl > 0])
        losing_trades = len([p for p in self._positions.values() if p.unrealized_pnl <= 0])
        
        return {
            "initial_balance": self.initial_balance,
            "current_equity": account.total_equity,
            "total_pnl": account.total_equity - self.initial_balance,
            "total_pnl_percent": ((account.total_equity - self.initial_balance) / self.initial_balance) * 100,
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": winning_trades / total_trades if total_trades > 0 else 0,
            "open_positions": len(self._positions),
            "realized_pnl": account.realized_pnl,
            "unrealized_pnl": account.unrealized_pnl,
        }