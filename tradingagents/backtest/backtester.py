"""
Backtester - Strategy backtesting engine with performance analysis.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any, Tuple
import pandas as pd
import numpy as np
import logging
from pathlib import Path
import json

logger = logging.getLogger(__name__)


@dataclass
class BacktestConfig:
    """Backtest configuration"""
    initial_capital: float = 100000
    commission: float = 0.001          # 0.1% commission
    slippage: float = 0.0005           # 0.05% slippage
    risk_free_rate: float = 0.02       # 2% annual risk-free rate
    benchmark_symbol: str = "SPY"       # Benchmark for comparison
    
    # Position limits
    max_position_pct: float = 0.10     # Max 10% per position
    max_positions: int = 20             # Max number of positions
    
    # Data settings
    price_field: str = "Close"          # Price field to use
    volume_field: str = "Volume"


@dataclass
class Trade:
    """Trade record"""
    timestamp: datetime
    symbol: str
    side: str              # "BUY" or "SELL"
    quantity: int
    price: float
    commission: float
    slippage: float
    pnl: float = 0.0       # Realized PnL (for sells)
    pnl_pct: float = 0.0   # PnL percentage
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "symbol": self.symbol,
            "side": self.side,
            "quantity": self.quantity,
            "price": self.price,
            "commission": self.commission,
            "slippage": self.slippage,
            "pnl": self.pnl,
            "pnl_pct": self.pnl_pct,
        }


@dataclass
class Position:
    """Position during backtest"""
    symbol: str
    quantity: int
    avg_cost: float
    entry_date: datetime
    
    def market_value(self, price: float) -> float:
        """Calculate market value"""
        return self.quantity * price
    
    def unrealized_pnl(self, price: float) -> float:
        """Calculate unrealized PnL"""
        return (price - self.avg_cost) * self.quantity
    
    def unrealized_pnl_pct(self, price: float) -> float:
        """Calculate unrealized PnL percentage"""
        if self.avg_cost == 0:
            return 0
        return (price - self.avg_cost) / self.avg_cost


class Backtester:
    """
    Event-driven backtest engine.
    
    Features:
    - Multi-asset backtesting
    - Commission and slippage modeling
    - Performance metrics calculation
    - Benchmark comparison
    - Detailed trade logging
    """
    
    def __init__(self, config: BacktestConfig):
        """
        Initialize backtester.
        
        Args:
            config: Backtest configuration
        """
        self.config = config
        
        # State
        self.cash = config.initial_capital
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.equity_curve: List[Dict] = []
        self.daily_returns: List[float] = []
        
        # Performance tracking
        self.total_commission = 0.0
        self.total_slippage = 0.0
        self.winning_trades = 0
        self.losing_trades = 0
    
    def run(
        self,
        data: pd.DataFrame,
        strategy: Callable,
        symbols: Optional[List[str]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict:
        """
        Run backtest on historical data.
        
        Args:
            data: Historical OHLCV data
                   - If single symbol: DataFrame with DatetimeIndex
                   - If multiple symbols: DataFrame with MultiIndex (symbol, date)
            strategy: Strategy function that returns signals
                      Signature: strategy(data, date, current_positions) -> Dict[symbol, signal]
                      Signal: "BUY", "SELL", or "HOLD"
            symbols: List of symbols to trade (optional)
            start_date: Start date for backtest
            end_date: End date for backtest
            
        Returns:
            Dictionary with backtest results
        """
        # Reset state
        self._reset()
        
        # Determine data structure
        if isinstance(data.index, pd.MultiIndex):
            # Multi-symbol data
            dates = data.index.get_level_values(1).unique().sort_values()
            if symbols is None:
                symbols = data.index.get_level_values(0).unique().tolist()
        else:
            # Single symbol data
            dates = data.index.sort_values()
            if symbols is None:
                symbols = [data.columns[0]] if data.columns else ["UNKNOWN"]
        
        # Filter dates
        if start_date:
            dates = dates[dates >= pd.Timestamp(start_date)]
        if end_date:
            dates = dates[dates <= pd.Timestamp(end_date)]
        
        logger.info(f"Running backtest from {dates[0]} to {dates[-1]}")
        logger.info(f"Symbols: {symbols}")
        
        # Main backtest loop
        prev_equity = self.config.initial_capital
        
        for date in dates:
            # Get current prices
            current_prices = self._get_prices(data, date, symbols)
            
            # Check pending orders (limit/stop orders if implemented)
            
            # Run strategy
            try:
                signals = strategy(data, date, self.positions)
            except Exception as e:
                logger.error(f"Strategy error on {date}: {e}")
                signals = {}
            
            # Execute signals
            self._execute_signals(signals, current_prices, date)
            
            # Calculate daily equity
            equity = self._calculate_equity(current_prices)
            
            # Record equity curve
            self.equity_curve.append({
                "date": date,
                "equity": equity,
                "cash": self.cash,
                "positions": {s: p.quantity for s, p in self.positions.items()},
                "position_value": equity - self.cash,
            })
            
            # Calculate daily return
            daily_return = (equity - prev_equity) / prev_equity
            self.daily_returns.append(daily_return)
            prev_equity = equity
        
        # Generate report
        return self._generate_report()
    
    def _reset(self):
        """Reset backtest state"""
        self.cash = self.config.initial_capital
        self.positions = {}
        self.trades = []
        self.equity_curve = []
        self.daily_returns = []
        self.total_commission = 0.0
        self.total_slippage = 0.0
        self.winning_trades = 0
        self.losing_trades = 0
    
    def _get_prices(self, data: pd.DataFrame, date: datetime, symbols: List[str]) -> Dict[str, float]:
        """Get prices for all symbols at a given date"""
        prices = {}
        price_field = self.config.price_field
        
        if isinstance(data.index, pd.MultiIndex):
            for symbol in symbols:
                try:
                    prices[symbol] = float(data.loc[(symbol, date), price_field])
                except (KeyError, IndexError):
                    pass
        else:
            # Single symbol
            try:
                symbol = symbols[0] if symbols else "UNKNOWN"
                prices[symbol] = float(data.loc[date, price_field])
            except (KeyError, IndexError):
                pass
        
        return prices
    
    def _execute_signals(
        self,
        signals: Dict[str, str],
        prices: Dict[str, float],
        date: datetime,
    ):
        """Execute trading signals"""
        for symbol, signal in signals.items():
            if symbol not in prices:
                continue
            
            price = prices[symbol]
            
            if signal == "BUY":
                self._execute_buy(symbol, price, date)
            elif signal == "SELL":
                self._execute_sell(symbol, price, date)
    
    def _execute_buy(self, symbol: str, price: float, date: datetime):
        """Execute a buy order"""
        # Check position limit
        if len(self.positions) >= self.config.max_positions and symbol not in self.positions:
            return
        
        # Calculate position size
        max_position_value = self.cash * self.config.max_position_pct
        shares_to_buy = int(max_position_value / price)
        
        if shares_to_buy <= 0:
            return
        
        # Calculate costs
        execution_price = price * (1 + self.config.slippage)
        trade_value = execution_price * shares_to_buy
        commission = trade_value * self.config.commission
        
        total_cost = trade_value + commission
        
        if total_cost > self.cash:
            # Adjust shares to available cash
            shares_to_buy = int(self.cash / (execution_price * (1 + self.config.commission)))
            if shares_to_buy <= 0:
                return
            trade_value = execution_price * shares_to_buy
            commission = trade_value * self.config.commission
            total_cost = trade_value + commission
        
        # Execute trade
        self.cash -= total_cost
        
        if symbol in self.positions:
            # Add to existing position
            pos = self.positions[symbol]
            total_cost_basis = pos.avg_cost * pos.quantity + trade_value
            total_shares = pos.quantity + shares_to_buy
            pos.avg_cost = total_cost_basis / total_shares
            pos.quantity = total_shares
        else:
            # Create new position
            self.positions[symbol] = Position(
                symbol=symbol,
                quantity=shares_to_buy,
                avg_cost=execution_price,
                entry_date=date,
            )
        
        # Record trade
        self.trades.append(Trade(
            timestamp=date,
            symbol=symbol,
            side="BUY",
            quantity=shares_to_buy,
            price=execution_price,
            commission=commission,
            slippage=execution_price - price,
        ))
        
        self.total_commission += commission
        self.total_slippage += (execution_price - price) * shares_to_buy
    
    def _execute_sell(self, symbol: str, price: float, date: datetime):
        """Execute a sell order"""
        if symbol not in self.positions:
            return
        
        pos = self.positions[symbol]
        
        # Calculate proceeds
        execution_price = price * (1 - self.config.slippage)
        trade_value = execution_price * pos.quantity
        commission = trade_value * self.config.commission
        
        net_proceeds = trade_value - commission
        
        # Calculate realized PnL
        cost_basis = pos.avg_cost * pos.quantity
        realized_pnl = net_proceeds - cost_basis
        realized_pnl_pct = realized_pnl / cost_basis if cost_basis > 0 else 0
        
        # Execute trade
        self.cash += net_proceeds
        
        # Record trade
        self.trades.append(Trade(
            timestamp=date,
            symbol=symbol,
            side="SELL",
            quantity=pos.quantity,
            price=execution_price,
            commission=commission,
            slippage=price - execution_price,
            pnl=realized_pnl,
            pnl_pct=realized_pnl_pct,
        ))
        
        # Update statistics
        if realized_pnl > 0:
            self.winning_trades += 1
        else:
            self.losing_trades += 1
        
        self.total_commission += commission
        self.total_slippage += (price - execution_price) * pos.quantity
        
        # Remove position
        del self.positions[symbol]
    
    def _calculate_equity(self, prices: Dict[str, float]) -> float:
        """Calculate total equity"""
        equity = self.cash
        
        for symbol, pos in self.positions.items():
            if symbol in prices:
                equity += pos.market_value(prices[symbol])
        
        return equity
    
    def _generate_report(self) -> Dict:
        """Generate comprehensive backtest report"""
        if not self.equity_curve:
            return {"error": "No equity curve data"}
        
        # Convert to DataFrame for analysis
        equity_df = pd.DataFrame(self.equity_curve)
        equity_df.set_index('date', inplace=True)
        
        # Calculate returns
        returns = pd.Series(self.daily_returns)
        
        # Performance metrics
        initial_capital = self.config.initial_capital
        final_equity = equity_df['equity'].iloc[-1]
        total_return = (final_equity / initial_capital) - 1
        
        # Annualized metrics
        trading_days = len(returns)
        years = trading_days / 252
        annual_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0
        
        # Risk metrics
        volatility = returns.std() * np.sqrt(252) if len(returns) > 1 else 0
        
        # Sharpe ratio
        excess_return = annual_return - self.config.risk_free_rate
        sharpe_ratio = excess_return / volatility if volatility > 0 else 0
        
        # Sortino ratio (downside deviation)
        downside_returns = returns[returns < 0]
        downside_std = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 1 else 0
        sortino_ratio = excess_return / downside_std if downside_std > 0 else 0
        
        # Drawdown
        equity_series = equity_df['equity']
        rolling_max = equity_series.cummax()
        drawdown = (equity_series - rolling_max) / rolling_max
        max_drawdown = drawdown.min()
        
        # Calmar ratio
        calmar_ratio = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0
        
        # Trade statistics
        total_trades = len(self.trades)
        buy_trades = len([t for t in self.trades if t.side == "BUY"])
        sell_trades = len([t for t in self.trades if t.side == "SELL"])
        
        win_rate = self.winning_trades / sell_trades if sell_trades > 0 else 0
        
        # Average trade
        sell_trades_list = [t for t in self.trades if t.side == "SELL"]
        avg_pnl = np.mean([t.pnl for t in sell_trades_list]) if sell_trades_list else 0
        avg_win = np.mean([t.pnl for t in sell_trades_list if t.pnl > 0]) if self.winning_trades > 0 else 0
        avg_loss = np.mean([t.pnl for t in sell_trades_list if t.pnl < 0]) if self.losing_trades > 0 else 0
        
        # Profit factor
        total_wins = sum(t.pnl for t in sell_trades_list if t.pnl > 0)
        total_losses = abs(sum(t.pnl for t in sell_trades_list if t.pnl < 0))
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
        
        return {
            # Summary
            "summary": {
                "initial_capital": initial_capital,
                "final_equity": final_equity,
                "total_return": total_return,
                "total_return_pct": total_return * 100,
                "annual_return": annual_return * 100,
                "trading_days": trading_days,
            },
            
            # Risk metrics
            "risk_metrics": {
                "volatility": volatility,
                "sharpe_ratio": sharpe_ratio,
                "sortino_ratio": sortino_ratio,
                "max_drawdown": max_drawdown,
                "max_drawdown_pct": max_drawdown * 100,
                "calmar_ratio": calmar_ratio,
            },
            
            # Trade statistics
            "trade_stats": {
                "total_trades": total_trades,
                "buy_trades": buy_trades,
                "sell_trades": sell_trades,
                "winning_trades": self.winning_trades,
                "losing_trades": self.losing_trades,
                "win_rate": win_rate,
                "win_rate_pct": win_rate * 100,
                "avg_pnl": avg_pnl,
                "avg_win": avg_win,
                "avg_loss": avg_loss,
                "profit_factor": profit_factor,
            },
            
            # Costs
            "costs": {
                "total_commission": self.total_commission,
                "total_slippage": self.total_slippage,
                "commission_pct": self.total_commission / final_equity * 100 if final_equity > 0 else 0,
            },
            
            # Time series
            "equity_curve": equity_df['equity'].to_dict(),
            "drawdown_series": drawdown.to_dict(),
            "daily_returns": returns.tolist(),
            
            # Trade history
            "trades": [t.to_dict() for t in self.trades],
        }
    
    def get_equity_curve_df(self) -> pd.DataFrame:
        """Get equity curve as DataFrame"""
        return pd.DataFrame(self.equity_curve).set_index('date')
    
    def get_trades_df(self) -> pd.DataFrame:
        """Get trades as DataFrame"""
        return pd.DataFrame([t.to_dict() for t in self.trades])
    
    def save_results(self, output_dir: str):
        """Save backtest results to files"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Save equity curve
        equity_df = self.get_equity_curve_df()
        equity_df.to_csv(output_path / "equity_curve.csv")
        
        # Save trades
        trades_df = self.get_trades_df()
        trades_df.to_csv(output_path / "trades.csv", index=False)
        
        # Save report
        report = self._generate_report()
        with open(output_path / "backtest_report.json", 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Saved backtest results to {output_path}")


def calculate_metrics(returns: pd.Series, risk_free_rate: float = 0.02) -> Dict:
    """
    Calculate performance metrics from a returns series.
    
    Args:
        returns: Daily returns series
        risk_free_rate: Annual risk-free rate
        
    Returns:
        Dictionary of performance metrics
    """
    if len(returns) == 0:
        return {}
    
    # Basic metrics
    total_return = (1 + returns).prod() - 1
    annual_return = (1 + total_return) ** (252 / len(returns)) - 1
    volatility = returns.std() * np.sqrt(252)
    
    # Risk-adjusted metrics
    excess_return = annual_return - risk_free_rate
    sharpe = excess_return / volatility if volatility > 0 else 0
    
    # Downside metrics
    downside = returns[returns < 0]
    downside_std = downside.std() * np.sqrt(252) if len(downside) > 0 else 0
    sortino = excess_return / downside_std if downside_std > 0 else 0
    
    # Drawdown
    cumulative = (1 + returns).cumprod()
    rolling_max = cumulative.cummax()
    drawdown = (cumulative - rolling_max) / rolling_max
    max_dd = drawdown.min()
    
    return {
        "total_return": total_return,
        "annual_return": annual_return,
        "volatility": volatility,
        "sharpe_ratio": sharpe,
        "sortino_ratio": sortino,
        "max_drawdown": max_dd,
        "calmar_ratio": annual_return / abs(max_dd) if max_dd != 0 else 0,
    }