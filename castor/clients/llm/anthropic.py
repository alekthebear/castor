"""Anthropic LLM client implementation."""

from __future__ import annotations

import asyncio
from typing import Optional

import anthropic

from castor.config.settings import settings
from castor.exceptions import LLMError


class AnthropicClient:
    """Client for Anthropic API with OpenTelemetry tracing."""

    def __init__(
        self,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        rate_limit: Optional[int] = None,
    ):
        self.model = model or settings.anthropic_model
        self.temperature = temperature if temperature is not None else settings.llm_temperature
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.rate_limiter = asyncio.Semaphore(
            rate_limit or settings.concurrent_requests_limit
        )

    async def call(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        trace_name: Optional[str] = None,
        trace_metadata: Optional[dict] = None,
    ) -> str:
        """Make a completion request to Anthropic.

        Args:
            prompt: The prompt to send to the LLM.
            temperature: Temperature override for this specific call.
            trace_name: Optional name for Langfuse trace (used via OTel).
            trace_metadata: Optional metadata for Langfuse trace (used via OTel).

        Returns:
            The LLM's response text.

        Raises:
            LLMError: If the LLM call fails.
        """
        temp = temperature if temperature is not None else self.temperature

        async with self.rate_limiter:
            try:
                response = await self.client.messages.create(
                    model=self.model,
                    max_tokens=8192,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temp,
                )
                if not response.content:
                    raise LLMError("No answer returned from Anthropic")
                return response.content[0].text
            except LLMError:
                raise
            except Exception as e:
                raise LLMError(f"Anthropic call failed: {e}") from e
