from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class AuditEventType(str, Enum):
    trade_intent_created = "trade_intent_created"
    risk_evaluated = "risk_evaluated"
    order_created = "order_created"
    order_approved = "order_approved"
    order_rejected = "order_rejected"
    order_canceled = "order_canceled"
    order_replaced = "order_replaced"
    broker_synced = "broker_synced"
    reconciliation_completed = "reconciliation_completed"
    live_trading_changed = "live_trading_changed"
    kill_switch_changed = "kill_switch_changed"


class AuditLogRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: AuditEventType
    entity_type: str
    entity_id: str
    actor: str
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AuditLogListResponse(BaseModel):
    items: list[AuditLogRecord]
