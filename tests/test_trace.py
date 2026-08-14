"""Timeline completeness, ordering, and JSON-safety tests."""

import json

from mao.models import AgentName, TaskStatus
from mao.orchestrator import run_task


def test_happy_timeline_contains_orchestrator_and_writer() -> None:
    result = run_task("Compare hybrid vs dense retrieval")

    actors = {event.actor for event in result.trace}
    assert AgentName.ORCHESTRATOR in actors
    assert AgentName.WRITER in actors
    assert result.trace[0].event == "task_started"
    assert result.trace[-1].event == "stop"
    assert [event.sequence for event in result.trace] == list(range(len(result.trace)))
    assert [event.ts_offset_ms for event in result.trace] == list(range(len(result.trace)))


def test_every_dispatched_handoff_is_in_the_timeline() -> None:
    result = run_task("Audit retrieval risk")

    handoffs = [event for event in result.trace if event.event == "handoff"]
    decisions = [event for event in result.trace if event.event == "decision"]
    assert len(handoffs) == result.handoffs_used == 5
    assert any(event.payload.get("action") == "re_research" for event in decisions)
    assert any(event.payload.get("action") == "complete" for event in decisions)


def test_trace_is_json_serializable_and_omits_full_task() -> None:
    task = "Compare a confidential-shaped but fake task string"
    result = run_task(task)

    encoded = json.dumps([event.model_dump(mode="json") for event in result.trace])
    assert task not in encoded
    assert '"provider": "fake"' in encoded


def test_budget_stop_is_an_explicit_terminal_decision() -> None:
    from mao.models import TaskBudget

    result = run_task("Compare systems", budget=TaskBudget(max_handoffs=1))

    assert result.status is TaskStatus.BUDGET_EXHAUSTED
    assert result.trace[-2].event == "decision"
    assert result.trace[-2].payload["reason"] == "max_handoffs"
    assert result.trace[-1].payload["status"] == "budget_exhausted"


def test_same_task_and_seed_produce_the_same_event_sequence() -> None:
    first = run_task("Audit retrieval risk", seed=41)
    second = run_task("Audit retrieval risk", seed=41)

    assert first.trace == second.trace
