"""
Risk Manager - Comprehensive risk management system.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple, Callable
import logging
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk alert levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertType(Enum):
    """Types of risk alerts"""
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    POSITION_LIMIT = "position_limit"
    DAILY_LOSS = "daily_loss"
    DRAWDOWN = "drawdown"
    SECTOR_EXPOSURE = "sector_exposure"


@dataclass
class RiskRules:
    """Risk management rules configuration"""
    # Position limits
    max_single_position: float = 0.10       # 10% max per position
    max_sector_exposure: float = 0.30        # 30% max per sector
    max_total_exposure: float = 0.95         # 95% max total exposure
    
    # Loss limits
    max_daily_loss: float = 0.03             # 3% max daily loss
    max_drawdown: float = 0.15               # 15% max drawdown
    max_weekly_loss: float = 0.06            # 6% max weekly loss
    
    # Stop loss / Take profit
    default_stop_loss: float = 0.08          # 8% stop loss
    default_take_profit: float = 0.20        # 20% take profit
    trailing_stop_pct: float = 0.05          # 5% trailing stop
    
    # Order limits
    max_orders_per_day: int = 20             # Max orders per day
    max_position_value: float = 50000        # Max dollar value per position
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "max_single_position": self.max_single_position,
            "max_sector_exposure": self.max_sector_exposure,
            "max_total_exposure": self.max_total_exposure,
            "max_daily_loss": self.max_daily_loss,
            "max_drawdown": self.max_drawdown,
            "max_weekly_loss": self.max_weekly_loss,
            "default_stop_loss": self.default_stop_loss,
            "default_take_profit": self.default_take_profit,
            "trailing_stop_pct": self.trailing_stop_pct,
            "max_orders_per_day": self.max_orders_per_day,
            "max_position_value": self.max_position_value,
        }


@dataclass
class PositionRisk:
    """Risk metrics for a single position"""
    symbol: str
    entry_price: float
    current_price: float
    highest_price: float
    lowest_price: float
    stop_loss_price: float
    take_profit_price: float
    quantity: int
    entry_time: datetime
    
    # Risk metrics
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0
    risk_amount: float = 0.0        # Amount at risk (to stop loss)
    risk_pct: float = 0.0           # Risk as % of position
    
    # Trailing stop
    trailing_stop_active: bool = False
    trailing_stop_price: float = 0.0
    
    def update(self, current_price: float):
        """Update position with new price"""
        self.current_price = current_price
        
        # Update high/low
        if current_price > self.highest_price:
            self.highest_price = current_price
        if current_price < self.lowest_price or self.lowest_price == 0:
            self.lowest_price = current_price
        
        # Calculate PnL
        self.unrealized_pnl = (current_price - self.entry_price) * self.quantity
        self.unrealized_pnl_pct = (current_price - self.entry_price) / self.entry_price
        
        # Calculate risk
        self.risk_amount = (self.entry_price - self.stop_loss_price) * self.quantity
        if self.entry_price > 0:
            self.risk_pct = (self.entry_price - self.stop_loss_price) / self.entry_price
    
    def update_trailing_stop(self, trailing_pct: float) -> bool:
        """
        Update trailing stop price.
        Returns True if stop was raised.
        """
        new_stop = self.highest_price * (1 - trailing_pct)
        
        if new_stop > self.stop_loss_price:
            self.stop_loss_price = new_stop
            self.trailing_stop_active = True
            self.trailing_stop_price = new_stop
            return True
        
        return False
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "symbol": self.symbol,
            "entry_price": self.entry_price,
            "current_price": self.current_price,
            "highest_price": self.highest_price,
            "lowest_price": self.lowest_price,
            "stop_loss_price": self.stop_loss_price,
            "take_profit_price": self.take_profit_price,
            "quantity": self.quantity,
            "entry_time": self.entry_time.isoformat(),
            "unrealized_pnl": self.unrealized_pnl,
            "unrealized_pnl_pct": self.unrealized_pnl_pct,
            "risk_amount": self.risk_amount,
            "trailing_stop_active": self.trailing_stop_active,
        }


@dataclass
class RiskAlert:
    """Risk alert notification"""
    alert_type: AlertType
    level: RiskLevel
    symbol: str
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    action_required: bool = False
    suggested_action: str = ""
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "alert_type": self.alert_type.value,
            "level": self.level.value,
            "symbol": self.symbol,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "action_required": self.action_required,
            "suggested_action": self.suggested_action,
        }


class RiskManager:
    """
    Comprehensive Risk Management System.
    
    Features:
    - Stop loss and take profit management
    - Position and exposure limits
    - Daily/drawdown loss limits
    - Trailing stops
    - Risk alerts and notifications
    """
    
    def __init__(
        self,
        rules: RiskRules,
        initial_capital: float,
        alert_callback: Optional[Callable[[RiskAlert], None]] = None,
    ):
        """
        Initialize Risk Manager.
        
        Args:
            rules: Risk rules configuration
            initial_capital: Starting capital
            alert_callback: Optional callback for risk alerts
        """
        self.rules = rules
        self.initial_capital = initial_capital
        self.alert_callback = alert_callback
        
        # State tracking
        self.peak_capital = initial_capital
        self.current_capital = initial_capital
        
        # Position risks
        self.position_risks: Dict[str, PositionRisk] = {}
        
        # PnL tracking
        self.daily_pnl: float = 0.0
        self.daily_pnl_reset: datetime = datetime.now().replace(hour=0, minute=0, second=0)
        self.weekly_pnl: float = 0.0
        self.weekly_pnl_reset: datetime = datetime.now() - timedelta(days=datetime.now().weekday())
        
        # Order tracking
        self.orders_today: int = 0
        self.order_reset: datetime = datetime.now().replace(hour=0, minute=0, second=0)
        
        # Alerts history
        self.alerts: List[RiskAlert] = []
        
        # Trading halt flag
        self.trading_halted: bool = False
        self.halt_reason: str = ""
    
    def check_order(
        self,
        order: Dict,
        current_positions: Dict[str, Dict],
        current_prices: Dict[str, float],
    ) -> Tuple[bool, str]:
        """
        Check if an order passes all risk checks.
        
        Args:
            order: Order dictionary with symbol, side, quantity, price
            current_positions: Current positions by symbol
            current_prices: Current prices by symbol
            
        Returns:
            Tuple of (approved, reason)
        """
        # Check if trading is halted
        if self.trading_halted:
            return False, f"Trading halted: {self.halt_reason}"
        
        # Reset daily counters if needed
        self._check_reset_counters()
        
        # Check order limit
        if self.orders_today >= self.rules.max_orders_per_day:
            return False, f"Max orders per day ({self.rules.max_orders_per_day}) reached"
        
        symbol = order.get('symbol', '')
        side = order.get('side', '').lower()
        quantity = order.get('quantity', 0)
        price = order.get('price', current_prices.get(symbol, 0))
        
        if side == 'buy':
            # Check position limit
            order_value = quantity * price
            current_position_value = current_positions.get(symbol, {}).get('market_value', 0)
            new_position_value = current_position_value + order_value
            
            # Single position limit
            if new_position_value / self.initial_capital > self.rules.max_single_position:
                return False, f"Exceeds max single position ({self.rules.max_single_position*100}%)"
            
            # Max position value
            if new_position_value > self.rules.max_position_value:
                return False, f"Exceeds max position value (${self.rules.max_position_value:,.0f})"
            
            # Total exposure check
            total_exposure = sum(
                p.get('market_value', 0) for p in current_positions.values()
            )
            new_exposure = total_exposure + order_value
            
            if new_exposure / self.initial_capital > self.rules.max_total_exposure:
                return False, f"Exceeds max total exposure ({self.rules.max_total_exposure*100}%)"
        
        elif side == 'sell':
            # Check if have position to sell
            current_qty = current_positions.get(symbol, {}).get('quantity', 0)
            if quantity > current_qty:
                return False, f"Insufficient shares. Have {current_qty}, trying to sell {quantity}"
        
        return True, "Approved"
    
    def register_position(
        self,
        symbol: str,
        quantity: int,
        entry_price: float,
        stop_loss_pct: Optional[float] = None,
        take_profit_pct: Optional[float] = None,
    ) -> PositionRisk:
        """
        Register a new position for risk tracking.
        
        Args:
            symbol: Stock symbol
            quantity: Number of shares
            entry_price: Entry price
            stop_loss_pct: Stop loss percentage (default from rules)
            take_profit_pct: Take profit percentage (default from rules)
            
        Returns:
            PositionRisk object
        """
        stop_pct = stop_loss_pct or self.rules.default_stop_loss
        take_profit_pct = take_profit_pct or self.rules.default_take_profit
        
        stop_loss_price = entry_price * (1 - stop_pct)
        take_profit_price = entry_price * (1 + take_profit_pct)
        
        position_risk = PositionRisk(
            symbol=symbol,
            entry_price=entry_price,
            current_price=entry_price,
            highest_price=entry_price,
            lowest_price=entry_price,
            stop_loss_price=stop_loss_price,
            take_profit_price=take_profit_price,
            quantity=quantity,
            entry_time=datetime.now(),
        )
        
        self.position_risks[symbol] = position_risk
        logger.info(f"Registered position: {symbol} x {quantity} @ ${entry_price:.2f}, SL=${stop_loss_price:.2f}")
        
        return position_risk
    
    def update_position(
        self,
        symbol: str,
        current_price: float,
        quantity: Optional[int] = None,
    ):
        """Update position with current price"""
        if symbol not in self.position_risks:
            return
        
        pos_risk = self.position_risks[symbol]
        pos_risk.update(current_price)
        
        if quantity is not None:
            pos_risk.quantity = quantity
    
    def remove_position(self, symbol: str):
        """Remove position from risk tracking"""
        if symbol in self.position_risks:
            del self.position_risks[symbol]
            logger.info(f"Removed position tracking for {symbol}")
    
    def check_stop_loss_take_profit(
        self,
        symbol: str,
        current_price: float,
    ) -> Optional[RiskAlert]:
        """
        Check if stop loss or take profit is triggered.
        
        Args:
            symbol: Stock symbol
            current_price: Current price
            
        Returns:
            RiskAlert if triggered, None otherwise
        """
        if symbol not in self.position_risks:
            return None
        
        pos_risk = self.position_risks[symbol]
        pos_risk.update(current_price)
        
        # Update trailing stop
        pos_risk.update_trailing_stop(self.rules.trailing_stop_pct)
        
        # Check stop loss
        if current_price <= pos_risk.stop_loss_price:
            alert = RiskAlert(
                alert_type=AlertType.STOP_LOSS,
                level=RiskLevel.HIGH,
                symbol=symbol,
                message=f"Stop loss triggered for {symbol} at ${pos_risk.stop_loss_price:.2f}",
                action_required=True,
                suggested_action=f"SELL {pos_risk.quantity} shares of {symbol}",
            )
            self._add_alert(alert)
            return alert
        
        # Check take profit
        if current_price >= pos_risk.take_profit_price:
            alert = RiskAlert(
                alert_type=AlertType.TAKE_PROFIT,
                level=RiskLevel.MEDIUM,
                symbol=symbol,
                message=f"Take profit target reached for {symbol} at ${pos_risk.take_profit_price:.2f}",
                action_required=False,
                suggested_action=f"Consider selling {pos_risk.quantity} shares of {symbol}",
            )
            self._add_alert(alert)
            return alert
        
        return None
    
    def check_all_positions(self, current_prices: Dict[str, float]) -> List[RiskAlert]:
        """
        Check all positions for stop loss / take profit triggers.
        
        Args:
            current_prices: Current prices by symbol
            
        Returns:
            List of triggered alerts
        """
        alerts = []
        
        for symbol, pos_risk in self.position_risks.items():
            if symbol in current_prices:
                alert = self.check_stop_loss_take_profit(symbol, current_prices[symbol])
                if alert:
                    alerts.append(alert)
        
        return alerts
    
    def update_pnl(self, pnl: float):
        """Update PnL tracking"""
        self._check_reset_counters()
        
        self.daily_pnl += pnl
        self.weekly_pnl += pnl
        self.current_capital += pnl
        
        # Update peak
        if self.current_capital > self.peak_capital:
            self.peak_capital = self.current_capital
        
        # Check daily loss limit
        daily_loss_pct = -self.daily_pnl / self.initial_capital
        if daily_loss_pct >= self.rules.max_daily_loss:
            self._halt_trading(f"Daily loss limit reached ({daily_loss_pct*100:.1f}%)")
        
        # Check weekly loss limit
        weekly_loss_pct = -self.weekly_pnl / self.initial_capital
        if weekly_loss_pct >= self.rules.max_weekly_loss:
            self._halt_trading(f"Weekly loss limit reached ({weekly_loss_pct*100:.1f}%)")
        
        # Check drawdown
        if self.peak_capital > 0:
            drawdown = (self.peak_capital - self.current_capital) / self.peak_capital
            if drawdown >= self.rules.max_drawdown:
                self._halt_trading(f"Max drawdown reached ({drawdown*100:.1f}%)")
    
    def get_drawdown(self) -> float:
        """Calculate current drawdown"""
        if self.peak_capital <= 0:
            return 0
        return (self.peak_capital - self.current_capital) / self.peak_capital
    
    def get_risk_report(self) -> Dict:
        """Generate comprehensive risk report"""
        total_position_value = sum(
            p.current_price * p.quantity for p in self.position_risks.values()
        )
        total_risk_amount = sum(p.risk_amount for p in self.position_risks.values())
        
        return {
            "capital": {
                "initial": self.initial_capital,
                "current": self.current_capital,
                "peak": self.peak_capital,
                "drawdown": self.get_drawdown(),
                "drawdown_pct": self.get_drawdown() * 100,
            },
            "pnl": {
                "daily": self.daily_pnl,
                "daily_pct": self.daily_pnl / self.initial_capital * 100,
                "weekly": self.weekly_pnl,
                "weekly_pct": self.weekly_pnl / self.initial_capital * 100,
            },
            "positions": {
                "count": len(self.position_risks),
                "total_value": total_position_value,
                "total_risk": total_risk_amount,
                "exposure": total_position_value / self.initial_capital,
            },
            "limits": {
                "daily_loss_remaining": self.rules.max_daily_loss + (self.daily_pnl / self.initial_capital),
                "orders_remaining": self.rules.max_orders_per_day - self.orders_today,
            },
            "trading_halted": self.trading_halted,
            "halt_reason": self.halt_reason,
            "position_risks": {
                symbol: pos.to_dict() for symbol, pos in self.position_risks.items()
            },
            "recent_alerts": [a.to_dict() for a in self.alerts[-10:]],
        }
    
    def set_stop_loss(self, symbol: str, stop_price: float) -> bool:
        """Manually set stop loss for a position"""
        if symbol not in self.position_risks:
            return False
        
        self.position_risks[symbol].stop_loss_price = stop_price
        logger.info(f"Set stop loss for {symbol} at ${stop_price:.2f}")
        return True
    
    def set_take_profit(self, symbol: str, take_profit_price: float) -> bool:
        """Manually set take profit for a position"""
        if symbol not in self.position_risks:
            return False
        
        self.position_risks[symbol].take_profit_price = take_profit_price
        logger.info(f"Set take profit for {symbol} at ${take_profit_price:.2f}")
        return True
    
    def enable_trailing_stop(self, symbol: str, trailing_pct: Optional[float] = None):
        """Enable trailing stop for a position"""
        if symbol not in self.position_risks:
            return
        
        pct = trailing_pct or self.rules.trailing_stop_pct
        pos_risk = self.position_risks[symbol]
        pos_risk.trailing_stop_active = True
        pos_risk.trailing_stop_price = pos_risk.highest_price * (1 - pct)
        logger.info(f"Enabled trailing stop for {symbol} at {pct*100}%")
    
    def _check_reset_counters(self):
        """Reset daily/weekly counters if needed"""
        now = datetime.now()
        
        # Reset daily
        if now.date() > self.daily_pnl_reset.date():
            self.daily_pnl = 0
            self.orders_today = 0
            self.daily_pnl_reset = now.replace(hour=0, minute=0, second=0)
            
            # Clear trading halt at start of new day
            if self.trading_halted:
                self.trading_halted = False
                self.halt_reason = ""
                logger.info("Trading halt cleared for new trading day")
        
        # Reset weekly
        if now.date() > self.weekly_pnl_reset.date() + timedelta(days=7):
            self.weekly_pnl = 0
            self.weekly_pnl_reset = now - timedelta(days=now.weekday())
    
    def _halt_trading(self, reason: str):
        """Halt all trading"""
        self.trading_halted = True
        self.halt_reason = reason
        
        alert = RiskAlert(
            alert_type=AlertType.DRAWDOWN,
            level=RiskLevel.CRITICAL,
            symbol="",
            message=f"Trading halted: {reason}",
            action_required=True,
            suggested_action="Review positions and risk management",
        )
        self._add_alert(alert)
        
        logger.warning(f"TRADING HALTED: {reason}")
    
    def _add_alert(self, alert: RiskAlert):
        """Add an alert and trigger callback"""
        self.alerts.append(alert)
        
        # Keep only last 100 alerts
        if len(self.alerts) > 100:
            self.alerts = self.alerts[-100:]
        
        # Trigger callback if set
        if self.alert_callback:
            try:
                self.alert_callback(alert)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")
    
    def resume_trading(self):
        """Resume trading after halt"""
        self.trading_halted = False
        self.halt_reason = ""
        logger.info("Trading resumed manually")
    
    def reset(self, initial_capital: Optional[float] = None):
        """Reset risk manager to initial state"""
        if initial_capital is not None:
            self.initial_capital = initial_capital
        
        self.peak_capital = self.initial_capital
        self.current_capital = self.initial_capital
        self.position_risks = {}
        self.daily_pnl = 0
        self.weekly_pnl = 0
        self.orders_today = 0
        self.alerts = []
        self.trading_halted = False
        self.halt_reason = ""
        
        logger.info(f"Risk manager reset. Capital: ${self.initial_capital:,.2f}")