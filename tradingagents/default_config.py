import os

_TRADINGAGENTS_HOME = os.path.join(os.path.expanduser("~"), ".tradingagents")

_PROVIDER_DEFAULTS = {
    "openai": {
        "deep_think_llm": "gpt-5.4",
        "quick_think_llm": "gpt-5.4-mini",
        "backend_url": "https://api.openai.com/v1",
    },
    "deepseek": {
        "deep_think_llm": "deepseek-reasoner",
        "quick_think_llm": "deepseek-chat",
        "backend_url": "https://api.deepseek.com",
    },
}


def build_default_config() -> dict:
    provider = os.getenv("TRADINGAGENTS_LLM_PROVIDER", "openai").lower()
    provider_defaults = _PROVIDER_DEFAULTS.get(provider, _PROVIDER_DEFAULTS["openai"])

    return {
        "project_dir": os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
        "results_dir": os.getenv("TRADINGAGENTS_RESULTS_DIR", os.path.join(_TRADINGAGENTS_HOME, "logs")),
        "data_cache_dir": os.getenv("TRADINGAGENTS_CACHE_DIR", os.path.join(_TRADINGAGENTS_HOME, "cache")),
        # LLM settings
        "llm_provider": provider,
        "deep_think_llm": os.getenv(
            "TRADINGAGENTS_DEEP_THINK_LLM",
            provider_defaults["deep_think_llm"],
        ),
        "quick_think_llm": os.getenv(
            "TRADINGAGENTS_QUICK_THINK_LLM",
            provider_defaults["quick_think_llm"],
        ),
        "backend_url": os.getenv(
            "TRADINGAGENTS_LLM_BACKEND_URL",
            provider_defaults["backend_url"],
        ),
        # Provider-specific thinking configuration
        "google_thinking_level": None,      # "high", "minimal", etc.
        "openai_reasoning_effort": None,    # "medium", "high", "low"
        "anthropic_effort": None,           # "high", "medium", "low"
        # Output language for analyst reports and final decision
        # Internal agent debate stays in English for reasoning quality
        "output_language": "English",
        # Debate and discussion settings
        "max_debate_rounds": 1,
        "max_risk_discuss_rounds": 1,
        "max_recur_limit": 100,
        # Data vendor configuration
        # Category-level configuration (default for all tools in category)
        "data_vendors": {
            "core_stock_apis": "yfinance",       # Options: alpha_vantage, yfinance
            "technical_indicators": "yfinance",  # Options: alpha_vantage, yfinance
            "fundamental_data": "yfinance",      # Options: alpha_vantage, yfinance
            "news_data": "yfinance",             # Options: alpha_vantage, yfinance
        },
        # Tool-level configuration (takes precedence over category-level)
        "tool_vendors": {
            # Example: "get_stock_data": "alpha_vantage",  # Override category default
        },
    }


DEFAULT_CONFIG = build_default_config()
