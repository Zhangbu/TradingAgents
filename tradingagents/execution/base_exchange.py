"""Abstract base class for exchange implementations."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List, Callable, Awaitable


class OrderType(str, Enum):
    """Order type enumeration."""
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    STOP_LIMIT = "stop_limit"
    TAKE_PROFIT = "take_profit"


class OrderSide(str, Enum):
    """Order side enumeration."""
    BUY = "buy"
    SELL = "sell"


class OrderStatus(str, Enum):
    """Order status enumeration."""
    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class TimeInForce(str, Enum):
    """Time in force enumeration."""
    GTC = "good_till_cancelled"  # Good till cancelled
    IOC = "immediate_or_cancel"  # Immediate or cancel
    FOK = "fill_or_kill"         # Fill or kill
    DAY = "day"                   # Day order


@dataclass
class OrderRequest:
    """Order request data structure."""
    symbol: str
    side: OrderSide
    quantity: float
    order_type: OrderType = OrderType.MARKET
    price: Optional[float] = None  # Required for limit orders
    stop_price: Optional[float] = None  # Required for stop orders
    time_in_force: TimeInForce = TimeInForce.GTC
    client_order_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Order:
    """Order data structure."""
    id: str
    symbol: str
    side: OrderSide
    quantity: float
    order_type: OrderType
    status: OrderStatus
    price: Optional[float] = None
    stop_price: Optional[float] = None
    filled_quantity: float = 0.0
    average_fill_price: Optional[float] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    client_order_id: Optional[str] = None
    exchange_order_id: Optional[str] = None
    time_in_force: TimeInForce = TimeInForce.GTC
    fees: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Position:
    """Position data structure."""
    symbol: str
    side: str  # "long" or "short"
    quantity: float
    entry_price: float
    current_price: Optional[float] = None
    unrealized_pnl: float = 0.0
    unrealized_pnl_percent: float = 0.0
    leverage: float = 1.0
    liquidation_price: Optional[float] = None
    margin: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Ticker:
    """Ticker data structure."""
    symbol: str
    last_price: float
    bid_price: Optional[float] = None
    ask_price: Optional[float] = None
    bid_size: Optional[float] = None
    ask_size: Optional[float] = None
    high_24h: Optional[float] = None
    low_24h: Optional[float] = None
    volume_24h: Optional[float] = None
    price_change_24h: Optional[float] = None
    price_change_percent_24h: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Balance:
    """Balance data structure."""
    asset: str
    free: float
    used: float
    total: float


@dataclass
class AccountInfo:
    """Account information data structure."""
    balances: List[Balance]
    total_equity: float
    available_margin: float
    margin_used: float
    unrealized_pnl: float
    realized_pnl: float


class BaseExchange(ABC):
    """Abstract base class for exchange implementations.
    
    All exchange implementations (Paper, CCXT, Futu, IBKR) should inherit
    from this class and implement the required methods.
    """
    
    def __init__(
        self,
        name: str,
        callback: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None,
    ):
        """Initialize the exchange.
        
        Args:
            name: Exchange name identifier
            callback: Optional async callback for order/position updates
        """
        self.name = name
        self.callback = callback
        self._connected = False
        self._orders: Dict[str, Order] = {}
        self._positions: Dict[str, Position] = {}
    
    @property
    def is_connected(self) -> bool:
        """Check if exchange is connected."""
        return self._connected
    
    @abstractmethod
    async def connect(self) -> bool:
        """Connect to the exchange.
        
        Returns:
            True if connection successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the exchange."""
        pass
    
    @abstractmethod
    async def get_account_info(self) -> AccountInfo:
        """Get account information including balances.
        
        Returns:
            AccountInfo object with current balances and positions
        """
        pass
    
    @abstractmethod
    async def get_ticker(self, symbol: str) -> Ticker:
        """Get current ticker for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., "BTC/USDT", "AAPL")
            
        Returns:
            Ticker object with current price data
        """
        pass
    
    @abstractmethod
    async def get_positions(self) -> List[Position]:
        """Get all open positions.
        
        Returns:
            List of Position objects
        """
        pass
    
    @abstractmethod
    async def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for a specific symbol.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Position object if exists, None otherwise
        """
        pass
    
    @abstractmethod
    async def place_order(self, request: OrderRequest) -> Order:
        """Place an order.
        
        Args:
            request: OrderRequest with order details
            
        Returns:
            Order object with order status
            
        Raises:
            ExchangeError: If order placement fails
        """
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order.
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            True if cancelled successfully, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID.
        
        Args:
            order_id: Order ID
            
        Returns:
            Order object if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """Get all open orders, optionally filtered by symbol.
        
        Args:
            symbol: Optional symbol filter
            
        Returns:
            List of open Order objects
        """
        pass
    
    async def close_position(
        self,
        symbol: str,
        quantity: Optional[float] = None,
        order_type: OrderType = OrderType.MARKET,
        price: Optional[float] = None,
    ) -> Order:
        """Close a position.
        
        Args:
            symbol: Symbol to close position for
            quantity: Quantity to close (default: close entire position)
            order_type: Order type for closing
            price: Price for limit orders
            
        Returns:
            Order object for the closing order
        """
        position = await self.get_position(symbol)
        if not position:
            raise ExchangeError(f"No position found for {symbol}")
        
        close_quantity = quantity or abs(position.quantity)
        close_side = OrderSide.SELL if position.side == "long" else OrderSide.BUY
        
        request = OrderRequest(
            symbol=symbol,
            side=close_side,
            quantity=close_quantity,
            order_type=order_type,
            price=price,
        )
        
        return await self.place_order(request)
    
    async def close_all_positions(self) -> List[Order]:
        """Close all open positions.
        
        Returns:
            List of Order objects for closing orders
        """
        positions = await self.get_positions()
        orders = []
        
        for position in positions:
            try:
                order = await self.close_position(position.symbol)
                orders.append(order)
            except Exception as e:
                # Log error but continue closing other positions
                print(f"Error closing position {position.symbol}: {e}")
        
        return orders
    
    async def _emit_callback(self, event_type: str, data: Dict[str, Any]) -> None:
        """Emit callback event.
        
        Args:
            event_type: Type of event (order_update, position_update, etc.)
            data: Event data
        """
        if self.callback:
            try:
                await self.callback({
                    "exchange": self.name,
                    "type": event_type,
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": data,
                })
            except Exception as e:
                print(f"Callback error: {e}")


class ExchangeError(Exception):
    """Exception raised for exchange-related errors."""
    
    def __init__(self, message: str, code: Optional[str] = None, details: Optional[Dict] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}
    
    def __str__(self):
        if self.code:
            return f"[{self.code}] {self.message}"
        return self.message


class InsufficientFundsError(ExchangeError):
    """Exception raised when account has insufficient funds."""
    pass


class OrderNotFoundError(ExchangeError):
    """Exception raised when order is not found."""
    pass


class PositionNotFoundError(ExchangeError):
    """Exception raised when position is not found."""
    pass


class ConnectionError(ExchangeError):
    """Exception raised when connection fails."""
    pass