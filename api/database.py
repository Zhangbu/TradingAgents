"""
Database models and session management using SQLAlchemy with SQLite.
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "trading.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# Engine and session
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)


# ==================== Models ====================

class Position(Base):
    """Trading position model."""
    __tablename__ = "positions"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    quantity = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    status = Column(String(20), default="open")  # open, closed
    opened_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)
    pnl = Column(Float, default=0.0)
    
    trades = relationship("Trade", back_populates="position")


class Trade(Base):
    """Trade record model."""
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    side = Column(String(10), nullable=False)  # buy, sell
    order_type = Column(String(20), default="market")  # market, limit
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    commission = Column(Float, default=0.0)
    status = Column(String(20), default="filled")  # pending, filled, cancelled
    executed_at = Column(DateTime, default=datetime.utcnow)
    position_id = Column(Integer, ForeignKey("positions.id"), nullable=True)
    
    position = relationship("Position", back_populates="trades")


class Signal(Base):
    """Trading signal model."""
    __tablename__ = "signals"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    signal_type = Column(String(10), nullable=False)  # buy, sell, hold
    confidence = Column(Float, nullable=False)
    reason = Column(Text, nullable=True)
    source = Column(String(50), default="agent")  # agent, manual, scanner
    status = Column(String(20), default="pending")  # pending, executed, ignored
    created_at = Column(DateTime, default=datetime.utcnow)
    executed_at = Column(DateTime, nullable=True)


class AnalysisReport(Base):
    """Analysis report model."""
    __tablename__ = "analysis_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    analysis_date = Column(String(20), nullable=False)
    report_type = Column(String(50), nullable=False)  # market, news, fundamentals, etc.
    content = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class SystemConfig(Base):
    """System configuration model."""
    __tablename__ = "system_config"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, nullable=True)
    description = Column(String(255), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ScheduledTask(Base):
    """Scheduled task model."""
    __tablename__ = "scheduled_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    task_type = Column(String(50), nullable=False)  # analysis, scan, rebalance
    schedule = Column(String(100), nullable=False)  # cron expression
    enabled = Column(Boolean, default=True)
    config = Column(Text, nullable=True)  # JSON config
    last_run = Column(DateTime, nullable=True)
    next_run = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class SystemLog(Base):
    """System log model."""
    __tablename__ = "system_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    level = Column(String(20), nullable=False)  # info, warning, error
    module = Column(String(50), nullable=True)
    message = Column(Text, nullable=False)
    details = Column(Text, nullable=True)  # JSON details
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class AccountSnapshot(Base):
    """Account snapshot for tracking equity curve."""
    __tablename__ = "account_snapshots"
    
    id = Column(Integer, primary_key=True, index=True)
    cash = Column(Float, nullable=False)
    equity = Column(Float, nullable=False)
    positions_value = Column(Float, default=0.0)
    unrealized_pnl = Column(Float, default=0.0)
    realized_pnl = Column(Float, default=0.0)
    snapshot_at = Column(DateTime, default=datetime.utcnow, index=True)