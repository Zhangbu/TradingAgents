from __future__ import annotations

from backend.app.schemas.broker import AlpacaBrokerConfig, InteractiveBrokersConfig
from backend.app.services.broker_state_repository import BrokerStateRepository
from backend.app.services.brokers.alpaca_api import AlpacaApiPaperBrokerAdapter
from backend.app.services.brokers.alpaca_paper import AlpacaPaperBrokerAdapter
from backend.app.services.brokers.interactive_brokers_paper import InteractiveBrokersPaperBrokerAdapter


def build_alpaca_broker_adapter(
    *,
    config: AlpacaBrokerConfig,
    state_repository: BrokerStateRepository,
):
    if config.enabled and config.paper_trading_mode == "api":
        return AlpacaApiPaperBrokerAdapter(config=config)
    return AlpacaPaperBrokerAdapter(state_repository=state_repository)


def build_interactive_brokers_adapter(
    *,
    config: InteractiveBrokersConfig,
    state_repository: BrokerStateRepository,
):
    return InteractiveBrokersPaperBrokerAdapter(
        config=config,
        state_repository=state_repository,
    )
