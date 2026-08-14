"""HTTP entry point for the bounded free-path orchestration service."""

from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from mao.agents import ResearchCapabilityMissing
from mao.api import (
    ErrorResponse,
    ErrorType,
    TaskRequest,
    TaskResponse,
    TaskRunner,
    execute_task_request,
)
from mao.metrics import MetricsRegistry
from mao.middleware import MetricsMiddleware, RequestIdMiddleware, request_id_of
from mao.models import TaskResult, TraceEnvelope
from mao.runs import RunRecord, RunStore, retain_run
from mao.ui import STATIC_DIRECTORY, build_ui_router


def create_app(*, runner: TaskRunner = execute_task_request) -> FastAPI:
    """Build an application around an injected, side-effect-free task runner."""
    metrics = MetricsRegistry()
    runs = RunStore(max_entries=128)

    def observed_runner(request: TaskRequest) -> TaskResult:
        result = runner(request)
        metrics.record_task(result)
        return result

    application = FastAPI(
        title="Multi-Agent Orchestration",
        description=(
            "Bounded research, critic, and writer specialists with a deterministic "
            "credential-free default path."
        ),
        version="0.1.0",
    )
    application.add_middleware(RequestIdMiddleware)
    application.add_middleware(MetricsMiddleware, registry=metrics)
    application.mount("/static", StaticFiles(directory=STATIC_DIRECTORY), name="static")

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

    @application.get("/metrics", include_in_schema=False)
    def prometheus_metrics() -> Response:
        """Expose dependency-free process counters in Prometheus text format."""
        return Response(
            content=metrics.render(),
            headers={"Content-Type": "text/plain; version=0.0.4; charset=utf-8"},
        )

    @application.post("/v1/tasks", response_model=TaskResponse)
    def execute_task(payload: TaskRequest, request: Request) -> TaskResponse:
        """Run one task under its global handoff budget."""
        result = observed_runner(payload)
        run_id = request_id_of(request.scope) or "unavailable"
        retain_run(
            runs,
            run_id=run_id,
            task=payload.task,
            seed=payload.seed,
            result=result,
        )
        return TaskResponse.from_result(result)

    @application.get("/v1/runs/{run_id}", response_model=RunRecord)
    def get_run(run_id: str) -> RunRecord | JSONResponse:
        """Return retained replay metadata for one process-local run."""
        record = runs.get(run_id)
        if record is None:
            return JSONResponse(
                status_code=int(HTTPStatus.NOT_FOUND),
                content={"error": "run_not_found", "run_id": run_id},
            )
        return record

    @application.get("/v1/runs/{run_id}/trace", response_model=TraceEnvelope)
    def get_run_trace(run_id: str) -> TraceEnvelope | JSONResponse:
        """Return the versioned replay trace for one process-local run."""
        trace = runs.get_trace(run_id)
        if trace is None:
            return JSONResponse(
                status_code=int(HTTPStatus.NOT_FOUND),
                content={"error": "run_not_found", "run_id": run_id},
            )
        return trace

    application.include_router(build_ui_router(observed_runner, runs))

    return application


app = create_app()
