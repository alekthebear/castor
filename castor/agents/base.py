"""Interface every Agent implements."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

Forecast = float | list[float] | dict[str, float]


@dataclass
class AgentResult:
    """What an Agent returns: the Forecast and the comment to post with it."""

    forecast: Forecast
    comment: str


class Agent(Protocol):
    """Takes a Question and produces a Forecast, recording Steps as it goes."""

    name: str

    def config(self) -> dict[str, Any]:
        """The Agent Config, recorded with every Forecast Run."""
        ...

    async def forecast(self, question: dict[str, Any]) -> AgentResult:
        """Forecast a Question given its Metaculus details."""
        ...
