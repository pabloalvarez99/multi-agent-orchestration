"""Policy document loading and characterization against v0.3 behavior."""

from __future__ import annotations

from mao.models import AgentName, TaskBudget, TaskStatus
from mao.orchestrator import (
    ALLOWED_HANDOFFS,
    DEFAULT_POLICY_PATH,
    FORBID_RESEARCH_TO_WRITER_PATH,
    OrchestrationPolicy,
    Orchestrator,
    load_default_policy,
    load_policy_document,
    run_task,
)


def test_default_policy_file_matches_v03_allowed_handoffs() -> None:
    document = load_default_policy()
    policy = OrchestrationPolicy(document)

    assert document.policy_id == "default-v0.3-characterization"
    assert policy.allowed_handoffs == ALLOWED_HANDOFFS
    assert document.budgets.max_handoffs == 8
    assert document.budgets.max_research_retries == 2
    assert DEFAULT_POLICY_PATH.is_file()
    assert len(policy.policy_hash) == 64


def test_default_policy_characterizes_happy_and_budget_paths() -> None:
    happy = run_task("Compare hybrid vs dense retrieval")
    budget = run_task("Compare hybrid vs dense", budget=TaskBudget(max_handoffs=2))

    assert happy.status is TaskStatus.DONE
    assert happy.result_author is AgentName.WRITER
    assert happy.handoffs_used == 3
    assert budget.status is TaskStatus.BUDGET_EXHAUSTED
    assert AgentName.WRITER not in budget.agents_involved


def test_forbid_research_to_writer_fixture_changes_happy_path() -> None:
    default = Orchestrator()
    restricted = Orchestrator(
        policy=OrchestrationPolicy(load_policy_document(FORBID_RESEARCH_TO_WRITER_PATH))
    )
    task = "Compare hybrid vs dense retrieval"

    done = default.run(task)
    blocked = restricted.run(task)

    assert done.status is TaskStatus.DONE
    assert done.result_author is AgentName.WRITER
    assert blocked.status is TaskStatus.DEGRADED
    assert blocked.stop_reason.value == "policy_violation"
    assert blocked.result_author is None
    assert "writer" not in {edge[1].value for edge in restricted.policy.allowed_handoffs}
    assert (AgentName.RESEARCH, AgentName.WRITER) not in restricted.policy.allowed_handoffs
