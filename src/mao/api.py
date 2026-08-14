"""Strict HTTP/CLI contract over the canonical orchestration models."""

from __future__ import annotations

from collections.abc import Callable

from pydantic import BaseModel, ConfigDict, Field

from mao.models import AgentName, TaskBudget, TaskResult, TaskStatus, TraceEvent


class TaskBudgetRequest(BaseModel):
    """Public budget shape from the P3 API sketch."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    max_handoffs: int = Field(default=8, ge=1, le=64)

    def to_domain(self) -> TaskBudget:
        """Build the richer internal budget without exposing retry controls."""
        return TaskBudget(max_handoffs=self.max_handoffs)


class TaskRequest(BaseModel):
    """One task submitted to the orchestrator."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    task: str = Field(min_length=1, max_length=8_000)
    budget: TaskBudgetRequest = Field(default_factory=TaskBudgetRequest)


class TaskResponse(BaseModel):
    """Exact P3 public response: outcome, final result, participants, trace."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: TaskStatus
    result: str
    agents_involved: tuple[AgentName, ...]
    trace: tuple[TraceEvent, ...]

    @classmethod
    def from_result(cls, result: TaskResult) -> TaskResponse:
        """Project an internal result onto the stable transport contract."""
        return cls(
            status=result.status,
            result=result.result,
            agents_involved=result.agents_involved,
            trace=result.trace,
        )


TaskRunner = Callable[[str, TaskBudget], TaskResult]
"""Dependency-injection seam used by the FastAPI application."""
