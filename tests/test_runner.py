from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from castor.agents import AgentResult
from castor.config.settings import settings
from castor.runner import ForecastRunner
from castor.storage import get_engine
from castor.storage.models import Base, ForecastRun, Question
from castor.tracing import artifact, step

QUESTION = {
    "id": 11,
    "title": "Will it rain?",
    "type": "binary",
    "status": "open",
    "scheduled_close_time": "2026-10-01T00:00:00Z",
}


class FakeMetaculus:
    def __init__(self) -> None:
        self.posted: list[tuple[int, dict]] = []

    def get_post_details(self, post_id: int) -> dict:
        return {"id": post_id, "question": QUESTION}

    def create_forecast_payload(self, forecast: Any, question_type: str) -> dict:
        return {"probability_yes": forecast}

    def post_forecast(self, question_id: int, payload: dict) -> None:
        self.posted.append((question_id, payload))

    def post_comment(self, post_id: int, comment: str) -> None:
        pass


class FakeAgent:
    name = "fake"

    def __init__(self, fail: bool = False) -> None:
        self.fail = fail

    def config(self) -> dict[str, Any]:
        return {"num_samples": 1}

    async def forecast(self, question: dict[str, Any]) -> AgentResult:
        with step("sample-1"):
            artifact("response", "Probability: 70%")
            if self.fail:
                raise ValueError("could not parse")
        return AgentResult(forecast=0.7, comment="because")


@pytest.fixture
def engine(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'castor.db'}"
    monkeypatch.setattr(settings, "database_url", url)
    monkeypatch.setattr(settings, "castor_env", "dev")
    engine = get_engine(url)
    Base.metadata.create_all(engine)
    return engine


def _runner(agent: FakeAgent, metaculus: FakeMetaculus | None = None) -> ForecastRunner:
    return ForecastRunner(metaculus or FakeMetaculus(), agent, tournament="t1")  # type: ignore[arg-type]


async def test_records_successful_run(engine):
    metaculus = FakeMetaculus()
    await _runner(FakeAgent(), metaculus).forecast_question(11, 22, submit=True)

    with Session(engine) as session:
        run = session.scalars(select(ForecastRun)).one()
        assert run.status == "succeeded" and run.submitted
        assert run.forecast == 0.7 and run.forecast_summary == "70%"
        assert run.agent == "fake" and run.agent_config == {"num_samples": 1}
        assert run.environment == "dev" and run.tournament == "t1"
        assert [s.name for s in run.steps] == [
            "forecast-run",
            "fetch-question",
            "agent",
            "sample-1",
            "submit",
        ]
        fetch = run.steps[1]
        assert fetch.artifacts[0].kind == "question"
        assert fetch.artifacts[0].content["title"] == "Will it rain?"
        question = session.get(Question, 11)
        assert question is not None and question.post_id == 22
    assert metaculus.posted == [(11, {"probability_yes": 0.7})]


async def test_records_failed_run_with_partial_trace(engine):
    with pytest.raises(ValueError):
        await _runner(FakeAgent(fail=True)).forecast_question(11, 22, submit=True)

    with Session(engine) as session:
        run = session.scalars(select(ForecastRun)).one()
        assert run.status == "failed" and not run.submitted
        assert run.error == "ValueError: could not parse"
        assert run.forecast is None
        sample = next(s for s in run.steps if s.name == "sample-1")
        assert sample.status == "failed"
        assert sample.artifacts[0].content == "Probability: 70%"


async def test_no_record_skips_database(engine):
    runner = ForecastRunner(FakeMetaculus(), FakeAgent(), record=False)  # type: ignore[arg-type]
    await runner.forecast_question(11, 22, submit=False)

    with Session(engine) as session:
        assert session.scalars(select(ForecastRun)).first() is None
