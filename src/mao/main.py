"""HTTP entry point for the orchestration scaffold."""

from fastapi import FastAPI

app = FastAPI(
    title="Multi-Agent Orchestration",
    description="Health-only scaffold; orchestration is not implemented yet.",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    """Report that the scaffold process is available."""
    return {"status": "ok"}
