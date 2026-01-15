"""OpenAI LLM client implementation."""

from __future__ import annotations

import asyncio
from typing import Optional

from openai import AsyncOpenAI

from castor.config.settings import settings
from castor.exceptions import LLMError


class OpenAIClient:
    """Client for OpenAI API with OpenTelemetry tracing."""

    def __init__(
        self,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        rate_limit: Optional[int] = None,
        reasoning: Optional[bool] = None,
    ):
        self.model = model or settings.openai_model
        self.temperature = temperature if temperature is not None else settings.llm_temperature
        self.reasoning = reasoning if reasoning is not None else settings.llm_reasoning
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
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
        """Make a completion request to OpenAI.

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
                    "messages": [{"role": "user", "content": prompt}],
                }

                if self.reasoning:
                    # GPT-5 reasoning: use "medium" effort level
                    params["reasoning_effort"] = "medium"
                else:
                    params["temperature"] = temp

                response = await self.client.chat.completions.create(**params)
                answer = response.choices[0].message.content
                if answer is None:
                    raise LLMError("No answer returned from OpenAI")
                return str(answer)
            except LLMError:
                raise
            except Exception as e:
                raise LLMError(f"OpenAI call failed: {e}") from e
