# Architecture — bounded specialist coordination

Status: **P3-M5 LIVE; M6 public release pending.** Integrated `main`
contains immutable message/result models, deterministic Research/Critic/Writer specialists,
an in-memory bus, explicit transition policy, global handoff and Critic-retry budgets,
Writer-only final enforcement, typed degraded/budget-exhausted results, an ordered JSON-safe
timeline, `POST /v1/tasks`, a JSON CLI, trace UI, a 12-task offline scorecard, two
configuration-boundary cases, an optional P2 HTTP Research agent, request IDs, and a non-root
container. There is no hosted model default, remote-process isolation, or public release yet.

The system exists to answer one question: how can several specialists cooperate without
turning role prompts into an unbounded, unauditable conversation?

## Current runtime

```mermaid
flowchart LR
    C[Python / CLI / API / browser UI] --> O[run_task / Orchestrator]
    O --> R{Research selection}
    R --> F[FakeResearchAgent default]
    R -. explicit URL .-> P2[P2 research API]
    F --> K[FakeCriticAgent]
    P2 --> K
    K -->|bounded reject| R
    K -->|accept| W[FakeWriterAgent]
    W --> X[TaskResult]
    H[Health caller] --> G[GET /health]
```

All four task surfaces project the same `TaskResult`; `GET /health` proves process
availability and does not invoke the team.

## Runtime topology

```mermaid
flowchart LR
    U[POST /v1/tasks\ntask + budget] --> O[Orchestrator\npolicy and accounting]
    O --> R[Research specialist\nevidence memo]
    R --> C[Critic specialist\naccept or reject]
    C -->|reject; retry budget left| R
    C -->|accept| W[Writer specialist\nsole final speaker]
    W --> X[TaskResult\nstatus + answer + timeline]
    R -. opt-in HTTP .-> P2[P2 research API]
    O --> T[(append-only timeline)]
    R --> T
    C --> T
    W --> T
```

The current orchestrator is policy, not a fourth content author. It validates messages,
selects the next recipient, counts handoffs/retries, and decides the terminal status.
Specialists exchange typed values rather than shared mutable state. Each transition is
recorded before the result is projected through API or CLI.

## Roles and authority

| Participant | Owns | Must not do |
| --- | --- | --- |
| Orchestrator | Routing, budgets, terminal policy, timeline | Invent research evidence or final prose |
| Research | Evidence memo and evidence references | Address the user or approve its own work |
| Critic | Accept/reject decision and actionable concerns | Write the final answer or retry without a bound |
| Writer | Final user-facing answer from accepted evidence | Research new facts or bypass Critic |

The role boundary is recorded in [ADR-0001](adr/0001-specialist-roles.md). The
Writer-only output rule is separate because it is a security and provenance property, not
merely a division of labor ([ADR-0002](adr/0002-writer-only-final.md)).

## Handoff contract

The M1 contract is strict and immutable. Some fields needed for an external timeline remain
planned rather than being backfilled into a LIVE claim:

| Field | Purpose | State |
| --- | --- | --- |
| `kind` | Discriminates handoff from Writer final. | **LIVE** |
| `sender`, `recipient` | Closed-set identities; prevents accidental broadcast. | **LIVE** |
| `task` | Bounded root work unit carried across handoffs. | **LIVE** |
| `content` | Bounded memo for the addressed specialist. | **LIVE** |
| `attempt` | Research/critique retry number. | **LIVE** |
| `TaskBudget` | Global handoff and research-retry ceilings supplied to the run. | **LIVE** |
| `trace_context` | Small JSON-safe dependency pointer; never a copied nested trace. | **LIVE** |
| `X-Request-ID` | Correlates every HTTP response and rendered result. | **LIVE (transport)** |

Models reject unknown fields, and policy rejects invalid sender/recipient transitions. A remote
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

A specialist failure is data for the orchestrator, not an empty memo. Today the isolation
boundary catches a specialist/policy exception and returns `TaskStatus.DEGRADED` with the
active specialist, exception type, and explanation. Tests cover a crashing Critic and a
Research specialist attempting to impersonate Writer.

The fuller evidence-preserving target is:

