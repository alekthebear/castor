import asyncio

import pytest

from castor.tracing import RunTrace, artifact, recording, step


def test_steps_nest_and_carry_artifacts():
    run = RunTrace()
    with recording(run):
        with step("outer", kind="test") as outer:
            artifact("query", "q", role="input")
            with step("inner") as inner:
                artifact("answer", {"value": 1})

    assert [s.name for s in run.steps] == ["outer", "inner"]
    assert inner.parent_id == outer.id and outer.parent_id is None
    assert outer.metadata == {"kind": "test"}
    assert [(a.kind, a.role) for a in outer.artifacts] == [("query", "input")]
    assert inner.artifacts[0].content == {"value": 1}
    assert all(s.status == "succeeded" and s.ended_at for s in run.steps)
    seqs = [outer.seq, outer.artifacts[0].seq, inner.seq, inner.artifacts[0].seq]
    assert seqs == sorted(seqs)


async def test_concurrent_steps_share_parent():
    run = RunTrace()

    async def sample(i: int) -> None:
        with step(f"sample-{i}"):
            await asyncio.sleep(0)
            with step("llm-call"):
                await asyncio.sleep(0)

    with recording(run), step("agent") as agent:
        await asyncio.gather(*(sample(i) for i in range(3)))

    by_id = {s.id: s for s in run.steps}
    samples = [s for s in run.steps if s.name.startswith("sample-")]
    calls = [s for s in run.steps if s.name == "llm-call"]
    assert len(samples) == 3 and len(calls) == 3
    assert all(s.parent_id == agent.id for s in samples)
    assert {by_id[c.parent_id].name for c in calls} == {"sample-0", "sample-1", "sample-2"}


def test_failed_step_records_error_and_reraises():
    run = RunTrace()
    with pytest.raises(ValueError), recording(run), step("outer"), step("parse"):
        raise ValueError("bad output")

    assert [s.status for s in run.steps] == ["failed", "failed"]
    assert run.steps[1].error == "ValueError: bad output"


def test_steps_outside_a_run_are_not_recorded():
    with step("orphan") as s:
        artifact("x", 1)
    assert s.artifacts[0].content == 1
