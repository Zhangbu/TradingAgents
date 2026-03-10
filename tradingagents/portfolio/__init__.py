"""
Portfolio Management Layer - Position sizing and allocation.

This module provides:
- Position sizing strategies (Kelly, Risk Parity, Equal Weight)
- Portfolio allocation engine
- Portfolio tracking and rebalancing
"""

from .position_manager import (
    PositionManager,
    Signal,
    AllocationMethod,
)

__all__ = [
    "PositionManager",
    "Signal",
    "AllocationMethod",
]