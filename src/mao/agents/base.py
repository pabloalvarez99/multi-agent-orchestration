"""Structural contract implemented by every specialist."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from mao.models import AgentMessage, AgentName, HandoffMessage


class AgentError(RuntimeError):
    """A specialist could not handle the message it received."""


@runtime_checkable
class Agent(Protocol):
    """One isolated specialist behind a message boundary."""

    @property
    def name(self) -> AgentName:
        """Return the participant name used for routing and traces."""

    def handle(self, message: HandoffMessage) -> AgentMessage:
        """Handle one addressed message and return a handoff or Writer final."""
