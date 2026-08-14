"""In-process message bus used by the free-path orchestrator."""

from __future__ import annotations

from collections.abc import Iterable

from mao.agents import Agent, AgentError
from mao.models import AgentMessage, AgentName, HandoffMessage


class InMemoryBus:
    """Address messages to isolated agent objects without network or globals."""

    def __init__(self, agents: Iterable[Agent]) -> None:
        """Register exactly one handler for each supplied specialist name."""
        self._agents: dict[AgentName, Agent] = {}
        for agent in agents:
            if agent.name in self._agents:
                raise ValueError(f"duplicate agent registration: {agent.name.value}")
            if agent.name is AgentName.ORCHESTRATOR:
                raise ValueError("orchestrator is the bus caller, not a specialist")
            self._agents[agent.name] = agent

    @property
    def registered(self) -> tuple[AgentName, ...]:
        """Return registered names in stable insertion order."""
        return tuple(self._agents)

    def dispatch(self, message: HandoffMessage) -> AgentMessage:
        """Deliver one message to its named specialist."""
        agent = self._agents.get(message.recipient)
        if agent is None:
            raise AgentError(f"no specialist is registered for {message.recipient.value}")
        return agent.handle(message)
