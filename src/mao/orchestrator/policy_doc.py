"""Loadable orchestration policy documents (data, not a second if-forest)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Final, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from mao.models import AgentName

REPO_ROOT: Final = Path(__file__).resolve().parents[3]
DEFAULT_POLICY_PATH: Final = REPO_ROOT / "policies" / "default-v0.3-characterization.json"
FORBID_RESEARCH_TO_WRITER_PATH: Final = (
    REPO_ROOT / "policies" / "fixtures" / "forbid-research-to-writer.json"
)


class PolicyBudgets(BaseModel):
    """Default budget ceilings carried by a policy document."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    max_handoffs: int = Field(default=8, ge=1, le=64)
    max_research_retries: int = Field(default=2, ge=0, le=2)


class PolicyAuthority(BaseModel):
    """Who may own successful user-facing text."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    final_author: Literal["writer"] = "writer"
    non_done_result_author: None = None


class PolicyTerminals(BaseModel):
    """Closed-set terminal vocabulary advertised by the policy."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    statuses: tuple[str, ...]
    stop_reasons: tuple[str, ...]


class PolicyDegraded(BaseModel):
    """Degraded-mode contract flags."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    require_non_empty_explanation: bool = True
    never_promote_intermediate_memo: bool = True


class PolicyProviders(BaseModel):
    """Default specialist provider posture."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    default_research: Literal["fake"] = "fake"
    optional_http_p2: Literal["fail_closed"] = "fail_closed"


class PolicyDocument(BaseModel):
    """Versioned handoff graph and authority rules loaded from JSON."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    policy_version: str = Field(min_length=1)
    policy_id: str = Field(min_length=1)
    allowed_handoffs: tuple[tuple[AgentName, AgentName], ...]
    budgets: PolicyBudgets = Field(default_factory=PolicyBudgets)
    authority: PolicyAuthority = Field(default_factory=PolicyAuthority)
    terminals: PolicyTerminals
    degraded: PolicyDegraded = Field(default_factory=PolicyDegraded)
    providers: PolicyProviders = Field(default_factory=PolicyProviders)

    @field_validator("allowed_handoffs", mode="before")
    @classmethod
    def _coerce_edges(cls, value: object) -> object:
        """Accept JSON arrays of two agent name strings."""
        if not isinstance(value, list):
            return value
        edges: list[tuple[str, str]] = []
        for item in value:
            if isinstance(item, (list, tuple)) and len(item) == 2:
                edges.append((str(item[0]), str(item[1])))
            else:
                raise ValueError("each allowed_handoffs entry must be [sender, recipient]")
        return edges

    def edge_set(self) -> frozenset[tuple[AgentName, AgentName]]:
        """Return the allowed directed graph as a frozenset of edges."""
        return frozenset(self.allowed_handoffs)

    def canonical_bytes(self) -> bytes:
        """Stable UTF-8 JSON for hashing (sorted keys, compact separators)."""
        payload = self.model_dump(mode="json")
        text = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return text.encode("utf-8")

    def policy_hash(self) -> str:
        """SHA-256 hex digest of the canonical policy document bytes."""
        return hashlib.sha256(self.canonical_bytes()).hexdigest()


class PolicyLoadError(ValueError):
    """The policy file is missing, malformed, or violates structural rules."""


def load_policy_document(path: Path | str) -> PolicyDocument:
    """Load and validate one policy JSON file from disk."""
    policy_path = Path(path)
    try:
        raw_text = policy_path.read_text(encoding="utf-8")
    except OSError as error:
        raise PolicyLoadError(f"cannot read policy file {policy_path}: {error}") from error
    try:
        raw: Any = json.loads(raw_text)
        document = PolicyDocument.model_validate(raw)
    except (json.JSONDecodeError, ValueError) as error:
        raise PolicyLoadError(f"invalid policy document {policy_path}: {error}") from error
    if not document.allowed_handoffs:
        raise PolicyLoadError(f"{policy_path}: allowed_handoffs must not be empty")
    return document


def load_default_policy() -> PolicyDocument:
    """Load the committed v0.3 characterization policy."""
    return load_policy_document(DEFAULT_POLICY_PATH)


def policy_hash_of_path(path: Path | str) -> str:
    """Hash a policy file after validation."""
    return load_policy_document(path).policy_hash()


__all__ = [
    "DEFAULT_POLICY_PATH",
    "FORBID_RESEARCH_TO_WRITER_PATH",
    "PolicyDocument",
    "PolicyLoadError",
    "load_default_policy",
    "load_policy_document",
    "policy_hash_of_path",
]
