"""Canonical value objects shared by agents and transports."""

from mao.models.messages import (
    AgentMessage,
    AgentName,
    FinalAnswer,
    HandoffMessage,
    TaskBudget,
)
from mao.models.task import TaskResult, TaskStatus

__all__ = [
    "AgentMessage",
    "AgentName",
    "FinalAnswer",
    "HandoffMessage",
    "TaskBudget",
    "TaskResult",
    "TaskStatus",
]
