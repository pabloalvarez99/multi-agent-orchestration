"""Pure transition rules for the multi-agent workflow, driven by policy data."""

from __future__ import annotations

from typing import Final

from mao.models import AgentName, FinalAnswer, HandoffMessage, TaskBudget
from mao.orchestrator.policy_doc import PolicyDocument, load_default_policy

# Characterization edge set for v0.3.0 (must match default policy file).
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
    """Validate routing, retry ceilings, and final-answer ownership from a document."""

    def __init__(self, document: PolicyDocument | None = None) -> None:
        """Build from an explicit document or the committed default characterization."""
        self._document = document if document is not None else load_default_policy()
        self._allowed = self._document.edge_set()
        final = self._document.authority.final_author
        self._final_author = AgentName(final)

    @property
    def document(self) -> PolicyDocument:
        """Return the loaded policy document."""
        return self._document

    @property
    def policy_id(self) -> str:
        """Stable policy identifier from the document."""
        return self._document.policy_id

    @property
    def policy_hash(self) -> str:
        """SHA-256 of the canonical policy document."""
        return self._document.policy_hash()

    @property
    def allowed_handoffs(self) -> frozenset[tuple[AgentName, AgentName]]:
        """Directed edges permitted by this policy instance."""
        return self._allowed

    def default_budget(self) -> TaskBudget:
        """Budget defaults advertised by the policy document."""
        return TaskBudget(
            max_handoffs=self._document.budgets.max_handoffs,
            max_research_retries=self._document.budgets.max_research_retries,
        )

    def validate_handoff(self, message: HandoffMessage) -> None:
        """Reject routes outside the policy graph."""
        edge = (message.sender, message.recipient)
        if edge not in self._allowed:
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
        """Require the final value to have been returned by the policy final author."""
        if dispatched is not self._final_author or answer.author is not self._final_author:
            raise PolicyError("only writer may return the final answer")
