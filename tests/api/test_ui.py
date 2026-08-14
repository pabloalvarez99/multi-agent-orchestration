"""Credential-free browser surface tests."""

import httpx
import pytest
from fastapi.testclient import TestClient

from mao.api import TaskRequest, execute_task_request
from mao.main import app, create_app
from mao.models import TaskResult


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
    assert "Specialist time" in response.text
    assert "Download export JSON" in response.text
    assert "Download events only" in response.text
    assert "Audit this run" in response.text
    assert "Versioned trace" in response.text
    assert "Load trace JSON" in response.text
    assert "orchestrator" in response.text
    assert "writer" in response.text
    assert response.headers["x-request-id"] in response.text


def test_result_timeline_download_matches_the_in_memory_trace() -> None:
    captured: list[TaskResult] = []

    def runner(request: TaskRequest) -> TaskResult:
        result = execute_task_request(request)
        captured.append(result)
        return result

    client = TestClient(create_app(runner=runner))
    result_page = client.post(
        "/ui/tasks",
        data={"task": "Compare hybrid vs dense retrieval", "max_handoffs": "8"},
    )
    request_id = result_page.headers["x-request-id"]

    download = client.get(f"/ui/tasks/{request_id}/timeline.json")

    assert download.status_code == 200
    assert download.headers["content-disposition"].startswith("attachment;")
    assert download.json() == [
        event.model_dump(mode="json") for event in captured[0].trace
    ]
    assert [event["event"] for event in download.json()] == [
        event.event for event in captured[0].trace
    ]
    versioned = client.get(f"/v1/runs/{request_id}/trace")
    assert versioned.json()["trace_schema"] == 1
    assert versioned.json()["events"] == download.json()


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
