"""Google Gemini LLM client implementation."""

from __future__ import annotations

import asyncio
from typing import Optional

from google import genai
from google.genai import types

from castor.config.settings import settings
from castor.exceptions import LLMError


class GeminiClient:
    """Client for Google Gemini API with OpenTelemetry tracing."""

    def __init__(
        self,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        rate_limit: Optional[int] = None,
        reasoning: Optional[bool] = None,
    ):
        self.model = model or settings.gemini_model
        self.temperature = temperature if temperature is not None else settings.llm_temperature
        self.reasoning = reasoning if reasoning is not None else settings.llm_reasoning
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.rate_limiter = asyncio.Semaphore(rate_limit or settings.concurrent_requests_limit)

    async def call(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        trace_name: Optional[str] = None,
        trace_metadata: Optional[dict] = None,
    ) -> str:
        """Make a completion request to Gemini.

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
                # Build config based on reasoning setting
                if self.reasoning:
                    # Gemini 3 Pro: use "high" thinking level (medium only for Flash)
                    config = types.GenerateContentConfig(
                        thinking_config=types.ThinkingConfig(
                            thinking_level=types.ThinkingLevel.HIGH, include_thoughts=True
                        )
                    )
                else:
                    config = types.GenerateContentConfig(temperature=temp)

                response = await self.client.aio.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=config,
                )
                if not response.text:
                    raise LLMError("No answer returned from Gemini")
                return response.text
            except LLMError:
                raise
            except Exception as e:
                raise LLMError(f"Gemini call failed: {e}") from e
