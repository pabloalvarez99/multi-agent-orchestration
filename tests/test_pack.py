"""Trace pack build, verify, and round-trip tests."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from mao.main import create_app
from mao.models import TaskBudget, TaskStatus
from mao.pack import (
    build_trace_pack,
    load_pack,
    pack_round_trip_ok,
    verify_pack,
    write_pack_directory,
    write_pack_json,
    write_pack_zip,
)
from mao.replay import parse_trace_document


def test_trace_pack_round_trip_and_hashes(tmp_path: Path) -> None:
    pack = build_trace_pack(
        task="Compare hybrid vs dense retrieval",
        budget=TaskBudget(max_handoffs=8),
        seed=7,
    )
    assert pack["pack_kind"] == "mao-trace-pack"
    assert pack["manifest"]["policy_id"] == "default-v0.3-characterization"
    assert len(pack["manifest"]["policy_hash"]) == 64
    assert len(pack["manifest"]["pack_hash"]) == 64
    assert pack["result"]["status"] == TaskStatus.DONE.value

    json_path = tmp_path / "pack.json"
    write_pack_json(json_path, pack)
    loaded = load_pack(json_path)
    envelope = verify_pack(loaded)
    assert len(envelope.events) == len(pack["trace"]["events"])
    assert pack_round_trip_ok(loaded)

    dir_path = tmp_path / "pack-dir"
    write_pack_directory(dir_path, pack)
    assert pack_round_trip_ok(load_pack(dir_path))

    zip_path = tmp_path / "pack.zip"
    write_pack_zip(zip_path, pack)
    assert pack_round_trip_ok(load_pack(zip_path))


def test_file_replay_ui_accepts_trace_pack() -> None:
    pack = build_trace_pack(task="Compare hybrid vs dense retrieval", seed=3)
    envelope = parse_trace_document(pack["trace"])
    assert envelope.events

    client = TestClient(create_app())
    # Policy page is part of the pack story surface.
    policy_page = client.get("/ui/policy")
    assert policy_page.status_code == 200
    assert "default-v0.3-characterization" in policy_page.text
    assert "Policy hash" in policy_page.text
    # Pack JSON remains loadable offline via replay module (browser uses same normalize path).
    assert pack["trace"]["events"][0]["event"] == "task_started"
    assert "policy_hash" in json.dumps(pack["trace"]["events"][0]["payload"])
