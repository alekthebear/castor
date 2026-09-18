"""LLM client wrapper that records each call as a Step."""

from __future__ import annotations

from typing import Optional

from castor.clients.llm.base import LLMClient
from castor.tracing import artifact, step


class TracedLLMClient:
    """Records the prompt and response of every call on the wrapped client."""

    def __init__(self, inner: LLMClient, provider: str):
        self.inner = inner
        self.provider = provider
        self.model: str | None = getattr(inner, "model", None)

    async def call(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        trace_name: Optional[str] = None,
        trace_metadata: Optional[dict] = None,
    ) -> str:
        with step("llm-call", provider=self.provider, model=self.model):
            artifact("prompt", prompt, role="input")
            response = await self.inner.call(
                prompt,
                temperature=temperature,
                trace_name=trace_name,
                trace_metadata=trace_metadata,
            )
            artifact("response", response)
            return response
