#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'").strip('"'))


def present(key: str) -> bool:
    return bool(os.getenv(key))


def main() -> int:
    load_env_file(PROJECT_ROOT / ".env")

    provider = os.getenv("TRADINGAGENTS_LLM_PROVIDER", "openai").lower()
    provider_key_map = {
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
    provider_key = provider_key_map.get(provider)

    data_vendors = {
        "core_stock_apis": os.getenv("TRADINGAGENTS_CORE_STOCK_VENDOR", "yfinance"),
        "technical_indicators": os.getenv("TRADINGAGENTS_TECHNICAL_VENDOR", "yfinance"),
        "fundamental_data": os.getenv("TRADINGAGENTS_FUNDAMENTAL_VENDOR", "yfinance"),
        "news_data": os.getenv("TRADINGAGENTS_NEWS_VENDOR", "yfinance"),
    }
    uses_alpha_vantage = any(vendor == "alpha_vantage" for vendor in data_vendors.values())

    print("TradingAgents platform environment check")
    print(f"- LLM provider: {provider}")
    print(f"- Provider key present: {'yes' if provider_key and present(provider_key) else 'no'}")
    print(f"- Deep model: {os.getenv('TRADINGAGENTS_DEEP_THINK_LLM', '(default)')}")
    print(f"- Quick model: {os.getenv('TRADINGAGENTS_QUICK_THINK_LLM', '(default)')}")
    print(f"- Data vendors: {data_vendors}")
    print("- Vendor fallback policy: explicit_multi_vendor_only")
    if uses_alpha_vantage:
        print(f"- Alpha Vantage key present: {'yes' if present('ALPHA_VANTAGE_API_KEY') else 'no'}")
    print(f"- Alpaca enabled: {os.getenv('TRADINGAGENTS_ALPACA_ENABLED', 'false')}")
    print(f"- Alpaca key present: {'yes' if present('ALPACA_API_KEY') else 'no'}")
    print(f"- Alpaca secret present: {'yes' if present('ALPACA_SECRET_KEY') else 'no'}")

    issues: list[str] = []
    if provider_key and not present(provider_key):
        issues.append(f"Missing {provider_key} for active provider '{provider}'.")
    if uses_alpha_vantage and not present("ALPHA_VANTAGE_API_KEY"):
        issues.append("Alpha Vantage is enabled for market data but ALPHA_VANTAGE_API_KEY is missing.")
    if os.getenv("TRADINGAGENTS_ALPACA_ENABLED", "false").lower() == "true":
        if not present("ALPACA_API_KEY") or not present("ALPACA_SECRET_KEY"):
            issues.append("Alpaca API mode is enabled but Alpaca credentials are incomplete.")

    if issues:
        print("\nIssues found:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    print("\nEnvironment looks internally consistent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
