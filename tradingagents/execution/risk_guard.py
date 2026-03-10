"""Risk Guard for order validation before execution."""

from decimal import Decimal
from typing import Dict, Any, Optional
from datetime import date, datetime
from dataclasses import dataclass, field
import logging

from tradingagents.execution.base_exchange import OrderSide, OrderType

logger = logging.getLogger(__name__)


class RiskError(Exception):
    """Exception raised when risk check fails."""
    pass


@dataclass
class RiskConfig:
    """Risk management configuration."""
    
    # Position limits
    max_position_size: Decimal = Decimal("10000")  # Max value per position in quote currency
    max_position_percent: Decimal = Decimal("0.1")  # Max % of portfolio per position
    
    # Daily limits
    max_daily_loss: Decimal = Decimal("1000")  # Max daily loss in quote currency
    max_daily_trades: int = 20  # Max trades per day
    
    # Order limits
    max_order_size: Decimal = Decimal("5000")  # Max single order size
    min_order_size: Decimal = Decimal("10")  # Min order size
    
    # Risk ratios
    max_portfolio_risk: Decimal = Decimal("0.02")  # Max 2% portfolio risk per trade
    default_stop_loss_percent: Decimal = Decimal("0.05")  # Default 5% stop loss
    
    # Restrictions
    allowed_symbols: Optional[list] = None  # If set, only these symbols can be traded
    blocked_symbols: list = field(default_factory=list)  # Always blocked symbols
    
    # Trading hours (24-hour format, UTC)
    trading_start_hour: int = 0
    trading_end_hour: int = 24


@dataclass
class DailyStats:
    """Daily trading statistics for risk management."""
    
    date: date
    starting_balance: Decimal = Decimal("0")
    current_balance: Decimal = Decimal("0")
    daily_pnl: Decimal = Decimal("0")
    trades_count: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    
    @property
    def daily_loss(self) -> Decimal:
        """Calculate daily loss (negative PnL)."""
        return min(self.daily_pnl, Decimal("0"))
    
    @property
    def win_rate(self) -> Decimal:
        """Calculate win rate."""
        if self.trades_count == 0:
            return Decimal("0")
        return Decimal(self.winning_trades) / Decimal(self.trades_count)


