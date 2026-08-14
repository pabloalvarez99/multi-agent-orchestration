"""Isolation simulation plumbing gates."""

from mao.sim.isolation import run_isolation_simulation


def test_isolation_simulation_swap_and_writer_gates() -> None:
    # Smaller n in unit test for speed; full n=1000 is the published artifact.
    report = run_isolation_simulation(n=40, seed=20260814, workers=4)
    assert report.swap_rate == 0.0
    assert report.writer_only_violations == 0
    assert report.n == 40
    assert report.label.startswith("isolation/plumbing")
