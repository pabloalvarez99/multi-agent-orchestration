"""Trace pack: policy + task + seed + schema-1 trace + result (lawyer-unzippable)."""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any, Final, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from mao import __version__
from mao.models import (
    TRACE_SCHEMA_VERSION,
    AgentName,
    StopReason,
    TaskBudget,
    TaskStatus,
    TraceEnvelope,
)
from mao.orchestrator import OrchestrationPolicy, Orchestrator, load_default_policy
from mao.orchestrator.policy_doc import PolicyDocument
from mao.replay import ReplayError, parse_trace_document

PACK_KIND: Final = "mao-trace-pack"
PACK_SCHEMA_VERSION: Final = 1


class PackTask(BaseModel):
    """Task submission fields reproduced offline."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    task: str = Field(min_length=1)
    budget: TaskBudget
    seed: int = Field(ge=0)


class PackResult(BaseModel):
    """Terminal fields needed to re-check ownership offline."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: TaskStatus
    stop_reason: StopReason
    result: str
    result_author: AgentName | None
    agents_involved: tuple[AgentName, ...]
    handoffs_used: int = Field(ge=0)
    research_retries: int = Field(ge=0)


def _canonical(payload: dict[str, Any]) -> bytes:
    """Stable JSON bytes for hashing."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def build_trace_pack(
    *,
    task: str,
    budget: TaskBudget | None = None,
    seed: int = 0,
    policy: OrchestrationPolicy | None = None,
    run_id: str = "pack-run",
) -> dict[str, Any]:
    """Run a task and assemble a pack dictionary."""
    orch_policy = policy or OrchestrationPolicy(load_default_policy())
    limits = budget or orch_policy.default_budget()
    result = Orchestrator(policy=orch_policy).run(task, budget=limits, seed=seed)
    policy_doc = orch_policy.document
    policy_payload = policy_doc.model_dump(mode="json")
    policy_hash = policy_doc.policy_hash()
    trace = TraceEnvelope(
        trace_schema=TRACE_SCHEMA_VERSION,
        run_id=run_id,
        events=result.trace,
    )
    pack_result = PackResult(
        status=result.status,
        stop_reason=result.stop_reason,
        result=result.result,
        result_author=result.result_author,
        agents_involved=result.agents_involved,
        handoffs_used=result.handoffs_used,
        research_retries=result.research_retries,
    )
    body: dict[str, Any] = {
        "pack_kind": PACK_KIND,
        "manifest": {
            "schema_version": PACK_SCHEMA_VERSION,
            "pack_kind": PACK_KIND,
            "policy_id": policy_doc.policy_id,
            "policy_hash": policy_hash,
            "seed": seed,
            "created_with": __version__,
        },
        "policy": policy_payload,
        "task": {
            "task": task,
            "budget": limits.model_dump(mode="json"),
            "seed": seed,
        },
        "result": pack_result.model_dump(mode="json"),
        "trace": trace.model_dump(mode="json"),
    }
    digest = hashlib.sha256(_canonical(body)).hexdigest()
    body["manifest"]["pack_hash"] = digest
    return body


def write_pack_json(path: Path, pack: dict[str, Any]) -> None:
    """Write a single-file pack."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(pack, indent=2) + "\n", encoding="utf-8")


def write_pack_directory(directory: Path, pack: dict[str, Any]) -> None:
    """Write an unzippable directory layout."""
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "manifest.json").write_text(
        json.dumps(pack["manifest"], indent=2) + "\n", encoding="utf-8"
    )
    (directory / "policy.json").write_text(
        json.dumps(pack["policy"], indent=2) + "\n", encoding="utf-8"
    )
    (directory / "task.json").write_text(
        json.dumps(pack["task"], indent=2) + "\n", encoding="utf-8"
    )
    (directory / "result.json").write_text(
        json.dumps(pack["result"], indent=2) + "\n", encoding="utf-8"
    )
    (directory / "trace.json").write_text(
        json.dumps(pack["trace"], indent=2) + "\n", encoding="utf-8"
    )
    (directory / "README.txt").write_text(
        "MAO trace pack\n"
        "Verify: python -m mao.pack verify <this-directory-or-pack.json>\n"
        "Replay: python -m mao.replay trace.json\n"
        "No secrets. Fake specialists. Not a quality claim.\n",
        encoding="utf-8",
    )


