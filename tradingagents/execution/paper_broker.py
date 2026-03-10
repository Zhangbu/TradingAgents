"""
Paper Trading Broker - Simulated trading without real execution.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import os

from .base_broker import (
    BaseBroker,
    Order,
    OrderResult,
    OrderSide,
    OrderType,
    OrderStatus,
    Position,
    AccountInfo,
    MarketData,
)

logger = logging.getLogger(__name__)


class PaperBroker(BaseBroker):
    """
    Paper Trading Broker - Simulates trading without real execution.
    
    Features:
    - Simulates order execution at current market prices
    - Supports limit and stop orders
    - Persistent state storage
    - Trade history tracking
    - Commission and slippage simulation
    """
    
    def __init__(
        self,
        initial_capital: float = 100000,
        data_dir: str = "data/paper_trading",
        commission_rate: float = 0.001,  # 0.1%
        slippage_rate: float = 0.0005,   # 0.05%
        leverage: float = 1.0,
    ):
        """
        Initialize paper trading broker.
        
        Args:
            initial_capital: Starting cash amount
            data_dir: Directory for state persistence
            commission_rate: Commission rate per trade
            slippage_rate: Slippage rate for execution
            leverage: Buying power leverage multiplier
        """
        super().__init__(name="PaperBroker")
        
        self.initial_capital = initial_capital
        self.data_dir = Path(data_dir)
        self.commission_rate = commission_rate
        self.slippage_rate = slippage_rate
        self.leverage = leverage
        
        # State
        self.cash = initial_capital
        self.positions: Dict[str, Position] = {}
        self.orders: Dict[str, Order] = {}
        self.trade_history: List[Dict] = []
        self.order_counter = 0
        
        # Ensure data directory exists
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Load existing state
        self._load_state()
    
    def connect(self) -> bool:
        """Connect to broker (always succeeds for paper trading)"""
        self._connected = True
        logger.info(f"Connected to PaperBroker with ${self.cash:,.2f} cash")
        return True
    
    def disconnect(self) -> bool:
        """Disconnect and save state"""
        self._save_state()
        self._connected = False
        logger.info("Disconnected from PaperBroker")
        return True
    
    def get_account(self) -> AccountInfo:
        """Get account information"""
        total_position_value = sum(p.market_value for p in self.positions.values())
        total_value = self.cash + total_position_value
        
        return AccountInfo(
            cash=self.cash,
            total_value=total_value,
            buying_power=self.cash * self.leverage,
            positions=list(self.positions.values()),
            account_id="paper_account",
        )
    
    def get_positions(self) -> List[Position]:
        """Get all positions"""
        # Update prices before returning
        for symbol, position in self.positions.items():
            try:
                current_price = self._get_current_price(symbol)
                position.update_price(current_price)
            except Exception as e:
                logger.warning(f"Failed to update price for {symbol}: {e}")
        
        return list(self.positions.values())
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for a specific symbol"""
        position = self.positions.get(symbol)
        if position:
            try:
                current_price = self._get_current_price(symbol)
                position.update_price(current_price)
            except Exception as e:
                logger.warning(f"Failed to update price for {symbol}: {e}")
        return position
    
    def place_order(self, order: Order) -> OrderResult:
        """
        Place an order.
        
        For paper trading, market orders are executed immediately at
        the current price (with slippage). Limit and stop orders are
        stored for later execution.
        """
        if not self._connected:
            return OrderResult(
                success=False,
                order_id="",
                filled_price=0,
                filled_quantity=0,
                message="Not connected to broker",
            )
        
        # Generate order ID
        self.order_counter += 1
        order.order_id = f"paper_{self.order_counter}"
        order.status = OrderStatus.PENDING
        
        # Handle based on order type
        if order.order_type == OrderType.MARKET:
            return self._execute_market_order(order)
        elif order.order_type == OrderType.LIMIT:
            return self._handle_limit_order(order)
        elif order.order_type == OrderType.STOP:
            return self._handle_stop_order(order)
        else:
            return OrderResult(
                success=False,
                order_id=order.order_id,
                filled_price=0,
                filled_quantity=0,
                message=f"Unsupported order type: {order.order_type}",
            )
    
    def _execute_market_order(self, order: Order) -> OrderResult:
        """Execute a market order immediately"""
        try:
            # Get current price
            base_price = self._get_current_price(order.symbol)
            
            # Apply slippage
            if order.side == OrderSide.BUY:
                execution_price = base_price * (1 + self.slippage_rate)
            else:
                execution_price = base_price * (1 - self.slippage_rate)
            
            # Calculate costs
            trade_value = execution_price * order.quantity
            commission = trade_value * self.commission_rate
            
            if order.side == OrderSide.BUY:
                # Check if enough cash
                total_cost = trade_value + commission
                if total_cost > self.cash:
                    order.status = OrderStatus.REJECTED
                    self.orders[order.order_id] = order
                    return OrderResult(
                        success=False,
                        order_id=order.order_id,
                        filled_price=0,
                        filled_quantity=0,
                        message=f"Insufficient funds. Need ${total_cost:,.2f}, have ${self.cash:,.2f}",
                    )
                
                # Deduct cash
                self.cash -= total_cost
                
                # Update or create position
                if order.symbol in self.positions:
                    pos = self.positions[order.symbol]
                    total_cost_basis = pos.avg_cost * pos.quantity + trade_value
                    total_quantity = pos.quantity + order.quantity
                    pos.avg_cost = total_cost_basis / total_quantity
                    pos.quantity = total_quantity
                    pos.update_price(execution_price)
                else:
                    self.positions[order.symbol] = Position(
                        symbol=order.symbol,
                        quantity=order.quantity,
                        avg_cost=execution_price,
                        current_price=execution_price,
                        market_value=execution_price * order.quantity,
                        unrealized_pnl=0,
                    )
                
                trade_side = "BUY"
                
            else:  # SELL
                # Check if have position
                if order.symbol not in self.positions:
                    order.status = OrderStatus.REJECTED
                    self.orders[order.order_id] = order
                    return OrderResult(
                        success=False,
                        order_id=order.order_id,
                        filled_price=0,
                        filled_quantity=0,
                        message=f"No position to sell for {order.symbol}",
                    )
                
                pos = self.positions[order.symbol]
                if pos.quantity < order.quantity:
                    order.status = OrderStatus.REJECTED
                    self.orders[order.order_id] = order
                    return OrderResult(
                        success=False,
                        order_id=order.order_id,
                        filled_price=0,
                        filled_quantity=0,
                        message=f"Insufficient shares. Have {pos.quantity}, trying to sell {order.quantity}",
                    )
                
                # Calculate realized PnL
                realized_pnl = (execution_price - pos.avg_cost) * order.quantity - commission
                pos.realized_pnl += realized_pnl
                
                # Add cash
                self.cash += trade_value - commission
                
                # Update position
                pos.quantity -= order.quantity
                if pos.quantity == 0:
                    del self.positions[order.symbol]
                else:
                    pos.update_price(execution_price)
                
                trade_side = "SELL"
            
            # Record trade
            order.status = OrderStatus.FILLED
            order.filled_price = execution_price
            order.filled_quantity = order.quantity
            self.orders[order.order_id] = order
            
            trade_record = {
                "timestamp": datetime.now().isoformat(),
                "order_id": order.order_id,
                "symbol": order.symbol,
                "side": trade_side,
                "quantity": order.quantity,
                "price": execution_price,
                "commission": commission,
                "cash_after": self.cash,
            }
            self.trade_history.append(trade_record)
            
            # Save state
            self._save_state()
            
            logger.info(f"Executed {trade_side} {order.quantity} {order.symbol} @ ${execution_price:.2f}")
            
            return OrderResult(
                success=True,
                order_id=order.order_id,
                filled_price=execution_price,
                filled_quantity=order.quantity,
                message=f"Filled {trade_side} {order.quantity} {order.symbol} @ ${execution_price:.2f}",
            )
            
        except Exception as e:
            logger.error(f"Error executing order: {e}")
            order.status = OrderStatus.REJECTED
            self.orders[order.order_id] = order
            return OrderResult(
                success=False,
                order_id=order.order_id,
                filled_price=0,
                filled_quantity=0,
                message=f"Error executing order: {str(e)}",
            )
    
    def _handle_limit_order(self, order: Order) -> OrderResult:
        """Store limit order for later execution"""
        self.orders[order.order_id] = order
        self._save_state()
        
        logger.info(f"Stored limit order {order.order_id}: {order.side.value} {order.quantity} {order.symbol} @ ${order.limit_price}")
        
        return OrderResult(
            success=True,
            order_id=order.order_id,
            filled_price=0,
            filled_quantity=0,
            message=f"Limit order placed. Waiting for price to reach ${order.limit_price}",
        )
    
    def _handle_stop_order(self, order: Order) -> OrderResult:
        """Store stop order for later execution"""
        self.orders[order.order_id] = order
        self._save_state()
        
        logger.info(f"Stored stop order {order.order_id}: {order.side.value} {order.quantity} {order.symbol} @ ${order.stop_price}")
        
        return OrderResult(
            success=True,
            order_id=order.order_id,
            filled_price=0,
            filled_quantity=0,
            message=f"Stop order placed. Will trigger at ${order.stop_price}",
        )
    
    def check_pending_orders(self) -> List[OrderResult]:
        """
        Check and execute pending limit/stop orders.
        
        Should be called periodically to check if prices have reached
        order trigger points.
        """
        results = []
        orders_to_execute = []
        
        for order_id, order in list(self.orders.items()):
            if order.status != OrderStatus.PENDING:
                continue
            
            try:
                current_price = self._get_current_price(order.symbol)
                
                # Check limit orders
                if order.order_type == OrderType.LIMIT:
                    if order.side == OrderSide.BUY and current_price <= order.limit_price:
                        orders_to_execute.append(order)
                    elif order.side == OrderSide.SELL and current_price >= order.limit_price:
                        orders_to_execute.append(order)
                
                # Check stop orders
                elif order.order_type == OrderType.STOP:
                    if order.side == OrderSide.SELL and current_price <= order.stop_price:
                        # Convert to market order
                        order.order_type = OrderType.MARKET
                        orders_to_execute.append(order)
                    elif order.side == OrderSide.BUY and current_price >= order.stop_price:
                        order.order_type = OrderType.MARKET
                        orders_to_execute.append(order)
                        
            except Exception as e:
                logger.error(f"Error checking order {order_id}: {e}")
        
        # Execute triggered orders
        for order in orders_to_execute:
            order.order_type = OrderType.MARKET
            result = self._execute_market_order(order)
            results.append(result)
        
        return results
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order"""
        if order_id not in self.orders:
            return False
        
        order = self.orders[order_id]
        if order.status != OrderStatus.PENDING:
            return False
        
        order.status = OrderStatus.CANCELLED
        self._save_state()
        logger.info(f"Cancelled order {order_id}")
        return True
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID"""
        return self.orders.get(order_id)
    
    def get_market_data(self, symbol: str) -> MarketData:
        """Get market data for a symbol"""
        try:
            import yfinance as yf
            
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1d")
            
            if hist.empty:
                raise ValueError(f"No data for {symbol}")
            
            last_price = hist['Close'].iloc[-1]
            
            return MarketData(
                symbol=symbol,
                bid=last_price * 0.9999,  # Simulated bid
                ask=last_price * 1.0001,  # Simulated ask
                last=last_price,
                volume=int(hist['Volume'].iloc[-1]) if 'Volume' in hist else 0,
                timestamp=datetime.now(),
                open_price=hist['Open'].iloc[-1] if 'Open' in hist else last_price,
                high=hist['High'].iloc[-1] if 'High' in hist else last_price,
                low=hist['Low'].iloc[-1] if 'Low' in hist else last_price,
                close=last_price,
            )
        except Exception as e:
            logger.error(f"Error getting market data for {symbol}: {e}")
            raise
    
    def is_market_open(self) -> bool:
        """Check if US market is open"""
        now = datetime.now()
        # Simple check: Mon-Fri, 9:30-16:00 ET
        # In production, use proper exchange calendar
        if now.weekday() >= 5:  # Weekend
            return False
        hour = now.hour
        return 9 <= hour < 16
    
    def get_trading_days(self, start_date: datetime, end_date: datetime) -> List[datetime]:
        """Get trading days between dates"""
        # Simplified - in production, use exchange calendar
        days = []
        current = start_date
        while current <= end_date:
            if current.weekday() < 5:  # Mon-Fri
                days.append(current)
            current = current.replace(day=current.day + 1)
        return days
    
    def _get_current_price(self, symbol: str) -> float:
        """Get current price for a symbol using yfinance"""
        import yfinance as yf
        
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1d")
        
        if hist.empty:
            raise ValueError(f"No price data available for {symbol}")
        
        return float(hist['Close'].iloc[-1])
    
    def _load_state(self):
        """Load persisted state from disk"""
        state_file = self.data_dir / "state.json"
        
        if state_file.exists():
            try:
                with open(state_file, 'r') as f:
                    state = json.load(f)
                
                self.cash = state.get('cash', self.initial_capital)
                self.order_counter = state.get('order_counter', 0)
                
                # Restore positions
                for symbol, pos_data in state.get('positions', {}).items():
                    self.positions[symbol] = Position(
                        symbol=symbol,
                        quantity=pos_data['quantity'],
                        avg_cost=pos_data['avg_cost'],
                        current_price=pos_data.get('current_price', pos_data['avg_cost']),
                        market_value=pos_data.get('market_value', 0),
                        unrealized_pnl=pos_data.get('unrealized_pnl', 0),
                        realized_pnl=pos_data.get('realized_pnl', 0),
                    )
                
                # Restore trade history
                self.trade_history = state.get('trade_history', [])
                
                logger.info(f"Loaded state: ${self.cash:,.2f} cash, {len(self.positions)} positions")
                
            except Exception as e:
                logger.error(f"Error loading state: {e}")
    
    def _save_state(self):
        """Persist state to disk"""
        state_file = self.data_dir / "state.json"
        
        try:
            state = {
                'cash': self.cash,
                'order_counter': self.order_counter,
                'positions': {
                    symbol: {
                        'quantity': pos.quantity,
                        'avg_cost': pos.avg_cost,
                        'current_price': pos.current_price,
                        'market_value': pos.market_value,
                        'unrealized_pnl': pos.unrealized_pnl,
                        'realized_pnl': pos.realized_pnl,
                    }
                    for symbol, pos in self.positions.items()
                },
                'trade_history': self.trade_history,
                'updated_at': datetime.now().isoformat(),
            }
            
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving state: {e}")
    
    def reset(self, initial_capital: Optional[float] = None):
        """Reset to initial state"""
        if initial_capital is not None:
            self.initial_capital = initial_capital
        
        self.cash = self.initial_capital
        self.positions = {}
        self.orders = {}
        self.trade_history = []
        self.order_counter = 0
        self._save_state()
        logger.info(f"Reset paper trading account to ${self.initial_capital:,.2f}")
    
    def get_trade_history(self) -> List[Dict]:
        """Get all trade history"""
        return self.trade_history.copy()
    
    def get_performance_summary(self) -> Dict:
        """Calculate performance metrics"""
        total_return = (self.cash + sum(p.market_value for p in self.positions.values())) / self.initial_capital - 1
        
        winning_trades = [t for t in self.trade_history if t['side'] == 'SELL']
        # This is simplified - proper implementation would track PnL per trade
        
        return {
            'initial_capital': self.initial_capital,
            'current_cash': self.cash,
            'total_value': self.cash + sum(p.market_value for p in self.positions.values()),
            'total_return': total_return,
            'total_return_pct': total_return * 100,
            'num_trades': len(self.trade_history),
            'num_positions': len(self.positions),
        }