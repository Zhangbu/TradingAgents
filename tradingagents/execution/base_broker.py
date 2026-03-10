"""
Base Broker Interface - Abstract base class for all broker implementations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any


class OrderSide(Enum):
    """Order side (buy/sell)"""
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    """Order type"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(Enum):
    """Order status"""
    PENDING = "pending"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class Order:
    """Order data structure"""
    symbol: str
    side: OrderSide
    quantity: int
    order_type: OrderType
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    order_id: Optional[str] = None
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    filled_price: Optional[float] = None
    filled_quantity: int = 0
    message: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "symbol": self.symbol,
            "side": self.side.value,
            "quantity": self.quantity,
            "order_type": self.order_type.value,
            "limit_price": self.limit_price,
            "stop_price": self.stop_price,
            "order_id": self.order_id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "filled_price": self.filled_price,
            "filled_quantity": self.filled_quantity,
            "message": self.message,
        }


@dataclass
class OrderResult:
    """Result of order execution"""
    success: bool
    order_id: str
    filled_price: float
    filled_quantity: int
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "success": self.success,
            "order_id": self.order_id,
            "filled_price": self.filled_price,
            "filled_quantity": self.filled_quantity,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class Position:
    """Position data structure"""
    symbol: str
    quantity: int
    avg_cost: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float = 0.0
    realized_pnl: float = 0.0
    opened_at: datetime = field(default_factory=datetime.now)
    
    def update_price(self, current_price: float):
        """Update position with new price"""
        self.current_price = current_price
        self.market_value = current_price * self.quantity
        cost_basis = self.avg_cost * self.quantity
        self.unrealized_pnl = self.market_value - cost_basis
        if cost_basis > 0:
            self.unrealized_pnl_pct = self.unrealized_pnl / cost_basis
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "symbol": self.symbol,
            "quantity": self.quantity,
            "avg_cost": self.avg_cost,
            "current_price": self.current_price,
            "market_value": self.market_value,
            "unrealized_pnl": self.unrealized_pnl,
            "unrealized_pnl_pct": self.unrealized_pnl_pct,
            "realized_pnl": self.realized_pnl,
            "opened_at": self.opened_at.isoformat(),
        }


@dataclass
class AccountInfo:
    """Account information"""
    cash: float
    total_value: float
    buying_power: float
    positions: List[Position]
    initial_margin: float = 0.0
    maintenance_margin: float = 0.0
    day_trades_remaining: int = 0
    account_id: str = ""
    
    @property
    def equity(self) -> float:
        """Total equity (cash + positions market value)"""
        return self.cash + sum(p.market_value for p in self.positions)
    
    @property
    def total_pnl(self) -> float:
        """Total unrealized PnL"""
        return sum(p.unrealized_pnl for p in self.positions)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "cash": self.cash,
            "total_value": self.total_value,
            "buying_power": self.buying_power,
            "positions": [p.to_dict() for p in self.positions],
            "initial_margin": self.initial_margin,
            "maintenance_margin": self.maintenance_margin,
            "day_trades_remaining": self.day_trades_remaining,
            "account_id": self.account_id,
            "equity": self.equity,
            "total_pnl": self.total_pnl,
        }


@dataclass
class MarketData:
    """Market data structure"""
    symbol: str
    bid: float
    ask: float
    last: float
    volume: int
    timestamp: datetime
    open_price: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    
    @property
    def mid(self) -> float:
        """Mid price"""
        return (self.bid + self.ask) / 2
    
    @property
    def spread(self) -> float:
        """Bid-ask spread"""
        return self.ask - self.bid
    
    @property
    def spread_pct(self) -> float:
        """Spread as percentage"""
        if self.mid > 0:
            return self.spread / self.mid
        return 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "symbol": self.symbol,
            "bid": self.bid,
            "ask": self.ask,
            "last": self.last,
            "volume": self.volume,
            "timestamp": self.timestamp.isoformat(),
            "open": self.open_price,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "mid": self.mid,
            "spread": self.spread,
            "spread_pct": self.spread_pct,
        }


