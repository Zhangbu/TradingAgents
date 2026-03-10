import os

DEFAULT_CONFIG = {
    "project_dir": os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
    "results_dir": os.getenv("TRADINGAGENTS_RESULTS_DIR", "./results"),
    "data_cache_dir": os.path.join(
        os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
        "dataflows/data_cache",
    ),
    # ============================================================
    # LLM Provider Configuration
    # ============================================================
    # Supported providers:
    #   - "openai": OpenAI GPT models (requires OPENAI_API_KEY)
    #   - "anthropic": Claude models (requires ANTHROPIC_API_KEY)
    #   - "google": Gemini models (requires GOOGLE_API_KEY)
    #   - "xai": X.AI Grok models (requires XAI_API_KEY)
    #   - "ollama": Local Ollama models (no API key needed)
    #   - "openrouter": OpenRouter API aggregator (requires OPENROUTER_API_KEY)
    #   - "deepseek": DeepSeek models (requires DEEPSEEK_API_KEY)
    #   - "moonshot": Moonshot 月之暗面 (requires MOONSHOT_API_KEY)
    #   - "zhipu": Zhipu AI 智谱 (requires ZHIPU_API_KEY)
    #   - "siliconflow": SiliconFlow (requires SILICONFLOW_API_KEY)
    #   - "custom": Any OpenAI-compatible API (requires BACKEND_URL + CUSTOM_API_KEY)
    #
    # Example usage for DeepSeek:
    #   llm_provider = "deepseek"
    #   deep_think_llm = "deepseek-chat"
    #   quick_think_llm = "deepseek-chat"
    #   (set DEEPSEEK_API_KEY in environment)
    #
    # Example usage for custom provider:
    #   llm_provider = "custom"
    #   backend_url = "https://your-api.com/v1"
    #   (set CUSTOM_API_KEY in environment or pass api_key in kwargs)
    "llm_provider": "openai",
    "deep_think_llm": "gpt-4o",
    "quick_think_llm": "gpt-4o-mini",
    # Custom backend URL (optional, for custom endpoints or overriding defaults)
    # For "custom" provider, this is required.
    # For other providers, this overrides the default API endpoint.
    "backend_url": None,  # e.g., "https://api.deepseek.com/v1"
    # Provider-specific thinking configuration
    "google_thinking_level": None,      # "high", "minimal", etc.
    "openai_reasoning_effort": None,    # "medium", "high", "low"
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
