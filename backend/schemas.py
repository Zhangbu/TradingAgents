"""Pydantic schemas for API request/response validation."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


# Re-export enums from models for convenience
class ProposalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TradeSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class PositionSide(str, Enum):
    LONG = "long"
    SHORT = "short"


class ExchangeType(str, Enum):
    PAPER = "paper"
    BINANCE = "binance"
    OKX = "okx"
    FUTU = "futu"
    IBKR = "ibkr"


class AgentType(str, Enum):
    MARKET_ANALYST = "market_analyst"
    SENTIMENT_ANALYST = "sentiment_analyst"
    NEWS_ANALYST = "news_analyst"
    FUNDAMENTALS_ANALYST = "fundamentals_analyst"
    BULL_RESEARCHER = "bull_researcher"
    BEAR_RESEARCHER = "bear_researcher"
    TRADER = "trader"
    RISK_AGGRESSIVE = "risk_aggressive"
    RISK_CONSERVATIVE = "risk_conservative"
    RISK_NEUTRAL = "risk_neutral"
    RESEARCH_MANAGER = "research_manager"
    RISK_MANAGER = "risk_manager"


# ==================== User Schemas ====================

class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: Optional[str] = Field(None, max_length=100)


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)


class UserResponse(UserBase):
    id: int
    is_active: bool
    is_admin: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== Proposal Schemas ====================

class ProposalBase(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)
    side: TradeSide
    quantity: float = Field(..., gt=0)
    proposed_price: Optional[float] = Field(None, gt=0)
    exchange: ExchangeType = ExchangeType.PAPER


class ProposalCreate(ProposalBase):
    """Schema for creating a new proposal from agent."""
    reasoning: Optional[str] = None
    confidence: Optional[float] = Field(None, ge=0, le=1)
    market_report: Optional[str] = None
    sentiment_report: Optional[str] = None
    news_report: Optional[str] = None
    fundamentals_report: Optional[str] = None
    investment_debate: Optional[str] = None
    risk_debate: Optional[str] = None


class ProposalUpdate(BaseModel):
    """Schema for updating proposal status."""
    status: Optional[ProposalStatus] = None
    rejection_reason: Optional[str] = None


class ProposalApproval(BaseModel):
    """Schema for approving/rejecting a proposal."""
    approved: bool
    rejection_reason: Optional[str] = None


class ProposalResponse(ProposalBase):
    """Full proposal response."""
    id: int
    status: ProposalStatus
    reasoning: Optional[str] = None
    confidence: Optional[float] = None
    
    # User approval
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    
    # Execution
    executed_price: Optional[float] = None
    executed_at: Optional[datetime] = None
    execution_error: Optional[str] = None
    order_id: Optional[str] = None
    
    # Timestamps
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProposalListResponse(BaseModel):
    """Paginated proposal list response."""
    proposals: List[ProposalResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ==================== Position Schemas ====================

class PositionBase(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)
    side: PositionSide
    quantity: float = Field(..., gt=0)
    entry_price: float = Field(..., gt=0)
    exchange: ExchangeType = ExchangeType.PAPER


class PositionCreate(PositionBase):
    """Schema for creating a new position."""
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    proposal_id: Optional[int] = None


class PositionUpdate(BaseModel):
    """Schema for updating a position."""
    current_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None


class PositionClose(BaseModel):
    """Schema for closing a position."""
    reason: Optional[str] = None


class PositionResponse(PositionBase):
    """Full position response."""
    id: int
    current_price: Optional[float] = None
    unrealized_pnl: float
    unrealized_pnl_percent: float
    realized_pnl: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    is_open: bool
    opened_at: datetime
    closed_at: Optional[datetime] = None
    close_reason: Optional[str] = None
    proposal_id: Optional[int] = None

    class Config:
        from_attributes = True


class PositionListResponse(BaseModel):
    """Paginated position list response."""
    positions: List[PositionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class PortfolioSummary(BaseModel):
    """Portfolio summary response."""
    total_positions: int
    total_value: float
    total_unrealized_pnl: float
    total_realized_pnl: float
    positions_by_exchange: Dict[str, int]
    positions_by_side: Dict[str, int]


# ==================== Trade History Schemas ====================

class TradeHistoryResponse(BaseModel):
    """Trade history response."""
    id: int
    symbol: str
    side: TradeSide
    quantity: float
    price: float
    total_value: float
    exchange: ExchangeType
    order_id: Optional[str] = None
    realized_pnl: Optional[float] = None
    position_id: Optional[int] = None
    proposal_id: Optional[int] = None
    executed_at: datetime

    class Config:
        from_attributes = True


class TradeHistoryListResponse(BaseModel):
    """Paginated trade history response."""
    trades: List[TradeHistoryResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ==================== Agent Log Schemas ====================

class AgentLogCreate(BaseModel):
    """Schema for creating an agent log."""
    proposal_id: Optional[int] = None
    agent_type: AgentType
    agent_name: Optional[str] = None
    message: str
    reasoning: Optional[str] = None
    action: Optional[str] = None
    structured_data: Optional[Dict[str, Any]] = None


class AgentLogResponse(BaseModel):
    """Agent log response."""
    id: int
    proposal_id: Optional[int] = None
    agent_type: AgentType
    agent_name: Optional[str] = None
    message: str
    reasoning: Optional[str] = None
    action: Optional[str] = None
    structured_data: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== Agent Run Schemas ====================

class AgentRunRequest(BaseModel):
    """Request to run agent analysis."""
    symbol: str = Field(..., min_length=1, max_length=20)
    trade_date: Optional[str] = Field(None, description="Trade date in YYYY-MM-DD format")
    exchange: ExchangeType = ExchangeType.PAPER
    selected_analysts: List[str] = Field(
        default=["market", "social", "news", "fundamentals"],
        description="List of analysts to include"
    )
    auto_approve: bool = Field(
        default=False,
        description="Auto-approve proposals (bypass HITL)"
    )
    max_debate_rounds: int = Field(default=1, ge=1, le=5)
    max_risk_discuss_rounds: int = Field(default=1, ge=1, le=5)


class AgentRunResponse(BaseModel):
    """Response from agent run."""
    run_id: str
    symbol: str
    status: str
    message: str
    proposal_id: Optional[int] = None


class AgentThinkingStream(BaseModel):
    """Schema for streaming agent thinking."""
    run_id: str
    agent_type: AgentType
    agent_name: str
    message: str
    reasoning: Optional[str] = None
    action: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ==================== Kill Switch Schemas ====================

class KillSwitchRequest(BaseModel):
    """Request to activate kill switch."""
    reason: Optional[str] = None
    close_all_positions: bool = False


class KillSwitchResponse(BaseModel):
    """Kill switch status response."""
    is_active: bool
    activated_at: Optional[datetime] = None
    activated_by: Optional[str] = None
    reason: Optional[str] = None
    positions_closed: int = 0


# ==================== WebSocket Message Schemas ====================

class WSMessageBase(BaseModel):
    """Base WebSocket message."""
    type: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class WSProposalUpdate(WSMessageBase):
    """WebSocket proposal update message."""
    type: str = "proposal_update"
    proposal: ProposalResponse


class WSPositionUpdate(WSMessageBase):
    """WebSocket position update message."""
    type: str = "position_update"
    position: PositionResponse


class WSAgentThinking(WSMessageBase):
    """WebSocket agent thinking message."""
    type: str = "agent_thinking"
    run_id: str
    agent_type: AgentType
    agent_name: str
    message: str
    reasoning: Optional[str] = None


class WSError(WSMessageBase):
    """WebSocket error message."""
    type: str = "error"
    message: str
    details: Optional[Dict[str, Any]] = None


# ==================== Health Check Schemas ====================

class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    database: str
    llm_provider: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ==================== Error Schemas ====================

class ErrorResponse(BaseModel):
    """Error response."""
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None