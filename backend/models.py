"""SQLAlchemy database models for TradingAgents."""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Enum, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from backend.database import Base


class ProposalStatus(str, PyEnum):
    """Trade proposal status."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TradeSide(str, PyEnum):
    """Trade side (buy/sell)."""
    BUY = "buy"
    SELL = "sell"


class PositionSide(str, PyEnum):
    """Position side (long/short)."""
    LONG = "long"
    SHORT = "short"


class ExchangeType(str, PyEnum):
    """Supported exchanges."""
    PAPER = "paper"
    BINANCE = "binance"
    OKX = "okx"
    FUTU = "futu"
    IBKR = "ibkr"


class AgentType(str, PyEnum):
    """Agent types."""
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


class User(Base):
    """User model for authentication and settings."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=True)
    hashed_password = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    proposals = relationship("Proposal", back_populates="user", lazy="dynamic")
    positions = relationship("Position", back_populates="user", lazy="dynamic")

    def __repr__(self):
        return f"<User {self.username}>"


class Proposal(Base):
    """Trade proposal from AI agents, pending human approval."""
    __tablename__ = "proposals"

    id = Column(Integer, primary_key=True, index=True)
    
    # Symbol and trade details
    symbol = Column(String(20), index=True, nullable=False)
    side = Column(Enum(TradeSide), nullable=False)
    quantity = Column(Float, nullable=False)
    proposed_price = Column(Float, nullable=True)  # Limit price or estimated
    exchange = Column(Enum(ExchangeType), default=ExchangeType.PAPER)
    
    # Agent reasoning
    reasoning = Column(Text, nullable=True)  # Full agent analysis
    confidence = Column(Float, nullable=True)  # Agent confidence 0-1
    
    # Status tracking
    status = Column(Enum(ProposalStatus), default=ProposalStatus.PENDING, index=True)
    
    # User approval tracking
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_by = Column(String(50), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    # Execution tracking
    executed_price = Column(Float, nullable=True)
    executed_at = Column(DateTime, nullable=True)
    execution_error = Column(Text, nullable=True)
    order_id = Column(String(100), nullable=True)  # Exchange order ID
    
    # Market context
    market_report = Column(Text, nullable=True)
    sentiment_report = Column(Text, nullable=True)
    news_report = Column(Text, nullable=True)
    fundamentals_report = Column(Text, nullable=True)
    investment_debate = Column(Text, nullable=True)
    risk_debate = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="proposals")
    agent_logs = relationship("AgentLog", back_populates="proposal", lazy="dynamic")

    def __repr__(self):
        return f"<Proposal {self.id}: {self.side.value} {self.quantity} {self.symbol}>"


class Position(Base):
    """Open position tracking."""
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, index=True)
    
    # Position details
    symbol = Column(String(20), index=True, nullable=False)
    side = Column(Enum(PositionSide), nullable=False)
    quantity = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=True)
    
    # PnL tracking
    unrealized_pnl = Column(Float, default=0.0)
    unrealized_pnl_percent = Column(Float, default=0.0)
    realized_pnl = Column(Float, default=0.0)
    
    # Exchange info
    exchange = Column(Enum(ExchangeType), default=ExchangeType.PAPER)
    exchange_position_id = Column(String(100), nullable=True)
    
    # Risk metrics
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    
    # Related proposal
    proposal_id = Column(Integer, ForeignKey("proposals.id"), nullable=True)
    
    # User ownership
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Status
    is_open = Column(Boolean, default=True, index=True)
    closed_at = Column(DateTime, nullable=True)
    close_reason = Column(String(50), nullable=True)
    
    # Timestamps
    opened_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="positions")
    proposal = relationship("Proposal", backref="positions")

    def __repr__(self):
        return f"<Position {self.id}: {self.side.value} {self.quantity} {self.symbol}>"

    def update_pnl(self, current_price: float):
        """Update unrealized PnL based on current price."""
        self.current_price = current_price
        if self.side == PositionSide.LONG:
            self.unrealized_pnl = (current_price - self.entry_price) * self.quantity
            self.unrealized_pnl_percent = ((current_price - self.entry_price) / self.entry_price) * 100
        else:  # SHORT
            self.unrealized_pnl = (self.entry_price - current_price) * self.quantity
            self.unrealized_pnl_percent = ((self.entry_price - current_price) / self.entry_price) * 100


class TradeHistory(Base):
    """Historical record of all completed trades."""
    __tablename__ = "trade_history"

    id = Column(Integer, primary_key=True, index=True)
    
    # Trade details
    symbol = Column(String(20), index=True, nullable=False)
    side = Column(Enum(TradeSide), nullable=False)
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    total_value = Column(Float, nullable=False)
    
    # Exchange info
    exchange = Column(Enum(ExchangeType), default=ExchangeType.PAPER)
    order_id = Column(String(100), nullable=True)
    
    # PnL (for closing trades)
    realized_pnl = Column(Float, nullable=True)
    
    # Related position
    position_id = Column(Integer, ForeignKey("positions.id"), nullable=True)
    
    # Related proposal
    proposal_id = Column(Integer, ForeignKey("proposals.id"), nullable=True)
    
    # User
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Timestamps
    executed_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    position = relationship("Position", backref="trades")
    proposal = relationship("Proposal", backref="trades")
    user = relationship("User", backref="trade_history")

    def __repr__(self):
        return f"<TradeHistory {self.id}: {self.side.value} {self.quantity} {self.symbol} @ {self.price}>"


class AgentLog(Base):
    """Log of agent thinking/reasoning during analysis."""
    __tablename__ = "agent_logs"

    id = Column(Integer, primary_key=True, index=True)
    
    # Associated proposal
    proposal_id = Column(Integer, ForeignKey("proposals.id"), nullable=True, index=True)
    
    # Agent info
    agent_type = Column(Enum(AgentType), nullable=False, index=True)
    agent_name = Column(String(50), nullable=True)
    
    # Log content
    message = Column(Text, nullable=False)
    reasoning = Column(Text, nullable=True)
    action = Column(String(100), nullable=True)
    
    # Structured data (JSON string)
    structured_data = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    proposal = relationship("Proposal", back_populates="agent_logs")

    def __repr__(self):
        return f"<AgentLog {self.id}: {self.agent_type.value}>"


class ApprovalHistory(Base):
    """History of approval/rejection actions."""
    __tablename__ = "approval_history"

    id = Column(Integer, primary_key=True, index=True)
    
    # Related proposal
    proposal_id = Column(Integer, ForeignKey("proposals.id"), nullable=False, index=True)
    
    # Action details
    action = Column(String(20), nullable=False)  # approved, rejected, cancelled
    actor = Column(String(50), nullable=True)  # User who performed the action
    reason = Column(Text, nullable=True)  # Reason for rejection/cancellation
    
    # Previous and new status
    previous_status = Column(Enum(ProposalStatus), nullable=True)
    new_status = Column(Enum(ProposalStatus), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    proposal = relationship("Proposal", backref="approval_history")

    def __repr__(self):
        return f"<ApprovalHistory {self.id}: Proposal {self.proposal_id} {self.action}>"


class SystemConfig(Base):
    """System configuration stored in database."""
    __tablename__ = "system_config"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, index=True, nullable=False)
    value = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<SystemConfig {self.key}={self.value}>"
