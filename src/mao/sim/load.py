"""Honest single-isolate load probe for POST /v1/tasks fake path."""

from __future__ import annotations

import argparse
import json
import statistics
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Final

from fastapi.testclient import TestClient

from mao.main import create_app

DEFAULT_N: Final = 50
REPO_ROOT: Final = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class LoadReport:
    """Latency summary for fake POST /v1/tasks on one process."""

    n: int
    p50_ms: float
    p95_ms: float
    mean_ms: float
    min_ms: float
    max_ms: float
    cold_start_ms: float
    honesty: str = (
        "single isolate / single process TestClient — not multi-region capacity planning"
    )
    path: str = "POST /v1/tasks"
    research: str = "fake"
    billed_usd: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """JSON body for docs/assets/load.json."""
        return asdict(self)


def _percentile(sorted_values: list[float], pct: float) -> float:
    """Nearest-rank percentile for a non-empty sorted list."""
    if not sorted_values:
        raise ValueError("empty sample")
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = max(0, min(len(sorted_values) - 1, int(round((pct / 100.0) * (len(sorted_values) - 1)))))
    return sorted_values[rank]


def run_load_probe(*, n: int = DEFAULT_N) -> LoadReport:
    """Issue n fake tasks against an in-process app and report p50/p95."""
    if n < 1:
        raise ValueError("n must be positive")
    client = TestClient(create_app())
    samples_ms: list[float] = []
    cold_start_ms = 0.0
    for index in range(n):
        payload = {
            "task": f"Compare load probe sample {index}",
            "budget": {"max_handoffs": 8},
            "research": "fake",
            "seed": index,
        }
        started = time.perf_counter()
        response = client.post("/v1/tasks", json=payload)
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        if response.status_code != 200:
            raise RuntimeError(f"load probe failed status={response.status_code}: {response.text}")
        samples_ms.append(elapsed_ms)
        if index == 0:
            cold_start_ms = elapsed_ms
    ordered = sorted(samples_ms)
    return LoadReport(
        n=n,
        p50_ms=round(_percentile(ordered, 50), 3),
        p95_ms=round(_percentile(ordered, 95), 3),
        mean_ms=round(statistics.fmean(samples_ms), 3),
        min_ms=round(min(samples_ms), 3),
        max_ms=round(max(samples_ms), 3),
        cold_start_ms=round(cold_start_ms, 3),
    )


def main(argv: list[str] | None = None) -> int:
    """CLI for the load probe."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=DEFAULT_N)
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / "docs" / "assets" / "load.json",
    )
    args = parser.parse_args(argv)
    report = run_load_probe(n=args.n)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report.to_dict(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
