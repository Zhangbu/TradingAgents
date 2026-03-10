"""Trading execution module for TradingAgents."""

from tradingagents.execution.base_exchange import (
    AbstractExchange,
    Balance,
    OrderResult,
    OrderSide,
    OrderType,
)
from tradingagents.execution.paper_exchange import PaperExchange
from tradingagents.execution.risk_guard import RiskGuard, RiskConfig, RiskError

# CCXT exchanges (optional, requires ccxt package)
try:
    from tradingagents.execution.ccxt_exchange import CCXTExchange, BinanceExchange, OKXExchange
    CCXT_AVAILABLE = True
except ImportError:
    CCXT_AVAILABLE = False

__all__ = [
    # Base
    "AbstractExchange",
    "Balance",
    "OrderResult",
    "OrderSide",
    "OrderType",
    # Paper trading
    "PaperExchange",
    # Risk management
    "RiskGuard",
    "RiskConfig",
    "RiskError",
    # CCXT (optional)
    "CCXT_AVAILABLE",
]

if CCXT_AVAILABLE:
    __all__.extend(["CCXTExchange", "BinanceExchange", "OKXExchange"])
