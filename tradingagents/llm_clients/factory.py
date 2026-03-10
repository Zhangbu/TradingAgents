import os
from typing import Optional

from .base_client import BaseLLMClient
from .openai_client import OpenAIClient
from .anthropic_client import AnthropicClient
from .google_client import GoogleClient


# Predefined provider configurations for convenience
PROVIDER_CONFIGS = {
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "api_key_env": "OPENAI_API_KEY",
    },
    "xai": {
        "base_url": "https://api.x.ai/v1",
        "api_key_env": "XAI_API_KEY",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "api_key_env": "OPENROUTER_API_KEY",
    },
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "api_key_env": None,  # Ollama doesn't require auth
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "api_key_env": "DEEPSEEK_API_KEY",
    },
    "moonshot": {
        "base_url": "https://api.moonshot.cn/v1",
        "api_key_env": "MOONSHOT_API_KEY",
    },
    "zhipu": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "api_key_env": "ZHIPU_API_KEY",
    },
    "siliconflow": {
        "base_url": "https://api.siliconflow.cn/v1",
        "api_key_env": "SILICONFLOW_API_KEY",
    },
}


def create_llm_client(
    provider: str,
    model: str,
    base_url: Optional[str] = None,
    **kwargs,
) -> BaseLLMClient:
    """Create an LLM client for the specified provider.

    Args:
        provider: LLM provider. Supported values:
            - "openai": OpenAI GPT models
            - "anthropic": Claude models
            - "google": Gemini models
            - "xai": X.AI Grok models
            - "ollama": Local Ollama models
            - "openrouter": OpenRouter API
            - "deepseek": DeepSeek models (OpenAI compatible)
            - "moonshot": Moonshot (月之暗面) models (OpenAI compatible)
            - "zhipu": Zhipu AI (智谱) models (OpenAI compatible)
            - "siliconflow": SiliconFlow models (OpenAI compatible)
            - "custom": Any OpenAI-compatible API with custom base_url
        model: Model name/identifier
        base_url: Optional base URL for API endpoint (required for "custom" provider)
        **kwargs: Additional provider-specific arguments (e.g., api_key, callbacks)

    Returns:
        Configured BaseLLMClient instance

    Raises:
        ValueError: If provider is "custom" but base_url is not provided

    Examples:
        # Use OpenAI
        client = create_llm_client("openai", "gpt-4o")

        # Use DeepSeek
        client = create_llm_client("deepseek", "deepseek-chat")

        # Use custom OpenAI-compatible API
        client = create_llm_client(
            provider="custom",
            model="my-model",
            base_url="https://my-api.com/v1",
            api_key="my-key"
        )
    """
    provider_lower = provider.lower()

    # Handle Anthropic and Google (non-OpenAI compatible)
    if provider_lower == "anthropic":
        return AnthropicClient(model, base_url, **kwargs)

    if provider_lower == "google":
        return GoogleClient(model, base_url, **kwargs)

    # Handle all OpenAI-compatible providers
    if provider_lower == "custom":
        # Custom provider requires explicit base_url and api_key
        if not base_url:
            raise ValueError(
                "Custom provider requires 'base_url' parameter. "
                "Example: create_llm_client('custom', 'model', base_url='https://api.example.com/v1')"
            )
        return OpenAIClient(model, base_url, provider="custom", **kwargs)

    # Check for predefined OpenAI-compatible providers
    if provider_lower in PROVIDER_CONFIGS:
        config = PROVIDER_CONFIGS[provider_lower]
        effective_base_url = base_url or config["base_url"]

        # Auto-detect API key if not provided
        api_key = kwargs.get("api_key")
        if not api_key and config["api_key_env"]:
            api_key = os.environ.get(config["api_key_env"])
            if api_key:
                kwargs["api_key"] = api_key

        return OpenAIClient(model, effective_base_url, provider=provider_lower, **kwargs)

    # Fallback: treat unknown providers as OpenAI-compatible with provided base_url
    # This allows flexibility for new providers without code changes
    if base_url:
        return OpenAIClient(model, base_url, provider=provider_lower, **kwargs)

    raise ValueError(
        f"Unsupported LLM provider: {provider}. "
        f"Supported providers: {', '.join(['openai', 'anthropic', 'google', 'xai', 'ollama', 'openrouter', 'deepseek', 'moonshot', 'zhipu', 'siliconflow', 'custom'])}. "
        f"For custom OpenAI-compatible APIs, use provider='custom' with base_url parameter."
    )
