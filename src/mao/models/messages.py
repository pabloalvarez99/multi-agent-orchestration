"""Typed messages that cross an agent boundary.

The orchestrator may inspect and route messages, but specialists communicate
only through these immutable values. That keeps a fake specialist and a future
remote specialist on the same boundary without sharing mutable state.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class AgentName(StrEnum):
    """Closed set of participants in the P3 workflow."""

    ORCHESTRATOR = "orchestrator"
    RESEARCH = "research"
    CRITIC = "critic"
    WRITER = "writer"


class TaskBudget(BaseModel):
    """Hard limits that make the workflow finite."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    max_handoffs: int = Field(default=8, ge=1, le=64)
    max_research_retries: int = Field(default=2, ge=0, le=2)


class HandoffMessage(BaseModel):
    """One specialist asking another participant to continue the task."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    kind: Literal["handoff"] = "handoff"
    sender: AgentName
    recipient: AgentName
    task: str = Field(min_length=1, max_length=8_000)
    content: str = Field(min_length=1, max_length=16_000)
    attempt: int = Field(default=0, ge=0, le=2)


class FinalAnswer(BaseModel):
    """User-facing text, which the type system permits only from Writer."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    kind: Literal["final"] = "final"
    author: Literal[AgentName.WRITER] = AgentName.WRITER
    text: str = Field(min_length=1, max_length=16_000)


AgentMessage = Annotated[HandoffMessage | FinalAnswer, Field(discriminator="kind")]
"""Every value an agent may return from ``handle``."""
