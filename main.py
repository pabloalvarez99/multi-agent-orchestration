"""Vercel FastAPI entry point for the public orchestration console."""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from mao.main import app  # noqa: E402

__all__ = ["app"]
