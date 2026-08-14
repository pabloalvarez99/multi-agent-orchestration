# Case study — policy before personality

**Multi-Agent Orchestration (P3)** coordinates deterministic Research, Critic, and Writer
specialists under typed handoffs, two hard budgets, explicit failure states, and an ordered
trace. The free path is intentionally simple: it demonstrates who may do what, how execution
stops, and what a caller can audit. It does not claim that three fake specialists produce a
better answer than one model.

![A bounded Research–Critic retry shown in the ordered trace](assets/ui-trace.png)

*Deterministic fake specialists. Not a quality claim. The capture fixes the displayed request
ID so reruns are byte-comparable; runtime responses still receive unique request IDs.*

## Problem

Many “multi-agent” demos are an unbounded group chat. Role prompts describe responsibilities,
but nothing prevents a researcher from answering the user, a critic from retrying forever,
or a failed specialist from becoming an empty success. That makes the system hard to operate
and harder to trust: the interesting behavior exists only in prompt text and terminal logs.

P3 treats coordination as a small policy engine instead. Specialists exchange immutable
messages over an in-memory bus. The orchestrator validates each edge, owns counters and
terminal status, and appends JSON-safe events without copying the full task into the trace.
The result is reproducible for CI and inspectable in the browser console.

The public free path now runs at <https://pax-orchestration.vercel.app>. Its serverless
process retains only the last 128 runs, so a recycle or another instance can make a replay
lookup return `404`. That is exposed as a boundary, not disguised as persistence.

## Decision 1 — only Writer may produce a final answer

**Options considered:** allow any specialist to return text; let the orchestrator compose a
final answer; or reserve a discriminated `FinalAnswer` value for Writer.

Allowing any role to finish is flexible, but destroys provenance: research evidence, critic
feedback, and user-facing prose become indistinguishable. Letting the orchestrator write would
turn the policy layer into a hidden fourth specialist. P3 therefore makes `writer` the literal
author of `FinalAnswer` and validates that rule again at dispatch. Research and Critic can only
return handoffs. An impersonation attempt terminates `degraded`; an intermediate memo is never
promoted to final prose. See [ADR-0001](adr/0001-specialist-roles.md) and
[ADR-0002](adr/0002-writer-only-final.md).

## Decision 2 — handoff budget and retry budget are different controls

**Options considered:** one generic step counter; only a Critic retry limit; or independent
global handoff and Research-retry ceilings.

A retry ceiling prevents the obvious Critic–Research loop, but does not bound an unexpected
route elsewhere. A single generic counter bounds cost but cannot express the policy “Critic may
request at most two additional Research passes.” P3 keeps both: `max_handoffs` limits every
specialist dispatch, while `max_research_retries` limits that specific feedback loop to two.
The orchestrator owns both counters; no message can reset them. Whichever limit is reached
first produces `budget_exhausted` with the accounting and stop reason preserved in the trace.

This separation also makes review easier. A hiring manager can lower `max_handoffs` to one and
see a six-event budget stop, or run “Audit retrieval risk” and see one bounded re-research pass
inside a five-handoff, 17-event completion.

## Decision 3 — degraded is not an empty success

**Options considered:** let exceptions escape; catch failures and return an empty answer; or
return a typed degraded result that identifies the active boundary and stops the graph.

Crashing the whole HTTP request is explicit but discards orchestration accounting. Returning
an empty successful answer is worse: a caller cannot distinguish “no evidence” from “the
Critic never ran.” P3 catches specialist and policy failures at the orchestrator boundary,
records `specialist_error` plus a terminal decision, and returns `status="degraded"` with an
explanation. Writer is not invoked after an upstream failure, so availability never outranks
the Writer-only and review invariants. [ADR-0003](adr/0003-degraded-mode.md) records the trade-off.

## Decision 4 — optional P2 Research fails closed

