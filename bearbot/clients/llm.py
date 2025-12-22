"""LLM client for making API calls."""

from __future__ import annotations

import asyncio
from typing import Optional

from openai import AsyncOpenAI

from bearbot.config.settings import settings
from bearbot.exceptions import LLMError


class LLMClient:
    """Client for interacting with LLM APIs."""

    def __init__(
        self,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        rate_limit: Optional[int] = None,
    ):
        """Initialize the LLM client.

        Args:
            model: Model name to use. If not provided, uses settings.
            temperature: Temperature setting. If not provided, uses settings.
            rate_limit: Max concurrent requests. If not provided, uses settings.
        """
        self.model = model or settings.llm_model
        self.temperature = temperature or settings.llm_temperature
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.rate_limiter = asyncio.Semaphore(
            rate_limit or settings.concurrent_requests_limit
        )

    async def call(self, prompt: str, temperature: Optional[float] = None) -> str:
        """Make a streaming completion request to OpenAI's API.

        Args:
            prompt: The prompt to send to the LLM.
            temperature: Temperature override for this specific call.

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
                )
                answer = response.choices[0].message.content
                if answer is None:
                    raise LLMError("No answer returned from LLM")
                return answer
            except Exception as e:
                raise LLMError(f"LLM call failed: {e}") from e
