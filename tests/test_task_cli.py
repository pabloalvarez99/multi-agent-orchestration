"""Task CLI JSON and exit-code tests."""

import json

import pytest

from mao.task import main


def test_cli_last_line_is_the_public_json_response(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["--task", "Compare hybrid vs dense retrieval in one paragraph"])

    lines = capsys.readouterr().out.splitlines()
    payload = json.loads(lines[-1])
    assert exit_code == 0
    assert payload["status"] == "done"
    assert payload["agents_involved"][-1] == "writer"


def test_cli_budget_stop_is_machine_readable(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["--task", "Compare systems", "--max-handoffs", "1"])

    payload = json.loads(capsys.readouterr().out.splitlines()[-1])
    assert exit_code == 1
    assert payload["status"] == "budget_exhausted"
