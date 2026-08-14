"""Process-local isolation under concurrent fake tasks."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

from fastapi.testclient import TestClient

from mao.main import create_app
from mao.orchestrator import run_task


def test_two_concurrent_fake_tasks_do_not_swap_writer_text_or_traces() -> None:
    client = TestClient(create_app())
    payloads = {
        "alpha": {
            "task": "Alpha isolation probe one unique token AAA-111",
            "seed": 11,
            "budget": {"max_handoffs": 8},
            "research": "fake",
        },
        "beta": {
            "task": "Beta isolation probe two unique token BBB-222",
            "seed": 22,
            "budget": {"max_handoffs": 8},
            "research": "fake",
        },
    }

    def run_one(label: str) -> tuple[str, dict[str, object]]:
        response = client.post(
            "/v1/tasks",
            json=payloads[label],
            headers={"x-request-id": f"concurrent-{label}"},
        )
        assert response.status_code == 200, response.text
        return label, response.json()

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(run_one, label) for label in ("alpha", "beta")]
        completed = (future.result() for future in as_completed(futures))
        results = {label: body for label, body in completed}

    alpha = results["alpha"]
    beta = results["beta"]
    assert alpha["status"] == "done"
    assert beta["status"] == "done"
    assert alpha["result_author"] == "writer"
    assert beta["result_author"] == "writer"
    assert "AAA-111" in alpha["result"]
    assert "BBB-222" in beta["result"]
    assert "BBB-222" not in alpha["result"]
    assert "AAA-111" not in beta["result"]
    assert alpha["trace"] != beta["trace"]
    assert [event["actor"] for event in alpha["trace"]] == [
        event["actor"] for event in alpha["trace"]
    ]

    alpha_run = client.get("/v1/runs/concurrent-alpha")
    beta_run = client.get("/v1/runs/concurrent-beta")
    assert alpha_run.status_code == 200
    assert beta_run.status_code == 200
    assert alpha_run.json()["result"] == alpha["result"]
    assert beta_run.json()["result"] == beta["result"]
    assert "AAA-111" in alpha_run.json()["result"]
    assert "BBB-222" in beta_run.json()["result"]

    alpha_trace = client.get("/v1/runs/concurrent-alpha/trace").json()
    beta_trace = client.get("/v1/runs/concurrent-beta/trace").json()
    assert alpha_trace["events"] == alpha["trace"]
    assert beta_trace["events"] == beta["trace"]
    assert alpha_trace["run_id"] == "concurrent-alpha"
    assert beta_trace["run_id"] == "concurrent-beta"


def test_library_path_isolation_is_also_deterministic() -> None:
    """Sanity: pure library runs with distinct seeds stay independent."""

    def run(label: str, seed: int) -> tuple[str, str, tuple[str, ...]]:
        result = run_task(f"{label} token {label.upper()}", seed=seed)
        return label, result.result, tuple(event.actor.value for event in result.trace)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(run, "left", 1),
            pool.submit(run, "right", 2),
        ]
        outcomes = {label: (text, actors) for label, text, actors in (f.result() for f in futures)}

    assert "LEFT" in outcomes["left"][0]
    assert "RIGHT" in outcomes["right"][0]
    assert "RIGHT" not in outcomes["left"][0]
    assert "LEFT" not in outcomes["right"][0]
