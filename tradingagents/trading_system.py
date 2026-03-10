"""
Trading System - Complete integration of agents, brokers, and risk management.

This module provides a unified interface for:
1. Running trading agents to generate signals
2. Executing trades through brokers
3. Managing risk and positions
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Callable, Any
from enum import Enum
import asyncio

from .execution.base_broker import BaseBroker, Order, Position, TradeResult
from .execution.paper_broker import PaperBroker
from .risk.risk_manager import RiskManager, RiskRules, RiskAlert
from .portfolio.position_manager import PositionManager, PositionSizingMethod

logger = logging.getLogger(__name__)


class TradingMode(Enum):
    """Trading mode"""
    PAPER = "paper"       # Paper trading simulation
    LIVE = "live"         # Live trading (use with caution)


class SignalType(Enum):
    """Trading signal types"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    CLOSE_ALL = "CLOSE_ALL"


@dataclass
class TradingSignal:
    """Trading signal from agents"""
    symbol: str
    signal: SignalType
    confidence: float = 0.5           # 0.0 to 1.0
    reason: str = ""
    suggested_price: Optional[float] = None
    suggested_quantity: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "signal": self.signal.value,
            "confidence": self.confidence,
            "reason": self.reason,
            "suggested_price": self.suggested_price,
            "suggested_quantity": self.suggested_quantity,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class TradingConfig:
    """Trading system configuration"""
    mode: TradingMode = TradingMode.PAPER
    initial_capital: float = 100000
    
    # Position sizing
    position_sizing: PositionSizingMethod = PositionSizingMethod.EQUAL_WEIGHT
    max_position_pct: float = 0.10          # Max 10% per position
    max_positions: int = 10                  # Max concurrent positions
    
    # Risk management
    default_stop_loss_pct: float = 0.05      # 5% default stop loss
    default_take_profit_pct: float = 0.15    # 15% default take profit
    max_daily_loss_pct: float = 0.03         # 3% max daily loss
    max_drawdown_pct: float = 0.10           # 10% max drawdown
    
    # Execution
    min_signal_confidence: float = 0.6       # Minimum confidence to act
    commission: float = 0.001                # 0.1% commission
    slippage: float = 0.0005                 # 0.05% slippage


