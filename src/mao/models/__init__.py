"""Canonical value objects shared by agents and transports."""

from mao.models.messages import (
    AgentMessage,
    AgentName,
    FinalAnswer,
    HandoffMessage,
    TaskBudget,
)
from mao.models.task import StopReason, TaskResult, TaskStatus
from mao.models.trace import TRACE_SCHEMA_VERSION, TraceEnvelope, TraceEvent, TraceEventName

__all__ = [
    "AgentMessage",
    "AgentName",
    "FinalAnswer",
    "HandoffMessage",
    "StopReason",
    "TaskBudget",
    "TaskResult",
    "TaskStatus",
    "TRACE_SCHEMA_VERSION",
    "TraceEnvelope",
    "TraceEvent",
    "TraceEventName",
]
