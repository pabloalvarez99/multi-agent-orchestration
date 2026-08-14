"""Optional Research specialist backed by P2's public HTTP contract."""

from __future__ import annotations

import os
from enum import StrEnum
from typing import Final, Literal
from urllib.parse import SplitResult, urlsplit

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from mao.agents.base import Agent, AgentError
from mao.agents.fake import FakeResearchAgent
from mao.models import AgentMessage, AgentName, HandoffMessage

AGENTIC_RAG_URL_ENV: Final = "AGENTIC_RAG_URL"
P2_RESEARCH_PATH: Final = "/v1/research"
DEFAULT_TIMEOUT_SECONDS: Final = 5.0


class ResearchChoice(StrEnum):
    """Research implementation a caller explicitly selected."""

    FAKE = "fake"
    HTTP = "http"


class ResearchCapabilityMissing(AgentError):
    """The caller selected HTTP research but no safe P2 URL is configured."""

    def __init__(self, message: str) -> None:
        """Classify the configuration failure for the HTTP boundary."""
        super().__init__(message, error_type="capability_missing")


class _P2Citation(BaseModel):
    """Citation fields P3 needs to preserve a compact evidence pointer."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    marker: int = Field(ge=1)
    source_path: str = Field(min_length=1, max_length=2_000)
    chunk_id: str | None = Field(default=None, max_length=500)
    snippet: str | None = Field(default=None, max_length=2_000)


class _P2Response(BaseModel):
    """Pinned subset of the P2 v0.1.0 response used by Research."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    status: Literal["done", "refused", "budget_exhausted", "degraded"]
    report: str = Field(min_length=1, max_length=12_000)
    citations: tuple[_P2Citation, ...] = Field(default=(), max_length=50)
    steps_used: int = Field(ge=0, le=20)
    request_id: str = Field(min_length=1, max_length=128)


def _validate_base_url(raw: str) -> tuple[str, SplitResult]:
    """Return a normalized absolute HTTP URL with no embedded credentials."""
    candidate = raw.strip().rstrip("/")
    parsed = urlsplit(candidate)
    if (
        not candidate
        or parsed.scheme not in {"http", "https"}
        or parsed.hostname is None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ResearchCapabilityMissing(
            f"{AGENTIC_RAG_URL_ENV} must be an absolute http(s) URL without credentials"
        )
    return candidate, parsed


class HttpP2ResearchAgent:
    """Use P2 as Research while preserving P3's existing handoff protocol."""

    name = AgentName.RESEARCH
    provider = "http_p2"

    def __init__(
        self,
        base_url: str,
        *,
        retriever: Literal["fake", "http"] = "fake",
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        client: httpx.Client | None = None,
    ) -> None:
        """Configure one bounded, no-retry client for P2."""
        normalized, parsed = _validate_base_url(base_url)
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self._endpoint = f"{normalized}{P2_RESEARCH_PATH}"
        self._host = parsed.netloc
        self._retriever = retriever
        self._timeout = httpx.Timeout(timeout_seconds)
        self._client = client

    @property
    def endpoint(self) -> str:
        """Return the P2 endpoint used for the request."""
        return self._endpoint

    def handle(self, message: HandoffMessage) -> AgentMessage:
        """Call P2 once and map its report and citations into Critic evidence."""
        if message.recipient is not self.name:
            raise AgentError(
                f"research received a message addressed to {message.recipient.value}"
            )
        if self._client is not None:
            response = self._post(self._client, message.task)
        else:
            with httpx.Client(timeout=self._timeout, follow_redirects=False) as client:
                response = self._post(client, message.task)
        return HandoffMessage(
            sender=self.name,
            recipient=AgentName.CRITIC,
            task=message.task,
            content=self._evidence_content(response),
            attempt=message.attempt,
            trace_context={
                "dependency": "agentic-rag-research",
                "host": self._host,
                "status": response.status,
                "steps_used": response.steps_used,
                "request_id": response.request_id,
            },
        )

    def _post(self, client: httpx.Client, task: str) -> _P2Response:
        """Issue one request, with no redirect and no retry layer."""
        try:
            response = client.post(
                self._endpoint,
                json={"question": task, "retriever": self._retriever},
                timeout=self._timeout,
                follow_redirects=False,
            )
            response.raise_for_status()
        except httpx.TimeoutException as error:
            raise AgentError(
                "P2 research timed out",
                error_type="dependency_timeout",
            ) from error
        except httpx.HTTPStatusError as error:
            raise AgentError(
                f"P2 research returned HTTP {error.response.status_code}",
                error_type="dependency_http_error",
            ) from error
        except httpx.RequestError as error:
            raise AgentError(
                "P2 research was unavailable",
                error_type="dependency_unavailable",
            ) from error

        try:
            return _P2Response.model_validate(response.json())
        except (ValueError, ValidationError) as error:
            raise AgentError(
                "P2 research returned an invalid response",
                error_type="dependency_contract_error",
            ) from error

    @staticmethod
    def _evidence_content(response: _P2Response) -> str:
        """Build Critic-readable evidence without copying P2's execution trace."""
        report = " ".join(response.report.split())
        lines = [
            f"P2 research status={response.status} steps_used={response.steps_used}",
            f"Evidence 1: {report}",
        ]
        if response.citations:
            pointers = "; ".join(
                f"[{citation.marker}] {citation.source_path}"
                + (f"#{citation.chunk_id}" if citation.chunk_id else "")
                for citation in response.citations
            )
            lines.append(f"Evidence 2: P2 citations: {pointers}")
        return "\n".join(lines)[:16_000]


def build_research_agent(
    choice: ResearchChoice = ResearchChoice.FAKE,
    *,
    base_url: str | None = None,
    client: httpx.Client | None = None,
    retriever: Literal["fake", "http"] = "fake",
) -> Agent:
    """Build fake by default, or the explicitly selected P2 HTTP specialist."""
    if choice is ResearchChoice.FAKE:
        return FakeResearchAgent()
    configured = os.environ.get(AGENTIC_RAG_URL_ENV, "") if base_url is None else base_url
    if not configured.strip():
        raise ResearchCapabilityMissing(
            f"research='http' requires a non-empty {AGENTIC_RAG_URL_ENV}"
        )
    return HttpP2ResearchAgent(configured, retriever=retriever, client=client)


__all__ = [
    "AGENTIC_RAG_URL_ENV",
    "HttpP2ResearchAgent",
    "ResearchCapabilityMissing",
    "ResearchChoice",
    "build_research_agent",
]
