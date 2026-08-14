"""Run the free golden-task evaluation and print a JSON scorecard."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from mao.evals.dataset import DEFAULT_DATASET, DatasetError
from mao.evals.runner import evaluate


def build_parser() -> argparse.ArgumentParser:
    """Create the evaluation CLI parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--pretty", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Evaluate the fake team, returning nonzero if a golden regresses."""
    arguments = build_parser().parse_args(argv)
    try:
        report = evaluate(arguments.dataset)
    except (DatasetError, OSError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False))
        return 2
    print(report.model_dump_json(indent=2 if arguments.pretty else None))
    return 0 if report.all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
