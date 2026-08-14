"""Pure transition rules for the multi-agent workflow."""

from __future__ import annotations

from typing import Final

from mao.models import AgentName, FinalAnswer, HandoffMessage, TaskBudget

ALLOWED_HANDOFFS: Final = frozenset(
    {
        (AgentName.ORCHESTRATOR, AgentName.RESEARCH),
        (AgentName.RESEARCH, AgentName.CRITIC),
        (AgentName.CRITIC, AgentName.RESEARCH),
        (AgentName.CRITIC, AgentName.WRITER),
    }
)


class PolicyError(RuntimeError):
    """A specialist attempted a transition the workflow does not permit."""


class OrchestrationPolicy:
    """Validate routing, retry ceilings, and final-answer ownership."""

    def validate_handoff(self, message: HandoffMessage) -> None:
        """Reject routes outside the explicit research/critic/writer graph."""
        edge = (message.sender, message.recipient)
        if edge not in ALLOWED_HANDOFFS:
            raise PolicyError(f"handoff {edge[0].value}->{edge[1].value} is not allowed")

    def next_retry_count(
        self,
        message: HandoffMessage,
        *,
        current: int,
        budget: TaskBudget,
    ) -> int:
        """Count Critic-to-Research loops and enforce their independent cap."""
        if (message.sender, message.recipient) != (AgentName.CRITIC, AgentName.RESEARCH):
            return current
        if current >= budget.max_research_retries:
            raise PolicyError("critic retry limit exhausted")
        return current + 1

    def validate_final(self, answer: FinalAnswer, *, dispatched: AgentName) -> None:
        """Require the final value to have been returned by Writer itself."""
        if dispatched is not AgentName.WRITER or answer.author is not AgentName.WRITER:
            raise PolicyError("only writer may return the final answer")
