"""
Backtest System - Strategy backtesting and performance analysis.

This module provides:
- Event-driven backtest engine
- Performance metrics calculation
- Report generation
- Visualization tools
"""

from .backtester import (
    Backtester,
    BacktestConfig,
    Trade,
)

__all__ = [
    "Backtester",
    "BacktestConfig",
    "Trade",
]