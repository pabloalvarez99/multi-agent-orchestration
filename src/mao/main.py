"""HTTP entry point for the bounded free-path orchestration service."""

from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from mao.agents import ResearchCapabilityMissing
from mao.api import (
    ErrorResponse,
    ErrorType,
    TaskRequest,
    TaskResponse,
    TaskRunner,
    execute_task_request,
)
from mao.middleware import RequestIdMiddleware, request_id_of


def create_app(*, runner: TaskRunner = execute_task_request) -> FastAPI:
    """Build an application around an injected, side-effect-free task runner."""
    application = FastAPI(
        title="Multi-Agent Orchestration",
        description=(
            "Bounded research, critic, and writer specialists with a deterministic "
            "credential-free default path."
        ),
        version="0.1.0",
    )
    application.add_middleware(RequestIdMiddleware)

    @application.exception_handler(ResearchCapabilityMissing)
    async def capability_missing(
        request: Request,
        error: ResearchCapabilityMissing,
    ) -> JSONResponse:
        """Return an explicit 4xx when HTTP Research was not configured."""
        request_id = request_id_of(request.scope) or "unavailable"
        envelope = ErrorResponse(
            error=str(error),
            error_type=ErrorType.CAPABILITY_MISSING,
            request_id=request_id,
        )
        return JSONResponse(
            status_code=int(HTTPStatus.CONFLICT),
            content=envelope.model_dump(mode="json"),
        )

    @application.get("/health")
    def health() -> dict[str, str]:
        """Report process availability without constructing a specialist."""
        return {"status": "ok"}

    @application.post("/v1/tasks", response_model=TaskResponse)
    def execute_task(request: TaskRequest) -> TaskResponse:
        """Run one task under its global handoff budget."""
        result = runner(request)
        return TaskResponse.from_result(result)

    return application


app = create_app()
