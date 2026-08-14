"""Offline golden-task evaluation for the fake specialist team."""

from mao.evals.dataset import DEFAULT_DATASET, load_dataset
from mao.evals.runner import evaluate, evaluate_case

__all__ = ["DEFAULT_DATASET", "evaluate", "evaluate_case", "load_dataset"]
