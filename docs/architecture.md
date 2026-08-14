# Architecture — bounded specialist coordination

Status: **P3-M0 LIVE; M1–M6 are target architecture.** The integrated repository exposes
only `GET /health` from a credential-free FastAPI scaffold. The agent protocol, specialists,
orchestrator, handoff budgets, timeline, evaluation set, and P2 integration described below
are not callable on `main` yet.

The system exists to answer one question: how can several specialists cooperate without
turning role prompts into an unbounded, unauditable conversation?

## Current runtime

```mermaid
flowchart LR
    C[Caller] --> H[GET /health]
    H --> O[{status: ok}]
```

That is the complete LIVE surface. The health response proves process availability, not
orchestration capability.

## Target topology

```mermaid
flowchart LR
    U[POST /v1/tasks\ntask + budget] --> O[Orchestrator\npolicy and accounting]
    O --> R[Research specialist\nevidence memo]
    R --> C[Critic specialist\naccept or reject]
    C -->|reject; retry budget left| R
    C -->|accept| W[Writer specialist\nsole final speaker]
    W --> X[TaskResult\nstatus + answer + timeline]
    R -. optional later .-> P2[P2 research API]
    O --> T[(append-only timeline)]
    R --> T
    C --> T
    W --> T
```

The orchestrator is policy, not a fourth content author. It validates messages, selects the
next recipient, decrements the global budget, records the transition, and decides which
terminal state is safe. Specialists exchange typed values rather than shared mutable state.

## Roles and authority

| Participant | Owns | Must not do |
| --- | --- | --- |
| Orchestrator | Routing, budgets, terminal policy, timeline | Invent research evidence or final prose |
| Research | Evidence memo and evidence references | Address the user or approve its own work |
| Critic | Accept/reject decision and actionable concerns | Write the final answer or retry without a bound |
| Writer | Final user-facing answer from accepted evidence | Research new facts or bypass Critic |

The proposed role boundary is recorded in [ADR-0001](adr/0001-specialist-roles.md). The
Writer-only output rule is separate because it is a security and provenance property, not
merely a division of labor ([ADR-0002](adr/0002-writer-only-final.md)).

## Target handoff contract

Every cross-agent message needs enough information to audit accountability and remaining
authority:

| Field | Purpose |
| --- | --- |
| `kind` | Discriminates handoff, final, failure, and timeline records. |
| `sender`, `recipient` | Closed-set identities; prevents accidental broadcast. |
| `task` | Immutable root work unit. |
| `content` | Bounded memo for the addressed specialist. |
| `context_refs` | Evidence pointers, not copied hidden state. |
| `attempt` | Research/critique retry number. |
| `budget` | Remaining handoffs and retry allowance. |
| `correlation_id` | Joins all events from one task without exposing content in logs. |

Models should reject unknown fields and invalid sender/recipient transitions. A future remote
specialist must implement the same contract as the deterministic fake; transport choice must
not change policy.

## Budgets and termination

Two independent bounds make the target workflow finite:

1. `max_handoffs` is global and decremented before every specialist invocation.
2. Critic rejection may return to Research at most twice.

The state, not a prompt, enforces both limits. A handoff that would overspend becomes a typed
terminal outcome. A specialist cannot reset its own allowance by returning a new message.

```text
research -> critic -> writer                         success
research -> critic -> research -> critic -> writer  accepted retry
research -> critic -> research -> critic -> research -> critic -> stop
                                                            retry limit
any route whose next edge exceeds max_handoffs -> stop      global limit
```

## Writer-only final output

Only a value authored by Writer may inhabit the final-answer variant. Enforce this with a
discriminated union whose final author is the literal `writer`, then validate the same rule
at the orchestrator boundary. Research and Critic return handoffs, never strings that the API
could accidentally expose as final prose.

This gives one auditable place for answer formatting, evidence-reference validation, and any
future redaction policy. It does not make Writer a fact source: accepted evidence remains the
only input it may summarize.

## Isolation and degraded mode

A specialist failure is data for the orchestrator, not an empty memo. The proposed policy is:

| Failure point | Safe result | Unsafe behavior |
| --- | --- | --- |
| Research fails before evidence | typed failure/refusal; no answer | Writer invents a substitute |
| Critic unavailable, evidence exists but is unapproved | `degraded` with no confident final, or a clearly labelled partial | silently treat missing review as acceptance |
| Writer fails after accepted evidence | `degraded` with evidence references and explanation, no fabricated prose | expose Critic memo as final answer |
| Optional P2 dependency unavailable | `degraded` only if a local evidence path produced usable evidence; otherwise typed dependency failure | silently claim P2 was used |
| Budget expires with partial evidence | `budget_exhausted` or `degraded`, preserving evidence and missing work | report success |

`degraded` means the workflow returned less than its intended contract and says exactly why.
It is not a synonym for exception suppression. The full decision is proposed in
[ADR-0003](adr/0003-degraded-mode.md).

## Timeline contract

M3 will add an append-only timeline. Each record should include sequence number,
correlation id, sender, recipient, event type, remaining budget, outcome, and a safe content
digest or bounded summary. No secrets, raw environment variables, hidden prompts, or provider
credentials belong in it.

The minimum event set is `task_started`, `handoff_requested`, `specialist_completed`,
`specialist_failed`, `budget_changed`, `final_written`, `degraded`, and `task_stopped`.
Sequence numbers, not wall-clock timestamps, establish deterministic order on the free path.

## Evaluation boundary

M4 will introduce offline golden tasks only after the orchestrator exists. Required slices:

- accepted first-pass research;
- Critic rejection followed by bounded re-research;
- Writer-only final enforcement;
- global handoff exhaustion;
- Research, Critic, and Writer failure isolation; and
- deterministic timeline replay.

Fake specialists may prove routing, accounting, isolation, and trace contracts. They cannot
prove answer quality, specialist diversity, or model collaboration gains. Any future claim
that multiple agents outperform one agent needs paired tasks, named providers, cost/step
accounting, and uncertainty.

## Optional P2 boundary

P3-M5 may let Research call P2 through an explicit URL. That integration is optional and
must fail closed when requested but unavailable. P3 consumes P2's typed result and trace
references; it does not copy P2's planner or P1's retrieval stack. The default CI path remains
local and credential-free.

## Milestones

| Milestone | Capability | State |
| --- | --- | --- |
| M0 | Package, FastAPI process, `GET /health`, offline test, empty-key CI | **LIVE** |
| M1 | Typed protocol and deterministic Research/Critic/Writer specialists | **PLANNED on `main`** |
| M2 | Orchestrator, transition policy, handoff/retry budgets | **PLANNED** |
| M3 | Deterministic multi-agent timeline | **PLANNED** |
| M4 | Offline golden tasks and behavioral scorecard | **PLANNED** |
| M5 | Optional P2 HTTP research boundary | **PLANNED** |
| M6 | Ship polish and v0.1.0 release | **PLANNED** |

The [SHIP page](SHIP.md) is the operational truth if code lands while this target design is
being implemented.