| Failure point | Safe result | Unsafe behavior |
| --- | --- | --- |
| Research fails before evidence | typed failure/refusal; no answer | Writer invents a substitute |
| Critic unavailable, evidence exists but is unapproved | `degraded` with no confident final, or a clearly labelled partial | silently treat missing review as acceptance |
| Writer fails after accepted evidence | `degraded` with evidence references and explanation, no fabricated prose | expose Critic memo as final answer |
| Optional P2 dependency unavailable | `degraded` only if a local evidence path produced usable evidence; otherwise typed dependency failure | silently claim P2 was used |
| Budget expires with partial evidence | `budget_exhausted` or `degraded`, preserving evidence and missing work | report success |

`degraded` means the workflow returned less than its intended contract and says exactly why.
It is not a synonym for exception suppression. The decision is recorded in
[ADR-0003](adr/0003-degraded-mode.md).

The current `TaskResult` does not yet expose partial evidence as a separate field; only its
explanation and accounting survive. Do not claim evidence-preserving partial output until that
contract and its tests land.

## Timeline contract

M3 records an immutable ordered tuple of JSON-safe events. Each event has a contiguous
`sequence`, closed-set `event`, closed-set `actor`, and bounded JSON payload. The event set is
`task_started`, `handoff`, `agent_output`, `decision`, `specialist_error`, and `stop`.

The trace omits the full task text and credentials. It records the selected Research provider
and billed cost `0.0` at task start, every dispatch, routing/retry/stop decision, specialist
error type, and final accounting. HTTP Research adds only dependency name, host, P2 status,
steps used, and P2 request ID to its output event—not P2's raw trace. Sequence numbers, not
wall-clock timestamps, establish deterministic order. External log transport remains future.

## Evaluation boundary

M4 runs 12 committed tasks across `happy_path`, `critic_retry`, and `budget_stop`. Each case
declares exact status, ordered participants, handoffs, and retries. The scorecard reports pass
rate, mean handoffs, retry-task rate, Writer completion rate, and terminal-status counts, with
provider `fake` and billed cost `$0`. See the [dataset README](../data/eval/README.md).

The dataset does not inject crashing specialists, so degraded failure isolation remains a
unit-test claim rather than a golden-scorecard slice. Fake specialists prove routing,
accounting, ownership, budgets, and trace contracts. They cannot prove answer quality,
specialist diversity, or model collaboration gains. Any future claim that multiple agents
outperform one agent needs paired tasks, named providers, cost/step accounting, and
uncertainty.

The M5 boundary slice adds two configuration cases: fake selection remains local and an HTTP
selection without a URL produces `capability_missing`. Both report zero network calls. This
proves opt-in behavior only; it does not score P2 answer quality.

## Optional P2 boundary

P3-M5 lets Research call P2 through an explicit absolute URL. The factory always returns
`FakeResearchAgent` unless the caller selects `research="http"`; missing configuration is a
typed API 4xx. One bounded HTTP request posts the task to `/v1/research` with
`retriever="fake"` by default. Transport, timeout, status, JSON, or missing-report failures
raise `AgentError`, which the orchestrator turns into `degraded` without invoking Writer.
P3 maps the report and citations into its existing Critic handoff; it does not copy P2's
planner, raw trace, or P1's retrieval stack. See [ADR-0004](adr/0004-optional-p2-boundary.md).

## Milestones

| Milestone | Capability | State |
| --- | --- | --- |
| M0 | Package, FastAPI process, `GET /health`, offline test, empty-key CI | **LIVE** |
| M1 | Typed protocol and deterministic Research/Critic/Writer specialists | **LIVE** |
| M2 | Orchestrator, transition policy, handoff/retry budgets, Writer-only final, degraded result | **LIVE as a library** |
| M3 | Deterministic multi-agent timeline | **LIVE** |
| M4 | `POST /v1/tasks`, JSON CLI, 12 offline goldens and behavioral scorecard | **LIVE** |
| M5 | Optional P2 HTTP Research boundary | **LIVE (opt-in)** |
| M6 | UI, strict CI, container, docs, and v0.1.0 release | **PARTIAL — public tag/release pending** |

The [SHIP page](SHIP.md) is the operational truth if code lands while this target design is
being implemented.
