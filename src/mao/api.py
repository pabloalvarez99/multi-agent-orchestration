"""Strict HTTP/CLI contract over the canonical orchestration models."""

from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from mao.agents import ResearchChoice, build_research_agent
from mao.models import (
    TRACE_SCHEMA_VERSION,
    AgentName,
    TaskBudget,
    TaskResult,
    TaskStatus,
    TraceEvent,
)
from mao.orchestrator import run_task


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
    research: ResearchChoice = ResearchChoice.FAKE
    seed: int = Field(default=0, ge=0, le=2_147_483_647)


class TaskResponse(BaseModel):
    """Exact P3 public response: outcome, final result, participants, trace."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    trace_schema: Literal[1] = TRACE_SCHEMA_VERSION
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


class ErrorType(StrEnum):
    """Stable failure categories returned by the API boundary."""

    CAPABILITY_MISSING = "capability_missing"


class ErrorResponse(BaseModel):
    """Public typed error envelope."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    error: str
    error_type: ErrorType
    request_id: str


def execute_task_request(request: TaskRequest) -> TaskResult:
    """Resolve the explicitly selected Research specialist and run the task."""
    research_agent = build_research_agent(request.research)
    return run_task(
        request.task,
        budget=request.budget.to_domain(),
        research_agent=research_agent,
        seed=request.seed,
    )


TaskRunner = Callable[[TaskRequest], TaskResult]
"""Dependency-injection seam used by the FastAPI application."""
