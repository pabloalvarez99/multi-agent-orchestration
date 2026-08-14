"""Accessible, server-rendered console for the deterministic orchestration path."""

from __future__ import annotations

import logging
from collections import OrderedDict
from http import HTTPStatus
from pathlib import Path
from threading import Lock
from typing import Annotated, Final

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError

from mao.api import TaskRequest, TaskRunner
from mao.middleware import request_id_of
from mao.models import TraceEvent

PACKAGE_DIRECTORY: Final = Path(__file__).resolve().parent
TEMPLATE_DIRECTORY: Final = PACKAGE_DIRECTORY / "templates"
STATIC_DIRECTORY: Final = PACKAGE_DIRECTORY / "static"
DEMO_TASK: Final = "Compare hybrid vs dense retrieval in one paragraph"

LOGGER: Final = logging.getLogger(__name__)
templates = Jinja2Templates(directory=TEMPLATE_DIRECTORY)


class TimelineStore:
    """Keep a bounded process-local set of downloadable UI traces."""

    def __init__(self, *, max_entries: int = 128) -> None:
        """Create a store that evicts the oldest completed run first."""
        self._max_entries = max_entries
        self._items: OrderedDict[str, tuple[TraceEvent, ...]] = OrderedDict()
        self._lock = Lock()

    def put(self, request_id: str, trace: tuple[TraceEvent, ...]) -> None:
        """Save one immutable trace and enforce the entry bound."""
        with self._lock:
            self._items[request_id] = trace
            self._items.move_to_end(request_id)
            while len(self._items) > self._max_entries:
                self._items.popitem(last=False)

    def get(self, request_id: str) -> tuple[TraceEvent, ...] | None:
        """Return one trace without extending its retention lifetime."""
        with self._lock:
            return self._items.get(request_id)


def _context(request: Request, **extra: object) -> dict[str, object]:
    """Return shared, deliberately small template context."""
    return {
        "request": request,
        "demo_task": DEMO_TASK,
        **extra,
    }


def build_ui_router(runner: TaskRunner) -> APIRouter:
    """Build UI routes over the same injected runner as the JSON API."""
    router = APIRouter(include_in_schema=False)
    timelines = TimelineStore()

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

        timelines.put(request_id, result.trace)
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
        """Download the exact JSON-safe trace retained for one UI run."""
        trace = timelines.get(request_id)
        if trace is None:
            return JSONResponse(
                status_code=int(HTTPStatus.NOT_FOUND),
                content={"error": "timeline_not_found"},
            )
        return JSONResponse(
            content=[event.model_dump(mode="json") for event in trace],
            headers={
                "Content-Disposition": f'attachment; filename="timeline-{request_id}.json"'
            },
        )

    return router


__all__ = ["STATIC_DIRECTORY", "TimelineStore", "build_ui_router"]