def write_pack_zip(path: Path, pack: dict[str, Any]) -> None:
    """Write a zip archive with the directory layout."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, key in (
            ("manifest.json", "manifest"),
            ("policy.json", "policy"),
            ("task.json", "task"),
            ("result.json", "result"),
            ("trace.json", "trace"),
        ):
            archive.writestr(name, json.dumps(pack[key], indent=2) + "\n")
        archive.writestr(
            "README.txt",
            "MAO trace pack\nVerify with: python -m mao.pack verify this.zip\n",
        )


def load_pack(path: Path) -> dict[str, Any]:
    """Load a pack from JSON file, directory, or zip."""
    if path.is_dir():
        return {
            "pack_kind": PACK_KIND,
            "manifest": json.loads((path / "manifest.json").read_text(encoding="utf-8")),
            "policy": json.loads((path / "policy.json").read_text(encoding="utf-8")),
            "task": json.loads((path / "task.json").read_text(encoding="utf-8")),
            "result": json.loads((path / "result.json").read_text(encoding="utf-8")),
            "trace": json.loads((path / "trace.json").read_text(encoding="utf-8")),
        }
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path, "r") as archive:
            return {
                "pack_kind": PACK_KIND,
                "manifest": json.loads(archive.read("manifest.json")),
                "policy": json.loads(archive.read("policy.json")),
                "task": json.loads(archive.read("task.json")),
                "result": json.loads(archive.read("result.json")),
                "trace": json.loads(archive.read("trace.json")),
            }
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def verify_pack(pack: dict[str, Any]) -> TraceEnvelope:
    """Validate pack structure, policy hash, and schema-1 trace."""
    if "manifest" not in pack or "trace" not in pack or "policy" not in pack:
        raise ReplayError("not a MAO trace pack", error_type="invalid_pack")
    try:
        policy = PolicyDocument.model_validate(pack["policy"])
        task = PackTask.model_validate(pack["task"])
        result = PackResult.model_validate(pack["result"])
        manifest = pack["manifest"]
    except (KeyError, ValidationError, TypeError) as error:
        raise ReplayError(f"pack schema invalid: {error}", error_type="invalid_pack") from error
    if manifest.get("policy_hash") != policy.policy_hash():
        raise ReplayError(
            "manifest.policy_hash does not match policy document",
            error_type="policy_hash",
        )
    if manifest.get("policy_id") != policy.policy_id:
        raise ReplayError(
            "manifest.policy_id does not match policy document",
            error_type="policy_id",
        )
    if int(manifest.get("seed", -1)) != task.seed:
        raise ReplayError("manifest.seed does not match task.seed", error_type="seed_mismatch")
    envelope = parse_trace_document(pack["trace"])
    if result.status is TaskStatus.DONE and result.result_author is not AgentName.WRITER:
        raise ReplayError("done result without writer author", error_type="writer_only")
    if result.status is not TaskStatus.DONE and result.result_author is not None:
        raise ReplayError("non-done result claims specialist author", error_type="writer_only")
    return envelope


def pack_round_trip_ok(pack: dict[str, Any]) -> bool:
    """True when verify succeeds and re-run under same policy matches terminals."""
    verify_pack(pack)
    policy = OrchestrationPolicy(PolicyDocument.model_validate(pack["policy"]))
    task = PackTask.model_validate(pack["task"])
    expected = PackResult.model_validate(pack["result"])
    actual = Orchestrator(policy=policy).run(
        task.task,
        budget=task.budget,
        seed=task.seed,
    )
    return (
        actual.status is expected.status
        and actual.stop_reason is expected.stop_reason
        and actual.result_author == expected.result_author
        and actual.handoffs_used == expected.handoffs_used
        and actual.research_retries == expected.research_retries
    )


def main(argv: list[str] | None = None) -> int:
    """CLI: build | verify a trace pack."""
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build", help="run a task and write a pack")
    build.add_argument("--task", required=True)
    build.add_argument("--seed", type=int, default=0)
    build.add_argument("--max-handoffs", type=int, default=8)
    build.add_argument("--out", type=Path, required=True)
    build.add_argument("--format", choices=("json", "dir", "zip"), default="json")

    verify = sub.add_parser("verify", help="verify a pack file, dir, or zip")
    verify.add_argument("path", type=Path)

    args = parser.parse_args(argv)
    if args.command == "build":
        pack = build_trace_pack(
            task=args.task,
            budget=TaskBudget(max_handoffs=args.max_handoffs),
            seed=args.seed,
        )
        if args.format == "json":
            write_pack_json(args.out, pack)
        elif args.format == "dir":
            write_pack_directory(args.out, pack)
        else:
            write_pack_zip(args.out, pack)
        print(json.dumps({"ok": True, "pack_hash": pack["manifest"]["pack_hash"]}, indent=2))
        return 0

    pack = load_pack(args.path)
    envelope = verify_pack(pack)
    print(
        json.dumps(
            {
                "ok": True,
                "events": len(envelope.events),
                "policy_id": pack["manifest"]["policy_id"],
                "policy_hash": pack["manifest"]["policy_hash"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
