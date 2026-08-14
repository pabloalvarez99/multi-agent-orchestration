# ADR-0001: Use narrow specialists behind an orchestrator

- Status: Accepted
- Date: 2026-08-13

## Context

Calling the same general-purpose prompt three times creates names, not useful boundaries.
P3 needs role-specific authority that can be tested, budgeted, and isolated.

## Decision

Use four closed-set participants:

- Orchestrator owns routing, budget accounting, terminal policy, and the timeline.
- Research produces evidence memos and references.
- Critic accepts evidence or requests an actionable, bounded retry.
- Writer converts accepted evidence into the only user-facing final answer.

Specialists communicate only through immutable typed messages. They do not share mutable
memory, invoke one another directly, or take over the orchestrator's policy decisions.

## Consequences

- Each role has a small contract and independent fake implementation.
- Failure attribution and timeline events have an accountable sender/recipient.
- Adding another specialist requires a new authority boundary and transition, not just a
  prompt label.
- Some information must be summarized into handoffs; that cost is intentional isolation.

## Alternatives considered

- **One generalist with role prompts:** less code, but no isolation or enforceable authority.
- **Shared mutable blackboard:** convenient context sharing, but hidden coupling makes replay
  and failure attribution unreliable.
- **Peer-to-peer agents:** flexible, but routing and budgets become distributed and harder to
  audit.
