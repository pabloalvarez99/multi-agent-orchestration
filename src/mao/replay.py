"""Offline schema-1 trace replay — client-side durability after the server forgets."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Final

from pydantic import ValidationError

from mao.models import TRACE_SCHEMA_VERSION, TraceEnvelope, TraceEvent

EXIT_OK: Final = 0
EXIT_INVALID: Final = 2


class ReplayError(ValueError):
    """Typed offline-replay failure; never maps to an HTTP 500."""

    def __init__(self, message: str, *, error_type: str) -> None:
        """Record a stable error category for CLI and tests."""
        super().__init__(message)
        self.error_type = error_type


def _as_mapping(raw: object) -> dict[str, Any]:
    """Normalize accepted JSON roots into an envelope-shaped mapping."""
    if isinstance(raw, list):
        return {
            "trace_schema": TRACE_SCHEMA_VERSION,
            "run_id": "file-replay",
            "events": raw,
        }
    if not isinstance(raw, dict):
        raise ReplayError(
            "trace JSON root must be an object or an events array",
            error_type="invalid_root",
        )
    if "trace" in raw and isinstance(raw["trace"], dict):
        return _as_mapping(raw["trace"])
    if "events" not in raw:
        raise ReplayError(
            "trace JSON must include events (schema-1 envelope or bare event list)",
            error_type="missing_events",
        )
    run_meta: dict[str, Any] = raw["run"] if isinstance(raw.get("run"), dict) else {}
    run_id = raw.get("run_id") or run_meta.get("run_id") or "file-replay"
    schema = raw.get("trace_schema", run_meta.get("trace_schema", TRACE_SCHEMA_VERSION))
    return {
        "trace_schema": schema,
        "run_id": run_id,
        "events": raw["events"],
    }


def parse_trace_document(raw: object) -> TraceEnvelope:
    """Validate one offline document into a frozen schema-1 envelope."""
    try:
        mapping = _as_mapping(raw)
        envelope = TraceEnvelope.model_validate(mapping)
    except ReplayError:
        raise
    except ValidationError as error:
        issues = error.error_count()
        raise ReplayError(
            f"trace failed schema-{TRACE_SCHEMA_VERSION} validation ({issues} issue(s))",
            error_type="schema_invalid",
        ) from error
    if envelope.trace_schema != TRACE_SCHEMA_VERSION:
        raise ReplayError(
            f"unsupported trace_schema={envelope.trace_schema}; expected {TRACE_SCHEMA_VERSION}",
            error_type="schema_version",
        )
    _assert_contiguous_sequence(envelope.events)
    return envelope


def load_trace_path(path: Path | str) -> TraceEnvelope:
    """Load and validate a schema-1 trace file from disk."""
    target = Path(path)
    try:
        text = target.read_text(encoding="utf-8")
    except OSError as error:
        raise ReplayError(
            f"could not read trace file: {target}",
            error_type="io_error",
        ) from error
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as error:
        raise ReplayError(
            f"trace file is not valid JSON: {error.msg}",
            error_type="invalid_json",
        ) from error
    return parse_trace_document(raw)


def actor_sequence(envelope: TraceEnvelope) -> tuple[str, ...]:
    """Return the ordered actor names for equality checks and CLI output."""
    return tuple(event.actor.value for event in envelope.events)


def event_names(envelope: TraceEnvelope) -> tuple[str, ...]:
    """Return the ordered event names for fixture comparisons."""
    return tuple(event.event for event in envelope.events)


def _assert_contiguous_sequence(events: tuple[TraceEvent, ...]) -> None:
    """Reject envelopes whose sequence indices are not a zero-based range."""
    for index, event in enumerate(events):
        if event.sequence != index:
            raise ReplayError(
                f"event sequence must be contiguous from 0; index {index} has {event.sequence}",
                error_type="sequence_gap",
            )


def build_parser() -> argparse.ArgumentParser:
    """Create the offline replay CLI parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Validate a downloaded schema-1 trace JSON file and print its actor sequence. "
            "Exit 0 on valid input, 2 on invalid schema. No network, no server store."
        )
    )
    parser.add_argument(
        "path",
        type=Path,
        help="Path to a schema-1 envelope, export pack, or bare events array.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit a machine-readable summary instead of a human actor list.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Validate one file and exit 0 (valid) or 2 (invalid)."""
    arguments = build_parser().parse_args(argv)
    try:
        envelope = load_trace_path(arguments.path)
    except ReplayError as error:
        payload = {
            "ok": False,
            "error": str(error),
            "error_type": error.error_type,
        }
        print(json.dumps(payload), file=sys.stderr)
        return EXIT_INVALID
    if arguments.json:
        print(
            json.dumps(
                {
                    "ok": True,
                    "trace_schema": envelope.trace_schema,
                    "run_id": envelope.run_id,
                    "events": len(envelope.events),
                    "actors": list(actor_sequence(envelope)),
                    "event_names": list(event_names(envelope)),
                }
            )
        )
    else:
        print(f"trace_schema={envelope.trace_schema} run_id={envelope.run_id}")
        print(f"events={len(envelope.events)}")
        print("actors=" + " > ".join(actor_sequence(envelope)))
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
