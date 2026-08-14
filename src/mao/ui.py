"""Accessible, server-rendered console for the deterministic orchestration path."""

from __future__ import annotations

import logging
from http import HTTPStatus
from pathlib import Path
from typing import Annotated, Final

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError

from mao.api import TaskRequest, TaskRunner
from mao.middleware import request_id_of
from mao.orchestrator import OrchestrationPolicy, load_default_policy
from mao.runs import RunStore, retain_run

PACKAGE_DIRECTORY: Final = Path(__file__).resolve().parent
TEMPLATE_DIRECTORY: Final = PACKAGE_DIRECTORY / "templates"
STATIC_DIRECTORY: Final = PACKAGE_DIRECTORY / "static"
DEMO_TASK: Final = "Compare hybrid vs dense retrieval in one paragraph"

LOGGER: Final = logging.getLogger(__name__)
templates = Jinja2Templates(directory=TEMPLATE_DIRECTORY)


def _context(request: Request, **extra: object) -> dict[str, object]:
    """Return shared, deliberately small template context."""
    return {
        "request": request,
        "demo_task": DEMO_TASK,
        **extra,
    }


def build_ui_router(runner: TaskRunner, runs: RunStore) -> APIRouter:
    """Build UI routes over the same injected runner as the JSON API."""
    router = APIRouter(include_in_schema=False)

    @router.get("/", response_class=HTMLResponse)
    def task_console(request: Request) -> Response:
        """Render the credential-free task console."""
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context=_context(
                request,
                task=DEMO_TASK,
                selected_max_handoffs="8",
            ),
        )

    @router.get("/ui/policy", response_class=HTMLResponse)
    def policy_console(request: Request) -> Response:
        """Render the loadable default policy document (read-only)."""
        document = load_default_policy()
        policy = OrchestrationPolicy(document)
        edges = [
            f"{sender.value} → {recipient.value}"
            for sender, recipient in sorted(
                document.allowed_handoffs,
                key=lambda edge: (edge[0].value, edge[1].value),
            )
        ]
        return templates.TemplateResponse(
            request=request,
            name="policy.html",
            context=_context(
                request,
                policy_id=document.policy_id,
                policy_version=document.policy_version,
                policy_hash=policy.policy_hash,
                max_handoffs=document.budgets.max_handoffs,
                max_research_retries=document.budgets.max_research_retries,
                final_author=document.authority.final_author,
                edges=edges,
                stop_reasons=list(document.terminals.stop_reasons),
                statuses=list(document.terminals.statuses),
            ),
        )

    @router.post("/ui/tasks", response_class=HTMLResponse)
    def submit_task(
        request: Request,
        task: Annotated[str, Form()],
        max_handoffs: Annotated[str, Form()] = "8",
    ) -> Response:
        """Run the fake team and render its result and complete P3 trace."""
        request_id = request_id_of(request.scope) or "unavailable"
        try:
            payload = TaskRequest.model_validate(
                {
                    "task": task,
                    "budget": {"max_handoffs": max_handoffs},
                    "research": "fake",
                }
            )
            result = runner(payload)
        except ValidationError as error:
            details = "; ".join(
                f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
                for item in error.errors()
            )
            return templates.TemplateResponse(
                request=request,
                name="error.html",
                context=_context(
                    request,
                    task=task,
                    selected_max_handoffs=max_handoffs,
                    error_type="request_invalid",
                    error=details,
                    request_id=request_id,
                ),
                status_code=int(HTTPStatus.UNPROCESSABLE_ENTITY),
            )
        except Exception as error:  # noqa: BLE001 - browser error boundary
            LOGGER.exception("UI task failed request_id=%s", request_id, exc_info=error)
            return templates.TemplateResponse(
                request=request,
                name="error.html",
                context=_context(
                    request,
                    task=task,
                    selected_max_handoffs=max_handoffs,
                    error_type="internal_error",
                    error="The task console could not complete this request.",
                    request_id=request_id,
                ),
                status_code=int(HTTPStatus.INTERNAL_SERVER_ERROR),
            )

        retain_run(
            runs,
            run_id=request_id,
            task=payload.task,
            seed=payload.seed,
            result=result,
        )
        return templates.TemplateResponse(
            request=request,
            name="result.html",
            context=_context(
                request,
                task=task,
                selected_max_handoffs=max_handoffs,
                result=result,
                request_id=request_id,
            ),
        )

    @router.get("/ui/tasks/{request_id}/timeline.json")
    def download_timeline(request_id: str) -> Response:
        """Download the bare event list for one UI run (legacy attachment)."""
        trace = runs.get_trace(request_id)
        if trace is None:
            return JSONResponse(
                status_code=int(HTTPStatus.NOT_FOUND),
                content={"error": "timeline_not_found"},
            )
        return JSONResponse(
            content=[event.model_dump(mode="json") for event in trace.events],
            headers={
                "Content-Disposition": f'attachment; filename="timeline-{request_id}.json"'
            },
        )

    @router.get("/ui/tasks/{request_id}/export.json")
    def download_export(request_id: str) -> Response:
        """Download schema-1 envelope + run record for offline replay-from-file."""
        record = runs.get(request_id)
        trace = runs.get_trace(request_id)
        if record is None or trace is None:
            return JSONResponse(
                status_code=int(HTTPStatus.NOT_FOUND),
                content={"error": "export_not_found", "run_id": request_id},
            )
        return JSONResponse(
            content={
                "trace_schema": trace.trace_schema,
                "run_id": trace.run_id,
                "run": record.model_dump(mode="json"),
                "events": [event.model_dump(mode="json") for event in trace.events],
            },
            headers={
                "Content-Disposition": f'attachment; filename="trace-{request_id}.json"'
            },
        )

    return router


__all__ = ["STATIC_DIRECTORY", "build_ui_router"]
