#!/usr/bin/env python3
"""
Live Trading Example - Demonstrates the complete trading system.

This example shows how to:
1. Set up the trading system with paper trading
2. Generate signals using trading agents
3. Execute trades with risk management
4. Monitor positions and performance

Usage:
    python examples/live_trading_example.py
"""

import os
import sys
import logging
from datetime import datetime, timezone
from decimal import Decimal

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tradingagents.trading_system import (
    TradingSystem,
    TradingConfig,
    TradingMode,
    TradingSignal,
    SignalType,
    TradingSystemBuilder,
)
from tradingagents.execution import PaperBroker
from tradingagents.portfolio.position_manager import PositionSizingMethod

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def example_basic_usage():
    """Basic usage example with paper trading."""
    print("\n" + "="*60)
    print("Example 1: Basic Paper Trading")
    print("="*60 + "\n")
    
    # Create trading system with builder pattern
    system = (TradingSystemBuilder()
        .with_mode(TradingMode.PAPER)
        .with_capital(100000)
        .with_position_sizing(PositionSizingMethod.EQUAL_WEIGHT)
        .with_max_position_pct(0.10)
        .with_max_positions(5)
        .with_risk_rules(
            stop_loss_pct=0.05,
            take_profit_pct=0.15,
            max_daily_loss_pct=0.03,
        )
        .with_min_confidence(0.6)
        .build())
    
    # Initialize
    if not system.initialize():
        print("Failed to initialize trading system")
        return
    
    try:
        # Create sample signals (in real usage, these come from agents)
        signals = [
            TradingSignal(
                symbol="AAPL",
                signal=SignalType.BUY,
                confidence=0.85,
                reason="Strong earnings, bullish technical pattern",
                stop_loss=170.0,
                take_profit=200.0,
            ),
            TradingSignal(
                symbol="MSFT",
                signal=SignalType.BUY,
                confidence=0.75,
                reason="Cloud growth momentum, AI integration",
            ),
            TradingSignal(
                symbol="GOOGL",
                signal=SignalType.BUY,
                confidence=0.70,
                reason="Search dominance, AI leadership",
            ),
        ]
        
        # Execute signals
        for signal in signals:
            print(f"\nExecuting signal: {signal.signal.value} {signal.symbol}")
            print(f"  Confidence: {signal.confidence:.0%}")
            print(f"  Reason: {signal.reason}")
            
            result = system.execute_signal(signal)
            
            if result.success:
                print(f"  ✓ Success: {result.message}")
                if result.order:
                    print(f"    Order ID: {result.order.order_id}")
                    print(f"    Quantity: {result.order.quantity}")
            else:
                print(f"  ✗ Failed: {result.message}")
        
        # Show status
        print("\n" + "-"*40)
        print("Portfolio Status:")
        status = system.get_status()
        print(f"  Account Equity: ${status['account']['equity']:,.2f}")
        print(f"  Cash: ${status['account']['cash']:,.2f} ({status['account']['cash_pct']:.1f}%)")
        print(f"  Positions: {status['positions']['count']}")
        for symbol, details in status['positions']['details'].items():
            print(f"    - {symbol}: {details['qty']} shares (${details['value']:,.2f})")
        
    finally:
        system.shutdown()


def example_with_alpaca():
    """Example with Alpaca broker (requires API keys)."""
    print("\n" + "="*60)
    print("Example 2: Alpaca Paper Trading (requires API keys)")
    print("="*60 + "\n")
    
    # Check for API keys
    api_key = os.environ.get("ALPACA_API_KEY")
    secret_key = os.environ.get("ALPACA_SECRET_KEY")
    
    if not api_key or not secret_key:
        print("Alpaca API keys not found. Set environment variables:")
        print("  export ALPACA_API_KEY=your_key")
        print("  export ALPACA_SECRET_KEY=your_secret")
        print("\nFalling back to PaperBroker simulation...")
        example_basic_usage()
        return
    
    try:
        from tradingagents.execution import AlpacaBroker
        
        # Create Alpaca broker
        broker = AlpacaBroker(
            api_key=api_key,
            secret_key=secret_key,
            paper=True,  # Always use paper for examples
        )
        
        # Create trading system
        config = TradingConfig(
            mode=TradingMode.PAPER,
            initial_capital=100000,
        )
        
        system = TradingSystem(config=config, broker=broker)
        
        if not system.initialize():
            print("Failed to connect to Alpaca")
            return
        
        try:
            # Get real account info
            status = system.get_status()
            print(f"Connected to Alpaca!")
            print(f"Account Equity: ${status['account']['equity']:,.2f}")
            print(f"Buying Power: ${status['account']['buying_power']:,.2f}")
            
        finally:
            system.shutdown()
            
    except ImportError:
        print("alpaca-py not installed. Install with: pip install alpaca-py")
        print("Falling back to PaperBroker simulation...")
        example_basic_usage()


