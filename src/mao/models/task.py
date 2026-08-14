"""Canonical result of one bounded orchestration run."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from mao.models.messages import AgentName, TaskBudget


class TaskStatus(StrEnum):
    """Terminal outcomes exposed by the orchestrator."""

    DONE = "done"
    DEGRADED = "degraded"
    BUDGET_EXHAUSTED = "budget_exhausted"


class TaskResult(BaseModel):
    """Outcome, participant set, and accounting for one task."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: TaskStatus
    result: str = Field(min_length=1)
    agents_involved: tuple[AgentName, ...]
    handoffs_used: int = Field(ge=0)
    research_retries: int = Field(ge=0, le=2)
    budget: TaskBudget

    @model_validator(mode="after")
    def validate_accounting(self) -> TaskResult:
        """Keep result accounting inside the budget it reports."""
        if self.handoffs_used > self.budget.max_handoffs:
            raise ValueError("handoffs_used exceeds max_handoffs")
        if self.research_retries > self.budget.max_research_retries:
            raise ValueError("research_retries exceeds max_research_retries")
        return self
