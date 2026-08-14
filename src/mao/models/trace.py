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
TRACE_SCHEMA_VERSION: Literal[1] = 1


class TraceEvent(BaseModel):
    """One ordered event containing only JSON values and no full task content."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    sequence: int = Field(ge=0)
    event: TraceEventName
    ts_offset_ms: int = Field(ge=0)
    actor: AgentName
    payload: dict[str, JsonValue] = Field(default_factory=dict)


class TraceEnvelope(BaseModel):
    """Versioned replay payload for one retained run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    trace_schema: Literal[1] = TRACE_SCHEMA_VERSION
    run_id: str = Field(min_length=1, max_length=128)
    events: tuple[TraceEvent, ...]
