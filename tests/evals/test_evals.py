"""Dataset integrity, metrics, and evaluation CLI tests."""

import json

import pytest

from mao.evals import evaluate, load_dataset
from mao.evals.run import main


def test_dataset_has_twelve_unique_tasks_and_all_slices() -> None:
    tasks = load_dataset()

    assert len(tasks) == 12
    assert len({task.id for task in tasks}) == len(tasks)
    assert {task.category for task in tasks} == {"happy_path", "critic_retry", "budget_stop"}


def test_all_goldens_pass_for_zero_billed_cost() -> None:
    report = evaluate()

    assert report.all_passed
    assert report.provider == "fake"
    assert report.billed_usd == 0.0
    assert report.metrics.total_tasks == report.metrics.passed_tasks == 12
    assert report.metrics.status_counts == {"budget_exhausted": 3, "done": 9}
    assert report.metrics.mean_handoffs == pytest.approx(40 / 12)
    assert report.metrics.writer_completion_rate == pytest.approx(9 / 12)


def test_eval_cli_prints_json_scorecard(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main([])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["provider"] == "fake"
    assert payload["metrics"]["pass_rate"] == 1.0
