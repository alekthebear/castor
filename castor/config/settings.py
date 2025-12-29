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

    # Langfuse Configuration
    langfuse_secret_key: Optional[str] = Field(default=None, alias="LANGFUSE_SECRET_KEY")
    langfuse_public_key: Optional[str] = Field(default=None, alias="LANGFUSE_PUBLIC_KEY")
    langfuse_base_url: Optional[str] = Field(
        default="https://us.cloud.langfuse.com",
        alias="LANGFUSE_BASE_URL",
    )

    # LLM Configuration
    llm_model: str = Field(default="gpt-5.2", description="OpenAI model to use")
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

    # Tournament Configuration
    forecast_window_before_close: Optional[int] = Field(
        default=12,
        description="Only forecast questions closing within this many hours (tournament mode only). Set to None to disable.",
        alias="FORECAST_WINDOW_BEFORE_CLOSE",
    )

    @property
    def langfuse_enabled(self) -> bool:
        """Check if Langfuse tracing is enabled."""
        return bool(self.langfuse_secret_key and self.langfuse_public_key)


# Global settings instance
settings = Settings()
