"""Bind one correlation id to every HTTP request and response."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from mao.request_id import REQUEST_ID_HEADER, resolve_request_id

if TYPE_CHECKING:
    from mao.metrics import MetricsRegistry

REQUEST_ID_SCOPE_KEY: Final = "request_id"


class MetricsMiddleware:
    """Count every HTTP request without adding route-cardinality labels."""

    def __init__(self, app: ASGIApp, *, registry: MetricsRegistry) -> None:
        """Wrap an ASGI application with its process-local registry."""
        self.app = app
        self.registry = registry

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Increment for HTTP scopes and transparently pass other scopes."""
        if scope["type"] == "http":
            self.registry.record_request()
        await self.app(scope, receive, send)


def request_id_of(scope: Scope) -> str | None:
    """Return the id stored by middleware for this request."""
    state = scope.get("state")
    if not isinstance(state, dict):
        return None
    value = state.get(REQUEST_ID_SCOPE_KEY)
    return value if isinstance(value, str) else None


class RequestIdMiddleware:
    """Resolve one request id and echo it in ``X-Request-ID``."""

    def __init__(self, app: ASGIApp) -> None:
        """Wrap an ASGI application."""
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Bind the id for HTTP scopes and transparently pass other scopes."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = resolve_request_id(Headers(scope=scope).get(REQUEST_ID_HEADER))
        state = scope.setdefault("state", {})
        if isinstance(state, dict):
            state[REQUEST_ID_SCOPE_KEY] = request_id

        async def send_with_request_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                MutableHeaders(scope=message).setdefault(REQUEST_ID_HEADER, request_id)
            await send(message)

        await self.app(scope, receive, send_with_request_id)
