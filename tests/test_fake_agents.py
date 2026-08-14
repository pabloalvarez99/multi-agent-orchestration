"""Offline specialist behavior and protocol conformance."""

import pytest

from mao.agents import Agent, AgentError, FakeCriticAgent, FakeResearchAgent, FakeWriterAgent
from mao.models import AgentName, FinalAnswer, HandoffMessage


def message(
    recipient: AgentName, *, task: str = "Compare hybrid vs dense retrieval"
) -> HandoffMessage:
    return HandoffMessage(
        sender=AgentName.ORCHESTRATOR,
        recipient=recipient,
        task=task,
        content="Begin",
    )


def test_fake_specialists_satisfy_the_agent_protocol() -> None:
    assert isinstance(FakeResearchAgent(), Agent)
    assert isinstance(FakeCriticAgent(), Agent)
    assert isinstance(FakeWriterAgent(), Agent)


def test_fake_pipeline_is_deterministic_and_writer_finishes() -> None:
    researcher = FakeResearchAgent()
    critic = FakeCriticAgent()
    writer = FakeWriterAgent()

    first = researcher.handle(message(AgentName.RESEARCH))
    second = researcher.handle(message(AgentName.RESEARCH))
    assert first == second
    assert isinstance(first, HandoffMessage)

    reviewed = critic.handle(first)
    assert isinstance(reviewed, HandoffMessage)
    assert reviewed.recipient is AgentName.WRITER
    answer = writer.handle(reviewed)
    assert isinstance(answer, FinalAnswer)
    assert answer.author is AgentName.WRITER


def test_critic_rejects_risk_work_once_then_accepts() -> None:
    researcher = FakeResearchAgent()
    critic = FakeCriticAgent()
    first = researcher.handle(message(AgentName.RESEARCH, task="Audit retrieval risk"))
    assert isinstance(first, HandoffMessage)

    rejection = critic.handle(first)
    assert isinstance(rejection, HandoffMessage)
    assert rejection.recipient is AgentName.RESEARCH

    revised_request = rejection.model_copy(update={"attempt": 1})
    revised = researcher.handle(revised_request)
    assert isinstance(revised, HandoffMessage)
    accepted = critic.handle(revised)
    assert isinstance(accepted, HandoffMessage)
    assert accepted.recipient is AgentName.WRITER


def test_specialist_fails_on_a_misrouted_message() -> None:
    with pytest.raises(AgentError, match="addressed to critic"):
        FakeWriterAgent().handle(message(AgentName.CRITIC))
