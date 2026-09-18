"""Agents: named processes that turn a Question into a Forecast."""

from __future__ import annotations

from typing import Callable

from castor.agents.base import Agent, AgentResult, Forecast
from castor.agents.baseline import BaselineAgent

AGENTS: dict[str, Callable[..., Agent]] = {
    BaselineAgent.name: BaselineAgent,
}

DEFAULT_AGENT = BaselineAgent.name


def create_agent(name: str, provider: str | None = None, num_samples: int | None = None) -> Agent:
    """Instantiate a registered Agent by name."""
    try:
        factory = AGENTS[name]
    except KeyError:
        raise ValueError(f"Unknown agent '{name}'. Available: {', '.join(AGENTS)}") from None
    return factory(provider=provider, num_samples=num_samples)


__all__ = ["AGENTS", "DEFAULT_AGENT", "Agent", "AgentResult", "Forecast", "create_agent"]
