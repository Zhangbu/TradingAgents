#!/usr/bin/env python3
"""
Tests for the trading system modules.
"""

import pytest
import sys
import os
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestExecutionModule:
    """Test execution module imports and basic functionality."""
    
    def test_import_base_broker(self):
        """Test importing base broker module."""
        from tradingagents.execution.base_broker import (
            BaseBroker,
            Order,
            OrderSide,
            OrderType,
            Position,
            AccountInfo,
        )
        
        # Test Order creation
        order = Order(
            order_id="test-123",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=100,
        )
        assert order.order_id == "test-123"
        assert order.symbol == "AAPL"
        assert order.side == OrderSide.BUY
    
    def test_import_paper_broker(self):
        """Test importing paper broker."""
        from tradingagents.execution.paper_broker import PaperBroker
        
        broker = PaperBroker(initial_capital=100000)
        assert broker is not None
        
        # Test connect
        result = broker.connect()
        assert result == True
        
        # Test account
        account = broker.get_account()
        assert account.cash == 100000
    
    def test_paper_broker_order_result(self):
        """Test paper broker OrderResult."""
        from tradingagents.execution.paper_broker import PaperBroker
        from tradingagents.execution.base_broker import Order, OrderSide, OrderType
        
        broker = PaperBroker(initial_capital=100000)
        broker.connect()
        
        # Mock the price fetch to avoid network calls
        with patch.object(broker, '_get_current_price', return_value=150.0):
            # Create order
            order = Order(
                order_id="",
                symbol="AAPL",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=10,
            )
            
            result = broker.place_order(order)
            assert result.success == True
            assert result.filled_quantity == 10


class TestPortfolioModule:
    """Test portfolio management module."""
    
    def test_import_position_manager(self):
        """Test importing position manager."""
        from tradingagents.portfolio.position_manager import (
            PositionManager,
            AllocationMethod,
        )
        
        pm = PositionManager(total_capital=100000)
        assert pm is not None
    
    def test_equal_weight_sizing(self):
        """Test equal weight position sizing."""
        from tradingagents.portfolio.position_manager import (
            PositionManager,
            AllocationMethod,
            Signal,
        )
        
        pm = PositionManager(
            total_capital=100000,
            max_single_position=0.10,
        )
        
        signal = Signal(
            symbol="AAPL",
            decision="BUY",
            confidence=0.8,
            price=150.0,
        )
        
        shares = pm.calculate_position_size(
            signal=signal,
            method=AllocationMethod.EQUAL_WEIGHT,
        )
        
        assert shares > 0
        # Should be about 10% of portfolio
        expected_value = 100000 * 0.10
        actual_value = shares * 150.0
        assert abs(actual_value - expected_value) < 1500  # Within one share


class TestRiskModule:
    """Test risk management module."""
    
    def test_import_risk_manager(self):
        """Test importing risk manager."""
        from tradingagents.risk.risk_manager import (
            RiskManager,
            RiskRules,
            RiskAlert,
        )
        
        rules = RiskRules(
            max_single_position=0.10,
            max_daily_loss=0.03,
        )
        
        rm = RiskManager(rules=rules, initial_capital=100000)
        assert rm is not None
    
    def test_check_order(self):
        """Test order risk check."""
        from tradingagents.risk.risk_manager import RiskManager, RiskRules
        
        rules = RiskRules(
            max_single_position=0.10,
            max_position_value=15000,
        )
        
        rm = RiskManager(rules=rules, initial_capital=100000)
        
        # Normal trade should pass
        order = {
            'symbol': 'AAPL',
            'side': 'buy',
            'quantity': 50,
            'price': 150.0,
        }
        approved, reason = rm.check_order(order, {}, {'AAPL': 150.0})
        assert approved == True
        
        # Trade too large should fail
        large_order = {
            'symbol': 'AAPL',
            'side': 'buy',
            'quantity': 1000,
            'price': 150.0,
        }
        approved, reason = rm.check_order(large_order, {}, {'AAPL': 150.0})
        assert approved == False
    
    def test_stop_loss(self):
        """Test stop loss functionality."""
        from tradingagents.risk.risk_manager import RiskManager, RiskRules
        
        rm = RiskManager(rules=RiskRules(), initial_capital=100000)
        
        # Register position with stop loss
        pos_risk = rm.register_position(
            symbol="AAPL",
            quantity=100,
            entry_price=150.0,
            stop_loss_pct=0.05,
        )
        
        assert pos_risk.stop_loss_price == 150.0 * 0.95
        
        # Check not triggered at normal price
        alert = rm.check_stop_loss_take_profit("AAPL", 148.0)
        assert alert is None
        
        # Check triggered when price drops
        alert = rm.check_stop_loss_take_profit("AAPL", 140.0)
        assert alert is not None


