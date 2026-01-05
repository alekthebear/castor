"""OpenAI LLM client implementation."""

from __future__ import annotations

import asyncio
from typing import Optional

from langfuse.openai import AsyncOpenAI

from castor.config.settings import settings
from castor.exceptions import LLMError


class OpenAIClient:
    """Client for OpenAI API with Langfuse tracing."""

    def __init__(
        self,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        rate_limit: Optional[int] = None,
    ):
        self.model = model or settings.openai_model
        self.temperature = temperature if temperature is not None else settings.llm_temperature
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
            trace_name: Optional name for Langfuse trace.
            trace_metadata: Optional metadata for Langfuse trace.

        Returns:
            The LLM's response text.

        Raises:
            LLMError: If the LLM call fails.
        """
        temp = temperature if temperature is not None else self.temperature

        async with self.rate_limiter:
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temp,
                    stream=False,
                    name=trace_name or "llm-call",
                    metadata=trace_metadata or {},
                )
                answer = response.choices[0].message.content
                if answer is None:
                    raise LLMError("No answer returned from OpenAI")
                return answer
            except LLMError:
                raise
            except Exception as e:
                raise LLMError(f"OpenAI call failed: {e}") from e
