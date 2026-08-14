"""Agent protocol and deterministic free-path specialists."""

from mao.agents.base import Agent, AgentError
from mao.agents.fake import FakeCriticAgent, FakeResearchAgent, FakeWriterAgent

__all__ = ["Agent", "AgentError", "FakeCriticAgent", "FakeResearchAgent", "FakeWriterAgent"]
