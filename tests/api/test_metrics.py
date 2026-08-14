"""Prometheus-compatible process metrics tests."""

import re

from fastapi.testclient import TestClient

from mao.main import create_app


def sample(body: str, metric: str) -> int:
    match = re.search(rf"^{re.escape(metric)} ([0-9]+)$", body, re.MULTILINE)
    assert match is not None
    return int(match.group(1))


def test_metrics_content_type_names_and_task_increment_are_stable() -> None:
    client = TestClient(create_app())

    before = client.get("/metrics")
    response = client.post("/v1/tasks", json={"task": "Compare systems"})
    after = client.get("/metrics")

    assert before.status_code == 200
    assert before.headers["content-type"] == "text/plain; version=0.0.4; charset=utf-8"
    assert response.status_code == 200
    assert sample(after.text, "mao_process_up") == 1
    assert sample(after.text, "mao_requests_total") > sample(
        before.text, "mao_requests_total"
    )
    assert sample(after.text, 'mao_tasks_total{status="done"}') == 1
    assert sample(after.text, 'mao_tasks_total{status="degraded"}') == 0
    assert sample(after.text, 'mao_tasks_total{status="budget_exhausted"}') == 0
    assert sample(after.text, "mao_handoffs_total") == 3
