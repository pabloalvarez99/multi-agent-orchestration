"""Bounded process-local retention for auditable orchestration runs."""

from __future__ import annotations

import hashlib
from collections import OrderedDict
from threading import Lock
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from mao.models import (
    TRACE_SCHEMA_VERSION,
    AgentName,
    StopReason,
    TaskBudget,
    TaskResult,
    TaskStatus,
    TraceEnvelope,
)


class RunRecord(BaseModel):
    """Replay metadata and terminal output retained without the full task text."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    trace_schema: Literal[1] = TRACE_SCHEMA_VERSION
    run_id: str = Field(min_length=1, max_length=128)
    task_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    seed: int = Field(ge=0)
    status: TaskStatus
    stop_reason: StopReason
    result: str
    result_author: AgentName | None
    agents_involved: tuple[AgentName, ...]
    handoffs_used: int = Field(ge=0)
    research_retries: int = Field(ge=0, le=2)
    budget: TaskBudget

    @classmethod
    def from_result(
        cls,
        *,
        run_id: str,
        task: str,
        seed: int,
        result: TaskResult,
    ) -> RunRecord:
        """Create a public replay record while retaining only a task fingerprint."""
        return cls(
            run_id=run_id,
            task_sha256=hashlib.sha256(task.encode("utf-8")).hexdigest(),
            seed=seed,
            status=result.status,
            stop_reason=result.stop_reason,
            result=result.result,
            result_author=result.result_author,
            agents_involved=result.agents_involved,
            handoffs_used=result.handoffs_used,
            research_retries=result.research_retries,
            budget=result.budget,
        )


class RunStore:
    """Retain the last N immutable runs and evict oldest completion first."""

    def __init__(self, *, max_entries: int = 128) -> None:
        """Create a bounded store with a positive capacity."""
        if max_entries < 1:
            raise ValueError("max_entries must be positive")
        self._max_entries = max_entries
        self._items: OrderedDict[str, tuple[RunRecord, TraceEnvelope]] = OrderedDict()
        self._lock = Lock()

    def put(self, record: RunRecord, trace: TraceEnvelope) -> None:
        """Save one run and enforce the configured retention bound."""
        if record.run_id != trace.run_id:
            raise ValueError("record and trace run_id must match")
        with self._lock:
            self._items[record.run_id] = (record, trace)
            self._items.move_to_end(record.run_id)
            while len(self._items) > self._max_entries:
                self._items.popitem(last=False)

    def get(self, run_id: str) -> RunRecord | None:
        """Return retained run metadata without extending its lifetime."""
        with self._lock:
            item = self._items.get(run_id)
            return item[0] if item is not None else None

    def get_trace(self, run_id: str) -> TraceEnvelope | None:
        """Return the versioned trace for a retained run."""
        with self._lock:
            item = self._items.get(run_id)
            return item[1] if item is not None else None

    def clear(self) -> None:
        """Drop every retained run (recycle-equivalent for local demos and tests)."""
        with self._lock:
            self._items.clear()

    def __len__(self) -> int:
        """Return how many runs this process currently retains."""
        with self._lock:
            return len(self._items)


def retain_run(
    store: RunStore,
    *,
    run_id: str,
    task: str,
    seed: int,
    result: TaskResult,
) -> None:
    """Persist one result and its versioned event envelope atomically."""
    store.put(
        RunRecord.from_result(
            run_id=run_id,
            task=task,
            seed=seed,
            result=result,
        ),
        TraceEnvelope(run_id=run_id, events=result.trace),
    )


__all__ = ["RunRecord", "RunStore", "retain_run"]
