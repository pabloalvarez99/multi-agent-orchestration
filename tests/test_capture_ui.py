"""Generated UI evidence stays tied to the deterministic browser contract."""

from __future__ import annotations

import hashlib

from fastapi.testclient import TestClient

from mao.main import app
from scripts.capture_ui import ASSETS, CAPTURE_SPECS, FIXED_REQUEST_ID, MANIFEST


def test_capture_script_declares_done_budget_and_trace_artifacts() -> None:
    assert [spec.filename for spec in CAPTURE_SPECS] == [
        "ui-done.png",
        "ui-budget.png",
        "ui-trace.png",
        "ui-replay.png",
        "ui-replay-from-file.png",
    ]
    assert [spec.expected_status for spec in CAPTURE_SPECS] == [
        "Done",
        "Budget Exhausted",
        "Done",
        "Done",
        "Done",
    ]
    assert CAPTURE_SPECS[-2].target == ".replay-panel"
    assert CAPTURE_SPECS[-1].target == ".file-replay-loader"
    assert FIXED_REQUEST_ID == "capture-fixed-request-id"


def test_capture_labels_exist_in_the_real_fake_path_html() -> None:
    client = TestClient(app)
    for spec in CAPTURE_SPECS:
        response = client.post(
            "/ui/tasks",
            data={"task": spec.task, "max_handoffs": str(spec.max_handoffs)},
        )
        assert response.status_code == 200
        assert spec.expected_status in response.text
        assert spec.task in response.text
        assert "Ordered execution trace" in response.text
        assert "Request ID" in response.text


def test_committed_capture_hashes_match_the_generated_manifest() -> None:
    expected = {}
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        digest, relative_path = line.split("  ", maxsplit=1)
        expected[relative_path] = digest

    assert set(expected) == {
        f"docs/assets/{spec.filename}" for spec in CAPTURE_SPECS
    }
    for spec in CAPTURE_SPECS:
        path = ASSETS / spec.filename
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected[
            f"docs/assets/{spec.filename}"
        ]