def example_risk_management():
    """Demonstrate risk management features."""
    print("\n" + "="*60)
    print("Example 3: Risk Management Demo")
    print("="*60 + "\n")
    
    from tradingagents.risk import RiskManager, RiskRules
    from tradingagents.execution import PaperBroker
    
    # Create risk manager with strict rules
    rules = RiskRules(
        max_position_size_pct=0.10,        # Max 10% per position
        max_portfolio_concentration_pct=0.30,  # Max 30% in one sector
        max_daily_loss_pct=0.02,           # Max 2% daily loss
        max_drawdown_pct=0.05,             # Max 5% drawdown
        default_stop_loss_pct=0.03,        # 3% stop loss
    )
    
    risk_mgr = RiskManager(rules=rules)
    
    # Simulate pre-trade checks
    print("Pre-trade Risk Checks:\n")
    
    # Check 1: Normal trade
    check1 = risk_mgr.pre_trade_check(
        symbol="AAPL",
        side="BUY",
        quantity=100,
        price=180.0,
        account_value=100000,
        positions={},
    )
    print(f"Trade 1: BUY 100 AAPL @ $180")
    print(f"  Approved: {check1.approved}")
    print(f"  Message: {check1.message}\n")
    
    # Check 2: Position too large
    check2 = risk_mgr.pre_trade_check(
        symbol="AAPL",
        side="BUY",
        quantity=1000,
        price=180.0,
        account_value=100000,
        positions={},
    )
    print(f"Trade 2: BUY 1000 AAPL @ $180 (too large)")
    print(f"  Approved: {check2.approved}")
    print(f"  Message: {check2.message}\n")
    
    # Check 3: Too many positions
    existing_positions = {
        f"STOCK{i}": type('obj', (object,), {
            'symbol': f"STOCK{i}",
            'quantity': 100,
            'market_value': 10000
        }) for i in range(10)
    }
    check3 = risk_mgr.pre_trade_check(
        symbol="NEW_STOCK",
        side="BUY",
        quantity=100,
        price=100.0,
        account_value=100000,
        positions=existing_positions,
    )
    print(f"Trade 3: BUY NEW_STOCK (already have 10 positions)")
    print(f"  Approved: {check3.approved}")
    print(f"  Message: {check3.message}\n")
    
    # Demonstrate stop loss
    print("Stop Loss Management:\n")
    
    risk_mgr.set_stop_loss("AAPL", stop_price=175.0, take_profit_price=200.0)
    print("Set stop loss for AAPL: Stop=$175, Take Profit=$200")
    
    # Check stop loss trigger
    stop_check = risk_mgr.check_stop_loss(
        symbol="AAPL",
        current_price=172.0,
        entry_price=180.0,
    )
    print(f"Price drops to $172:")
    print(f"  Triggered: {stop_check.triggered}")
    print(f"  Action: {stop_check.action}")


def example_backtest():
    """Demonstrate backtesting."""
    print("\n" + "="*60)
    print("Example 4: Backtesting Demo")
    print("="*60 + "\n")
    
    import pandas as pd
    import numpy as np
    from datetime import datetime, timedelta
    
    from tradingagents.backtest import Backtester, BacktestConfig
    
    # Generate sample price data
    np.random.seed(42)
    dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='B')
    n = len(dates)
    
    # Random walk prices
    returns = np.random.randn(n) * 0.02
    prices = 100 * np.exp(np.cumsum(returns))
    
    data = pd.DataFrame({
        'Close': prices,
        'Volume': np.random.randint(1000000, 10000000, n),
    }, index=dates)
    
    # Simple moving average strategy
    def sma_strategy(data, date, positions):
        """Simple SMA crossover strategy."""
        current_idx = data.index.get_loc(date)
        if current_idx < 20:
            return {}
        
        window = 20
        sma = data['Close'].iloc[current_idx-window:current_idx].mean()
        current_price = data['Close'].iloc[current_idx]
        
        symbol = "STOCK"
        
        if current_price > sma * 1.02 and symbol not in positions:
            return {symbol: "BUY"}
        elif current_price < sma * 0.98 and symbol in positions:
            return {symbol: "SELL"}
        
        return {}
    
    # Run backtest
    config = BacktestConfig(
        initial_capital=100000,
        commission=0.001,
        slippage=0.0005,
    )
    
    backtester = Backtester(config)
    results = backtester.run(data, sma_strategy)
    
    # Print results
    print("Backtest Results:")
    print("-" * 40)
    
    summary = results['summary']
    print(f"Initial Capital: ${summary['initial_capital']:,.2f}")
    print(f"Final Equity: ${summary['final_equity']:,.2f}")
    print(f"Total Return: {summary['total_return_pct']:.2f}%")
    print(f"Annual Return: {summary['annual_return_pct']:.2f}%")
    print(f"Trading Days: {summary['trading_days']}")
    
    print("\nRisk Metrics:")
    risk = results['risk_metrics']
    print(f"  Volatility: {risk['volatility']:.2%}")
    print(f"  Sharpe Ratio: {risk['sharpe_ratio']:.2f}")
    print(f"  Max Drawdown: {risk['max_drawdown_pct']:.2f}%")
    
    print("\nTrade Statistics:")
    trades = results['trade_stats']
    print(f"  Total Trades: {trades['total_trades']}")
    print(f"  Win Rate: {trades['win_rate_pct']:.1f}%")
    print(f"  Profit Factor: {trades['profit_factor']:.2f}")


def main():
    """Run all examples."""
    print("\n" + "#"*60)
    print("# TradingAgents - Live Trading System Examples")
    print("#"*60)
    
    # Run examples
    example_basic_usage()
    example_risk_management()
    example_backtest()
    example_with_alpaca()
    
    print("\n" + "#"*60)
    print("# Examples Complete!")
    print("#"*60 + "\n")


if __name__ == "__main__":
    main()