class TradingSystem:
    """
    Complete trading system integrating agents, execution, and risk management.
    
    Usage:
        # Initialize
        config = TradingConfig(mode=TradingMode.PAPER)
        system = TradingSystem(config)
        
        # Connect
        system.initialize()
        
        # Generate signal from agents
        signal = TradingSignal(
            symbol="AAPL",
            signal=SignalType.BUY,
            confidence=0.8,
            reason="Strong fundamentals and bullish technicals"
        )
        
        # Execute signal
        result = system.execute_signal(signal)
        
        # Get status
        status = system.get_status()
    """
    
    def __init__(
        self,
        config: TradingConfig,
        broker: Optional[BaseBroker] = None,
    ):
        """
        Initialize trading system.
        
        Args:
            config: Trading configuration
            broker: Broker instance (if None, creates PaperBroker)
        """
        self.config = config
        
        # Initialize broker
        if broker:
            self.broker = broker
        else:
            self.broker = PaperBroker(
                initial_capital=config.initial_capital,
                commission=config.commission,
                slippage=config.slippage,
            )
        
        # Initialize risk manager
        risk_rules = RiskRules(
            max_position_size_pct=config.max_position_pct,
            max_portfolio_concentration_pct=0.25,
            max_daily_loss_pct=config.max_daily_loss_pct,
            max_drawdown_pct=config.max_drawdown_pct,
            default_stop_loss_pct=config.default_stop_loss_pct,
        )
        self.risk_manager = RiskManager(rules=risk_rules)
        
        # Initialize position manager
        self.position_manager = PositionManager(
            method=config.position_sizing,
            max_position_pct=config.max_position_pct,
            max_positions=config.max_positions,
        )
        
        # State
        self._initialized = False
        self._signals_history: List[TradingSignal] = []
        self._execution_history: List[Dict] = []
    
    def initialize(self) -> bool:
        """
        Initialize the trading system.
        
        Returns:
            True if initialization successful
        """
        try:
            # Connect broker
            if not self.broker.connect():
                logger.error("Failed to connect broker")
                return False
            
            self._initialized = True
            logger.info(f"Trading system initialized in {self.config.mode.value} mode")
            
            return True
            
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            return False
    
    def shutdown(self):
        """Shutdown the trading system"""
        try:
            # Cancel all open orders
            orders = self.broker.get_open_orders()
            for order in orders:
                self.broker.cancel_order(order.order_id)
            
            # Disconnect broker
            self.broker.disconnect()
            
            self._initialized = False
            logger.info("Trading system shutdown complete")
            
        except Exception as e:
            logger.error(f"Shutdown error: {e}")
    
    def execute_signal(self, signal: TradingSignal) -> TradeResult:
        """
        Execute a trading signal.
        
        Args:
            signal: Trading signal from agents
            
        Returns:
            TradeResult with execution details
        """
        if not self._initialized:
            return TradeResult(
                success=False,
                message="Trading system not initialized",
            )
        
        # Record signal
        self._signals_history.append(signal)
        
        # Check confidence threshold
        if signal.confidence < self.config.min_signal_confidence:
            logger.info(f"Signal confidence {signal.confidence:.2f} below threshold, skipping")
            return TradeResult(
                success=False,
                message=f"Signal confidence below threshold ({signal.confidence:.2f} < {self.config.min_signal_confidence})",
            )
        
        # Get current state
        account = self.broker.get_account()
        positions = self.broker.get_positions()
        current_price = self.broker.get_current_price(signal.symbol)
        
        if current_price is None:
            return TradeResult(
                success=False,
                message=f"Could not get price for {signal.symbol}",
            )
        
        # Pre-trade risk check
        risk_check = self.risk_manager.pre_trade_check(
            symbol=signal.symbol,
            side=signal.signal.value,
            quantity=signal.suggested_quantity or 1,
            price=current_price,
            account_value=account.equity,
            positions=positions,
        )
        
        if not risk_check.approved:
            logger.warning(f"Risk check failed: {risk_check.message}")
            return TradeResult(
                success=False,
                message=f"Risk check failed: {risk_check.message}",
            )
        
        # Execute based on signal type
        result = self._execute_signal_type(signal, current_price, account, positions)
        
        # Record execution
        self._execution_history.append({
            "timestamp": datetime.now(timezone.utc),
            "signal": signal.to_dict(),
            "result": {
                "success": result.success,
                "message": result.message,
                "order_id": result.order.order_id if result.order else None,
            },
        })
        
        # Update risk manager
        if result.success:
            self.risk_manager.record_trade(
                symbol=signal.symbol,
                side=signal.signal.value,
                quantity=result.order.quantity if result.order else 0,
                price=result.order.avg_fill_price if result.order else current_price,
            )
            
            # Set stop loss / take profit
            if signal.stop_loss or signal.take_profit:
                self.risk_manager.set_stop_loss(
                    symbol=signal.symbol,
                    stop_price=signal.stop_loss,
                    take_profit_price=signal.take_profit,
                )
        
        return result
    
    def _execute_signal_type(
        self,
        signal: TradingSignal,
        current_price: float,
        account,
        positions: Dict[str, Position],
    ) -> TradeResult:
        """Execute based on signal type"""
        
        if signal.signal == SignalType.BUY:
            return self._execute_buy(signal, current_price, account, positions)
        
        elif signal.signal == SignalType.SELL:
            return self._execute_sell(signal, current_price, positions)
        
        elif signal.signal == SignalType.CLOSE_ALL:
            return self._close_all_positions(positions)
        
        else:  # HOLD
            return TradeResult(
                success=True,
                message="Signal is HOLD, no action taken",
            )
    
    def _execute_buy(
        self,
        signal: TradingSignal,
        current_price: float,
        account,
        positions: Dict[str, Position],
    ) -> TradeResult:
        """Execute buy signal"""
        
        # Calculate position size
        if signal.suggested_quantity:
            quantity = signal.suggested_quantity
        else:
            # Use position manager to calculate size
            position_result = self.position_manager.calculate_position_size(
                symbol=signal.symbol,
                current_price=current_price,
                account_value=account.equity,
                existing_positions=list(positions.values()),
            )
            
            if not position_result.approved:
                return TradeResult(
                    success=False,
                    message=f"Position sizing rejected: {position_result.message}",
                )
            
            quantity = position_result.quantity
        
        # Check if we already have a position
        if signal.symbol in positions:
            existing = positions[signal.symbol]
            logger.info(f"Adding to existing position of {existing.quantity} shares")
        
        # Execute market buy
        result = self.broker.buy_market(
            symbol=signal.symbol,
            quantity=quantity,
        )
        
        if result.success:
            logger.info(f"BUY executed: {quantity} {signal.symbol} @ ${current_price:.2f}")
        
        return result
    
    def _execute_sell(
        self,
        signal: TradingSignal,
        current_price: float,
        positions: Dict[str, Position],
    ) -> TradeResult:
        """Execute sell signal"""
        
        if signal.symbol not in positions:
            return TradeResult(
                success=False,
                message=f"No position to sell for {signal.symbol}",
            )
        
        position = positions[signal.symbol]
        
        # Determine quantity to sell
        if signal.suggested_quantity:
            quantity = min(signal.suggested_quantity, position.quantity)
        else:
            quantity = position.quantity  # Sell all
        
        result = self.broker.sell_market(
            symbol=signal.symbol,
            quantity=quantity,
        )
        
        if result.success:
            logger.info(f"SELL executed: {quantity} {signal.symbol} @ ${current_price:.2f}")
        
        return result
    
    def _close_all_positions(self, positions: Dict[str, Position]) -> TradeResult:
        """Close all positions"""
        if not positions:
            return TradeResult(
                success=True,
                message="No positions to close",
            )
        
        closed = 0
        errors = []
        
        for symbol, position in positions.items():
            result = self.broker.close_position(symbol)
            if result.success:
                closed += 1
            else:
                errors.append(f"{symbol}: {result.message}")
        
        if errors:
            return TradeResult(
                success=closed > 0,
                message=f"Closed {closed}/{len(positions)} positions. Errors: {errors}",
            )
        
        return TradeResult(
            success=True,
            message=f"Closed all {closed} positions",
        )
    
    def update_risk_management(self):
        """Update risk management (call periodically)"""
        if not self._initialized:
            return
        
        try:
            # Get current state
            account = self.broker.get_account()
            positions = self.broker.get_positions()
            
            # Check stop losses
            for symbol, position in positions.items():
                current_price = self.broker.get_current_price(symbol)
                if current_price:
                    stop_check = self.risk_manager.check_stop_loss(
                        symbol=symbol,
                        current_price=current_price,
                        entry_price=position.avg_cost,
                    )
                    
                    if stop_check.triggered:
                        logger.warning(f"Stop loss triggered for {symbol}")
                        self.broker.close_position(symbol)
            
            # Check risk alerts
            alerts = self.risk_manager.check_risk_limits(
                account_value=account.equity,
                positions=positions,
            )
            
            for alert in alerts:
                if alert.level == "CRITICAL":
                    logger.critical(f"RISK ALERT: {alert.message}")
                    # Could implement auto-liquidation here
                else:
                    logger.warning(f"Risk alert: {alert.message}")
            
            # Record portfolio value for drawdown tracking
            self.risk_manager.record_portfolio_value(account.equity)
            
        except Exception as e:
            logger.error(f"Risk management update error: {e}")
    
    def get_status(self) -> Dict:
        """Get current trading system status"""
        if not self._initialized:
            return {"status": "not_initialized"}
        
        try:
            account = self.broker.get_account()
            positions = self.broker.get_positions()
            orders = self.broker.get_open_orders()
            
            # Calculate portfolio metrics
            total_value = account.equity
            cash_pct = account.cash / total_value * 100 if total_value > 0 else 0
            
            return {
                "status": "active",
                "mode": self.config.mode.value,
                "account": {
                    "cash": account.cash,
                    "equity": total_value,
                    "buying_power": account.buying_power,
                    "cash_pct": cash_pct,
                },
                "positions": {
                    "count": len(positions),
                    "symbols": list(positions.keys()),
                    "details": {s: {"qty": p.quantity, "value": p.market_value} for s, p in positions.items()},
                },
                "orders": {
                    "open": len(orders),
                },
                "history": {
                    "signals": len(self._signals_history),
                    "executions": len(self._execution_history),
                },
                "risk": {
                    "daily_pnl_pct": self.risk_manager.daily_pnl_pct,
                    "drawdown_pct": self.risk_manager.current_drawdown_pct,
                },
            }
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def get_trading_summary(self) -> Dict:
        """Get trading performance summary"""
        if not self._execution_history:
            return {"message": "No trading history"}
        
        # Calculate basic stats
        total_signals = len(self._signals_history)
        total_executions = len(self._execution_history)
        successful = len([e for e in self._execution_history if e["result"]["success"]])
        
        buy_count = len([s for s in self._signals_history if s.signal == SignalType.BUY])
        sell_count = len([s for s in self._signals_history if s.signal == SignalType.SELL])
        
        return {
            "signals": {
                "total": total_signals,
                "buy": buy_count,
                "sell": sell_count,
            },
            "executions": {
                "total": total_executions,
                "successful": successful,
                "success_rate": successful / total_executions * 100 if total_executions > 0 else 0,
            },
        }


