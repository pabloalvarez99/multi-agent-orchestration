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
    """Load one strict case for every required isolation scenario."""
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
    required = {
        "specialist_crash",
        "critic_reject_twice",
        "max_handoffs",
        "writer_impersonation",
    }
    missing = required - {case.scenario for case in cases}
    if missing:
        raise DatasetError(f"{path}: missing chaos scenarios: {sorted(missing)}")
    return tuple(cases)


__all__ = [
    "DEFAULT_BOUNDARY_DATASET",
    "DEFAULT_DATASET",
    "DEFAULT_CHAOS_DATASET",
    "DatasetError",
    "load_boundary_dataset",
    "load_dataset",
    "load_chaos_dataset",
]
