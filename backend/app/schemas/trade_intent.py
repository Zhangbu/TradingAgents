from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field

from backend.app.schemas.analysis import PlatformMode


class TradeRating(str, Enum):
    buy = "BUY"
    overweight = "OVERWEIGHT"
    hold = "HOLD"
    underweight = "UNDERWEIGHT"
    sell = "SELL"


class TradeSide(str, Enum):
    buy = "buy"
    sell = "sell"
    hold = "hold"


class EntryType(str, Enum):
    market = "market"
    limit = "limit"
    none = "none"


class TimeHorizon(str, Enum):
    intraday = "intraday"
    swing = "swing"
    position = "position"


class TradeIntentStatus(str, Enum):
    draft = "draft"
    ready = "ready"
    blocked = "blocked"
    approval_required = "approval_required"


class RiskSeverity(str, Enum):
    info = "info"
    warning = "warning"
    critical = "critical"


class RiskOutcome(str, Enum):
    pass_check = "pass"
    require_approval = "require_approval"
    block = "block"


class RiskCheck(BaseModel):
    rule_code: str
    severity: RiskSeverity
    outcome: RiskOutcome
    message: str


class RiskSummary(BaseModel):
    outcome: TradeIntentStatus
    checks: list[RiskCheck] = Field(default_factory=list)


class TradeIntentRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    analysis_id: str
    symbol: str
    trade_date: str | None = None
    mode: PlatformMode
    rating: TradeRating
    side: TradeSide
    status: TradeIntentStatus = TradeIntentStatus.draft
    confidence: float = Field(..., ge=0.0, le=1.0)
    entry_type: EntryType
    time_horizon: TimeHorizon
    max_position_pct: float = Field(..., ge=0.0, le=1.0)
    max_loss_pct: float = Field(..., ge=0.0, le=1.0)
    take_profit_pct: float = Field(..., ge=0.0, le=2.0)
    thesis_summary: str
    source_signal: str | None = None
    risk_flags: list[str] = Field(default_factory=list)
    risk_summary: RiskSummary | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TradeIntentListResponse(BaseModel):
    items: list[TradeIntentRecord]
