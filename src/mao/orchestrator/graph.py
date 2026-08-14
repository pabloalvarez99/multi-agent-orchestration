"""Bounded execution loop for the in-memory specialist graph."""

from __future__ import annotations

from collections.abc import Iterable

from mao.agents import FakeCriticAgent, FakeResearchAgent, FakeWriterAgent
from mao.models import (
    AgentName,
    FinalAnswer,
    HandoffMessage,
    TaskBudget,
    TaskResult,
    TaskStatus,
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
    ) -> None:
        """Build the default fake team or accept an injected test team."""
        self._bus = bus or InMemoryBus(
            [FakeResearchAgent(), FakeCriticAgent(), FakeWriterAgent()]
        )
        self._policy = policy or OrchestrationPolicy()

    def run(self, task: str, *, budget: TaskBudget | None = None) -> TaskResult:
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

        while True:
            if handoffs >= limits.max_handoffs:
                return self._result(
                    TaskStatus.BUDGET_EXHAUSTED,
                    "The task stopped before Writer could finish because max_handoffs was reached.",
                    involved,
                    handoffs,
                    retries,
                    limits,
                )
            try:
                self._policy.validate_handoff(current)
                dispatched = current.recipient
                if dispatched not in involved:
                    involved.append(dispatched)
                output = self._bus.dispatch(current)
                handoffs += 1
                if isinstance(output, FinalAnswer):
                    self._policy.validate_final(output, dispatched=dispatched)
                    return self._result(
                        TaskStatus.DONE,
                        output.text,
                        involved,
                        handoffs,
                        retries,
                        limits,
                    )
                retries = self._policy.next_retry_count(
                    output,
                    current=retries,
                    budget=limits,
                )
                current = output.model_copy(update={"attempt": retries})
            except Exception as error:  # noqa: BLE001 - isolation boundary is intentional
                status = (
                    TaskStatus.BUDGET_EXHAUSTED
                    if isinstance(error, PolicyError) and "limit exhausted" in str(error)
                    else TaskStatus.DEGRADED
                )
                explanation = (
                    f"The task degraded while {current.recipient.value} was active: "
                    f"{type(error).__name__}: {error}"
                )
                return self._result(
                    status,
                    explanation,
                    involved,
                    handoffs,
                    retries,
                    limits,
                )

    @staticmethod
    def _result(
        status: TaskStatus,
        result: str,
        involved: Iterable[AgentName],
        handoffs: int,
        retries: int,
        budget: TaskBudget,
    ) -> TaskResult:
        """Construct one terminal result with stable participant ordering."""
        return TaskResult(
            status=status,
            result=result,
            agents_involved=tuple(involved),
            handoffs_used=handoffs,
            research_retries=retries,
            budget=budget,
        )


def run_task(task: str, *, budget: TaskBudget | None = None) -> TaskResult:
    """Run a task with the default credential-free team."""
    return Orchestrator().run(task, budget=budget)


__all__ = ["Orchestrator", "run_task"]
