"""Generated UI evidence stays tied to the deterministic browser contract."""

from __future__ import annotations

import hashlib

from fastapi.testclient import TestClient

from mao.main import app
from scripts.capture_ui import ASSETS, CAPTURE_SPECS, FIXED_REQUEST_ID, MANIFEST

TASK_CAPTURES = tuple(spec for spec in CAPTURE_SPECS if spec.task != "POLICY_PAGE")


def test_capture_script_declares_done_budget_and_trace_artifacts() -> None:
    assert [spec.filename for spec in CAPTURE_SPECS] == [
        "ui-done.png",
        "ui-budget.png",
        "ui-trace.png",
        "ui-replay.png",
        "ui-replay-from-file.png",
        "ui-policy.png",
    ]
    assert [spec.expected_status for spec in CAPTURE_SPECS] == [
        "Done",
        "Budget Exhausted",
        "Done",
        "Done",
        "Done",
        "Policy as data",
    ]
    assert CAPTURE_SPECS[-3].target == ".replay-panel"
    assert CAPTURE_SPECS[-2].target == ".file-replay-loader"
    assert CAPTURE_SPECS[-1].target == ".policy-panel"
    assert FIXED_REQUEST_ID == "capture-fixed-request-id"


def test_capture_labels_exist_in_the_real_fake_path_html() -> None:
    client = TestClient(app)
    for spec in TASK_CAPTURES:
        response = client.post(
            "/ui/tasks",
            data={"task": spec.task, "max_handoffs": str(spec.max_handoffs)},
        )
        assert response.status_code == 200
        assert spec.expected_status in response.text
        assert spec.task in response.text
        assert "Ordered execution trace" in response.text
        assert "Request ID" in response.text
    policy = client.get("/ui/policy")
    assert policy.status_code == 200
    assert "Policy as data" in policy.text
    assert "default-v0.3-characterization" in policy.text


def test_committed_capture_hashes_match_the_generated_manifest() -> None:
    expected = {}
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        digest, relative_path = line.split("  ", maxsplit=1)
        expected[relative_path] = digest

    assert set(expected) == {f"docs/assets/{spec.filename}" for spec in CAPTURE_SPECS}
    for spec in CAPTURE_SPECS:
        path = ASSETS / spec.filename
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected[
            f"docs/assets/{spec.filename}"
        ]
