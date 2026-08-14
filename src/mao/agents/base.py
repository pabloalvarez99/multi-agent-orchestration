"""Structural contract implemented by every specialist."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from mao.models import AgentMessage, AgentName, HandoffMessage


class AgentError(RuntimeError):
    """A specialist could not handle the message it received."""

    def __init__(self, message: str, *, error_type: str = "agent_error") -> None:
        """Store a human explanation and stable machine-readable category."""
        super().__init__(message)
        self.error_type = error_type


@runtime_checkable
class Agent(Protocol):
    """One isolated specialist behind a message boundary."""

    @property
    def name(self) -> AgentName:
        """Return the participant name used for routing and traces."""

    def handle(self, message: HandoffMessage) -> AgentMessage:
        """Handle one addressed message and return a handoff or Writer final."""
