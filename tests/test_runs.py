"""Bounded replay-store contracts."""

from mao.models import TraceEnvelope
from mao.orchestrator import run_task
from mao.runs import RunRecord, RunStore


def record(run_id: str) -> tuple[RunRecord, TraceEnvelope]:
    """Build one deterministic retained-run pair."""
    result = run_task(f"Task {run_id}")
    return (
        RunRecord.from_result(run_id=run_id, task=f"Task {run_id}", seed=0, result=result),
        TraceEnvelope(run_id=run_id, events=result.trace),
    )


def test_store_evicts_oldest_run_without_extending_on_read() -> None:
    store = RunStore(max_entries=2)
    one, one_trace = record("one")
    two, two_trace = record("two")
    three, three_trace = record("three")

    store.put(one, one_trace)
    store.put(two, two_trace)
    assert store.get("one") == one
    store.put(three, three_trace)

    assert store.get("one") is None
    assert store.get("two") == two
    assert store.get_trace("three") == three_trace
