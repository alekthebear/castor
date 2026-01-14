"""Settings and configuration management using Pydantic."""

from __future__ import annotations

from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict


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
    anthropic_api_key: Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY")
    gemini_api_key: Optional[str] = Field(default=None, alias="GEMINI_API_KEY")
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
    llm_provider: str = Field(
        default="openai",
        description="LLM provider to use: openai, anthropic, or gemini",
        alias="LLM_PROVIDER",
    )
    llm_temperature: float = Field(default=0.3, description="LLM temperature setting")
    llm_reasoning: bool = Field(
        default=True,
        description="Enable extended thinking/reasoning for LLM calls",
        alias="LLM_REASONING",
    )
    concurrent_requests_limit: int = Field(
        default=5,
        description="Maximum concurrent LLM requests",
    )

    # Per-provider model settings
    openai_model: str = Field(default="gpt-5.2", alias="OPENAI_MODEL")
    anthropic_model: str = Field(default="claude-opus-4-5-20251101", alias="ANTHROPIC_MODEL")
    gemini_model: str = Field(default="gemini-3-pro-preview", alias="GEMINI_MODEL")

    # API Configuration
    api_base_url: str = Field(
        default="https://www.metaculus.com/api",
        description="Metaculus API base URL",
    )

    # Tournament Configuration
    forecast_window_before_close: Optional[int] = Field(
        default=12,
        description="Only forecast questions closing within this many hours "
        "(tournament mode only). Set to None to disable.",
        alias="FORECAST_WINDOW_BEFORE_CLOSE",
    )

    @property
    def langfuse_enabled(self) -> bool:
        """Check if Langfuse tracing is enabled."""
        return bool(self.langfuse_secret_key and self.langfuse_public_key)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # Prioritize .env file over environment variables
        return init_settings, dotenv_settings, env_settings, file_secret_settings


# Global settings instance
settings = Settings()
