"""Deterministic specialists for the credential-free path.

These agents demonstrate orchestration mechanics, not answer quality. Their
outputs are simple transformations of the task, contain no model calls, and are
byte-identical for the same message.
"""

from __future__ import annotations

import re
from typing import Final

from mao.agents.base import AgentError
from mao.models import AgentMessage, AgentName, FinalAnswer, HandoffMessage

REVIEW_TERMS: Final = frozenset({"risk", "verify", "validate", "evidence", "audit"})
"""Terms that make the fake critic request one corroborating research round."""


def _normalise(text: str) -> str:
    """Collapse whitespace without changing the task's words."""
    return " ".join(text.split())


def _require_recipient(message: HandoffMessage, expected: AgentName) -> None:
    """Fail loudly when routing sent a message to the wrong specialist."""
    if message.recipient is not expected:
        raise AgentError(
            f"{expected.value} received a message addressed to {message.recipient.value}"
        )


class FakeResearchAgent:
    """Produce a deterministic evidence memo for Critic."""

    name = AgentName.RESEARCH

    def handle(self, message: HandoffMessage) -> AgentMessage:
        """Turn the task and any critique into a small evidence memo."""
        _require_recipient(message, self.name)
        task = _normalise(message.task)
        lines = [
            f"Research round {message.attempt + 1} for: {task}",
            f"Evidence 1: The task asks for {task.rstrip('.')}.",
        ]
        if "compare" in task.casefold() or " vs " in f" {task.casefold()} ":
            lines.append(
                "Evidence 2: A comparison must state benefits and limitations of both sides."
            )
        if message.attempt:
            lines.append(
                "Evidence 2: The requested concern was checked in a second deterministic pass."
            )
        return HandoffMessage(
            sender=self.name,
            recipient=AgentName.CRITIC,
            task=task,
            content="\n".join(lines),
            attempt=message.attempt,
        )


class FakeCriticAgent:
    """Accept a memo or request at most one deterministic follow-up."""

    name = AgentName.CRITIC

    def handle(self, message: HandoffMessage) -> AgentMessage:
        """Route weak first-pass evidence back to Research, otherwise to Writer."""
        _require_recipient(message, self.name)
        words = set(re.findall(r"[a-z0-9]+", message.task.casefold()))
        needs_follow_up = bool(words & REVIEW_TERMS) and message.attempt == 0
        if needs_follow_up:
            return HandoffMessage(
                sender=self.name,
                recipient=AgentName.RESEARCH,
                task=message.task,
                content="Critic rejected the first pass: add corroborating evidence.",
                attempt=message.attempt,
            )
        return HandoffMessage(
            sender=self.name,
            recipient=AgentName.WRITER,
            task=message.task,
            content=f"Critic accepted round {message.attempt + 1}.\n{message.content}",
            attempt=message.attempt,
        )


class FakeWriterAgent:
    """Create the only user-facing text in the workflow."""

    name = AgentName.WRITER

    def handle(self, message: HandoffMessage) -> AgentMessage:
        """Render the accepted memo as one deterministic paragraph."""
        _require_recipient(message, self.name)
        evidence = " ".join(
            line.removeprefix("Evidence 1: ").removeprefix("Evidence 2: ")
            for line in message.content.splitlines()
            if line.startswith("Evidence ")
        )
        if not evidence:
            raise AgentError("writer received no accepted evidence")
        return FinalAnswer(text=f"{evidence} This answer was composed by the Writer specialist.")
