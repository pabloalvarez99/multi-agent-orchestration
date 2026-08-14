# ADR-0007: Policy as loadable data, not a second if-forest

- Status: Accepted
- Date: 2026-08-14

## Context

v0.3.0 already enforces Writer-only finals, an allowed handoff graph, and two budgets. Those
rules lived as Python constants and methods on `OrchestrationPolicy`. Behavior was correct and
tested, but a staff interviewer can still ask: **is the policy data, or is it if-statements?**

Shipping another wave of orchestration features without a versioned document leaves the product
story as “read the graph source.” Characterization tests alone do not give a stranger a file they
can open, hash, and pack with a trace.

## Decision

1. Commit a **default policy JSON** (`policies/default-v0.3-characterization.json`) whose
   allowed edges and budget defaults equal the v0.3.0 hard-coded behavior.
2. Load that document at orchestrator construction; `OrchestrationPolicy` validates handoffs and
   finals against the **loaded edge set**, not a parallel hard-coded graph that can drift.
3. Keep pure methods (`validate_handoff`, `next_retry_count`, `validate_final`) — the algorithm
   stays code; the **configuration** is data.
4. Ship fixture policies (for example `forbid-research-to-writer`) that change reachable edges and
   must change observed terminals under the same specialists.
5. Embed `policy_id` and `policy_hash` on `task_started` events and in season trace packs.

## Consequences

- Characterization tests bind the default file to today’s fixtures; silent policy edits fail CI.
- Demo and pack surfaces can show a human-readable graph without opening `graph.py`.
- New routing behavior requires a new `policy_id` (or an explicit ADR), not a stealth constant edit.
- Callers can still inject `OrchestrationPolicy(document=...)` in tests without HTTP policy APIs.

## Alternatives considered

| Option | Why not |
| --- | --- |
| Keep only Python constants | Correct but loses the hiring product: policy is still “read the code.” |
| Remote policy service / feature flags | Secrets, network, multi-tenant scope — out of free-path season. |
| Encode the whole loop in YAML | Turns YAML into a programming language; validation and debugging get worse. |
| Generate policy from tests only | Tests are not an operator-facing document a lawyer can unzip with a pack. |

## Relationship to prior ADRs

- ADR-0002 (Writer-only) and ADR-0003 (degraded) remain normative; the document **represents** them.
- ADR-0006 (file replay) remains durability; policy data rides inside packs, not a server store.
