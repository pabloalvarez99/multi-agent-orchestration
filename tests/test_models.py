"""Message and budget contracts."""

import pytest
from pydantic import ValidationError

from mao.models import AgentName, FinalAnswer, HandoffMessage, TaskBudget


def test_budget_defaults_are_finite_and_retry_bound_is_hard() -> None:
    assert TaskBudget() == TaskBudget(max_handoffs=8, max_research_retries=2)
    with pytest.raises(ValidationError):
        TaskBudget(max_research_retries=3)


def test_messages_reject_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        HandoffMessage.model_validate(
            {
                "sender": "orchestrator",
                "recipient": "research",
                "task": "Compare systems",
                "content": "Start",
                "secret_control": True,
            }
        )


def test_only_writer_can_construct_a_final_answer() -> None:
    answer = FinalAnswer(text="Grounded result.")
    assert answer.author is AgentName.WRITER
    with pytest.raises(ValidationError):
        FinalAnswer.model_validate({"author": "critic", "text": "Not allowed."})
