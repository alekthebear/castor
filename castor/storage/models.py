"""Database tables for Questions and recorded Forecast Runs."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

JSONType = JSON().with_variant(JSONB(), "postgresql")


class Base(DeclarativeBase):
    pass


class Question(Base):
    """Latest known state of a Metaculus Question."""

    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    post_id: Mapped[int] = mapped_column(Integer, index=True)
    title: Mapped[str] = mapped_column(Text)
    type: Mapped[str] = mapped_column(String(32))
    status: Mapped[str | None] = mapped_column(String(32))
    scheduled_close_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    details: Mapped[dict[str, Any]] = mapped_column(JSONType)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    runs: Mapped[list[ForecastRun]] = relationship(back_populates="question")


class ForecastRun(Base):
    """One execution of an Agent against one Question."""

    __tablename__ = "forecast_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), index=True)
    agent: Mapped[str] = mapped_column(String(64))
    agent_config: Mapped[dict[str, Any]] = mapped_column(JSONType)
    git_sha: Mapped[str | None] = mapped_column(String(40))
    git_dirty: Mapped[bool | None]
    environment: Mapped[str] = mapped_column(String(16), index=True)
    tournament: Mapped[str | None] = mapped_column(String(128), index=True)
    status: Mapped[str] = mapped_column(String(16))
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    forecast: Mapped[Any | None] = mapped_column(JSONType)
    forecast_summary: Mapped[str | None] = mapped_column(Text)
    submitted: Mapped[bool]
    langfuse_trace_id: Mapped[str | None] = mapped_column(String(64))

    question: Mapped[Question] = relationship(back_populates="runs")
    steps: Mapped[list[Step]] = relationship(
        back_populates="run", cascade="all, delete-orphan", order_by="Step.seq"
    )


class Step(Base):
    """A timed unit of work within a Forecast Run; Steps nest via parent_id."""

    __tablename__ = "steps"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("forecast_runs.id"), index=True)
    parent_id: Mapped[str | None] = mapped_column(String(36))
    seq: Mapped[int]
    name: Mapped[str] = mapped_column(String(128))
    step_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSONType)
    status: Mapped[str] = mapped_column(String(16))
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    run: Mapped[ForecastRun] = relationship(back_populates="steps")
    artifacts: Mapped[list[Artifact]] = relationship(
        back_populates="step", cascade="all, delete-orphan", order_by="Artifact.seq"
    )


class Artifact(Base):
    """A piece of content a Step consumed or produced."""

    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    step_id: Mapped[str] = mapped_column(ForeignKey("steps.id"), index=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("forecast_runs.id"), index=True)
    seq: Mapped[int]
    kind: Mapped[str] = mapped_column(String(64))
    role: Mapped[str] = mapped_column(String(8))
    name: Mapped[str | None] = mapped_column(String(128))
    content: Mapped[Any] = mapped_column(JSONType)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    step: Mapped[Step] = relationship(back_populates="artifacts")
