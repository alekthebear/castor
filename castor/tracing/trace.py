"""In-memory trace of a Forecast Run: a tree of Steps carrying Artifacts."""

from __future__ import annotations

import contextlib
import itertools
import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterator, Literal

from castor.config.settings import settings

ArtifactRole = Literal["input", "output"]


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class ArtifactRecord:
    """A piece of content a Step consumed or produced."""

    kind: str
    role: ArtifactRole
    content: Any
    seq: int
    name: str | None = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=_now)


@dataclass
class StepRecord:
    """A timed unit of work within a Forecast Run."""

    name: str
    seq: int
    parent_id: str | None
    metadata: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    started_at: datetime = field(default_factory=_now)
    ended_at: datetime | None = None
    status: Literal["running", "succeeded", "failed"] = "running"
    error: str | None = None
    artifacts: list[ArtifactRecord] = field(default_factory=list)


@dataclass
class RunTrace:
    """Everything recorded while a Forecast Run executes."""

    steps: list[StepRecord] = field(default_factory=list)
    langfuse_trace_id: str | None = None
    # Shared counter so Steps and Artifacts keep a total order even when timestamps tie
    _seq: Iterator[int] = field(default_factory=itertools.count)

    def next_seq(self) -> int:
        return next(self._seq)


_current_run: ContextVar[RunTrace | None] = ContextVar("castor_run", default=None)
_current_step: ContextVar[StepRecord | None] = ContextVar("castor_step", default=None)


def current_run() -> RunTrace | None:
    """Return the trace of the Forecast Run executing in this context, if any."""
    return _current_run.get()


@contextlib.contextmanager
def recording(run: RunTrace) -> Iterator[RunTrace]:
    """Collect Steps created in this context into `run`."""
    run_token = _current_run.set(run)
    step_token = _current_step.set(None)
    try:
        yield run
    finally:
        _current_step.reset(step_token)
        _current_run.reset(run_token)


@contextlib.contextmanager
def step(name: str, **metadata: Any) -> Iterator[StepRecord]:
    """Record a Step nested under the current one, mirrored as a Langfuse span.

    Works outside a Forecast Run too; the Step is then only sent to Langfuse.
    """
    run = _current_run.get()
    parent = _current_step.get()
    record = StepRecord(
        name=name,
        seq=run.next_seq() if run else 0,
        parent_id=parent.id if parent else None,
        metadata=metadata,
    )
    if run is not None:
        run.steps.append(record)

    token = _current_step.set(record)
    with _langfuse_span(name, metadata) as span:
        if run is not None and run.langfuse_trace_id is None and span is not None:
            run.langfuse_trace_id = span.trace_id
        try:
            yield record
        except BaseException as e:
            record.status = "failed"
            record.error = f"{type(e).__name__}: {e}"
            raise
        else:
            record.status = "succeeded"
        finally:
            record.ended_at = _now()
            _current_step.reset(token)
            if span is not None:
                span.update(
                    input=_artifact_payload(record, "input"),
                    output=_artifact_payload(record, "output"),
                    level="ERROR" if record.status == "failed" else None,
                    status_message=record.error,
                )


def artifact(
    kind: str,
    content: Any,
    role: ArtifactRole = "output",
    name: str | None = None,
) -> None:
    """Attach an Artifact to the current Step. No-op outside a Step."""
    current = _current_step.get()
    if current is None:
        return
    run = _current_run.get()
    current.artifacts.append(
        ArtifactRecord(
            kind=kind,
            role=role,
            content=content,
            name=name,
            seq=run.next_seq() if run else 0,
        )
    )


def _artifact_payload(record: StepRecord, role: ArtifactRole) -> dict[str, Any] | None:
    items = {a.name or a.kind: a.content for a in record.artifacts if a.role == role}
    return items or None


@contextlib.contextmanager
def _langfuse_span(name: str, metadata: dict[str, Any]) -> Iterator[Any]:
    if not settings.langfuse_enabled:
        yield None
        return
    from langfuse import get_client

    with get_client().start_as_current_span(name=name, metadata=metadata or None) as span:
        yield span
