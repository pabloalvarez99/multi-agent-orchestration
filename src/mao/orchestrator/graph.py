"""Bounded execution loop for the in-memory specialist graph."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from time import perf_counter_ns

from pydantic import JsonValue

from mao.agents import Agent, FakeCriticAgent, FakeResearchAgent, FakeWriterAgent
from mao.models import (
    AgentName,
    FinalAnswer,
    HandoffMessage,
    StopReason,
    TaskBudget,
    TaskResult,
    TaskStatus,
    TraceEvent,
    TraceEventName,
)
from mao.orchestrator.bus import InMemoryBus
from mao.orchestrator.policy import OrchestrationPolicy, PolicyError


class Orchestrator:
    """Route specialists under global handoff and critic-retry budgets."""

    def __init__(
        self,
        *,
        bus: InMemoryBus | None = None,
        policy: OrchestrationPolicy | None = None,
        research_agent: Agent | None = None,
        clock_ns: Callable[[], int] = perf_counter_ns,
    ) -> None:
        """Build the default fake team or accept an injected test team."""
        if bus is not None and research_agent is not None:
            raise ValueError("bus and research_agent cannot both be supplied")
        self._bus = bus or InMemoryBus(
            [research_agent or FakeResearchAgent(), FakeCriticAgent(), FakeWriterAgent()]
        )
        self._research_provider = (
            "custom"
            if bus is not None
            else str(getattr(research_agent or FakeResearchAgent(), "provider", "custom"))
        )
        self._policy = policy or OrchestrationPolicy()
        self._clock_ns = clock_ns

    def run(
        self,
        task: str,
        *,
        budget: TaskBudget | None = None,
        seed: int = 0,
    ) -> TaskResult:
        """Execute ``task`` until Writer finishes, a budget ends, or a specialist fails."""
        limits = budget or TaskBudget()
        current = HandoffMessage(
            sender=AgentName.ORCHESTRATOR,
            recipient=AgentName.RESEARCH,
            task=task,
            content="Begin the task on the deterministic free path.",
        )
        involved: list[AgentName] = [AgentName.ORCHESTRATOR]
        handoffs = 0
        retries = 0
        trace: list[TraceEvent] = []
        specialist_timings_ns: dict[AgentName, int] = {}
        self._record(
            trace,
            "task_started",
            AgentName.ORCHESTRATOR,
            {
                "max_handoffs": limits.max_handoffs,
                "max_research_retries": limits.max_research_retries,
                "provider": self._research_provider,
                "billed_usd": 0.0,
                "seed": seed,
            },
        )

        while True:
            if handoffs >= limits.max_handoffs:
                self._record(
                    trace,
                    "decision",
                    AgentName.ORCHESTRATOR,
                    {"action": "stop", "reason": "max_handoffs"},
                )
                return self._result(
                    TaskStatus.BUDGET_EXHAUSTED,
                    StopReason.MAX_HANDOFFS,
                    "The task stopped before Writer could finish because max_handoffs was reached.",
                    None,
                    involved,
                    handoffs,
                    retries,
                    limits,
                    trace,
                    specialist_timings_ns,
                )
            try:
                self._policy.validate_handoff(current)
                dispatched = current.recipient
                if dispatched not in involved:
                    involved.append(dispatched)
                self._record(
                    trace,
                    "handoff",
                    current.sender,
                    {
                        "recipient": dispatched.value,
                        "attempt": current.attempt,
                        "handoff_number": handoffs + 1,
                    },
                )
                started_ns = self._clock_ns()
                try:
                    output = self._bus.dispatch(current)
                finally:
                    elapsed_ns = max(0, self._clock_ns() - started_ns)
                    specialist_timings_ns[dispatched] = (
                        specialist_timings_ns.get(dispatched, 0) + elapsed_ns
                    )
                handoffs += 1
                if isinstance(output, FinalAnswer):
                    self._record(
                        trace,
                        "agent_output",
                        dispatched,
                        {"kind": "final"},
                    )
                    self._policy.validate_final(output, dispatched=dispatched)
                    self._record(
                        trace,
                        "decision",
                        AgentName.ORCHESTRATOR,
                        {"action": "complete", "reason": "writer_final"},
                    )
                    return self._result(
                        TaskStatus.DONE,
                        StopReason.WRITER_FINAL,
                        output.text,
                        AgentName.WRITER,
                        involved,
                        handoffs,
                        retries,
                        limits,
                        trace,
                        specialist_timings_ns,
                    )
                self._record(
                    trace,
                    "agent_output",
                    dispatched,
                    {
                        "kind": "handoff",
                        "recipient": output.recipient.value,
                        **output.trace_context,
                    },
                )
                previous_retries = retries
                retries = self._policy.next_retry_count(
                    output,
                    current=retries,
                    budget=limits,
                )
                self._record(
                    trace,
                    "decision",
                    AgentName.ORCHESTRATOR,
                    {
                        "action": "re_research" if retries > previous_retries else "route",
                        "recipient": output.recipient.value,
                        "research_retries": retries,
                    },
                )
                current = output.model_copy(update={"attempt": retries})
            except Exception as error:  # noqa: BLE001 - isolation boundary is intentional
                status = (
                    TaskStatus.BUDGET_EXHAUSTED
                    if isinstance(error, PolicyError) and "limit exhausted" in str(error)
                    else TaskStatus.DEGRADED
                )
                stop_reason = (
                    StopReason.RETRY_LIMIT
                    if status is TaskStatus.BUDGET_EXHAUSTED
                    else (
                        StopReason.POLICY_VIOLATION
                        if isinstance(error, PolicyError)
                        else StopReason.SPECIALIST_ERROR
                    )
                )
                self._record(
                    trace,
                    "specialist_error",
                    current.recipient,
                    {
                        "error_type": getattr(
                            error,
                            "error_type",
                            type(error).__name__,
                        )
                    },
                )
                self._record(
                    trace,
                    "decision",
                    AgentName.ORCHESTRATOR,
                    {
                        "action": "stop",
                        "reason": stop_reason.value,
                        "status": status.value,
                    },
                )
                explanation = (
                    f"The task degraded while {current.recipient.value} was active: "
                    f"{type(error).__name__}: {error}"
                )
                return self._result(
                    status,
                    stop_reason,
                    explanation,
                    None,
                    involved,
                    handoffs,
                    retries,
                    limits,
                    trace,
                    specialist_timings_ns,
                )

    @staticmethod
    def _record(
        trace: list[TraceEvent],
        event: TraceEventName,
        actor: AgentName,
        payload: dict[str, JsonValue],
    ) -> None:
        """Append one event with deterministic logical replay time."""
        trace.append(
            TraceEvent(
                sequence=len(trace),
                event=event,
                ts_offset_ms=len(trace),
                actor=actor,
                payload=payload,
            )
        )

    @staticmethod
    def _result(
        status: TaskStatus,
        stop_reason: StopReason,
        result: str,
        result_author: AgentName | None,
        involved: Iterable[AgentName],
        handoffs: int,
        retries: int,
        budget: TaskBudget,
        trace: list[TraceEvent],
        specialist_timings_ns: dict[AgentName, int],
    ) -> TaskResult:
        """Construct one terminal result with stable participant ordering."""
        Orchestrator._record(
            trace,
            "stop",
            AgentName.ORCHESTRATOR,
            {
                "status": status.value,
                "stop_reason": stop_reason.value,
                "handoffs_used": handoffs,
                "research_retries": retries,
            },
        )
        return TaskResult(
            status=status,
            stop_reason=stop_reason,
            result=result,
            result_author=result_author,
            agents_involved=tuple(involved),
            handoffs_used=handoffs,
            research_retries=retries,
            budget=budget,
            trace=tuple(trace),
            specialist_timings_ms={
                agent: round(elapsed_ns / 1_000_000, 3)
                for agent, elapsed_ns in specialist_timings_ns.items()
            },
        )


def run_task(
    task: str,
    *,
    budget: TaskBudget | None = None,
    research_agent: Agent | None = None,
    seed: int = 0,
) -> TaskResult:
    """Run a task with the default credential-free team."""
    return Orchestrator(research_agent=research_agent).run(task, budget=budget, seed=seed)


__all__ = ["Orchestrator", "run_task"]
