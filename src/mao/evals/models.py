"""Typed golden tasks and evaluation scorecards."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from mao.models import AgentName, TaskStatus


class GoldenTask(BaseModel):
    """One deterministic orchestration scenario and its expected accounting."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1)
    category: Literal["happy_path", "critic_retry", "budget_stop"]
    task: str = Field(min_length=1, max_length=8_000)
    max_handoffs: int = Field(ge=1, le=64)
    expected_status: TaskStatus
    expected_agents: tuple[AgentName, ...]
    expected_handoffs: int = Field(ge=0)
    expected_retries: int = Field(ge=0, le=2)


class GoldenResult(BaseModel):
    """Observed outcome and expectation verdict for one golden task."""

    model_config = ConfigDict(frozen=True)

    id: str
    status: TaskStatus
    handoffs_used: int = Field(ge=0)
    research_retries: int = Field(ge=0)
    writer_finished: bool
    passed: bool
    failures: tuple[str, ...] = ()


class BoundaryGolden(BaseModel):
    """One configuration-boundary expectation that never calls a dependency."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1)
    research: Literal["fake", "http"]
    url_configured: Literal[False]
    expected_outcome: Literal["fake_agent", "capability_missing"]


class BoundaryResult(BaseModel):
    """Observed specialist selection with explicit network accounting."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    outcome: Literal["fake_agent", "capability_missing", "unexpected"]
    network_calls: Literal[0] = 0
    passed: bool


class EvalMetrics(BaseModel):
    """Aggregate routing behavior across the committed scenarios."""

    model_config = ConfigDict(frozen=True)

    total_tasks: int = Field(ge=0)
    passed_tasks: int = Field(ge=0)
    pass_rate: float = Field(ge=0.0, le=1.0)
    mean_handoffs: float = Field(ge=0.0)
    retry_task_rate: float = Field(ge=0.0, le=1.0)
    writer_completion_rate: float = Field(ge=0.0, le=1.0)
    status_counts: dict[str, int]


class EvalReport(BaseModel):
    """Free-path scorecard with explicit provider and cost truth."""

    model_config = ConfigDict(frozen=True)

    provider: Literal["fake"] = "fake"
    billed_usd: float = Field(default=0.0, ge=0.0)
    dataset: str
    boundary_dataset: str
    metrics: EvalMetrics
    results: tuple[GoldenResult, ...]
    boundary_results: tuple[BoundaryResult, ...]

    @property
    def all_passed(self) -> bool:
        """Return whether every committed expectation held."""
        return (
            self.metrics.total_tasks > 0
            and self.metrics.passed_tasks == self.metrics.total_tasks
            and bool(self.boundary_results)
            and all(result.passed for result in self.boundary_results)
        )
