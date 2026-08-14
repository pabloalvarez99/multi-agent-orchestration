"""Isolation simulation and load probes (plumbing metrics, not quality)."""

from __future__ import annotations

__all__ = ["IsolationReport", "run_isolation_simulation"]


def __getattr__(name: str) -> object:
    """Lazy export to avoid double-import warnings under ``python -m``."""
    if name in __all__:
        from mao.sim import isolation as isolation_module

        return getattr(isolation_module, name)
    raise AttributeError(name)
