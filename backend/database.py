"""Database configuration and session management."""

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, sessionmaker
from backend.config import settings

# Synchronous engine for SQLite
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},  # SQLite specific
    echo=settings.debug,
)

# Async engine (using aiosqlite for SQLite)
async_database_url = settings.database_url.replace("sqlite://", "sqlite+aiosqlite://")
async_engine = create_async_engine(async_database_url, echo=settings.debug)

# Session factories
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base class for models
Base = declarative_base()


def init_db():
    """Initialize database tables."""
    from backend.models import Proposal, Position, TradeHistory, AgentLog, User
    Base.metadata.create_all(bind=engine)


async def async_init_db():
    """Initialize database tables asynchronously."""
    from backend.models import Proposal, Position, TradeHistory, AgentLog, User
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db():
    """Dependency to get async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()