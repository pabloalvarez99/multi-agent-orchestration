"""Credential-free task route and OpenAPI contract tests."""

import httpx
import pytest
from fastapi.testclient import TestClient

from mao.main import app

client = TestClient(app)


def test_default_task_returns_the_exact_public_shape() -> None:
    response = client.post(
        "/v1/tasks",
        json={"task": "Compare hybrid vs dense retrieval in one paragraph"},
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"status", "result", "agents_involved", "trace"}
    assert body["status"] == "done"
    assert body["agents_involved"] == ["orchestrator", "research", "critic", "writer"]
    assert body["trace"][-1]["event"] == "stop"


def test_request_budget_controls_the_global_handoff_limit() -> None:
    response = client.post(
        "/v1/tasks",
        json={"task": "Compare systems", "budget": {"max_handoffs": 2}},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "budget_exhausted"
    assert "max_handoffs" in response.json()["result"]


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
