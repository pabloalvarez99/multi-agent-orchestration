"""Deterministic, JSON-safe timeline values for one orchestration run."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from mao.models.messages import AgentName

TraceEventName = Literal[
    "task_started",
    "handoff",
    "agent_output",
    "decision",
    "specialist_error",
    "stop",
]


class TraceEvent(BaseModel):
    """One ordered event containing only JSON values and no full task content."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    sequence: int = Field(ge=0)
    event: TraceEventName
    actor: AgentName
    payload: dict[str, JsonValue] = Field(default_factory=dict)
