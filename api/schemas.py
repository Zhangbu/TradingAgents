"""
Pydantic schemas for API request/response models.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ==================== Enums ====================

class SignalType(str, Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class PositionStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"


class TaskType(str, Enum):
    ANALYSIS = "analysis"
    SCAN = "scan"
    REBALANCE = "rebalance"


# ==================== Request Schemas ====================

class AnalysisRequest(BaseModel):
    """Request for running analysis on a symbol."""
    symbol: str = Field(..., description="Stock symbol to analyze")
    date: Optional[str] = Field(None, description="Analysis date (YYYY-MM-DD)")
    analysts: Optional[List[str]] = Field(
        default=["market", "news", "fundamentals"],
        description="List of analysts to use"
    )
    research_depth: Optional[int] = Field(default=1, ge=1, le=5)


class OrderRequest(BaseModel):
    """Request for placing an order."""
    symbol: str = Field(..., description="Stock symbol")
    side: OrderSide = Field(..., description="Buy or sell")
    quantity: float = Field(..., gt=0, description="Number of shares")
    order_type: OrderType = Field(default=OrderType.MARKET, description="Order type")
    limit_price: Optional[float] = Field(None, gt=0, description="Limit price for limit orders")
    stop_price: Optional[float] = Field(None, gt=0, description="Stop price for stop orders")


class SignalRequest(BaseModel):
    """Request for creating a trading signal."""
    symbol: str = Field(..., description="Stock symbol")
    signal_type: SignalType = Field(..., description="Signal type")
    confidence: float = Field(..., ge=0, le=1, description="Signal confidence (0-1)")
    reason: Optional[str] = Field(None, description="Reason for the signal")


class PositionUpdateRequest(BaseModel):
    """Request for updating a position."""
    stop_loss: Optional[float] = Field(None, gt=0, description="Stop loss price")
    take_profit: Optional[float] = Field(None, gt=0, description="Take profit price")


class ConfigUpdateRequest(BaseModel):
    """Request for updating system configuration."""
    key: str = Field(..., description="Configuration key")
    value: str = Field(..., description="Configuration value")
    description: Optional[str] = Field(None, description="Configuration description")


class TaskCreateRequest(BaseModel):
    """Request for creating a scheduled task."""
    name: str = Field(..., description="Task name")
    task_type: TaskType = Field(..., description="Task type")
    schedule: str = Field(..., description="Cron expression for schedule")
    config: Optional[Dict[str, Any]] = Field(default={}, description="Task configuration")


class ScannerRequest(BaseModel):
    """Request for running stock scanner."""
    filters: Optional[Dict[str, Any]] = Field(default={}, description="Scanner filters")
    symbols: Optional[List[str]] = Field(None, description="List of symbols to scan (optional)")


# ==================== Response Schemas ====================

class PositionResponse(BaseModel):
    """Position response model."""
    id: int
    symbol: str
    quantity: float
    entry_price: float
    current_price: Optional[float]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    status: str
    opened_at: datetime
    closed_at: Optional[datetime]
    pnl: float
    market_value: Optional[float] = None
    
    class Config:
        from_attributes = True


class TradeResponse(BaseModel):
    """Trade response model."""
    id: int
    symbol: str
    side: str
    order_type: str
    quantity: float
    price: float
    commission: float
    status: str
    executed_at: datetime
    
    class Config:
        from_attributes = True


class SignalResponse(BaseModel):
    """Signal response model."""
    id: int
    symbol: str
    signal_type: str
    confidence: float
    reason: Optional[str]
    source: str
    status: str
    created_at: datetime
    executed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class AnalysisResponse(BaseModel):
    """Analysis response model."""
    symbol: str
    date: str
    decision: Optional[str]
    confidence: Optional[float]
    reports: Dict[str, str] = {}
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AccountResponse(BaseModel):
    """Account information response."""
    cash: float
    equity: float
    positions_value: float
    unrealized_pnl: float
    realized_pnl: float
    buying_power: float
    positions: List[PositionResponse] = []


class SystemStatusResponse(BaseModel):
    """System status response."""
    status: str  # running, stopped, error
    mode: str  # paper, live
    uptime: float
    last_analysis: Optional[datetime]
    pending_signals: int
    open_positions: int
    daily_pnl: float


class ConfigResponse(BaseModel):
    """Configuration response model."""
    id: int
    key: str
    value: Optional[str]
    description: Optional[str]
    updated_at: datetime
    
    class Config:
        from_attributes = True


class TaskResponse(BaseModel):
    """Scheduled task response model."""
    id: int
    name: str
    task_type: str
    schedule: str
    enabled: bool
    config: Optional[str]
    last_run: Optional[datetime]
    next_run: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class LogResponse(BaseModel):
    """System log response model."""
    id: int
    level: str
    module: Optional[str]
    message: str
    details: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class ScannerResultResponse(BaseModel):
    """Scanner result response model."""
    symbol: str
    score: float
    signals: List[str]
    metrics: Dict[str, Any]
    recommendation: str


class WebSocketMessage(BaseModel):
    """WebSocket message model."""
    type: str  # log, signal, trade, status, analysis
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SuccessResponse(BaseModel):
    """Generic success response."""
    success: bool = True
    message: str
    data: Optional[Dict[str, Any]] = None