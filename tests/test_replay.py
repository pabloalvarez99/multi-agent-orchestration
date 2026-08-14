"""Offline schema-1 file replay contracts."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from mao.main import app, create_app
from mao.models import TraceEnvelope
from mao.orchestrator import run_task
from mao.replay import (
    EXIT_INVALID,
    EXIT_OK,
    ReplayError,
    actor_sequence,
    event_names,
    load_trace_path,
    parse_trace_document,
)
from mao.replay import (
    main as replay_main,
)
from mao.runs import RunStore, retain_run

FIXTURE = Path(__file__).parent / "fixtures" / "schema1-audit-retrieval-risk.json"


def test_committed_fixture_matches_live_actor_sequence() -> None:
    envelope = load_trace_path(FIXTURE)
    live = run_task("Audit retrieval risk", seed=41)

    assert envelope.trace_schema == 1
    assert actor_sequence(envelope) == tuple(event.actor.value for event in live.trace)
    assert event_names(envelope) == tuple(event.event for event in live.trace)
    assert [event.model_dump(mode="json") for event in envelope.events] == [
        event.model_dump(mode="json") for event in live.trace
    ]


def test_invalid_schema_is_typed_replay_error_never_500() -> None:
    with pytest.raises(ReplayError) as raised:
        parse_trace_document({"trace_schema": 99, "run_id": "x", "events": []})
    assert raised.value.error_type in {"schema_invalid", "schema_version"}

    with pytest.raises(ReplayError) as raised_gap:
        parse_trace_document(
            {
                "trace_schema": 1,
                "run_id": "x",
                "events": [
                    {
                        "sequence": 1,
                        "event": "task_started",
                        "ts_offset_ms": 0,
                        "actor": "orchestrator",
                        "payload": {},
                    }
                ],
            }
        )
    assert raised_gap.value.error_type in {"schema_invalid", "sequence_gap"}

    client = TestClient(app)
    home = client.get("/")
    assert home.status_code == 200
    assert "Load trace JSON" in home.text
    assert 'id="trace-file"' in home.text
    # File load is client-side only — there is no upload POST that could 500.
    assert client.post("/ui/tasks/import", json={"events": []}).status_code == 404


def test_cli_exits_zero_on_fixture_and_two_on_invalid(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert replay_main([str(FIXTURE)]) == EXIT_OK
    out = capsys.readouterr().out
    assert "trace_schema=1" in out
    assert "orchestrator" in out

    bad = tmp_path / "bad.json"
    bad.write_text('{"trace_schema": 1, "run_id": "x"}', encoding="utf-8")
    assert replay_main([str(bad)]) == EXIT_INVALID
    err = capsys.readouterr().err
    assert "error_type" in err


def test_export_download_round_trips_through_file_replay() -> None:
    client = TestClient(app)
    page = client.post(
        "/ui/tasks",
        data={"task": "Audit retrieval risk", "max_handoffs": "8"},
        headers={"x-request-id": "export-roundtrip"},
    )
    assert page.status_code == 200
    export = client.get("/ui/tasks/export-roundtrip/export.json")
    assert export.status_code == 200
    assert export.headers["content-disposition"].startswith("attachment;")
    body = export.json()
    assert body["trace_schema"] == 1
    assert body["run_id"] == "export-roundtrip"
    assert body["run"]["run_id"] == "export-roundtrip"
    envelope = parse_trace_document(body)
    assert actor_sequence(envelope) == tuple(
        event["actor"] for event in body["events"]
    )


def test_recycle_equivalent_clears_server_but_file_replay_still_works(
    tmp_path: Path,
) -> None:
    store = RunStore(max_entries=8)
    result = run_task("Compare hybrid vs dense retrieval", seed=7)
    retain_run(
        store,
        run_id="recycle-demo",
        task="Compare hybrid vs dense retrieval",
        seed=7,
        result=result,
    )
    envelope = store.get_trace("recycle-demo")
    assert envelope is not None
    path = tmp_path / "saved.json"
    path.write_text(
        json.dumps(envelope.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )

    store.clear()
    assert store.get("recycle-demo") is None
    assert store.get_trace("recycle-demo") is None
    assert len(store) == 0

    reloaded = load_trace_path(path)
    assert actor_sequence(reloaded) == tuple(event.actor.value for event in result.trace)
    assert reloaded.events == TraceEnvelope(
        run_id="recycle-demo", events=result.trace
    ).events


def test_home_and_result_expose_file_replay_loader() -> None:
    client = TestClient(create_app())
    home = client.get("/")
    assert "Load trace JSON" in home.text
    assert "replay.js" in home.text
    result_page = client.post(
        "/ui/tasks",
        data={"task": "Compare systems", "max_handoffs": "8"},
    )
    assert result_page.status_code == 200
    assert "Download export JSON" in result_page.text
    assert 'id="trace-file"' in result_page.text
