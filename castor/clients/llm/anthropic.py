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
        reasoning: Optional[bool] = None,
    ):
        self.model = model or settings.anthropic_model
        self.temperature = temperature if temperature is not None else settings.llm_temperature
        self.reasoning = reasoning if reasoning is not None else settings.llm_reasoning
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
                # Build request parameters
                params: dict = {
                    "model": self.model,
                    "max_tokens": 16000,
                    "messages": [{"role": "user", "content": prompt}],
                }

                if self.reasoning:
                    # Extended thinking: budget_tokens ~10k for medium reasoning depth
                    # Note: temperature is not compatible with thinking mode
                    params["thinking"] = {
                        "type": "enabled",
                        "budget_tokens": 10000,
                    }
                else:
                    params["temperature"] = temp

                response = await self.client.messages.create(**params)
                if not response.content:
                    raise LLMError("No answer returned from Anthropic")

                # Extract text from response (skip thinking blocks)
                for block in response.content:
                    if block.type == "text":
                        return block.text

                raise LLMError("No text content returned from Anthropic")
            except LLMError:
                raise
            except Exception as e:
                raise LLMError(f"Anthropic call failed: {e}") from e
