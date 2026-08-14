"""Execute golden tasks on the deterministic default team."""

from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
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
from mao.models import (
    AgentMessage,
    AgentName,
    FinalAnswer,
    HandoffMessage,
    TaskBudget,
    TaskResult,
)
from mao.orchestrator import (
    FORBID_RESEARCH_TO_WRITER_PATH,
    InMemoryBus,
    OrchestrationPolicy,
    Orchestrator,
    load_policy_document,
    run_task,
)


class CrashingCritic:
    """Fault-injection Critic that fails before returning a message."""

    name = AgentName.CRITIC

    def handle(self, message: HandoffMessage) -> AgentMessage:
        """Raise a stable fault for the isolation golden."""
        raise RuntimeError("chaos critic unavailable")


class CrashingResearch:
    """Fault-injection Research agent that fails immediately."""

    name = AgentName.RESEARCH
    provider = "fake"

    def handle(self, message: HandoffMessage) -> AgentMessage:
        """Raise before producing evidence."""
        raise RuntimeError("chaos research unavailable")


class CrashingWriter:
    """Fault-injection Writer that fails after Critic accept."""

    name = AgentName.WRITER

    def handle(self, message: HandoffMessage) -> AgentMessage:
        """Raise instead of composing a final answer."""
        raise RuntimeError("chaos writer unavailable")


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


class AlwaysRejectCritic:
    """Reject every Research memo to hit the retry ceiling."""

    name = AgentName.CRITIC

    def handle(self, message: HandoffMessage) -> AgentMessage:
        """Always request another Research round."""
        return HandoffMessage(
            sender=self.name,
            recipient=AgentName.RESEARCH,
            task=message.task,
            content="Chaos permanent rejection.",
            attempt=message.attempt,
        )


class ImpersonatingResearcher:
    """Fault-injection Research agent that attempts to become final speaker."""

    name = AgentName.RESEARCH
    provider = "fake"

    def handle(self, message: HandoffMessage) -> AgentMessage:
        """Return a forbidden final value for policy validation."""
        return FinalAnswer(text="Research attempted user-facing output.")


class ImpersonatingCritic:
    """Fault-injection Critic that attempts to become final speaker."""

    name = AgentName.CRITIC

    def handle(self, message: HandoffMessage) -> AgentMessage:
        """Return a forbidden final value for policy validation."""
        return FinalAnswer(text="Critic attempted user-facing output.")


class ResearchToWriterHandoff:
    """Research agent that attempts an illegal direct handoff to Writer."""

    name = AgentName.RESEARCH
    provider = "fake"

    def handle(self, message: HandoffMessage) -> AgentMessage:
        """Bypass Critic with a Research→Writer edge."""
        return HandoffMessage(
            sender=self.name,
            recipient=AgentName.WRITER,
            task=message.task,
            content="Research tried to skip Critic.",
            attempt=message.attempt,
        )


def _chaos_bus(
    *,
    research: Agent | None = None,
    critic: Agent | None = None,
    writer: Agent | None = None,
) -> InMemoryBus:
    """Build a complete fake team with optional injected faults."""
    return InMemoryBus(
        [
            research or FakeResearchAgent(),
            critic or FakeCriticAgent(),
            writer or FakeWriterAgent(),
        ]
    )


def _policy_for(golden: ChaosGolden) -> OrchestrationPolicy | None:
    """Resolve an optional named policy for a chaos case."""
    if golden.policy_id is None:
        return None
    if golden.policy_id == "forbid-research-to-writer":
        return OrchestrationPolicy(load_policy_document(FORBID_RESEARCH_TO_WRITER_PATH))
    raise ValueError(f"unknown chaos policy_id={golden.policy_id!r}")


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


