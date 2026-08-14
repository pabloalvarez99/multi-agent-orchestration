"""Run one orchestration task and print its JSON response."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from pydantic import ValidationError

from mao.api import TaskBudgetRequest, TaskRequest, TaskResponse
from mao.orchestrator import run_task


def build_parser() -> argparse.ArgumentParser:
    """Create the task CLI parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", required=True, help="Task for the specialist team.")
    parser.add_argument("--max-handoffs", type=int, default=8, help="Global dispatch budget.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the default fake team and emit one JSON object as the last line."""
    arguments = build_parser().parse_args(argv)
    try:
        request = TaskRequest(
            task=arguments.task,
            budget=TaskBudgetRequest(max_handoffs=arguments.max_handoffs),
        )
    except ValidationError as error:
        print(json.dumps({"error": "invalid_request", "details": error.error_count()}))
        return 2
    result = run_task(request.task, budget=request.budget.to_domain())
    print(TaskResponse.from_result(result).model_dump_json())
    return 0 if result.status.value == "done" else 1


if __name__ == "__main__":
    raise SystemExit(main())
