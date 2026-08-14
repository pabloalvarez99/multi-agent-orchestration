"""Execute golden tasks on the deterministic default team."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Literal

from mao.agents import (
    Agent,
    FakeCriticAgent,
    FakeResearchAgent,
    FakeWriterAgent,
    ResearchCapabilityMissing,
    ResearchChoice,
    build_research_agent,
)
from mao.evals.dataset import (
    DEFAULT_BOUNDARY_DATASET,
    DEFAULT_CHAOS_DATASET,
    DEFAULT_DATASET,
    load_boundary_dataset,
    load_chaos_dataset,
    load_dataset,
)
from mao.evals.models import (
    BoundaryGolden,
    BoundaryResult,
    ChaosGolden,
    ChaosResult,
    EvalMetrics,
    EvalReport,
    GoldenResult,
    GoldenTask,
)
from mao.models import AgentMessage, AgentName, FinalAnswer, HandoffMessage, TaskBudget
from mao.orchestrator import InMemoryBus, Orchestrator, run_task


class CrashingCritic:
    """Fault-injection Critic that fails before returning a message."""

    name = AgentName.CRITIC

    def handle(self, message: HandoffMessage) -> AgentMessage:
        """Raise a stable fault for the isolation golden."""
        raise RuntimeError("chaos critic unavailable")


class RejectTwiceCritic:
    """Reject exactly two Research rounds, then hand accepted work to Writer."""

    name = AgentName.CRITIC

    def handle(self, message: HandoffMessage) -> AgentMessage:
        """Exercise the maximum allowed retries without exhausting them."""
        if message.attempt < 2:
            return HandoffMessage(
                sender=self.name,
                recipient=AgentName.RESEARCH,
                task=message.task,
                content=f"Chaos rejection {message.attempt + 1}: research again.",
                attempt=message.attempt,
            )
        return HandoffMessage(
            sender=self.name,
            recipient=AgentName.WRITER,
            task=message.task,
            content=f"Critic accepted round 3.\n{message.content}",
            attempt=message.attempt,
        )


class ImpersonatingResearcher:
    """Fault-injection Research agent that attempts to become final speaker."""

    name = AgentName.RESEARCH

    def handle(self, message: HandoffMessage) -> AgentMessage:
        """Return a forbidden final value for policy validation."""
        return FinalAnswer(text="Research attempted user-facing output.")


def _chaos_bus(*, research: Agent | None = None, critic: Agent | None = None) -> InMemoryBus:
    """Build a complete fake team with one optional injected fault."""
    return InMemoryBus(
        [research or FakeResearchAgent(), critic or FakeCriticAgent(), FakeWriterAgent()]
    )


def evaluate_case(golden: GoldenTask) -> GoldenResult:
    """Run one golden and compare status, participants, handoffs, and retries."""
    result = run_task(golden.task, budget=TaskBudget(max_handoffs=golden.max_handoffs))
    failures: list[str] = []
    _equal(failures, "status", result.status, golden.expected_status)
    _equal(failures, "agents", result.agents_involved, golden.expected_agents)
    _equal(failures, "handoffs", result.handoffs_used, golden.expected_handoffs)
    _equal(failures, "retries", result.research_retries, golden.expected_retries)
    return GoldenResult(
        id=golden.id,
        status=result.status,
        handoffs_used=result.handoffs_used,
        research_retries=result.research_retries,
        writer_finished=AgentName.WRITER in result.agents_involved,
        passed=not failures,
        failures=tuple(failures),
    )


def _equal(failures: list[str], field: str, actual: object, expected: object) -> None:
    """Record a stable mismatch without hiding the observed value."""
    if actual != expected:
        failures.append(f"{field}={actual!r}, expected {expected!r}")


def evaluate_boundary_case(golden: BoundaryGolden) -> BoundaryResult:
    """Exercise configuration only; construction cannot make a network call."""
    outcome: Literal["fake_agent", "capability_missing", "unexpected"] = "unexpected"
    try:
        agent = build_research_agent(ResearchChoice(golden.research), base_url="")
        if isinstance(agent, FakeResearchAgent):
            outcome = "fake_agent"
    except ResearchCapabilityMissing:
        outcome = "capability_missing"
    return BoundaryResult(
        id=golden.id,
        outcome=outcome,
        passed=outcome == golden.expected_outcome,
    )


def evaluate_chaos_case(golden: ChaosGolden) -> ChaosResult:
    """Run one named fault and check isolation, stop, and Writer ownership."""
    if golden.scenario == "specialist_crash":
        orchestrator = Orchestrator(bus=_chaos_bus(critic=CrashingCritic()))
    elif golden.scenario == "critic_reject_twice":
        orchestrator = Orchestrator(bus=_chaos_bus(critic=RejectTwiceCritic()))
    elif golden.scenario == "writer_impersonation":
        orchestrator = Orchestrator(bus=_chaos_bus(research=ImpersonatingResearcher()))
    else:
        orchestrator = Orchestrator()
    result = orchestrator.run(
        golden.task,
        budget=TaskBudget(max_handoffs=golden.max_handoffs),
    )
    writer_finished = result.result_author is AgentName.WRITER
    failures: list[str] = []
    _equal(failures, "status", result.status, golden.expected_status)
    _equal(failures, "stop_reason", result.stop_reason, golden.expected_stop_reason)
    _equal(failures, "writer_finished", writer_finished, golden.expected_writer_finished)
    if not result.result.strip():
        failures.append("result is empty")
    if result.result_author not in (None, AgentName.WRITER):
        failures.append(f"result_author={result.result_author!r}, expected writer or system")
    return ChaosResult(
        id=golden.id,
        status=result.status,
        stop_reason=result.stop_reason,
        writer_finished=writer_finished,
        non_empty_result=bool(result.result.strip()),
        handoffs_used=result.handoffs_used,
        research_retries=result.research_retries,
        passed=not failures,
        failures=tuple(failures),
    )


def evaluate(
    path: Path = DEFAULT_DATASET,
    boundary_path: Path = DEFAULT_BOUNDARY_DATASET,
    chaos_path: Path = DEFAULT_CHAOS_DATASET,
) -> EvalReport:
    """Run every golden and aggregate handoff, retry, Writer, and status metrics."""
    results = tuple(evaluate_case(golden) for golden in load_dataset(path))
    total = len(results)
    passed = sum(result.passed for result in results)
    handoffs = sum(result.handoffs_used for result in results)
    retried = sum(result.research_retries > 0 for result in results)
    writer_finished = sum(result.writer_finished for result in results)
    counts = dict(sorted(Counter(result.status.value for result in results).items()))
    boundary_results = tuple(
        evaluate_boundary_case(golden) for golden in load_boundary_dataset(boundary_path)
    )
    chaos_results = tuple(
        evaluate_chaos_case(golden) for golden in load_chaos_dataset(chaos_path)
    )
    return EvalReport(
        dataset=path.as_posix(),
        boundary_dataset=boundary_path.as_posix(),
        chaos_dataset=chaos_path.as_posix(),
        metrics=EvalMetrics(
            total_tasks=total,
            passed_tasks=passed,
            pass_rate=passed / total,
            mean_handoffs=handoffs / total,
            retry_task_rate=retried / total,
            writer_completion_rate=writer_finished / total,
            status_counts=counts,
        ),
        results=results,
        boundary_results=boundary_results,
        chaos_results=chaos_results,
    )


__all__ = ["evaluate", "evaluate_boundary_case", "evaluate_case", "evaluate_chaos_case"]
