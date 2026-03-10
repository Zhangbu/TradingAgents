"""
Execution Layer - Trading execution and broker interfaces.

This module provides:
- Base broker interface for trading operations
- Paper trading simulation
- Real broker integrations (Alpaca, Binance, etc.)
"""

from .base_broker import (
    BaseBroker,
    Order,
    OrderResult,
    OrderSide,
    OrderType,
    Position,
    AccountInfo,
)
from .paper_broker import PaperBroker

# Conditionally import AlpacaBroker if alpaca-py is installed
try:
    from .alpaca_broker import AlpacaBroker
    _ALPACA_AVAILABLE = True
except ImportError:
    _ALPACA_AVAILABLE = False
    AlpacaBroker = None

__all__ = [
    "BaseBroker",
    "Order",
    "OrderResult",
    "OrderSide",
    "OrderType",
    "Position",
    "AccountInfo",
    "PaperBroker",
    "AlpacaBroker",
]

def get_available_brokers():
    """Return list of available broker implementations."""
    brokers = ["PaperBroker"]
    if _ALPACA_AVAILABLE:
        brokers.append("AlpacaBroker")
    return brokers
