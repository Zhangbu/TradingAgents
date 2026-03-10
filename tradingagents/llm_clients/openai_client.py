import os
from typing import Any, Optional

from langchain_openai import ChatOpenAI

from .base_client import BaseLLMClient
from .validators import validate_model


class UnifiedChatOpenAI(ChatOpenAI):
    """ChatOpenAI subclass that strips incompatible params for certain models."""

    def __init__(self, **kwargs):
        model = kwargs.get("model", "")
        if self._is_reasoning_model(model):
            kwargs.pop("temperature", None)
            kwargs.pop("top_p", None)
        super().__init__(**kwargs)

    @staticmethod
    def _is_reasoning_model(model: str) -> bool:
        """Check if model is a reasoning model that doesn't support temperature."""
        model_lower = model.lower()
        return (
            model_lower.startswith("o1")
            or model_lower.startswith("o3")
            or "gpt-5" in model_lower
        )


class OpenAIClient(BaseLLMClient):
    """Client for OpenAI and OpenAI-compatible providers.

    Supports:
    - openai: Official OpenAI API
    - xai: X.AI Grok models
    - ollama: Local Ollama server
    - openrouter: OpenRouter API aggregator
    - deepseek: DeepSeek models
    - moonshot: Moonshot (月之暗面) models
    - zhipu: Zhipu AI (智谱) models
    - siliconflow: SiliconFlow models
    - custom: Any OpenAI-compatible API
    """

    # API key environment variables for each provider (fallback if not passed in kwargs)
    PROVIDER_API_KEY_ENV = {
        "openai": "OPENAI_API_KEY",
        "xai": "XAI_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "moonshot": "MOONSHOT_API_KEY",
        "zhipu": "ZHIPU_API_KEY",
        "siliconflow": "SILICONFLOW_API_KEY",
        "custom": "CUSTOM_API_KEY",
    }

    def __init__(
        self,
        model: str,
        base_url: Optional[str] = None,
        provider: str = "openai",
        **kwargs,
    ):
        super().__init__(model, base_url, **kwargs)
        self.provider = provider.lower()

    def get_llm(self) -> Any:
        """Return configured ChatOpenAI instance."""
        llm_kwargs = {"model": self.model}

        # Set base_url if provided
        if self.base_url:
            llm_kwargs["base_url"] = self.base_url

        # Handle API key
        # Priority: kwargs > environment variable
        if "api_key" in self.kwargs:
            llm_kwargs["api_key"] = self.kwargs["api_key"]
        elif self.provider in self.PROVIDER_API_KEY_ENV:
            env_key = os.environ.get(self.PROVIDER_API_KEY_ENV[self.provider])
            if env_key:
                llm_kwargs["api_key"] = env_key

        # Special case: Ollama doesn't require auth
        if self.provider == "ollama" and "api_key" not in llm_kwargs:
            llm_kwargs["api_key"] = "ollama"

        # Pass through additional parameters
        for key in ("timeout", "max_retries", "reasoning_effort", "callbacks", "temperature", "max_tokens"):
            if key in self.kwargs:
                llm_kwargs[key] = self.kwargs[key]

        return UnifiedChatOpenAI(**llm_kwargs)

    def validate_model(self) -> bool:
        """Validate model for the provider."""
        return validate_model(self.provider, self.model)
