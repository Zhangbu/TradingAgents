from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from backend.app.schemas.automation import AutomationHealthSnapshot
from backend.app.schemas.order import AccountSnapshot


class BrokerPosition(BaseModel):
    symbol: str
    quantity: int
    average_price: float


class PaperBrokerState(BaseModel):
    cash: float = 100000.0
    equity: float = 100000.0
    buying_power: float = 100000.0
    positions: dict[str, BrokerPosition] = Field(default_factory=dict)


class AlpacaBrokerConfig(BaseModel):
    enabled: bool = False
    paper_trading_mode: str = "simulator"
    api_key: str | None = None
    secret_key: str | None = None
    base_url: str = "https://paper-api.alpaca.markets/v2"


class InteractiveBrokersConfig(BaseModel):
    enabled: bool = False
    paper_trading_mode: str = "simulator"
    host: str = "127.0.0.1"
    port: int = 7497
    client_id: int = 101
    account_id: str | None = None


class BrokerHealthCheckResult(BaseModel):
    broker_name: str
    environment: str
    integration_mode: str
    configured: bool
    credentials_present: bool
    connectivity_ok: bool
    message: str
    base_url: str | None = None
    account_snapshot: AccountSnapshot | None = None
    checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AlpacaPaperReadiness(BaseModel):
    broker_health: BrokerHealthCheckResult
    automation_health: AutomationHealthSnapshot
    manual_ready: bool
    auto_ready: bool
    checklist: list[str] = Field(default_factory=list)
