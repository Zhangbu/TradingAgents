from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class AnalysisStatus(str, Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class PlatformMode(str, Enum):
    analysis_only = "analysis_only"
    paper_manual = "paper_manual"
    paper_auto = "paper_auto"
    live_manual = "live_manual"
    live_auto = "live_auto"


class AnalysisRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=32)
    trade_date: str | None = Field(default=None, description="YYYY-MM-DD")
    selected_analysts: list[str] = Field(
        default_factory=lambda: ["market", "social", "news", "fundamentals"]
    )
    llm_provider: str | None = None
    deep_think_llm: str | None = None
    quick_think_llm: str | None = None
    max_debate_rounds: int | None = Field(default=None, ge=1, le=10)
    max_risk_discuss_rounds: int | None = Field(default=None, ge=1, le=10)
    mode: PlatformMode = PlatformMode.analysis_only


class AnalysisArtifacts(BaseModel):
    market_report: str | None = None
    sentiment_report: str | None = None
    news_report: str | None = None
    fundamentals_report: str | None = None
    investment_plan: str | None = None
    trader_investment_plan: str | None = None
    final_trade_decision: str | None = None
    processed_signal: str | None = None
    raw_state: dict[str, Any] | None = None


class AnalysisRunRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    symbol: str
    trade_date: str | None = None
    selected_analysts: list[str]
    mode: PlatformMode
    status: AnalysisStatus
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    llm_provider: str | None = None
    deep_think_llm: str | None = None
    quick_think_llm: str | None = None
    error_message: str | None = None
    artifacts: AnalysisArtifacts | None = None


class AnalysisRunListResponse(BaseModel):
    items: list[AnalysisRunRecord]


class AnalysisExecutionResult(BaseModel):
    artifacts: AnalysisArtifacts
