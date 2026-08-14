"""Offline contract tests for the optional P2 Research specialist."""

from __future__ import annotations

import httpx
import pytest

from mao.agents import (
    AgentError,
    FakeResearchAgent,
    HttpP2ResearchAgent,
    ResearchChoice,
    build_research_agent,
)
from mao.models import AgentName, HandoffMessage, TaskStatus
from mao.orchestrator import run_task


def research_message(task: str = "Compare hybrid and dense retrieval") -> HandoffMessage:
    return HandoffMessage(
        sender=AgentName.ORCHESTRATOR,
        recipient=AgentName.RESEARCH,
        task=task,
        content="Begin research.",
    )


def test_http_research_maps_p2_report_and_compact_trace_pointer() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["body"] = request.read()
        return httpx.Response(
            200,
            json={
                "status": "done",
                "report": "Hybrid retrieval combines lexical and semantic evidence [1].",
                "citations": [
                    {
                        "marker": 1,
                        "source_path": "hybrid.md",
                        "chunk_id": "hybrid-1",
                        "snippet": "Short evidence.",
                    }
                ],
                "steps_used": 2,
                "request_id": "p2-request-1",
                "trace": [{"raw": "must not cross the boundary"}],
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    agent = HttpP2ResearchAgent("https://p2.example.test", client=client)

    output = agent.handle(research_message())

    assert isinstance(output, HandoffMessage)
    assert output.recipient is AgentName.CRITIC
    assert "Hybrid retrieval combines" in output.content
    assert "[1] hybrid.md#hybrid-1" in output.content
    assert "must not cross" not in output.content
    assert output.trace_context == {
        "dependency": "agentic-rag-research",
        "host": "p2.example.test",
        "status": "done",
        "steps_used": 2,
        "request_id": "p2-request-1",
    }
    assert captured["path"] == "/v1/research"
    assert captured["body"] == (
        b'{"question":"Compare hybrid and dense retrieval","retriever":"fake"}'
    )


@pytest.mark.parametrize(
    ("failure", "expected_error_type"),
    [
        (httpx.Response(502, json={"error": "downstream"}), "dependency_http_error"),
        (httpx.ReadTimeout("too slow"), "dependency_timeout"),
    ],
)
def test_http_failure_degrades_without_writer(
    failure: httpx.Response | httpx.ReadTimeout,
    expected_error_type: str,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if isinstance(failure, httpx.Response):
            return failure
        failure.request = request
        raise failure

    agent = HttpP2ResearchAgent(
        "https://p2.example.test",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    result = run_task("Compare systems", research_agent=agent)

    assert result.status is TaskStatus.DEGRADED
    assert AgentName.WRITER not in result.agents_involved
    error_events = [event for event in result.trace if event.event == "specialist_error"]
    assert error_events[0].payload["error_type"] == expected_error_type


def test_invalid_p2_response_is_a_contract_error() -> None:
    client = httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"status": "done"}))
    )
    agent = HttpP2ResearchAgent("https://p2.example.test", client=client)

    with pytest.raises(AgentError, match="invalid response") as raised:
        agent.handle(research_message())

    assert raised.value.error_type == "dependency_contract_error"


def test_factory_keeps_fake_as_default_even_when_url_is_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENTIC_RAG_URL", "https://p2.example.test")
    assert isinstance(build_research_agent(), FakeResearchAgent)
    assert isinstance(build_research_agent(ResearchChoice.FAKE), FakeResearchAgent)


def test_factory_allows_caller_to_explicitly_select_p2_http_retrieval() -> None:
    captured: dict[str, bytes] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = request.read()
        return httpx.Response(
            200,
            json={
                "status": "done",
                "report": "Evidence from P2.",
                "citations": [],
                "steps_used": 1,
                "request_id": "p2-request-2",
            },
        )

    agent = build_research_agent(
        ResearchChoice.HTTP,
        base_url="https://p2.example.test",
        retriever="http",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    agent.handle(research_message())

    assert captured["body"].endswith(b'"retriever":"http"}')
