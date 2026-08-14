"""Run one orchestration task and print its JSON response."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from pydantic import ValidationError

from mao.agents import ResearchCapabilityMissing, ResearchChoice
from mao.api import TaskBudgetRequest, TaskRequest, TaskResponse, execute_task_request


def build_parser() -> argparse.ArgumentParser:
    """Create the task CLI parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", required=True, help="Task for the specialist team.")
    parser.add_argument("--max-handoffs", type=int, default=8, help="Global dispatch budget.")
    parser.add_argument("--seed", type=int, default=0, help="Recorded deterministic run seed.")
    parser.add_argument(
        "--research",
        choices=[choice.value for choice in ResearchChoice],
        default=ResearchChoice.FAKE.value,
        help="Research specialist; http requires AGENTIC_RAG_URL.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the default fake team and emit one JSON object as the last line."""
    arguments = build_parser().parse_args(argv)
    try:
        request = TaskRequest(
            task=arguments.task,
            budget=TaskBudgetRequest(max_handoffs=arguments.max_handoffs),
            research=ResearchChoice(arguments.research),
            seed=arguments.seed,
        )
        result = execute_task_request(request)
    except ValidationError as error:
        print(json.dumps({"error": "invalid_request", "details": error.error_count()}))
        return 2
    except ResearchCapabilityMissing as error:
        print(json.dumps({"error": str(error), "error_type": error.error_type}))
        return 3
    print(TaskResponse.from_result(result).model_dump_json())
    return 0 if result.status.value == "done" else 1


if __name__ == "__main__":
    raise SystemExit(main())
