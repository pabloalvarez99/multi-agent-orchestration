"""HTTP entry point for the bounded free-path orchestration service."""

from fastapi import FastAPI

from mao.api import TaskRequest, TaskResponse, TaskRunner
from mao.models import TaskBudget, TaskResult
from mao.orchestrator import run_task


def _default_runner(task: str, budget: TaskBudget) -> TaskResult:
    """Adapt the keyword-only domain function to the transport runner seam."""
    return run_task(task, budget=budget)


def create_app(*, runner: TaskRunner = _default_runner) -> FastAPI:
    """Build an application around an injected, side-effect-free task runner."""
    application = FastAPI(
        title="Multi-Agent Orchestration",
        description=(
            "Bounded research, critic, and writer specialists with a deterministic "
            "credential-free default path."
        ),
        version="0.1.0",
    )

    @application.get("/health")
    def health() -> dict[str, str]:
        """Report process availability without constructing a specialist."""
        return {"status": "ok"}

    @application.post("/v1/tasks", response_model=TaskResponse)
    def execute_task(request: TaskRequest) -> TaskResponse:
        """Run one task under its global handoff budget."""
        result = runner(request.task, request.budget.to_domain())
        return TaskResponse.from_result(result)

    return application


app = create_app()
