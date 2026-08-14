"""Credential-free task route and OpenAPI contract tests."""

import httpx
import pytest
from fastapi.testclient import TestClient

from mao.api import TaskRequest
from mao.main import app, create_app
from mao.models import AgentMessage, AgentName, HandoffMessage, TaskResult
from mao.orchestrator import InMemoryBus, Orchestrator


class CrashingCritic:
    """API-level fault injection for the degraded 200 contract."""

    name = AgentName.CRITIC

    def handle(self, message: HandoffMessage) -> AgentMessage:
        raise RuntimeError("critic unavailable in API chaos")

client = TestClient(app)


def test_default_task_returns_the_exact_public_shape() -> None:
    response = client.post(
        "/v1/tasks",
        json={"task": "Compare hybrid vs dense retrieval in one paragraph"},
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "trace_schema",
        "status",
        "stop_reason",
        "result",
        "result_author",
        "agents_involved",
        "trace",
    }
    assert body["trace_schema"] == 1
    assert body["status"] == "done"
    assert body["stop_reason"] == "writer_final"
    assert body["result_author"] == "writer"
    assert body["agents_involved"] == ["orchestrator", "research", "critic", "writer"]
    assert body["trace"][-1]["event"] == "stop"


def test_completed_task_is_available_through_versioned_run_endpoints() -> None:
    response = client.post(
        "/v1/tasks",
        json={"task": "Replay this exact route", "seed": 37},
        headers={"x-request-id": "replay-contract-test"},
    )

    run = client.get("/v1/runs/replay-contract-test")
    trace = client.get("/v1/runs/replay-contract-test/trace")

    assert response.status_code == run.status_code == trace.status_code == 200
    assert run.json()["trace_schema"] == trace.json()["trace_schema"] == 1
    assert run.json()["seed"] == 37
    assert len(run.json()["task_sha256"]) == 64
    assert "Replay this exact route" not in trace.text
    assert trace.json()["run_id"] == "replay-contract-test"
    assert trace.json()["events"] == response.json()["trace"]
    assert all(
        {"event", "ts_offset_ms", "actor", "payload"} <= set(event)
        for event in trace.json()["events"]
    )


def test_unknown_run_returns_a_typed_404() -> None:
    response = client.get("/v1/runs/not-retained")

    assert response.status_code == 404
    assert response.json() == {"error": "run_not_found", "run_id": "not-retained"}


def test_request_budget_controls_the_global_handoff_limit() -> None:
    response = client.post(
        "/v1/tasks",
        json={"task": "Compare systems", "budget": {"max_handoffs": 2}},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "budget_exhausted"
    assert response.json()["stop_reason"] == "max_handoffs"
    assert response.json()["result_author"] is None
    assert "max_handoffs" in response.json()["result"]


def test_specialist_crash_is_a_non_empty_degraded_http_200() -> None:
    from mao.agents import FakeResearchAgent, FakeWriterAgent

    orchestrator = Orchestrator(
        bus=InMemoryBus([FakeResearchAgent(), CrashingCritic(), FakeWriterAgent()])
    )

    def crashing_runner(request: TaskRequest) -> TaskResult:
        return orchestrator.run(request.task, budget=request.budget.to_domain())

    response = TestClient(create_app(runner=crashing_runner)).post(
        "/v1/tasks", json={"task": "Exercise degraded isolation"}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["stop_reason"] == "specialist_error"
    assert response.json()["result"].strip()
    assert response.json()["result_author"] is None


def test_unknown_request_fields_are_rejected() -> None:
    response = client.post("/v1/tasks", json={"task": "Compare systems", "model": "openai"})
    assert response.status_code == 422


def test_openapi_exposes_only_max_handoffs_inside_budget() -> None:
    schema = client.get("/openapi.json").json()
    budget = schema["components"]["schemas"]["TaskBudgetRequest"]
    assert set(budget["properties"]) == {"max_handoffs"}


def test_http_choice_without_url_is_a_typed_client_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AGENTIC_RAG_URL", raising=False)

    response = client.post(
        "/v1/tasks",
        json={"task": "Compare systems", "research": "http"},
    )

    assert response.status_code == 409
    body = response.json()
    assert body["error_type"] == "capability_missing"
    assert body["request_id"] == response.headers["x-request-id"]


def test_default_request_never_constructs_an_http_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENTIC_RAG_URL", "https://p2.example.test")

    def forbidden_client(*args: object, **kwargs: object) -> httpx.Client:
        raise AssertionError("the default fake path opened a socket client")

    monkeypatch.setattr(httpx, "Client", forbidden_client)

    response = client.post("/v1/tasks", json={"task": "Compare systems"})

    assert response.status_code == 200
    assert response.json()["status"] == "done"
