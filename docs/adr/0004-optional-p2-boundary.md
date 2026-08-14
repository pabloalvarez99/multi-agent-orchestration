# ADR-0004: Keep P2 Research optional and fail closed

- Status: Accepted
- Date: 2026-08-14

## Context

P3 demonstrates coordination policy; P2 owns bounded retrieval research. Copying P2 into P3
would blur ownership, while requiring it would break the repository's credential-free,
offline default. A remote dependency can also timeout, reject a request, or return data that
does not satisfy the published contract.

## Decision

Keep `FakeResearchAgent` as the unconditional default. Construct the HTTP Research specialist
only when a caller explicitly selects `research="http"` and `AGENTIC_RAG_URL` is a non-empty
absolute HTTP(S) URL. The specialist makes one bounded, no-retry `POST /v1/research` and asks
P2 to use its fake retriever unless a programmatic caller explicitly selects otherwise.

Map only P2's report and citation pointers into the existing Critic handoff. Record a compact
dependency pointer—host, terminal status, steps used, and request ID—in P3's trace; never copy
P2's raw prompt or full nested trace. Missing configuration is a stable typed 4xx. Transport,
timeout, HTTP-status, JSON, and missing-report failures raise `AgentError`; the orchestrator
terminates `degraded` and does not invent a Writer answer.

## Consequences

- Cloning, testing, evaluating, and using the default API remains offline and billed at `$0`.
- P2 can evolve behind its public contract without sharing implementation with P3.
- Optional availability does not weaken Writer ownership or orchestration budgets.
- HTTP integration tests establish boundary behavior, not improved answer quality.
- There is no automatic fallback from requested HTTP Research to fake Research; such a
  fallback would conceal which evidence path actually ran.

## Alternatives considered

- **Require P2 for every task:** closer to a distributed demo, but destroys the standalone
  free path and makes CI depend on another process.
- **Copy P2's loop into P3:** avoids a network boundary but duplicates ownership and couples
  two portfolio projects internally.
- **Silently fall back to fake:** appears more available but misrepresents the selected
  evidence source.
- **Retry HTTP failures:** may amplify dependency load and creates work outside P3's handoff
  budget; v0.1.0 performs one bounded call instead.