class TradingSystemBuilder:
    """
    Builder for creating TradingSystem instances with fluent API.
    
    Usage:
        system = (TradingSystemBuilder()
            .with_mode(TradingMode.PAPER)
            .with_capital(100000)
            .with_position_sizing(PositionSizingMethod.RISK_PARITY)
            .with_risk_rules(max_daily_loss_pct=0.02)
            .build())
    """
    
    def __init__(self):
        self._config = TradingConfig()
        self._broker: Optional[BaseBroker] = None
    
    def with_mode(self, mode: TradingMode) -> "TradingSystemBuilder":
        self._config.mode = mode
        return self
    
    def with_capital(self, capital: float) -> "TradingSystemBuilder":
        self._config.initial_capital = capital
        return self
    
    def with_position_sizing(self, method: PositionSizingMethod) -> "TradingSystemBuilder":
        self._config.position_sizing = method
        return self
    
    def with_max_position_pct(self, pct: float) -> "TradingSystemBuilder":
        self._config.max_position_pct = pct
        return self
    
    def with_max_positions(self, count: int) -> "TradingSystemBuilder":
        self._config.max_positions = count
        return self
    
    def with_risk_rules(
        self,
        stop_loss_pct: Optional[float] = None,
        take_profit_pct: Optional[float] = None,
        max_daily_loss_pct: Optional[float] = None,
        max_drawdown_pct: Optional[float] = None,
    ) -> "TradingSystemBuilder":
        if stop_loss_pct:
            self._config.default_stop_loss_pct = stop_loss_pct
        if take_profit_pct:
            self._config.default_take_profit_pct = take_profit_pct
        if max_daily_loss_pct:
            self._config.max_daily_loss_pct = max_daily_loss_pct
        if max_drawdown_pct:
            self._config.max_drawdown_pct = max_drawdown_pct
        return self
    
    def with_min_confidence(self, confidence: float) -> "TradingSystemBuilder":
        self._config.min_signal_confidence = confidence
        return self
    
    def with_broker(self, broker: BaseBroker) -> "TradingSystemBuilder":
        self._broker = broker
        return self
    
    def build(self) -> TradingSystem:
        return TradingSystem(
            config=self._config,
            broker=self._broker,
        )