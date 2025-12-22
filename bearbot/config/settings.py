"""Settings and configuration management using Pydantic."""

from __future__ import annotations

from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # API Keys
    metaculus_token: Optional[str] = Field(default=None, alias="METACULUS_TOKEN")
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    perplexity_api_key: Optional[str] = Field(default=None, alias="PERPLEXITY_API_KEY")
    asknews_client_id: Optional[str] = Field(default=None, alias="ASKNEWS_CLIENT_ID")
    asknews_secret: Optional[str] = Field(default=None, alias="ASKNEWS_SECRET")
    exa_api_key: Optional[str] = Field(default=None, alias="EXA_API_KEY")

    # Bot Configuration

    # LLM Configuration
    llm_model: str = Field(default="gpt-4o", description="OpenAI model to use")
    llm_temperature: float = Field(default=0.3, description="LLM temperature setting")
    concurrent_requests_limit: int = Field(
        default=5,
        description="Maximum concurrent LLM requests",
    )

    # API Configuration
    api_base_url: str = Field(
        default="https://www.metaculus.com/api",
        description="Metaculus API base URL",
    )


# Global settings instance
settings = Settings()
