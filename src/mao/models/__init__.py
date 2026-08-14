"""Canonical value objects shared by agents and transports."""

from mao.models.messages import (
    AgentMessage,
    AgentName,
    FinalAnswer,
    HandoffMessage,
    TaskBudget,
)

__all__ = ["AgentMessage", "AgentName", "FinalAnswer", "HandoffMessage", "TaskBudget"]
