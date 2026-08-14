"""Dataset integrity, metrics, and evaluation CLI tests."""

import json

import pytest

from mao.evals import evaluate, load_boundary_dataset, load_chaos_dataset, load_dataset
from mao.evals.dataset import (
    BASELINE_CHAOS_IDS,
    MIN_CHAOS_CASES,
    assert_chaos_difficulty_predicates,
)
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
    assert [result.outcome for result in report.boundary_results] == [
        "fake_agent",
        "capability_missing",
    ]
    assert all(result.network_calls == 0 for result in report.boundary_results)
    assert len(report.chaos_results) >= MIN_CHAOS_CASES
    assert all(result.passed and result.non_empty_result for result in report.chaos_results)


def test_chaos_dataset_covers_isolation_product_contracts() -> None:
    cases = load_chaos_dataset()

    assert {case.scenario for case in cases} >= {
        "specialist_crash",
        "critic_reject_twice",
        "max_handoffs",
        "writer_impersonation",
    }
    assert len(cases) >= 40
    assert BASELINE_CHAOS_IDS <= {case.id for case in cases}


def test_chaos_difficulty_predicates_reject_all_easy_new_rows() -> None:
    cases = load_chaos_dataset()
    assert_chaos_difficulty_predicates(cases)
    new_rows = [case for case in cases if case.id not in BASELINE_CHAOS_IDS]
    assert any(case.difficulty != "easy" for case in new_rows)
    assert {case.difficulty for case in cases} == {"easy", "medium", "hard"}


def test_boundary_dataset_covers_default_and_missing_capability() -> None:
    cases = load_boundary_dataset()

    assert len(cases) == 2
    assert {case.research for case in cases} == {"fake", "http"}


def test_eval_cli_prints_json_scorecard(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main([])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["provider"] == "fake"
    assert payload["metrics"]["pass_rate"] == 1.0
