"""Persistence for Forecast Runs."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from castor.storage.models import Artifact, ForecastRun, Question, Step
from castor.tracing import RunTrace

logger = logging.getLogger(__name__)


@dataclass
class RunRecord:
    """A finished Forecast Run, ready to be persisted."""

    id: str
    question: dict[str, Any]
    post_id: int
    agent: str
    agent_config: dict[str, Any]
    git_sha: str | None
    git_dirty: bool | None
    environment: str
    tournament: str | None
    status: str
    error: str | None
    started_at: datetime
    finished_at: datetime
    forecast: Any | None
    forecast_summary: str | None
    submitted: bool
    trace: RunTrace


def normalize_url(database_url: str) -> str:
    """Use the psycopg 3 driver for plain Postgres URLs (as Supabase provides them)."""
    for prefix in ("postgres://", "postgresql://"):
        if database_url.startswith(prefix):
            return "postgresql+psycopg://" + database_url.removeprefix(prefix)
    return database_url


@lru_cache(maxsize=None)
def get_engine(database_url: str) -> Engine:
    return create_engine(normalize_url(database_url), pool_pre_ping=True)


def save_run(engine: Engine, record: RunRecord) -> None:
    """Upsert the Question and insert the Forecast Run with its Steps and Artifacts."""
    with Session(engine) as session, session.begin():
        _upsert_question(session, record.question, record.post_id)
        session.add(
            ForecastRun(
                id=record.id,
                question_id=record.question["id"],
                agent=record.agent,
                agent_config=record.agent_config,
                git_sha=record.git_sha,
                git_dirty=record.git_dirty,
                environment=record.environment,
                tournament=record.tournament,
                status=record.status,
                error=record.error,
                started_at=record.started_at,
                finished_at=record.finished_at,
                forecast=record.forecast,
                forecast_summary=record.forecast_summary,
                submitted=record.submitted,
                langfuse_trace_id=record.trace.langfuse_trace_id,
                steps=[
                    Step(
                        id=s.id,
                        run_id=record.id,
                        parent_id=s.parent_id,
                        seq=s.seq,
                        name=s.name,
                        step_metadata=s.metadata,
                        status=s.status,
                        error=s.error,
                        started_at=s.started_at,
                        ended_at=s.ended_at,
                        artifacts=[
                            Artifact(
                                id=a.id,
                                run_id=record.id,
                                seq=a.seq,
                                kind=a.kind,
                                role=a.role,
                                name=a.name,
                                content=a.content,
                                created_at=a.created_at,
                            )
                            for a in s.artifacts
                        ],
                    )
                    for s in record.trace.steps
                ],
            )
        )


def _upsert_question(session: Session, details: dict[str, Any], post_id: int) -> None:
    question = session.get(Question, details["id"]) or Question(id=details["id"])
    question.post_id = post_id
    question.title = details["title"]
    question.type = details["type"]
    question.status = details.get("status")
    question.scheduled_close_time = _parse_time(details.get("scheduled_close_time"))
    question.details = details
    question.updated_at = datetime.now(timezone.utc)
    session.add(question)


def _parse_time(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None
