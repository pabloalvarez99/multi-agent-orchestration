"""1000-task isolation simulation with deterministic seed."""

from __future__ import annotations

import argparse
import json
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Final

from mao.models import AgentName, TaskBudget, TaskStatus
from mao.orchestrator import Orchestrator

DEFAULT_N: Final = 1000
DEFAULT_SEED: Final = 20260814
DEFAULT_WORKERS: Final = 8
REPO_ROOT: Final = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class IsolationReport:
    """Plumbing metrics for concurrent fake-task isolation."""

    n: int
    seed: int
    workers: int
    swap_rate: float
    writer_only_violations: int
    swap_count: int
    degraded_rate: float
    budget_exhausted_rate: float
    done_rate: float
    label: str = "isolation/plumbing — not multi-agent quality"
    provider: str = "fake"
    billed_usd: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """JSON-serializable report body."""
        return asdict(self)


def _unique_token(index: int, seed: int) -> str:
    """Build a task-unique token that will not substring-collide with neighbors."""
    return f"ISO{seed:08d}-{index:05d}-X"


def _run_one(index: int, seed: int) -> dict[str, Any]:
    """Execute one fake task and return isolation-relevant fields."""
    token = _unique_token(index, seed)
    # Mix: mostly happy path, some budget pressure, some retry terms.
    if index % 17 == 0:
        task = f"Audit isolation token {token}"
        budget = TaskBudget(max_handoffs=8)
    elif index % 11 == 0:
        task = f"Compare isolation token {token}"
        budget = TaskBudget(max_handoffs=2)
    else:
        task = f"Compare isolation token {token}"
        budget = TaskBudget(max_handoffs=8)
    result = Orchestrator().run(task, budget=budget, seed=(seed + index) % 1_000_000)
    return {
        "index": index,
        "token": token,
        "status": result.status.value,
        "result": result.result,
        "result_author": result.result_author.value if result.result_author else None,
        "writer_only_violation": (
            (result.status is TaskStatus.DONE and result.result_author is not AgentName.WRITER)
            or (
                result.status is not TaskStatus.DONE
                and result.result_author is not None
            )
        ),
    }


def run_isolation_simulation(
    *,
    n: int = DEFAULT_N,
    seed: int = DEFAULT_SEED,
    workers: int = DEFAULT_WORKERS,
) -> IsolationReport:
    """Run n concurrent-capable fake tasks and compute isolation plumbing metrics."""
    if n < 1:
        raise ValueError("n must be positive")
    if workers < 1:
        raise ValueError("workers must be positive")
    # Deterministic shuffle of indices only for scheduling noise; outcomes are per-index.
    order = list(range(n))
    random.Random(seed).shuffle(order)
    rows: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_run_one, index, seed) for index in order]
        for future in as_completed(futures):
            rows.append(future.result())
    rows.sort(key=lambda row: int(row["index"]))
    tokens = {int(row["index"]): str(row["token"]) for row in rows}
    swap_count = 0
    for row in rows:
        text = str(row["result"])
        own = str(row["token"])
        for other_index, other_token in tokens.items():
            if other_index == int(row["index"]):
                continue
            if other_token in text and other_token != own:
                swap_count += 1
                break
    writer_violations = sum(1 for row in rows if row["writer_only_violation"])
    status_counts = {"done": 0, "degraded": 0, "budget_exhausted": 0}
    for row in rows:
        status_counts[str(row["status"])] = status_counts.get(str(row["status"]), 0) + 1
    return IsolationReport(
        n=n,
        seed=seed,
        workers=workers,
        swap_rate=swap_count / n,
        writer_only_violations=writer_violations,
        swap_count=swap_count,
        degraded_rate=status_counts.get("degraded", 0) / n,
        budget_exhausted_rate=status_counts.get("budget_exhausted", 0) / n,
        done_rate=status_counts.get("done", 0) / n,
    )


def render_html(report: IsolationReport) -> str:
    """Render a small HTML scorecard for the isolation simulation."""
    body = report.to_dict()
    rows = "".join(
        f"<tr><th scope=\"row\">{key}</th><td><code>{value}</code></td></tr>"
        for key, value in body.items()
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>P3 isolation simulation</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; max-width: 52rem; }}
    h1 {{ font-size: 1.4rem; }}
    .note {{ color: #444; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #ccc; padding: 0.4rem 0.6rem; text-align: left; }}
    th {{ width: 40%; background: #f6f6f6; }}
  </style>
</head>
<body>
  <h1>Isolation simulation (plumbing)</h1>
  <p class="note">{body["label"]}. Fake specialists only. Single process / single isolate.</p>
  <table><tbody>{rows}</tbody></table>
</body>
</html>
"""


def write_report(
    report: IsolationReport,
    *,
    json_path: Path,
    html_path: Path,
) -> None:
    """Persist JSON and HTML artifacts."""
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8")
    html_path.write_text(render_html(report), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    """CLI entry for the isolation simulation."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=DEFAULT_N)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument(
        "--json-out",
        type=Path,
        default=REPO_ROOT / "docs" / "assets" / "isolation-sim.json",
    )
    parser.add_argument(
        "--html-out",
        type=Path,
        default=REPO_ROOT / "docs" / "assets" / "isolation-sim.html",
    )
    args = parser.parse_args(argv)
    report = run_isolation_simulation(n=args.n, seed=args.seed, workers=args.workers)
    write_report(report, json_path=args.json_out, html_path=args.html_out)
    print(json.dumps(report.to_dict(), indent=2))
    if report.swap_rate != 0.0 or report.writer_only_violations != 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
