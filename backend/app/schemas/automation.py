from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class SchedulerConfig(BaseModel):
    enabled: bool = False
    interval_minutes: int = Field(default=30, ge=1, le=1440)
    target_mode: str = "paper_auto"


class AutomationState(BaseModel):
    kill_switch_active: bool = False
    kill_switch_reason: str | None = None
    auto_trading_enabled: bool = False
    live_trading_enabled: bool = False
    live_trading_double_confirmed: bool = False
    live_trading_unlocked_by: str | None = None
    live_trading_unlocked_at: datetime | None = None
    broker_sync_healthy: bool = True
    last_broker_sync_at: datetime | None = None
    sync_stale_after_seconds: int = Field(default=900, ge=60, le=86400)
    consecutive_broker_failures: int = Field(default=0, ge=0)
    max_consecutive_broker_failures: int = Field(default=3, ge=1, le=20)
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AutomationHealthSnapshot(BaseModel):
    kill_switch_active: bool
    auto_trading_enabled: bool
    effective_auto_trading_enabled: bool
    effective_live_trading_enabled: bool
    broker_sync_healthy: bool
    broker_sync_stale: bool
    consecutive_broker_failures: int
    status_summary: str
    state: AutomationState


class KillSwitchRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=280)


class AutoTradingRequest(BaseModel):
    enabled: bool


class LiveTradingRequest(BaseModel):
    enabled: bool
    actor: str = Field(..., min_length=1, max_length=128)
    reason: str = Field(..., min_length=3, max_length=280)


class LiveTradingConfirmRequest(BaseModel):
    actor: str = Field(..., min_length=1, max_length=128)


class BrokerSyncRequest(BaseModel):
    synced_at: datetime | None = None


class SchedulerUpdateRequest(BaseModel):
    enabled: bool
    interval_minutes: int = Field(..., ge=1, le=1440)
    target_mode: str = Field(default="paper_auto", min_length=1, max_length=64)
