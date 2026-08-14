"""Credential-free browser surface tests."""

import httpx
import pytest
from fastapi.testclient import TestClient

from mao.main import app


def test_home_is_an_accessible_task_console() -> None:
    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert '<label for="task">Task</label>' in response.text
    assert 'aria-label="Developer links"' in response.text
    assert "Fake team · $0" in response.text
    assert response.headers["x-request-id"]


def test_submit_renders_status_request_id_and_ordered_trace_without_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden_client(*args: object, **kwargs: object) -> httpx.Client:
        raise AssertionError("the UI fake path opened a socket client")

    monkeypatch.setattr(httpx, "Client", forbidden_client)
    response = TestClient(app).post(
        "/ui/tasks",
        data={"task": "Compare hybrid vs dense retrieval", "max_handoffs": "8"},
    )

    assert response.status_code == 200
    assert "Done" in response.text
    assert "Writer output" in response.text
    assert "Ordered execution trace" in response.text
    assert "orchestrator" in response.text
    assert "writer" in response.text
    assert response.headers["x-request-id"] in response.text


def test_budget_exhausted_is_rendered_as_a_first_class_result() -> None:
    response = TestClient(app).post(
        "/ui/tasks",
        data={"task": "Compare systems", "max_handoffs": "1"},
    )

    assert response.status_code == 200
    assert "Budget Exhausted" in response.text
    assert "max_handoffs" in response.text


def test_invalid_form_is_typed_and_keeps_request_id() -> None:
    response = TestClient(app).post(
        "/ui/tasks",
        data={"task": "Compare systems", "max_handoffs": "0"},
    )

    assert response.status_code == 422
    assert "request_invalid" in response.text
    assert response.headers["x-request-id"] in response.text
