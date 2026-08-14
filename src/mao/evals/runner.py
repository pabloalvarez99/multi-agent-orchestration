"""Execute golden tasks on the deterministic default team."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from mao.evals.dataset import DEFAULT_DATASET, load_dataset
from mao.evals.models import EvalMetrics, EvalReport, GoldenResult, GoldenTask
from mao.models import AgentName, TaskBudget
from mao.orchestrator import run_task


def evaluate_case(golden: GoldenTask) -> GoldenResult:
    """Run one golden and compare status, participants, handoffs, and retries."""
    result = run_task(golden.task, budget=TaskBudget(max_handoffs=golden.max_handoffs))
    failures: list[str] = []
    _equal(failures, "status", result.status, golden.expected_status)
    _equal(failures, "agents", result.agents_involved, golden.expected_agents)
    _equal(failures, "handoffs", result.handoffs_used, golden.expected_handoffs)
    _equal(failures, "retries", result.research_retries, golden.expected_retries)
    return GoldenResult(
        id=golden.id,
        status=result.status,
        handoffs_used=result.handoffs_used,
        research_retries=result.research_retries,
        writer_finished=AgentName.WRITER in result.agents_involved,
        passed=not failures,
        failures=tuple(failures),
    )


def _equal(failures: list[str], field: str, actual: object, expected: object) -> None:
    """Record a stable mismatch without hiding the observed value."""
    if actual != expected:
        failures.append(f"{field}={actual!r}, expected {expected!r}")


def evaluate(path: Path = DEFAULT_DATASET) -> EvalReport:
    """Run every golden and aggregate handoff, retry, Writer, and status metrics."""
    results = tuple(evaluate_case(golden) for golden in load_dataset(path))
    total = len(results)
    passed = sum(result.passed for result in results)
    handoffs = sum(result.handoffs_used for result in results)
    retried = sum(result.research_retries > 0 for result in results)
    writer_finished = sum(result.writer_finished for result in results)
    counts = dict(sorted(Counter(result.status.value for result in results).items()))
    return EvalReport(
        dataset=path.as_posix(),
        metrics=EvalMetrics(
            total_tasks=total,
            passed_tasks=passed,
            pass_rate=passed / total,
            mean_handoffs=handoffs / total,
            retry_task_rate=retried / total,
            writer_completion_rate=writer_finished / total,
            status_counts=counts,
        ),
        results=results,
    )


__all__ = ["evaluate", "evaluate_case"]
