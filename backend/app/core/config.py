from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from backend.app.schemas.broker import AlpacaBrokerConfig, InteractiveBrokersConfig


def _load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        os.environ.setdefault(key, value)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
_load_env_file(PROJECT_ROOT / ".env")


class Settings:
    """Application settings sourced from environment variables."""

    def __init__(self) -> None:
        home_dir = Path(os.path.expanduser("~"))
        default_data_dir = home_dir / ".tradingagents" / "platform"

        self.app_name = "TradingAgents Platform API"
        self.api_prefix = "/api"
        self.environment = os.getenv("TRADINGAGENTS_PLATFORM_ENV", "development")
        self.auth_enabled = os.getenv("TRADINGAGENTS_AUTH_ENABLED", "false").lower() == "true"
        self.auth_username = os.getenv("TRADINGAGENTS_AUTH_USERNAME", "operator")
        self.auth_password = os.getenv("TRADINGAGENTS_AUTH_PASSWORD")
        self.auth_secret = os.getenv("TRADINGAGENTS_AUTH_SECRET")
        self.auth_session_ttl_hours = int(os.getenv("TRADINGAGENTS_AUTH_SESSION_TTL_HOURS", "24"))
        self.auth_cookie_secure = os.getenv(
            "TRADINGAGENTS_AUTH_COOKIE_SECURE",
            "true" if self.environment != "development" else "false",
        ).lower() == "true"
        self.frontend_origin = os.getenv("TRADINGAGENTS_FRONTEND_ORIGIN", "http://localhost:3000")
        raw_cors_origins = os.getenv(
            "TRADINGAGENTS_PLATFORM_CORS_ORIGINS",
            f"{self.frontend_origin},http://127.0.0.1:3000,http://localhost:3000",
        )
        self.cors_origins = [
            origin.strip()
            for origin in raw_cors_origins.split(",")
            if origin.strip()
        ]
        self.data_dir = Path(os.getenv("TRADINGAGENTS_PLATFORM_DATA_DIR", default_data_dir))
        self.analysis_runs_dir = self.data_dir / "analysis_runs"
        self.trade_intents_dir = self.data_dir / "trade_intents"
        self.orders_dir = self.data_dir / "orders"
        self.paper_broker_state_path = self.data_dir / "paper_broker" / "alpaca_state.json"
        self.automation_state_path = self.data_dir / "automation" / "state.json"
        self.audit_logs_dir = self.data_dir / "audit_logs"
        self.alpaca = AlpacaBrokerConfig(
            enabled=os.getenv("TRADINGAGENTS_ALPACA_ENABLED", "false").lower() == "true",
            paper_trading_mode=os.getenv("TRADINGAGENTS_ALPACA_PAPER_MODE", "simulator"),
            api_key=os.getenv("ALPACA_API_KEY"),
            secret_key=os.getenv("ALPACA_SECRET_KEY"),
            base_url=os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets/v2"),
        )
        self.interactive_brokers = InteractiveBrokersConfig(
            enabled=os.getenv("TRADINGAGENTS_IB_ENABLED", "false").lower() == "true",
            paper_trading_mode=os.getenv("TRADINGAGENTS_IB_PAPER_MODE", "simulator"),
            host=os.getenv("TRADINGAGENTS_IB_HOST", "127.0.0.1"),
            port=int(os.getenv("TRADINGAGENTS_IB_PORT", "7497")),
            client_id=int(os.getenv("TRADINGAGENTS_IB_CLIENT_ID", "101")),
            account_id=os.getenv("TRADINGAGENTS_IB_ACCOUNT_ID"),
        )

    def ensure_directories(self) -> None:
        self.analysis_runs_dir.mkdir(parents=True, exist_ok=True)
        self.trade_intents_dir.mkdir(parents=True, exist_ok=True)
        self.orders_dir.mkdir(parents=True, exist_ok=True)
        self.paper_broker_state_path.parent.mkdir(parents=True, exist_ok=True)
        self.automation_state_path.parent.mkdir(parents=True, exist_ok=True)
        self.audit_logs_dir.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_directories()
    return settings
