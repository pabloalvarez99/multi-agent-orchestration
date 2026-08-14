"""Budget, retry, ownership, and failure-isolation tests."""

from mao.agents import Agent
from mao.models import AgentMessage, AgentName, FinalAnswer, HandoffMessage, TaskBudget, TaskStatus
from mao.orchestrator import InMemoryBus, Orchestrator, run_task


class AlwaysRejectCritic:
    name = AgentName.CRITIC

    def handle(self, message: HandoffMessage) -> AgentMessage:
        return HandoffMessage(
            sender=self.name,
            recipient=AgentName.RESEARCH,
            task=message.task,
            content="Reject again.",
            attempt=message.attempt,
        )


class CrashingCritic:
    name = AgentName.CRITIC

    def handle(self, message: HandoffMessage) -> AgentMessage:
        raise RuntimeError("critic unavailable")


class ImpersonatingResearcher:
    name = AgentName.RESEARCH

    def handle(self, message: HandoffMessage) -> AgentMessage:
        return FinalAnswer(text="Research tried to bypass Writer.")


def team(*, research: Agent | None = None, critic: Agent | None = None) -> InMemoryBus:
    from mao.agents import FakeCriticAgent, FakeResearchAgent, FakeWriterAgent

    return InMemoryBus(
        [research or FakeResearchAgent(), critic or FakeCriticAgent(), FakeWriterAgent()]
    )


def test_happy_path_finishes_only_after_writer() -> None:
    result = run_task("Compare hybrid vs dense retrieval")

    assert result.status is TaskStatus.DONE
    assert result.agents_involved == (
        AgentName.ORCHESTRATOR,
        AgentName.RESEARCH,
        AgentName.CRITIC,
        AgentName.WRITER,
    )
    assert result.handoffs_used == 3
    assert result.result.endswith("composed by the Writer specialist.")


def test_specialist_timings_use_an_injected_monotonic_clock_and_stay_internal() -> None:
    ticks = iter([0, 1_500_000, 10_000_000, 12_000_000, 20_000_000, 23_250_000])

    result = Orchestrator(clock_ns=ticks.__next__).run(
        "Compare hybrid vs dense retrieval"
    )

    assert result.specialist_timings_ms == {
        AgentName.RESEARCH: 1.5,
        AgentName.CRITIC: 2.0,
        AgentName.WRITER: 3.25,
    }
    assert "specialist_timings_ms" not in result.model_dump()


def test_critic_rejection_causes_one_bounded_research_retry() -> None:
    result = run_task("Audit retrieval risk")

    assert result.status is TaskStatus.DONE
    assert result.research_retries == 1
    assert result.handoffs_used == 5


def test_critic_cannot_trigger_more_than_two_research_retries() -> None:
    result = Orchestrator(bus=team(critic=AlwaysRejectCritic())).run("Audit risk")

    assert result.status is TaskStatus.BUDGET_EXHAUSTED
    assert result.research_retries == 2
    assert result.handoffs_used == 6
    assert "retry limit" in result.result


def test_global_handoff_budget_stops_before_writer() -> None:
    result = run_task("Compare hybrid vs dense", budget=TaskBudget(max_handoffs=2))

    assert result.status is TaskStatus.BUDGET_EXHAUSTED
    assert result.handoffs_used == 2
    assert AgentName.WRITER not in result.agents_involved


def test_specialist_crash_is_degraded_and_explained() -> None:
    result = Orchestrator(bus=team(critic=CrashingCritic())).run("Compare systems")

    assert result.status is TaskStatus.DEGRADED
    assert result.result == (
        "The task degraded while critic was active: RuntimeError: critic unavailable"
    )
    assert result.handoffs_used == 1


def test_non_writer_final_is_a_degraded_policy_violation() -> None:
    result = Orchestrator(bus=team(research=ImpersonatingResearcher())).run("Compare systems")

    assert result.status is TaskStatus.DEGRADED
    assert "only writer may return the final answer" in result.result
    assert result.handoffs_used == 1
