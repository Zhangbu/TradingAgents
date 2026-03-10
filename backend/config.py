"""Backend configuration settings."""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    app_name: str = "TradingAgents API"
    debug: bool = False
    environment: str = "development"
    
    # LLM Provider API Keys
    # Major providers
    openai_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    
    # OpenAI-compatible providers
    xai_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    
    # Chinese LLM providers
    deepseek_api_key: Optional[str] = None
    moonshot_api_key: Optional[str] = None
    zhipu_api_key: Optional[str] = None
    siliconflow_api_key: Optional[str] = None
    
    # Custom provider (for any OpenAI-compatible API)
    custom_api_key: Optional[str] = None
    
    # Data provider API keys
    alpha_vantage_api_key: Optional[str] = None
    
    # Exchange API Keys
    binance_api_key: Optional[str] = None
    binance_api_secret: Optional[str] = None
    okx_api_key: Optional[str] = None
    okx_api_secret: Optional[str] = None
    okx_passphrase: Optional[str] = None
    futu_host: str = "127.0.0.1"
    futu_port: int = 11111
    
    # Database
    database_url: str = "sqlite:///./tradingagents.db"
    
    # LLM Settings
    llm_provider: str = "openai"
    deep_think_llm: str = "gpt-4o"
    quick_think_llm: str = "gpt-4o-mini"
    backend_url: Optional[str] = None
    
    # Agent Settings
    max_debate_rounds: int = 1
    max_risk_discuss_rounds: int = 1
    
    # Security
    secret_key: str = "your-secret-key-change-in-production"
    api_key_header: str = "X-API-Key"
    
    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:5173"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Export settings instance
settings = get_settings()