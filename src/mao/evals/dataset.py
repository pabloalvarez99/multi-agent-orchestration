"""Strict JSONL loader for orchestration golden tasks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Final

from pydantic import ValidationError

from mao.evals.models import GoldenTask

DEFAULT_DATASET: Final = Path(__file__).resolve().parents[3] / "data" / "eval" / "tasks.jsonl"
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


__all__ = ["DEFAULT_DATASET", "DatasetError", "load_dataset"]
