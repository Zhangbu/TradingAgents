"""Model name validators for each provider.

Only validates model names - does NOT enforce limits.
Let LLM providers use their own defaults for unspecified params.
"""

VALID_MODELS = {
    "openai": [
        # GPT-5 series (2025)
        "gpt-5.2",
        "gpt-5.1",
        "gpt-5",
        "gpt-5-mini",
        "gpt-5-nano",
        # GPT-4.1 series (2025)
        "gpt-4.1",
        "gpt-4.1-mini",
        "gpt-4.1-nano",
        # o-series reasoning models
        "o4-mini",
        "o3",
        "o3-mini",
        "o1",
        "o1-preview",
        # GPT-4o series (legacy but still supported)
        "gpt-4o",
        "gpt-4o-mini",
    ],
    "anthropic": [
        # Claude 4.5 series (2025)
        "claude-opus-4-5",
        "claude-sonnet-4-5",
        "claude-haiku-4-5",
        # Claude 4.x series
        "claude-opus-4-1-20250805",
        "claude-sonnet-4-20250514",
        # Claude 3.7 series
        "claude-3-7-sonnet-20250219",
        # Claude 3.5 series (legacy)
        "claude-3-5-haiku-20241022",
        "claude-3-5-sonnet-20241022",
    ],
    "google": [
        # Gemini 3 series (preview)
        "gemini-3-pro-preview",
        "gemini-3-flash-preview",
        # Gemini 2.5 series
        "gemini-2.5-pro",
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        # Gemini 2.0 series
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
    ],
    "xai": [
        # Grok 4.1 series
        "grok-4-1-fast",
        "grok-4-1-fast-reasoning",
        "grok-4-1-fast-non-reasoning",
        # Grok 4 series
        "grok-4",
        "grok-4-0709",
        "grok-4-fast-reasoning",
        "grok-4-fast-non-reasoning",
    ],
    "deepseek": [
        # DeepSeek chat models
        "deepseek-chat",
        "deepseek-coder",
        # DeepSeek reasoning models
        "deepseek-reasoner",
    ],
    "moonshot": [
        # Moonshot models
        "moonshot-v1-8k",
        "moonshot-v1-32k",
        "moonshot-v1-128k",
    ],
    "zhipu": [
        # GLM models
        "glm-4-plus",
        "glm-4-0520",
        "glm-4",
        "glm-4-air",
        "glm-4-airx",
        "glm-4-flash",
        "glm-4-long",
        "glm-3-turbo",
    ],
    "siliconflow": [
        # SiliconFlow hosts various models
        # Validation is relaxed for this provider
    ],
}

# Providers that accept any model (OpenAI-compatible APIs)
OPENAI_COMPATIBLE_PROVIDERS = {
    "ollama",       # Local models
    "openrouter",   # Model aggregator
    "custom",       # User-defined endpoints
    "siliconflow",  # Model hosting platform
}


def validate_model(provider: str, model: str) -> bool:
    """Check if model name is valid for the given provider.

    For OpenAI-compatible providers (ollama, openrouter, custom, etc.),
    any model name is accepted.

    Args:
        provider: Provider name (case-insensitive)
        model: Model name to validate

    Returns:
        True if model is valid for the provider, False otherwise
    """
    provider_lower = provider.lower()

    # OpenAI-compatible providers accept any model
    if provider_lower in OPENAI_COMPATIBLE_PROVIDERS:
        return True

    # For providers with known models, validate against the list
    if provider_lower in VALID_MODELS:
        # If provider has an empty list, accept any model
        if not VALID_MODELS[provider_lower]:
            return True
        return model in VALID_MODELS[provider_lower]

    # Unknown provider - accept any model (flexible for future providers)
    return True