class RiskGuard:
    """
    Risk management guard that validates all orders before execution.
    
    All orders must pass through this guard before being sent to the exchange.
    """
    
    def __init__(self, config: RiskConfig = None):
        """
        Initialize the risk guard.
        
        Args:
            config: Risk configuration. Uses defaults if not provided.
        """
        self.config = config or RiskConfig()
        self.daily_stats: Dict[date, DailyStats] = {}
        self._portfolio_value = Decimal("0")
        self._positions: Dict[str, Decimal] = {}  # symbol -> quantity
    
    def update_portfolio_state(
        self,
        portfolio_value: Decimal,
        positions: Dict[str, Decimal],
    ):
        """
        Update the current portfolio state for risk calculations.
        
        Args:
            portfolio_value: Total portfolio value in quote currency
            positions: Current positions {symbol: quantity}
        """
        self._portfolio_value = portfolio_value
        self._positions = positions.copy()
    
    def update_daily_stats(
        self,
        current_balance: Decimal,
        trades_count: int = None,
        winning_trades: int = None,
        losing_trades: int = None,
    ):
        """
        Update daily trading statistics.
        
        Args:
            current_balance: Current account balance
            trades_count: Total trades today (optional)
            winning_trades: Winning trades today (optional)
            losing_trades: Losing trades today (optional)
        """
        today = date.today()
        
        if today not in self.daily_stats:
            self.daily_stats[today] = DailyStats(
                date=today,
                starting_balance=current_balance,
                current_balance=current_balance,
            )
        
        stats = self.daily_stats[today]
        stats.current_balance = current_balance
        stats.daily_pnl = current_balance - stats.starting_balance
        
        if trades_count is not None:
            stats.trades_count = trades_count
        if winning_trades is not None:
            stats.winning_trades = winning_trades
        if losing_trades is not None:
            stats.losing_trades = losing_trades
    
    def validate(
        self,
        symbol: str,
        side: OrderSide,
        quantity: Decimal,
        price: Decimal,
        order_type: OrderType = OrderType.MARKET,
    ) -> bool:
        """
        Validate an order against risk rules.
        
        Args:
            symbol: Trading symbol
            side: Order side (BUY/SELL)
            quantity: Order quantity
            price: Order price
            order_type: Order type
            
        Returns:
            True if order passes all risk checks
            
        Raises:
            RiskError: If order fails any risk check
        """
        order_value = quantity * price
        
        # Check trading hours
        self._check_trading_hours()
        
        # Check symbol restrictions
        self._check_symbol_restrictions(symbol)
        
        # Check order size limits
        self._check_order_size(order_value)
        
        # Check position limits
        self._check_position_limits(symbol, order_value)
        
        # Check daily limits
        self._check_daily_limits()
        
        # Check portfolio risk
        self._check_portfolio_risk(order_value)
        
        logger.info(
            f"Order validated: {side.value} {quantity} {symbol} @ {price} "
            f"(value: {order_value})"
        )
        return True
    
    def _check_trading_hours(self):
        """Check if trading is allowed at current time."""
        now = datetime.utcnow()
        current_hour = now.hour
        
        if not (self.config.trading_start_hour <= current_hour < self.config.trading_end_hour):
            raise RiskError(
                f"Trading not allowed at this hour ({current_hour}:00 UTC). "
                f"Allowed hours: {self.config.trading_start_hour}:00 - {self.config.trading_end_hour}:00"
            )
    
    def _check_symbol_restrictions(self, symbol: str):
        """Check if symbol is allowed for trading."""
        # Check blocked symbols
        if symbol in self.config.blocked_symbols:
            raise RiskError(f"Trading {symbol} is blocked")
        
        # Check allowed symbols (if set)
        if self.config.allowed_symbols and symbol not in self.config.allowed_symbols:
            raise RiskError(f"Trading {symbol} is not in the allowed list")
    
    def _check_order_size(self, order_value: Decimal):
        """Check order size limits."""
        if order_value < self.config.min_order_size:
            raise RiskError(
                f"Order value {order_value} below minimum {self.config.min_order_size}"
            )
        
        if order_value > self.config.max_order_size:
            raise RiskError(
                f"Order value {order_value} exceeds maximum {self.config.max_order_size}"
            )
    
    def _check_position_limits(self, symbol: str, order_value: Decimal):
        """Check position size limits."""
        # Check absolute position limit
        current_position_value = self._positions.get(symbol, Decimal("0"))
        
        # For crypto, positions are typically small
        if order_value > self.config.max_position_size:
            raise RiskError(
                f"Order value {order_value} exceeds max position size {self.config.max_position_size}"
            )
        
        # Check position as percentage of portfolio
        if self._portfolio_value > 0:
            position_percent = order_value / self._portfolio_value
            if position_percent > self.config.max_position_percent:
                raise RiskError(
                    f"Order represents {position_percent:.1%} of portfolio, "
                    f"exceeds max {self.config.max_position_percent:.1%}"
                )
    
    def _check_daily_limits(self):
        """Check daily trading limits."""
        today = date.today()
        stats = self.daily_stats.get(today)
        
        if stats:
            # Check daily loss limit
            if stats.daily_loss < -self.config.max_daily_loss:
                raise RiskError(
                    f"Daily loss {stats.daily_loss} exceeds limit {self.config.max_daily_loss}. "
                    "Trading suspended for today."
                )
            
            # Check daily trade count
            if stats.trades_count >= self.config.max_daily_trades:
                raise RiskError(
                    f"Daily trade limit ({self.config.max_daily_trades}) reached. "
                    "Trading suspended for today."
                )
    
    def _check_portfolio_risk(self, order_value: Decimal):
        """Check portfolio-level risk."""
        if self._portfolio_value <= 0:
            return  # Can't calculate risk without portfolio value
        
        risk_amount = order_value * self.config.default_stop_loss_percent
        portfolio_risk = risk_amount / self._portfolio_value
        
        if portfolio_risk > self.config.max_portfolio_risk:
            raise RiskError(
                f"Portfolio risk {portfolio_risk:.1%} exceeds max {self.config.max_portfolio_risk:.1%}"
            )
    
    def get_risk_report(self) -> Dict[str, Any]:
        """Generate a risk report."""
        today = date.today()
        stats = self.daily_stats.get(today)
        
        return {
            "portfolio_value": float(self._portfolio_value),
            "positions": {k: float(v) for k, v in self._positions.items()},
            "daily_stats": {
                "date": str(stats.date) if stats else None,
                "daily_pnl": float(stats.daily_pnl) if stats else 0,
                "trades_count": stats.trades_count if stats else 0,
                "win_rate": float(stats.win_rate) if stats else 0,
            },
            "limits": {
                "max_position_size": float(self.config.max_position_size),
                "max_daily_loss": float(self.config.max_daily_loss),
                "max_daily_trades": self.config.max_daily_trades,
                "max_portfolio_risk": float(self.config.max_portfolio_risk),
            },
        }
    
    def calculate_suggested_size(
        self,
        symbol: str,
        price: Decimal,
        account_balance: Decimal,
    ) -> Decimal:
        """
        Calculate suggested position size based on risk parameters.
        
        Uses fixed fractional position sizing based on stop loss.
        
        Args:
            symbol: Trading symbol
            price: Current price
            account_balance: Account balance
            
        Returns:
            Suggested quantity
        """
        # Risk per trade (e.g., 2% of account)
        risk_per_trade = account_balance * self.config.max_portfolio_risk
        
        # Assume stop loss distance
        stop_loss_distance = price * self.config.default_stop_loss_percent
        
        # Position size = Risk / Stop Loss Distance
        if stop_loss_distance > 0:
            position_size = risk_per_trade / stop_loss_distance
        else:
            position_size = Decimal("0")
        
        # Apply max position size limit
        max_by_position = self.config.max_position_size / price
        position_size = min(position_size, max_by_position)
        
        # Apply max position percent limit
        max_by_percent = (account_balance * self.config.max_position_percent) / price
        position_size = min(position_size, max_by_percent)
        
        return position_size.quantize(Decimal("0.00000001"))