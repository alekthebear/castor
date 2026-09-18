"""Baseline Agent: research once, draw N Samples from one prompt, aggregate."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from castor.agents.base import AgentResult, Forecast
from castor.agents.baseline.binary import BinaryForecaster
from castor.agents.baseline.multiple_choice import MultipleChoiceForecaster
from castor.agents.baseline.numeric import NumericForecaster
from castor.clients.llm import TracedLLMClient, create_llm_client
from castor.config.settings import settings
from castor.research import Researcher

DEFAULT_NUM_SAMPLES = 3


class BaselineConfig(BaseModel):
    provider: str
    model: str | None
    temperature: float
    reasoning: bool
    num_samples: int
    research_provider: str


class BaselineAgent:
    name = "baseline"

    def __init__(self, provider: str | None = None, num_samples: int | None = None):
        provider = provider or settings.llm_provider
        llm = TracedLLMClient(create_llm_client(provider), provider)
        researcher = Researcher()
        self._config = BaselineConfig(
            provider=provider,
            model=llm.model,
            temperature=settings.llm_temperature,
            reasoning=settings.llm_reasoning,
            num_samples=num_samples or DEFAULT_NUM_SAMPLES,
            research_provider=researcher.provider,
        )
        self.binary = BinaryForecaster(llm, researcher)
        self.numeric = NumericForecaster(llm, researcher)
        self.multiple_choice = MultipleChoiceForecaster(llm, researcher)

    def config(self) -> dict[str, Any]:
        return self._config.model_dump()

    async def forecast(self, question: dict[str, Any]) -> AgentResult:
        num_samples = self._config.num_samples
        question_type = question["type"]
        forecast: Forecast
        if question_type == "binary":
            forecast, comment = await self.binary.forecast(question, num_samples)
        elif question_type in ("numeric", "discrete"):
            forecast, comment = await self.numeric.forecast(question, num_samples)
        elif question_type == "multiple_choice":
            forecast, comment = await self.multiple_choice.forecast(question, num_samples)
        else:
            raise ValueError(f"Unknown question type: {question_type}")
        return AgentResult(forecast=forecast, comment=comment)
