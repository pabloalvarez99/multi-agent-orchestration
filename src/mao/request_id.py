"""Safe request-id generation and caller-header validation."""

from __future__ import annotations

import re
from typing import Final
from uuid import uuid4

REQUEST_ID_HEADER: Final = "X-Request-ID"
MAX_REQUEST_ID_CHARS: Final = 128
_SAFE_REQUEST_ID: Final = re.compile(
    rf"[A-Za-z0-9][A-Za-z0-9._:-]{{0,{MAX_REQUEST_ID_CHARS - 1}}}"
)


def resolve_request_id(value: str | None) -> str:
    """Keep a safe caller id or mint one that is safe to log and echo."""
    if value is not None:
        candidate = value.strip()
        if _SAFE_REQUEST_ID.fullmatch(candidate) is not None:
            return candidate
    return str(uuid4())