def _build_chaos_orchestrator(golden: ChaosGolden) -> Orchestrator:
    """Map a chaos scenario name to a fault-injected orchestrator."""
    policy = _policy_for(golden)
    scenario = golden.scenario
    if scenario in {"specialist_crash"}:
        return Orchestrator(bus=_chaos_bus(critic=CrashingCritic()), policy=policy)
    if scenario == "specialist_crash_research":
        return Orchestrator(bus=_chaos_bus(research=CrashingResearch()), policy=policy)
    if scenario in {"specialist_crash_writer", "writer_crash_after_accept"}:
        return Orchestrator(bus=_chaos_bus(writer=CrashingWriter()), policy=policy)
    if scenario == "critic_reject_twice":
        return Orchestrator(bus=_chaos_bus(critic=RejectTwiceCritic()), policy=policy)
    if scenario in {"critic_reject_until_limit", "retry_then_budget", "max_handoffs_mid_retry"}:
        return Orchestrator(bus=_chaos_bus(critic=AlwaysRejectCritic()), policy=policy)
    if scenario == "writer_impersonation":
        return Orchestrator(bus=_chaos_bus(research=ImpersonatingResearcher()), policy=policy)
    if scenario == "critic_impersonation":
        return Orchestrator(bus=_chaos_bus(critic=ImpersonatingCritic()), policy=policy)
    if scenario in {"illegal_handoff", "illegal_handoff_research_writer"}:
        return Orchestrator(bus=_chaos_bus(research=ResearchToWriterHandoff()), policy=policy)
    if scenario == "policy_no_writer_path":
        return Orchestrator(policy=policy or _policy_for(
            golden.model_copy(update={"policy_id": "forbid-research-to-writer"})
        ))
    if scenario in {"max_handoffs", "concurrent_isolation"}:
        return Orchestrator(policy=policy)
    return Orchestrator(policy=policy)


def evaluate_chaos_case(golden: ChaosGolden) -> ChaosResult:
    """Run one named fault and check isolation, stop, and Writer ownership."""
    failures: list[str] = []
    budget_kwargs: dict[str, int] = {"max_handoffs": golden.max_handoffs}
    if golden.max_research_retries is not None:
        budget_kwargs["max_research_retries"] = golden.max_research_retries
    budget = TaskBudget(**budget_kwargs)

    if golden.scenario == "concurrent_isolation":
        token_a = golden.pair_token or "TOK-ALPHA-111"
        if golden.pair_token is None:
            token_b = "TOK-BETA-999"
        else:
            token_b = f"TOK-BETA-{abs(hash(token_a)) % 10_000:04d}"

        def _run(label: str, token: str) -> TaskResult:
            return Orchestrator().run(
                f"{golden.task} token {token} label {label}",
                budget=TaskBudget(max_handoffs=golden.max_handoffs),
                seed=(abs(hash(token)) % 10_000) + 1,
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            future_a = pool.submit(_run, "a", token_a)
            future_b = pool.submit(_run, "b", token_b)
            result_a = future_a.result()
            result_b = future_b.result()
        for label, result, own, other in (
            ("a", result_a, token_a, token_b),
            ("b", result_b, token_b, token_a),
        ):
            text = result.result
            if other in text and other != own:
                failures.append(f"swap detected in {label} result")
            if own not in text:
                failures.append(f"missing own token in {label} result")
            if result.status.value != golden.expected_status.value:
                failures.append(
                    f"{label} status={result.status!r}, expected {golden.expected_status!r}"
                )
        writer_finished = (
            result_a.result_author is AgentName.WRITER
            and result_b.result_author is AgentName.WRITER
        )
        if writer_finished != golden.expected_writer_finished:
            failures.append(
                f"writer_finished={writer_finished!r}, expected {golden.expected_writer_finished!r}"
            )
        primary = result_a
        return ChaosResult(
            id=golden.id,
            status=primary.status,
            stop_reason=primary.stop_reason,
            writer_finished=writer_finished,
            non_empty_result=bool(primary.result.strip()),
            handoffs_used=primary.handoffs_used,
            research_retries=primary.research_retries,
            difficulty=golden.difficulty,
            family=golden.family,
            passed=not failures,
            failures=tuple(failures),
        )

    orchestrator = _build_chaos_orchestrator(golden)
    if golden.scenario == "policy_no_writer_path" and golden.policy_id is None:
        orchestrator = Orchestrator(
            policy=OrchestrationPolicy(load_policy_document(FORBID_RESEARCH_TO_WRITER_PATH))
        )
    result = orchestrator.run(golden.task, budget=budget)
    writer_finished = result.result_author is AgentName.WRITER
    _equal(failures, "status", result.status, golden.expected_status)
    _equal(failures, "stop_reason", result.stop_reason, golden.expected_stop_reason)
    _equal(failures, "writer_finished", writer_finished, golden.expected_writer_finished)
    if golden.expected_handoffs is not None:
        _equal(failures, "handoffs", result.handoffs_used, golden.expected_handoffs)
    if golden.expected_retries is not None:
        _equal(failures, "retries", result.research_retries, golden.expected_retries)
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
        difficulty=golden.difficulty,
        family=golden.family,
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