**Options considered:** require P2 for every task; silently fall back to fake Research; copy
P2's loop into this repository; or put P2 behind an explicit HTTP capability.

The default factory always returns `FakeResearchAgent`, even if a URL happens to exist in the
environment. A caller must select `research="http"` and configure an absolute
`AGENTIC_RAG_URL`. Selecting HTTP without it returns a stable `409 capability_missing` with a
request ID; it is a client configuration error, not a server crash. Once configured, P3 makes
one bounded request to P2 and asks for P2's fake retriever by default. Timeout, transport,
non-success status, invalid JSON, or a missing report raises `AgentError`, which becomes a
degraded orchestration result without Writer.

P3 maps only P2's report and citation pointers into the existing Critic handoff. Its trace
stores a compact dependency pointer—not P2's raw task or nested trace. This preserves project
ownership (`P3 → P2`) and prevents a silent fake fallback from misrepresenting which evidence
path ran. See [ADR-0004](adr/0004-optional-p2-boundary.md).

## Decision 5 — replay time is logical, storage is bounded

**Options considered:** wall-clock timestamps in every event; sequence numbers only; or a
versioned envelope with logical offsets and a process-local retention window.

Wall time makes identical fake runs differ for reasons unrelated to policy. Sequence alone is
deterministic but leaves no explicit replay clock or schema evolution point. Trace schema 1
therefore records `ts_offset_ms` as a logical offset from run start and keeps operational
latency in a separate debug field. Same task + seed yields an exactly equal event sequence.

`GET /v1/runs/{id}` and `/trace` retain the last 128 completed runs in a locked FIFO. The
record stores a task fingerprint, terminal output, accounting, ownership, and typed stop;
the versioned endpoint stores events. There is intentionally no disk, replication, retention
SLA, or cross-instance lookup. [ADR-0005](adr/0005-versioned-process-local-traces.md) makes the
trade-off explicit.

## Isolation as a product contract

The free scorecard grows from four chaos cases in v0.3 to **n ≥ 40** in v1.0, each tagged with
a family and an **easy / medium / hard** difficulty. A crashing Critic still returns a non-empty
`degraded` result with `specialist_error`; two consecutive Critic rejections consume both
allowed retries and still reach Writer on handoff seven; a narrow global budget stops with
typed `max_handoffs`; and a Research attempt to return `FinalAnswer` stops as
`policy_violation`. Harder rows add concurrent token isolation, restrictive policy fixtures,
writer crashes after Critic accept, and accounting fields that must match—not just a status
string. Mechanical predicates fail CI when new rows are all easy or when medium/hard slices
collapse into status-only clones. These cases test authority and availability semantics, not
prose quality.

Successful answers are always `result_author="writer"`. Degraded and exhausted outcomes are
system explanations with `result_author=null`, so the UI does not label an orchestrator error
or an intermediate memo as Writer output.

## Decision 6 — policy as data (season product)

**Options considered:** keep handoff rules as private Python constants forever; invent a remote
policy service; encode the entire loop in YAML; or load a versioned document the orchestrator
actually consults.

v0.3 already had the right invariants, but a staff engineer could still ask whether the product
was policy or “if-statements with a nice README.” v1.0 commits
`policies/default-v0.3-characterization.json`, loads it into `OrchestrationPolicy`, and keeps
pure validation methods as the algorithm. Characterization tests bind the file to today’s happy
path, budget stop, and Writer-only rules. A second fixture, `forbid-research-to-writer`, removes
the Critic→Writer edge (and still forbids Research→Writer); the same specialists that complete
under the default policy terminate `degraded` / `policy_violation` under the fixture. That is the
proof that **loading different data changes behavior**, not that we renamed a constant.

Every `task_started` event now carries `policy_id` and `policy_hash`. The read-only
`/ui/policy` page shows the graph and hash without requiring a code tour. ADR-0007 records why
we rejected a multi-tenant policy SaaS and why we refused to turn YAML into a programming
language.