class TestBacktestModule:
    """Test backtest module."""
    
    def test_import_backtester(self):
        """Test importing backtester."""
        from tradingagents.backtest.backtester import (
            Backtester,
            BacktestConfig,
        )
        
        config = BacktestConfig(
            initial_capital=100000,
        )
        
        backtester = Backtester(config)
        assert backtester is not None


class TestTradingSystemIntegration:
    """Test trading system integration."""
    
    def test_paper_broker_workflow(self):
        """Test complete workflow with paper broker."""
        from tradingagents.execution.paper_broker import PaperBroker
        from tradingagents.execution.base_broker import Order, OrderSide, OrderType
        
        # Create broker
        broker = PaperBroker(initial_capital=100000)
        broker.connect()
        
        # Mock price
        with patch.object(broker, '_get_current_price', return_value=100.0):
            # Buy
            buy_order = Order(
                order_id="",
                symbol="TEST",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=100,
            )
            result = broker.place_order(buy_order)
            assert result.success == True
            
            # Check position
            positions = broker.get_positions()
            assert any(p.symbol == "TEST" for p in positions)
            
            # Sell
            sell_order = Order(
                order_id="",
                symbol="TEST",
                side=OrderSide.SELL,
                order_type=OrderType.MARKET,
                quantity=100,
            )
            result = broker.place_order(sell_order)
            assert result.success == True
        
        broker.disconnect()
    
    def test_risk_manager_workflow(self):
        """Test risk manager workflow."""
        from tradingagents.risk.risk_manager import RiskManager, RiskRules
        
        rules = RiskRules(
            max_single_position=0.10,
            max_daily_loss=0.03,
            default_stop_loss=0.05,
        )
        
        rm = RiskManager(rules=rules, initial_capital=100000)
        
        # Register position
        rm.register_position("AAPL", 100, 150.0)
        
        # Update price
        rm.update_position("AAPL", 155.0)
        
        # Get report
        report = rm.get_risk_report()
        assert report['capital']['initial'] == 100000
        assert 'AAPL' in report['position_risks']
    
    def test_position_manager_workflow(self):
        """Test position manager workflow."""
        from tradingagents.portfolio.position_manager import (
            PositionManager,
            AllocationMethod,
            Signal,
        )
        
        pm = PositionManager(total_capital=100000)
        
        # Create signals
        signals = [
            Signal(symbol="AAPL", decision="BUY", confidence=0.8, price=150.0),
            Signal(symbol="MSFT", decision="BUY", confidence=0.7, price=300.0),
        ]
        
        # Allocate
        allocations = pm.allocate_portfolio(signals, method=AllocationMethod.EQUAL_WEIGHT)
        
        assert len(allocations) == 2
        assert allocations[0].symbol == "AAPL"
        assert allocations[1].symbol == "MSFT"


def run_tests():
    """Run all tests manually without pytest."""
    print("Running Trading System Tests...\n")
    
    test_classes = [
        TestExecutionModule,
        TestPortfolioModule,
        TestRiskModule,
        TestBacktestModule,
        TestTradingSystemIntegration,
    ]
    
    passed = 0
    failed = 0
    
    for test_class in test_classes:
        print(f"\n{test_class.__name__}:")
        instance = test_class()
        
        for method_name in dir(instance):
            if method_name.startswith('test_'):
                try:
                    method = getattr(instance, method_name)
                    method()
                    print(f"  ✓ {method_name}")
                    passed += 1
                except Exception as e:
                    print(f"  ✗ {method_name}: {e}")
                    failed += 1
    
    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed")
    print(f"{'='*50}")
    
    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)