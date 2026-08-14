"""Offline golden-task evaluation for the fake specialist team."""

from mao.evals.dataset import (
    DEFAULT_BOUNDARY_DATASET,
    DEFAULT_DATASET,
    load_boundary_dataset,
    load_dataset,
)
from mao.evals.runner import evaluate, evaluate_boundary_case, evaluate_case

__all__ = [
    "DEFAULT_BOUNDARY_DATASET",
    "DEFAULT_DATASET",
    "evaluate",
    "evaluate_boundary_case",
    "evaluate_case",
    "load_boundary_dataset",
    "load_dataset",
]
