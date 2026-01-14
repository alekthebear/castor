"""LLM client module with multi-provider support."""

from __future__ import annotations

from typing import Optional

from castor.clients.llm.anthropic import AnthropicClient
from castor.clients.llm.base import LLMClient
from castor.clients.llm.gemini import GeminiClient
from castor.clients.llm.openai import OpenAIClient
from castor.config.settings import settings


def create_llm_client(provider: Optional[str] = None) -> LLMClient:
    """Create an LLM client for the specified provider.

    Args:
        provider: The provider to use. If not specified, uses settings.llm_provider.
                  Valid values: "openai", "anthropic", "gemini".

    Returns:
        An LLM client instance.

    Raises:
        ValueError: If the provider is not recognized.
    """
    provider = provider or settings.llm_provider

    match provider:
        case "openai":
            return OpenAIClient()
        case "anthropic":
            return AnthropicClient()
        case "gemini":
            return GeminiClient()
        case _:
            raise ValueError(f"Unknown LLM provider: {provider}")


__all__ = [
    "LLMClient",
    "OpenAIClient",
    "AnthropicClient",
    "GeminiClient",
    "create_llm_client",
]
