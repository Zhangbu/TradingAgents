import os
import unittest
from unittest.mock import patch

from tradingagents.default_config import build_default_config


class TradingAgentsDefaultConfigTests(unittest.TestCase):
    def test_uses_deepseek_defaults_from_environment(self) -> None:
        with patch.dict(
            os.environ,
            {
                "TRADINGAGENTS_LLM_PROVIDER": "deepseek",
            },
            clear=False,
        ):
            config = build_default_config()

        self.assertEqual(config["llm_provider"], "deepseek")
        self.assertEqual(config["deep_think_llm"], "deepseek-reasoner")
        self.assertEqual(config["quick_think_llm"], "deepseek-chat")
        self.assertEqual(config["backend_url"], "https://api.deepseek.com")

    def test_uses_nvidia_defaults_from_environment(self) -> None:
        with patch.dict(
            os.environ,
            {
                "TRADINGAGENTS_LLM_PROVIDER": "nvidia",
            },
            clear=False,
        ):
            config = build_default_config()

        self.assertEqual(config["llm_provider"], "nvidia")
        self.assertEqual(config["deep_think_llm"], "meta/llama-3.3-70b-instruct")
        self.assertEqual(config["quick_think_llm"], "meta/llama-3.1-8b-instruct")
        self.assertEqual(config["backend_url"], "https://integrate.api.nvidia.com/v1")

    def test_model_overrides_take_precedence(self) -> None:
        with patch.dict(
            os.environ,
            {
                "TRADINGAGENTS_LLM_PROVIDER": "deepseek",
                "TRADINGAGENTS_DEEP_THINK_LLM": "custom-deep-model",
                "TRADINGAGENTS_QUICK_THINK_LLM": "custom-quick-model",
                "TRADINGAGENTS_LLM_BACKEND_URL": "https://example.com/v1",
            },
            clear=False,
        ):
            config = build_default_config()

        self.assertEqual(config["deep_think_llm"], "custom-deep-model")
        self.assertEqual(config["quick_think_llm"], "custom-quick-model")
        self.assertEqual(config["backend_url"], "https://example.com/v1")
