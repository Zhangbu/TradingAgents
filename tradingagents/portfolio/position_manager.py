"""
Position Manager - Position sizing and portfolio allocation strategies.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class AllocationMethod(Enum):
    """Portfolio allocation methods"""
    EQUAL_WEIGHT = "equal_weight"
    RISK_PARITY = "risk_parity"
    KELLY = "kelly"
    MIN_VARIANCE = "min_variance"
    CUSTOM = "custom"


@dataclass
class Signal:
    """Trading signal with metadata"""
    symbol: str
    decision: str  # BUY, SELL, HOLD
    confidence: float  # 0.0 - 1.0
    price: float
    volatility: float = 0.0
    expected_return: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Optional metadata
    sector: str = ""
    industry: str = ""
    market_cap: float = 0.0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "symbol": self.symbol,
            "decision": self.decision,
            "confidence": self.confidence,
            "price": self.price,
            "volatility": self.volatility,
            "expected_return": self.expected_return,
            "timestamp": self.timestamp.isoformat(),
            "sector": self.sector,
            "industry": self.industry,
        }


@dataclass
class Allocation:
    """Position allocation result"""
    symbol: str
    shares: int
    value: float
    weight: float
    price: float
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "symbol": self.symbol,
            "shares": self.shares,
            "value": self.value,
            "weight": self.weight,
            "price": self.price,
        }


class PositionManager:
    """
    Position Manager - Handles position sizing and portfolio allocation.
    
    Features:
    - Multiple allocation strategies (Equal Weight, Risk Parity, Kelly, etc.)
    - Position limit enforcement
    - Sector exposure management
    - Risk-adjusted position sizing
    """
    
    def __init__(
        self,
        total_capital: float,
        max_single_position: float = 0.10,    # Max 10% in single position
        max_sector_exposure: float = 0.30,     # Max 30% in single sector
        max_total_exposure: float = 0.95,      # Max 95% total invested
        min_position_size: float = 100,        # Minimum position value
        kelly_fraction: float = 0.25,          # Max Kelly fraction to use
    ):
        """
        Initialize Position Manager.
        
        Args:
            total_capital: Total capital available for trading
            max_single_position: Maximum fraction for single position
            max_sector_exposure: Maximum fraction for single sector
            max_total_exposure: Maximum total portfolio exposure
            min_position_size: Minimum position value in dollars
            kelly_fraction: Maximum fraction of Kelly criterion to use
        """
        self.total_capital = total_capital
        self.max_single_position = max_single_position
        self.max_sector_exposure = max_sector_exposure
        self.max_total_exposure = max_total_exposure
        self.min_position_size = min_position_size
        self.kelly_fraction = kelly_fraction
        
        # Current portfolio state
        self.current_positions: Dict[str, float] = {}  # symbol -> value
        self.sector_allocations: Dict[str, float] = {}  # sector -> value
        
    def calculate_position_size(
        self,
        signal: Signal,
        method: AllocationMethod = AllocationMethod.KELLY,
        current_positions: Optional[Dict[str, float]] = None,
    ) -> int:
        """
        Calculate the number of shares to trade for a single signal.
        
        Args:
            signal: Trading signal
            method: Allocation method to use
            current_positions: Current position values by symbol
            
        Returns:
            Number of shares to trade
        """
        if signal.decision != "BUY":
            return 0
        
        if current_positions is None:
            current_positions = self.current_positions
        
        # Calculate target position value based on method
        if method == AllocationMethod.EQUAL_WEIGHT:
            target_value = self._equal_weight_position(signal, current_positions)
        elif method == AllocationMethod.RISK_PARITY:
            target_value = self._risk_parity_position(signal, current_positions)
        elif method == AllocationMethod.KELLY:
            target_value = self._kelly_position(signal)
        elif method == AllocationMethod.MIN_VARIANCE:
            target_value = self._min_variance_position(signal, current_positions)
        else:
            target_value = self._equal_weight_position(signal, current_positions)
        
        # Apply position limits
        max_value = self.total_capital * self.max_single_position
        target_value = min(target_value, max_value)
        
        # Check minimum position size
        if target_value < self.min_position_size:
            return 0
        
        # Convert to shares
        shares = int(target_value / signal.price)
        
        return shares
    
    def allocate_portfolio(
        self,
        signals: List[Signal],
        method: AllocationMethod = AllocationMethod.RISK_PARITY,
    ) -> List[Allocation]:
        """
        Allocate capital across multiple signals.
        
        Args:
            signals: List of trading signals
            method: Allocation method to use
            
        Returns:
            List of allocation recommendations
        """
        # Filter to BUY signals only
        buy_signals = [s for s in signals if s.decision == "BUY"]
        
        if not buy_signals:
            return []
        
        if method == AllocationMethod.EQUAL_WEIGHT:
            allocations = self._allocate_equal_weight(buy_signals)
        elif method == AllocationMethod.RISK_PARITY:
            allocations = self._allocate_risk_parity(buy_signals)
        elif method == AllocationMethod.KELLY:
            allocations = self._allocate_kelly(buy_signals)
        else:
            allocations = self._allocate_equal_weight(buy_signals)
        
        # Validate and adjust allocations
        allocations = self._validate_allocations(allocations)
        
        return allocations
    
    def _equal_weight_position(
        self,
        signal: Signal,
        current_positions: Dict[str, float],
    ) -> float:
        """Calculate position size using equal weight method"""
        n_positions = len(current_positions) + 1  # Including new position
        return self.total_capital / n_positions
    
    def _risk_parity_position(
        self,
        signal: Signal,
        current_positions: Dict[str, float],
    ) -> float:
        """
        Calculate position size using risk parity.
        Lower volatility = higher allocation.
        """
        if signal.volatility <= 0:
            return self.total_capital * self.max_single_position
        
        # Inverse volatility weight
        inv_vol = 1.0 / signal.volatility
        
        # This is simplified - full implementation would consider
        # all positions and their correlations
        base_weight = inv_vol / (inv_vol + 1)  # Normalized weight
        
        return self.total_capital * min(base_weight, self.max_single_position)
    
    def _kelly_position(self, signal: Signal) -> float:
        """
        Calculate position size using Kelly Criterion.
        
        Kelly formula: f* = (p*b - q) / b
        where:
            p = probability of winning
            q = probability of losing (1-p)
            b = win/loss ratio
        
        Simplified: f* = 2*p - 1 (when b=1)
        """
        # Use confidence as win probability
        win_prob = signal.confidence
        
        # If we have expected return and volatility, estimate win/loss ratio
        if signal.volatility > 0 and signal.expected_return > 0:
            win_loss_ratio = signal.expected_return / signal.volatility
        else:
            win_loss_ratio = 1.0  # Assume 1:1
        
        # Kelly fraction
        q = 1 - win_prob
        kelly = (win_prob * win_loss_ratio - q) / win_loss_ratio
        
        # Apply fractional Kelly and limits
        kelly = max(0, min(kelly, self.kelly_fraction))
        
        return self.total_capital * kelly
    
    def _min_variance_position(
        self,
        signal: Signal,
        current_positions: Dict[str, float],
    ) -> float:
        """
        Calculate position size for minimum variance portfolio.
        This is simplified - full implementation would use covariance matrix.
        """
        if signal.volatility <= 0:
            return self.total_capital * self.max_single_position
        
        # Allocate inversely proportional to variance
        variance = signal.volatility ** 2
        inv_var = 1.0 / variance
        
        # Simplified - assume equal weights for other positions
        weight = inv_var / (inv_var + len(current_positions))
        
        return self.total_capital * min(weight, self.max_single_position)
    
    def _allocate_equal_weight(self, signals: List[Signal]) -> List[Allocation]:
        """Allocate equally across all signals"""
        n = len(signals)
        weight = 1.0 / n
        value_per_position = self.total_capital * weight
        
        allocations = []
        for signal in signals:
            shares = int(value_per_position / signal.price)
            allocations.append(Allocation(
                symbol=signal.symbol,
                shares=shares,
                value=shares * signal.price,
                weight=weight,
                price=signal.price,
            ))
        
        return allocations
    
    def _allocate_risk_parity(self, signals: List[Signal]) -> List[Allocation]:
        """Allocate using risk parity - inverse volatility weighting"""
        # Calculate inverse volatilities
        inv_vols = {}
        for signal in signals:
            vol = signal.volatility if signal.volatility > 0 else 0.01
            inv_vols[signal.symbol] = 1.0 / vol
        
        total_inv_vol = sum(inv_vols.values())
        
        allocations = []
        for signal in signals:
            weight = inv_vols[signal.symbol] / total_inv_vol
            value = self.total_capital * weight
            shares = int(value / signal.price)
            
            allocations.append(Allocation(
                symbol=signal.symbol,
                shares=shares,
                value=shares * signal.price,
                weight=weight,
                price=signal.price,
            ))
        
        return allocations
    
    def _allocate_kelly(self, signals: List[Signal]) -> List[Allocation]:
        """Allocate using Kelly Criterion for each signal"""
        allocations = []
        total_kelly = 0
        
        # Calculate Kelly fraction for each signal
        kelly_weights = {}
        for signal in signals:
            win_prob = signal.confidence
            kelly = max(0, 2 * win_prob - 1)  # Simplified Kelly
            kelly = min(kelly, self.kelly_fraction)
            kelly_weights[signal.symbol] = kelly
            total_kelly += kelly
        
        # Normalize if total exceeds max exposure
        if total_kelly > self.max_total_exposure:
            scale = self.max_total_exposure / total_kelly
            for symbol in kelly_weights:
                kelly_weights[symbol] *= scale
        
        # Create allocations
        for signal in signals:
            weight = kelly_weights[signal.symbol]
            value = self.total_capital * weight
            shares = int(value / signal.price)
            
            allocations.append(Allocation(
                symbol=signal.symbol,
                shares=shares,
                value=shares * signal.price,
                weight=weight,
                price=signal.price,
            ))
        
        return allocations
    
    def _validate_allocations(self, allocations: List[Allocation]) -> List[Allocation]:
        """Validate and adjust allocations to meet constraints"""
        if not allocations:
            return []
        
        # Check total exposure
        total_value = sum(a.value for a in allocations)
        max_total = self.total_capital * self.max_total_exposure
        
        if total_value > max_total:
            # Scale down proportionally
            scale = max_total / total_value
            for alloc in allocations:
                alloc.value *= scale
                alloc.weight *= scale
                alloc.shares = int(alloc.value / alloc.price)
        
        # Check individual position limits
        max_single = self.total_capital * self.max_single_position
        for alloc in allocations:
            if alloc.value > max_single:
                alloc.value = max_single
                alloc.weight = max_single / self.total_capital
                alloc.shares = int(alloc.value / alloc.price)
        
        # Remove positions below minimum
        allocations = [
            a for a in allocations
            if a.value >= self.min_position_size
        ]
        
        return allocations
    
    def update_position(self, symbol: str, value: float, sector: str = ""):
        """Update current position value"""
        # Remove old sector allocation if exists
        for s, v in list(self.sector_allocations.items()):
            if v > 0 and symbol in self.current_positions:
                self.sector_allocations[s] -= self.current_positions.get(symbol, 0)
        
        # Update position
        self.current_positions[symbol] = value
        
        # Update sector allocation
        if sector:
            self.sector_allocations[sector] = self.sector_allocations.get(sector, 0) + value
    
    def remove_position(self, symbol: str, sector: str = ""):
        """Remove a position from tracking"""
        if symbol in self.current_positions:
            value = self.current_positions[symbol]
            
            # Update sector allocation
            if sector and sector in self.sector_allocations:
                self.sector_allocations[sector] -= value
            
            del self.current_positions[symbol]
    
    def get_portfolio_summary(self) -> Dict:
        """Get current portfolio summary"""
        total_position_value = sum(self.current_positions.values())
        cash = self.total_capital - total_position_value
        
        return {
            "total_capital": self.total_capital,
            "position_value": total_position_value,
            "cash": cash,
            "exposure": total_position_value / self.total_capital,
            "num_positions": len(self.current_positions),
            "sector_allocations": self.sector_allocations.copy(),
            "positions": self.current_positions.copy(),
        }
    
    def check_sector_exposure(self, sector: str, new_value: float = 0) -> bool:
        """Check if adding to a sector would exceed limits"""
        current = self.sector_allocations.get(sector, 0)
        total = current + new_value
        
        return total <= self.total_capital * self.max_sector_exposure
    
    def get_available_capital(self) -> float:
        """Get available capital for new positions"""
        total_position_value = sum(self.current_positions.values())
        max_allowed = self.total_capital * self.max_total_exposure
        
        return max(0, max_allowed - total_position_value)
    
    def set_capital(self, total_capital: float):
        """Update total capital"""
        self.total_capital = total_capital
        logger.info(f"Updated total capital to ${total_capital:,.2f}")