## Decision 7 — measure isolation, not vibes

Unit tests that run two threads are necessary but not sufficient as a portfolio claim. The
season ships a **1000-task** deterministic simulation (`seed=20260814`) that reports
`swap_rate`, `writer_only_violations`, `degraded_rate`, and `budget_exhausted_rate`. The pass
gates for release are **`swap_rate=0`** and **`writer_only_violations=0`**. The HTML/JSON
artifacts are labeled **isolation/plumbing — not multi-agent quality**. If those numbers are
cited as “agents coordinate well,” the citation is wrong by construction.

Separately, a load probe records p50/p95 for `POST /v1/tasks` on the fake path. The honesty
line is mandatory: **single isolate / single process**, not multi-region capacity planning.
Cold-start is reported as the first sample, not hidden.

## Decision 8 — a pack a third party can unzip

File replay (ADR-0006) already survived recycle for a single schema-1 export. The season pack
adds **policy identity** and a verify path a lawyer or hiring manager can run offline:

- `manifest.json` with `policy_hash`, `seed`, `pack_hash`
- `policy.json` (the document, not a screenshot)
- `task.json`, `result.json`, `trace.json`
- optional zip layout under `docs/assets/sample-trace-pack.zip`

`python -m mao.pack verify` checks policy hash integrity and Writer-only ownership offline.
`python -m mao.replay` still validates the schema-1 member. The browser loader accepts a pack
JSON by reading `pack.trace` without uploading bytes to the server. Round-trip tests re-run the
task under the embedded policy and require matching terminals.

## Evidence and limits

- `pytest` covers Writer ownership, retry and global budgets, specialist crashes, P2 success,
  HTTP error, timeout, missing capability, UI states, policy loading, pack verify, isolation
  simulation gates, and capture integrity without paid APIs.
- Twelve routing goldens, two boundary cases, and **≥40 chaos goldens** run with
  `network_calls=0` and `billed_usd=0.0`.
- CI runs Ruff, strict mypy, pytest, and routing/boundary/chaos evals with provider
  configuration empty; `AGENTIC_RAG_URL` remains unset in CI.
- Isolation sim artifact: `docs/assets/isolation-sim.json` + HTML; load artifact:
  `docs/assets/load.json`.
- The UI capture script starts the real app on localhost and submits the same fake form a
  reviewer uses; it also captures `/ui/policy`. It normalizes only the displayed request ID and
  records PNG SHA-256 values in `docs/assets/ui-captures.sha256`.
- Live P2 availability is opt-in and fail-closed. Remote multi-instance storage, Redis, real
  LLM specialists as default, and any claim that fake specialists produce quality answers remain
  **PLANNED / out of free path**. File and pack replay are client-side durability, not a
  database.

## What we still refuse to claim

We do not claim multi-agent answer quality, faithfulness, or model uplift from template fakes.
We do not claim that a single Vercel isolate’s p50/p95 is a production SLA. We do not claim that
process-local FIFO retention is multi-tenant audit storage. We do not invent Redis “for the
demo.” Those refusals are part of the product: honesty is a feature when the alternative is a
slide that does not survive `curl` after recycle.

## Interview version

I built P3 as a policy engine whose claims can be replayed. Research, Critic, and Writer cross
typed message boundaries, while the orchestrator alone owns routing, a global handoff budget,
and the two-retry Critic loop. Successful text is always Writer-authored; system stops carry a
separate typed reason and never promote an intermediate memo. Schema-1 traces use logical
offsets, so same task + seed is exactly comparable, and the last 128 runs are inspectable with
an explicit serverless-retention caveat. Policy is a versioned JSON document with a hash in
every run; chaos n≥40 and a 1000-task simulation prove isolation plumbing (`swap_rate=0`); a
trace pack unzips policy, task, seed, trace, and result for offline verify after the process is
gone. That is an auditability and isolation story, not a claim about model quality.
