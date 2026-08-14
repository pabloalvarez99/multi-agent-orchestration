"""Canonical result of one bounded orchestration run."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from mao.models.messages import AgentName, TaskBudget
from mao.models.trace import TraceEvent


class TaskStatus(StrEnum):
    """Terminal outcomes exposed by the orchestrator."""

    DONE = "done"
    DEGRADED = "degraded"
    BUDGET_EXHAUSTED = "budget_exhausted"


class StopReason(StrEnum):
    """Typed reason the orchestrator ended a run."""

    WRITER_FINAL = "writer_final"
    MAX_HANDOFFS = "max_handoffs"
    RETRY_LIMIT = "retry_limit"
    SPECIALIST_ERROR = "specialist_error"
    POLICY_VIOLATION = "policy_violation"


class TaskResult(BaseModel):
    """Outcome, participant set, and accounting for one task."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: TaskStatus
    stop_reason: StopReason
    result: str = Field(min_length=1)
    result_author: AgentName | None = None
    agents_involved: tuple[AgentName, ...]
    handoffs_used: int = Field(ge=0)
    research_retries: int = Field(ge=0, le=2)
    budget: TaskBudget
    trace: tuple[TraceEvent, ...]
    specialist_timings_ms: dict[AgentName, float] = Field(
        default_factory=dict,
        exclude=True,
        repr=False,
    )

    @model_validator(mode="after")
    def validate_accounting(self) -> TaskResult:
        """Keep result accounting inside the budget it reports."""
        if self.handoffs_used > self.budget.max_handoffs:
            raise ValueError("handoffs_used exceeds max_handoffs")
        if self.research_retries > self.budget.max_research_retries:
            raise ValueError("research_retries exceeds max_research_retries")
        if self.status is TaskStatus.DONE and self.result_author is not AgentName.WRITER:
            raise ValueError("done results must be authored by writer")
        if self.status is not TaskStatus.DONE and self.result_author is not None:
            raise ValueError("non-done explanations cannot claim specialist authorship")
        return self
