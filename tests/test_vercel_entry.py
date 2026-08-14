"""Public serverless entry-point contract tests."""

from fastapi import FastAPI


def test_root_entry_exports_the_mao_app() -> None:
    """Vercel's root module must expose the production FastAPI application."""
    from main import app

    assert isinstance(app, FastAPI)
