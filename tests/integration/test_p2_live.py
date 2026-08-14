"""Live P2 smoke test; skipped unless an operator configures the dependency."""

import os

import pytest

from mao.agents import AgentError, ResearchChoice, build_research_agent
from mao.models import AgentName, HandoffMessage


@pytest.mark.integration
def test_live_p2_contract() -> None:
    base_url = os.getenv("AGENTIC_RAG_URL", "").strip()
    if not base_url:
        pytest.skip("AGENTIC_RAG_URL is not configured")

    agent = build_research_agent(ResearchChoice.HTTP, base_url=base_url)
    message = HandoffMessage(
        sender=AgentName.ORCHESTRATOR,
        recipient=AgentName.RESEARCH,
        task="Why use reciprocal rank fusion in hybrid retrieval?",
        content="Run the opt-in live contract smoke test.",
    )
    try:
        output = agent.handle(message)
    except AgentError as error:
        pytest.skip(f"configured P2 is unavailable: {error.error_type}")

    assert isinstance(output, HandoffMessage)
    assert output.recipient is AgentName.CRITIC
    assert output.trace_context["dependency"] == "agentic-rag-research"
