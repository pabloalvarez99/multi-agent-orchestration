"""Strict JSONL loader for orchestration golden tasks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Final

from pydantic import ValidationError

from mao.evals.models import BoundaryGolden, ChaosGolden, GoldenTask

DEFAULT_DATASET: Final = Path(__file__).resolve().parents[3] / "data" / "eval" / "tasks.jsonl"
DEFAULT_BOUNDARY_DATASET: Final = (
    Path(__file__).resolve().parents[3] / "data" / "eval" / "research_boundaries.jsonl"
)
DEFAULT_CHAOS_DATASET: Final = (
    Path(__file__).resolve().parents[3] / "data" / "eval" / "chaos.jsonl"
)
REQUIRED_CATEGORIES: Final = frozenset({"happy_path", "critic_retry", "budget_stop"})
REQUIRED_CHAOS_SCENARIOS: Final = frozenset(
    {
        "specialist_crash",
        "critic_reject_twice",
        "max_handoffs",
        "writer_impersonation",
    }
)
BASELINE_CHAOS_IDS: Final = frozenset(
    {
        "critic-crash-degrades",
        "critic-rejects-twice-writer-finishes",
        "global-budget-typed-stop",
        "research-cannot-impersonate-writer",
    }
)
MIN_CHAOS_CASES: Final = 15


class DatasetError(ValueError):
    """The golden task file is malformed or does not cover the workflow."""


def load_dataset(path: Path = DEFAULT_DATASET) -> tuple[GoldenTask, ...]:
    """Load a strict, unique set of at least ten golden tasks."""
    tasks: list[GoldenTask] = []
    seen: set[str] = set()
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            golden = GoldenTask.model_validate(json.loads(raw))
        except (json.JSONDecodeError, ValidationError) as error:
            raise DatasetError(f"{path}:{line_number}: invalid golden task: {error}") from error
        if golden.id in seen:
            raise DatasetError(f"{path}:{line_number}: duplicate id {golden.id!r}")
        seen.add(golden.id)
        tasks.append(golden)

    if len(tasks) < 10:
        raise DatasetError(f"{path}: expected at least 10 tasks, found {len(tasks)}")
    missing = REQUIRED_CATEGORIES - {task.category for task in tasks}
    if missing:
        raise DatasetError(f"{path}: missing categories: {sorted(missing)}")
    return tuple(tasks)


def load_boundary_dataset(
    path: Path = DEFAULT_BOUNDARY_DATASET,
) -> tuple[BoundaryGolden, ...]:
    """Load the small, strict set of optional-research boundary cases."""
    cases: list[BoundaryGolden] = []
    seen: set[str] = set()
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            golden = BoundaryGolden.model_validate(json.loads(raw))
        except (json.JSONDecodeError, ValidationError) as error:
            raise DatasetError(f"{path}:{line_number}: invalid boundary case: {error}") from error
        if golden.id in seen:
            raise DatasetError(f"{path}:{line_number}: duplicate id {golden.id!r}")
        seen.add(golden.id)
        cases.append(golden)
    if not cases:
        raise DatasetError(f"{path}: expected at least one boundary case")
    return tuple(cases)


def load_chaos_dataset(path: Path = DEFAULT_CHAOS_DATASET) -> tuple[ChaosGolden, ...]:
    """Load chaos isolation cases with difficulty metadata."""
    cases: list[ChaosGolden] = []
    seen: set[str] = set()
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            golden = ChaosGolden.model_validate(json.loads(raw))
        except (json.JSONDecodeError, ValidationError) as error:
            raise DatasetError(f"{path}:{line_number}: invalid chaos case: {error}") from error
        if golden.id in seen:
            raise DatasetError(f"{path}:{line_number}: duplicate id {golden.id!r}")
        seen.add(golden.id)
        cases.append(golden)
    if len(cases) < MIN_CHAOS_CASES:
        raise DatasetError(
            f"{path}: expected at least {MIN_CHAOS_CASES} chaos cases, found {len(cases)}"
        )
    missing = REQUIRED_CHAOS_SCENARIOS - {case.scenario for case in cases}
    if missing:
        raise DatasetError(f"{path}: missing chaos scenarios: {sorted(missing)}")
    difficulties = {case.difficulty for case in cases}
    if difficulties != {"easy", "medium", "hard"}:
        raise DatasetError(
            f"{path}: chaos must include easy, medium, and hard; found {sorted(difficulties)}"
        )
    return tuple(cases)


def assert_chaos_difficulty_predicates(cases: tuple[ChaosGolden, ...]) -> None:
    """Fail when new chaos rows are all easy or hard/medium slices are trivial."""
    if len(cases) < MIN_CHAOS_CASES:
        raise DatasetError(f"chaos n={len(cases)} < {MIN_CHAOS_CASES}")
    new_rows = [case for case in cases if case.id not in BASELINE_CHAOS_IDS]
    if not new_rows:
        raise DatasetError("chaos dataset has no rows beyond the v0.3 baseline four")
    if all(case.difficulty == "easy" for case in new_rows):
        raise DatasetError("all new chaos rows are easy; medium/hard required")
    medium = [case for case in cases if case.difficulty == "medium"]
    hard = [case for case in cases if case.difficulty == "hard"]
    if not medium or not hard:
        raise DatasetError("chaos must include medium and hard difficulty rows")
    # Medium must not collapse to status-only with max_handoffs>=8 and no composition.
    weak_medium = [
        case
        for case in medium
        if case.max_handoffs >= 8
        and case.expected_handoffs is None
        and case.expected_retries is None
        and case.scenario
        in {"specialist_crash", "writer_impersonation", "max_handoffs", "illegal_handoff"}
    ]
    if medium and len(weak_medium) / len(medium) >= 0.8:
        raise DatasetError(
            ">=80% of medium chaos cases are weak single-fault status-only checks"
        )
    # Hard must not be single-fault easy clones.
    hard_easy_clones = [
        case
        for case in hard
        if case.scenario
        in {"specialist_crash", "writer_impersonation", "max_handoffs"}
        and case.expected_handoffs is None
        and case.policy_id is None
        and case.pair_token is None
    ]
    if hard and len(hard_easy_clones) / len(hard) >= 0.5:
        raise DatasetError(">=50% of hard chaos cases look like single-fault easy clones")


__all__ = [
    "BASELINE_CHAOS_IDS",
    "DEFAULT_BOUNDARY_DATASET",
    "DEFAULT_DATASET",
    "DEFAULT_CHAOS_DATASET",
    "MIN_CHAOS_CASES",
    "DatasetError",
    "assert_chaos_difficulty_predicates",
    "load_boundary_dataset",
    "load_dataset",
    "load_chaos_dataset",
]
