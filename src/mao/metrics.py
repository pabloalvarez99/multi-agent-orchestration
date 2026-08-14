"""Small dependency-free Prometheus exposition for process-local signals."""

from __future__ import annotations

from collections import Counter
from threading import Lock

from mao.models import TaskResult, TaskStatus


class MetricsRegistry:
    """Accumulate low-cardinality process metrics under one lock."""

    def __init__(self) -> None:
        """Start every counter at zero while the process-up gauge is implicit."""
        self._lock = Lock()
        self._requests_total = 0
        self._tasks_total: Counter[TaskStatus] = Counter()
        self._handoffs_total = 0

    def record_request(self) -> None:
        """Count one HTTP request received by this application instance."""
        with self._lock:
            self._requests_total += 1

    def record_task(self, result: TaskResult) -> None:
        """Count one terminal orchestration result and its completed handoffs."""
        with self._lock:
            self._tasks_total[result.status] += 1
            self._handoffs_total += result.handoffs_used

    def render(self) -> str:
        """Render the stable Prometheus text exposition format."""
        with self._lock:
            requests_total = self._requests_total
            tasks_total = self._tasks_total.copy()
            handoffs_total = self._handoffs_total
        lines = [
            "# HELP mao_process_up Whether this application process is serving metrics.",
            "# TYPE mao_process_up gauge",
            "mao_process_up 1",
            "# HELP mao_requests_total HTTP requests received by this process.",
            "# TYPE mao_requests_total counter",
            f"mao_requests_total {requests_total}",
            "# HELP mao_tasks_total Terminal orchestration tasks by status.",
            "# TYPE mao_tasks_total counter",
        ]
        lines.extend(
            f'mao_tasks_total{{status="{status.value}"}} {tasks_total[status]}'
            for status in TaskStatus
        )
        lines.extend(
            [
                "# HELP mao_handoffs_total Specialist handoffs completed by this process.",
                "# TYPE mao_handoffs_total counter",
                f"mao_handoffs_total {handoffs_total}",
            ]
        )
        return "\n".join(lines) + "\n"


__all__ = ["MetricsRegistry"]
