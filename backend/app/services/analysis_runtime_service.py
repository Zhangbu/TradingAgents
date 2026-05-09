from __future__ import annotations

import os

from backend.app.schemas.runtime import (
    AnalysisRuntimeCatalog,
    AnalysisRuntimeHealth,
    AnalysisRuntimeProfile,
    RuntimeDataVendorCategory,
    AnalysisRuntimeProfile,
    RuntimeModelOption,
    RuntimeProviderCatalog,
    RuntimeHealthCheck,
    RuntimeHealthState,
)
from tradingagents.default_config import build_default_config
from tradingagents.llm_clients.model_catalog import MODEL_OPTIONS


class AnalysisRuntimeService:
    """Expose the current analysis runtime profile and coarse health checks."""

    _API_KEY_ENV_MAP = {
        "openai": "OPENAI_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "nvidia": "NVIDIA_API_KEY",
        "google": "GOOGLE_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "xai": "XAI_API_KEY",
        "qwen": "DASHSCOPE_API_KEY",
        "glm": "ZHIPU_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
    }
    _DATA_VENDOR_LABELS = {
        "core_stock_apis": "Core stock prices",
        "technical_indicators": "Technical indicators",
        "fundamental_data": "Fundamentals",
        "news_data": "News and sentiment",
    }

    def get_profile(self) -> AnalysisRuntimeProfile:
        config = build_default_config()
        provider = config["llm_provider"].lower()

        api_keys_present = {
            provider_name: bool(os.getenv(env_name))
            for provider_name, env_name in self._API_KEY_ENV_MAP.items()
        }

        return AnalysisRuntimeProfile(
            llm_provider=provider,
            deep_think_llm=config["deep_think_llm"],
            quick_think_llm=config["quick_think_llm"],
            backend_url=config.get("backend_url"),
            data_vendors=config.get("data_vendors", {}),
            vendor_fallback_policy="explicit_multi_vendor_only",
            api_keys_present=api_keys_present,
        )

    def get_catalog(self) -> AnalysisRuntimeCatalog:
        config = build_default_config()
        providers: dict[str, RuntimeProviderCatalog] = {}

        for provider_name, mode_options in MODEL_OPTIONS.items():
            provider_defaults = (
                config
                if provider_name == config["llm_provider"]
                else build_default_config_for_provider(provider_name)
            )
            providers[provider_name] = RuntimeProviderCatalog(
                provider=provider_name,
                backend_url=provider_defaults.get("backend_url"),
                api_key_env=self._API_KEY_ENV_MAP.get(provider_name),
                quick_models=[
                    RuntimeModelOption(label=label, value=value)
                    for label, value in mode_options.get("quick", [])
                ],
                deep_models=[
                    RuntimeModelOption(label=label, value=value)
                    for label, value in mode_options.get("deep", [])
                ],
            )

        categories = [
            RuntimeDataVendorCategory(
                category=category,
                label=self._DATA_VENDOR_LABELS.get(category, category.replace("_", " ").title()),
                current_vendor=config.get("data_vendors", {}).get(category, "yfinance"),
                options=["yfinance", "alpha_vantage"],
            )
            for category in self._DATA_VENDOR_LABELS
        ]

        return AnalysisRuntimeCatalog(
            providers=providers,
            data_vendor_categories=categories,
            known_data_vendors=["yfinance", "alpha_vantage"],
            vendor_fallback_policy="explicit_multi_vendor_only",
        )

    def get_health(self) -> AnalysisRuntimeHealth:
        profile = self.get_profile()
        llm_key_env = self._API_KEY_ENV_MAP.get(profile.llm_provider)
        llm_key_present = bool(llm_key_env and os.getenv(llm_key_env))

        if llm_key_present:
            llm_health = RuntimeHealthCheck(
                component="llm",
                state=RuntimeHealthState.healthy,
                configured=True,
                healthy=True,
                message=(
                    f"{profile.llm_provider} is configured for analysis runs with "
                    f"{profile.deep_think_llm} / {profile.quick_think_llm}."
                ),
            )
        else:
            llm_health = RuntimeHealthCheck(
                component="llm",
                state=RuntimeHealthState.blocked,
                configured=False,
                healthy=False,
                message=(
                    f"{profile.llm_provider} is the active analysis provider, but its "
                    "API key is missing from the environment."
                ),
                recommended_action=(
                    f"Set {llm_key_env or 'the provider API key'} in the root .env and "
                    "restart the backend."
                ),
            )

        data_vendors = profile.data_vendors
        uses_alpha_vantage = any(vendor == "alpha_vantage" for vendor in data_vendors.values())
        uses_yfinance = any(vendor == "yfinance" for vendor in data_vendors.values())
        alpha_vantage_key_present = bool(os.getenv("ALPHA_VANTAGE_API_KEY"))

        if uses_alpha_vantage and not alpha_vantage_key_present:
            market_data_health = RuntimeHealthCheck(
                component="market_data",
                state=RuntimeHealthState.blocked,
                configured=False,
                healthy=False,
                message=(
                    "Alpha Vantage is selected for at least one market data category, "
                    "but ALPHA_VANTAGE_API_KEY is missing."
                ),
                recommended_action=(
                    "Set ALPHA_VANTAGE_API_KEY in the root .env or switch the active "
                    "data vendors back to yfinance."
                ),
            )
        elif uses_yfinance:
            market_data_health = RuntimeHealthCheck(
                component="market_data",
                state=RuntimeHealthState.warning,
                configured=True,
                healthy=True,
                message=(
                    "Yahoo Finance is active for at least one data category. It works "
                    "without an API key, but some WSL/conda environments can hit a "
                    "curl/OpenSSL TLS mismatch."
                ),
                recommended_action=(
                    "If analysis fails with curl TLS errors, reinstall the pinned "
                    "dependencies or switch the affected data vendors to alpha_vantage."
                ),
            )
        else:
            market_data_health = RuntimeHealthCheck(
                component="market_data",
                state=RuntimeHealthState.healthy,
                configured=True,
                healthy=True,
                message="Configured market data vendors have the required credentials.",
            )

        return AnalysisRuntimeHealth(
            profile=profile,
            llm=llm_health,
            market_data=market_data_health,
        )


def build_default_config_for_provider(provider: str) -> dict:
    original_provider = os.getenv("TRADINGAGENTS_LLM_PROVIDER")
    try:
        os.environ["TRADINGAGENTS_LLM_PROVIDER"] = provider
        return build_default_config()
    finally:
        if original_provider is None:
            os.environ.pop("TRADINGAGENTS_LLM_PROVIDER", None)
        else:
            os.environ["TRADINGAGENTS_LLM_PROVIDER"] = original_provider