class BaseBroker(ABC):
    """
    Abstract base class for broker implementations.
    
    All broker implementations (paper trading, Alpaca, Binance, etc.)
    should inherit from this class and implement the required methods.
    """
    
    def __init__(self, name: str = "BaseBroker"):
        self.name = name
        self._connected = False
    
    @abstractmethod
    def connect(self) -> bool:
        """
        Connect to the broker.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """
        Disconnect from the broker.
        
        Returns:
            bool: True if disconnection successful, False otherwise
        """
        pass
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to broker"""
        return self._connected
    
    @abstractmethod
    def get_account(self) -> AccountInfo:
        """
        Get account information.
        
        Returns:
            AccountInfo: Account information including cash, buying power, etc.
        """
        pass
    
    @abstractmethod
    def get_positions(self) -> List[Position]:
        """
        Get all positions.
        
        Returns:
            List[Position]: List of current positions
        """
        pass
    
    @abstractmethod
    def get_position(self, symbol: str) -> Optional[Position]:
        """
        Get position for a specific symbol.
        
        Args:
            symbol: Stock/asset symbol
            
        Returns:
            Position if exists, None otherwise
        """
        pass
    
    @abstractmethod
    def place_order(self, order: Order) -> OrderResult:
        """
        Place an order.
        
        Args:
            order: Order to place
            
        Returns:
            OrderResult: Result of order execution
        """
        pass
    
    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an order.
        
        Args:
            order_id: ID of order to cancel
            
        Returns:
            bool: True if cancelled successfully
        """
        pass
    
    @abstractmethod
    def get_order(self, order_id: str) -> Optional[Order]:
        """
        Get order by ID.
        
        Args:
            order_id: Order ID
            
        Returns:
            Order if found, None otherwise
        """
        pass
    
    @abstractmethod
    def get_market_data(self, symbol: str) -> MarketData:
        """
        Get current market data for a symbol.
        
        Args:
            symbol: Stock/asset symbol
            
        Returns:
            MarketData: Current market data
        """
        pass
    
    @abstractmethod
    def is_market_open(self) -> bool:
        """
        Check if market is currently open.
        
        Returns:
            bool: True if market is open
        """
        pass
    
    @abstractmethod
    def get_trading_days(self, start_date: datetime, end_date: datetime) -> List[datetime]:
        """
        Get trading days between two dates.
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            List of trading days
        """
        pass
    
    # Convenience methods
    def buy_market(self, symbol: str, quantity: int) -> OrderResult:
        """Place a market buy order"""
        order = Order(
            symbol=symbol,
            side=OrderSide.BUY,
            quantity=quantity,
            order_type=OrderType.MARKET,
        )
        return self.place_order(order)
    
    def sell_market(self, symbol: str, quantity: int) -> OrderResult:
        """Place a market sell order"""
        order = Order(
            symbol=symbol,
            side=OrderSide.SELL,
            quantity=quantity,
            order_type=OrderType.MARKET,
        )
        return self.place_order(order)
    
    def buy_limit(self, symbol: str, quantity: int, limit_price: float) -> OrderResult:
        """Place a limit buy order"""
        order = Order(
            symbol=symbol,
            side=OrderSide.BUY,
            quantity=quantity,
            order_type=OrderType.LIMIT,
            limit_price=limit_price,
        )
        return self.place_order(order)
    
    def sell_limit(self, symbol: str, quantity: int, limit_price: float) -> OrderResult:
        """Place a limit sell order"""
        order = Order(
            symbol=symbol,
            side=OrderSide.SELL,
            quantity=quantity,
            order_type=OrderType.LIMIT,
            limit_price=limit_price,
        )
        return self.place_order(order)
    
    def close_position(self, symbol: str) -> Optional[OrderResult]:
        """Close entire position for a symbol"""
        position = self.get_position(symbol)
        if position and position.quantity > 0:
            return self.sell_market(symbol, position.quantity)
        return None