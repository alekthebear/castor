"""Base protocol for LLM clients."""

from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable


@runtime_checkable
class LLMClient(Protocol):
    """Protocol defining the interface for LLM clients."""

    async def call(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        trace_name: Optional[str] = None,
        trace_metadata: Optional[dict] = None,
    ) -> str:
        """Make a completion request to the LLM.

        Args:
            prompt: The prompt to send to the LLM.
            temperature: Temperature override for this specific call.
            trace_name: Optional name for Langfuse trace.
            trace_metadata: Optional metadata for Langfuse trace.

        Returns:
            The LLM's response text.
        """
        ...
