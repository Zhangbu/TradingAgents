from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field
from backend.app.schemas.analysis import FailureDetails


class BrokerName(str, Enum):
    alpaca = "alpaca"
    interactive_brokers = "interactive_brokers"


class BrokerEnvironment(str, Enum):
    paper = "paper"
    live = "live"


class OrderStatus(str, Enum):
    pending_approval = "pending_approval"
    approved = "approved"
    rejected = "rejected"
    submitted = "submitted"
    partially_filled = "partially_filled"
    filled = "filled"
    cancel_requested = "cancel_requested"
    canceled = "canceled"
    replace_requested = "replace_requested"
    replaced = "replaced"
    expired = "expired"
    failed = "failed"


class OrderType(str, Enum):
    market = "market"
    limit = "limit"


class ApprovalDecision(str, Enum):
    approved = "approved"
    rejected = "rejected"


class ApprovalRequest(BaseModel):
    order_id: str
    reviewer: str = Field(..., min_length=1, max_length=128)
    note: str | None = None


class OrderCreateRequest(BaseModel):
    intent_id: str
    broker_name: BrokerName = BrokerName.alpaca
    broker_environment: BrokerEnvironment = BrokerEnvironment.paper
    reference_price: float = Field(default=100.0, gt=0)
    limit_price: float | None = Field(default=None, gt=0)


class OrderCancelRequest(BaseModel):
    reviewer: str = Field(..., min_length=1, max_length=128)
    note: str | None = None


class OrderReplaceRequest(BaseModel):
    reviewer: str = Field(..., min_length=1, max_length=128)
    quantity: int | None = Field(default=None, gt=0)
    limit_price: float | None = Field(default=None, gt=0)
    note: str | None = None


class PositionRecord(BaseModel):
    symbol: str
    quantity: int
    average_price: float
    market_value: float


class AccountSnapshot(BaseModel):
    cash: float
    equity: float
    buying_power: float
    positions: list[PositionRecord] = Field(default_factory=list)


class ReconciliationDiff(BaseModel):
    category: str
    field: str
    severity: str
    local_value: str | float | int | None = None
    broker_value: str | float | int | None = None
    message: str


class OrderRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    intent_id: str
    analysis_id: str
    symbol: str
    broker_name: BrokerName
    broker_environment: BrokerEnvironment
    side: str
    order_type: OrderType
    quantity: int = Field(..., gt=0)
    filled_quantity: int = Field(default=0, ge=0)
    remaining_quantity: int | None = None
    broker_order_id: str | None = None
    requested_price: float | None = None
    filled_price: float | None = None
    average_fill_price: float | None = None
    broker_status_raw: str | None = None
    status: OrderStatus
    status_reason: str | None = None
    failure_details: FailureDetails | None = None
    approval_required: bool
    replaces_order_id: str | None = None
    replaced_by_order_id: str | None = None
    submitted_at: datetime | None = None
    broker_updated_at: datetime | None = None
    cancel_requested_at: datetime | None = None
    canceled_at: datetime | None = None
    filled_at: datetime | None = None
    last_synced_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class OrderListResponse(BaseModel):
    items: list[OrderRecord]


class BrokerSyncResult(BaseModel):
    synced_orders: list[OrderRecord]
    account_snapshot: AccountSnapshot | None = None
    matched_positions: list[PositionRecord] = Field(default_factory=list)
    unmatched_local_symbols: list[str] = Field(default_factory=list)
    unmatched_broker_symbols: list[str] = Field(default_factory=list)
    order_diffs: list[ReconciliationDiff] = Field(default_factory=list)
    position_diffs: list[ReconciliationDiff] = Field(default_factory=list)
    account_diffs: list[ReconciliationDiff] = Field(default_factory=list)
    cash_diff: float = 0.0
    equity_diff: float = 0.0
    requires_operator_review: bool = False
    summary_message: str | None = None
    failure_details: FailureDetails | None = None
