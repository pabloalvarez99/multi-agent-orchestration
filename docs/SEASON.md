# Season plan — multi-agent-orchestration toward v1.0

**Status:** Month 1 · Week 1 design only (this file)  
**Baseline:** `main@8feb31a` · release **v0.3.0** (Latest; also **v0.2.0**) · hosted **https://pax-orchestration.vercel.app** (Vercel project **`pax-orchestration` only** — never `pax-mao`)  
**Branch / worktree:** `a1/p3-v1-season` · `C:\dev\portfolio-workers\a1-p3-v1-season`  
**Horizon:** ~90 days · three months · **`REPORTE … OK` is illegal before the Month 3 gate**  
**Authority:** portfolio master plan §8 (P3), §12 (eval doctrine), §33 (failure taxonomy), §37 (demo day); dispatch `2026-08-14-v1-season`

This document is the lab ledger for the quarter. It freezes the threat model, fifteen invariants, policy-as-data shape, chaos taxonomy, simulation contract, pack contract, load honesty, and the v1.0 checklist. **Week 1 ships only this design.** Weeks 2–4 implement Month 1 surfaces; Months 2–3 follow only after the prior month’s quantitative doors close.

If you would ship **v1.0.0 tonight**, you misunderstood the assignment. v0.3.0 is a **demo** of bounded orchestration + file replay. The season product is **policy**: handoff rules as loadable data, chaos with difficulty slices, a 1000-task isolation simulation, and a trace pack a lawyer can unzip.

---

## 1. Mission for the quarter

v0.3.0 already proves:

- Fake Research → Critic → Writer under `max_handoffs` and `max_research_retries`
- Writer-only final (type + policy)
- Typed `degraded` / `budget_exhausted` / `done` with closed-set stop reasons
- Schema-1 process-local traces + **client-side file replay** (not KV) after recycle
- 12 golden tasks + 4 chaos + 2 P2-boundary cases (18-case free scorecard)
- Concurrent isolation smoke (two threads do not swap Writer text/traces)
- Hosted free path on **pax-orchestration.vercel.app** · health `{"status":"ok"}`

A staff interviewer will still ask:

1. **Is the policy data, or is it if-statements?**
2. After the serverless recycle, what is still true — and can a stranger re-prove it offline?
3. When specialists crash or impersonate, is isolation a **measured** property or a unit-test anecdote?
4. Can failure stories scale past four hand-picked chaos rows?

**Season answer:** make **policy the product**. Encode handoff rules, budgets, and authority in a versioned YAML/JSON document the orchestrator **loads**; grow chaos to **n ≥ 40** with mechanical **easy/medium/hard** predicates; run a **1000-task** deterministic simulation whose metrics are **isolation/plumbing** (swap rate, writer-only violations), not “agents are good”; ship a **trace pack** (policy hash + task + seed + trace + result) that round-trips through file-replay UI and tests. Fake specialists stay fake. No Redis. No real LLM specialists. No durable multi-instance server store.

---

## 2. What is already LIVE (do not regress)

| Surface | Evidence on baseline `8feb31a` |
| --- | --- |
| Fake-first free path | Default bus; CI empty keys; `provider="fake"`, `billed_usd=0.0` |
| Writer-only final | ADR-0002; type system + `OrchestrationPolicy.validate_final` |
| Degraded ≠ silent success | ADR-0003; crash / policy_violation goldens |
| Allowed handoff graph + retry cap | `ALLOWED_HANDOFFS` + `max_research_retries` (default 2) in code |
| Global `max_handoffs` | `TaskBudget.max_handoffs` (default 8); budget_stop goldens |
| Schema-1 process-local runs | ADR-0005; FIFO 128; typed 404 after eviction |
| Client-side file replay | ADR-0006; UI “Load trace JSON”; `python -m mao.replay`; recycle story honest |
| Chaos | `data/eval/chaos.jsonl` **n = 4** (crash, reject×2, max_handoffs, impersonation) |
| Task goldens | `tasks.jsonl` **n = 12** (happy / critic_retry / budget_stop) |
| Concurrent isolation | `tests/test_concurrency.py` (2 workers) |
| Hosted | **https://pax-orchestration.vercel.app** only; not `pax-mao` |
| Optional P2 research | `AGENTIC_RAG_URL` opt-in; fail-closed `capability_missing`; CI unset |

**Durability honesty (keep forever):** durability = **downloaded schema-1 file** (+ season pack). In-memory run ids die with the isolate. Do not invent KV/Postgres/Redis to “fix” recycle demos.

---

## 3. Threat model (coordination policy lab, not multi-agent quality)

| Threat | Failure mode | Season control |
| --- | --- | --- |
| T1 Policy-as-code only | Staff: “just if-statements”; config drift vs tests | Policy document + characterization tests (I11); ADR Month 1 |
| T2 Writer impersonation | Research/Critic user-facing text | Writer-only final (I1); chaos `writer_impersonation` family |
| T3 Unbounded handoffs | Hang / CI timeout / bill fiction | `max_handoffs` (I2); budget chaos slices |
| T4 Silent specialist death | Empty success / blank answer | `degraded` with typed stop + non-empty explanation (I3) |
| T5 Id-as-durability | 404 after recycle ends the story | File replay + pack (I4, I14) |
| T6 Isolation cosplay | One happy concurrent test | 1000-task sim + swap_rate / writer_only metrics (I12–I13) |
| T7 Chaos theater | n=4 all easy; no difficulty gate | n≥40 + easy/medium/hard predicates (I12) |
| T8 Quality claim from fakes | “Agents coordinate well” | Metrics labeled isolation/plumbing (I13); CASESTUDY honesty |
| T9 Real-LLM / multi-tenant scope creep | Keys, Redis, durable audit SaaS | Explicit non-goals + PLANNED list (I15) |
| T10 Wrong host | Demo on dead `pax-mao` or wrong project | Host table fixed to `pax-orchestration` (I15) |

---

## 4. Fifteen invariants

Each invariant is **normative**. Column **Test now** = enforced on baseline `8feb31a`. **Season** = month when remaining proof lands if not already green.

| # | Invariant | Test now | Season proof |
| ---: | --- | --- | --- |
| **I1** | **Writer-only final.** `status=done` requires `result_author=writer` and a final produced by Writer after Critic accept. Research/Critic cannot own successful user text. | Yes (types + policy + chaos impersonation) | Month 1 characterization against default policy doc; chaos family expands |
| **I2** | **Global `max_handoffs`.** Dispatches never exceed budget; terminal is `budget_exhausted` + `stop_reason=max_handoffs` when the ceiling binds before Writer. | Yes | Policy field + goldens; sim reports `budget_exhausted_rate` |
| **I3** | **`degraded` ≠ empty success.** Specialist crash or policy violation → `status=degraded`, closed-set stop reason (`specialist_error` / `policy_violation`), **non-empty** system explanation, `result_author=null`. Never silent empty `done`. | Yes | Month 1–2 chaos hard slice; sim `degraded_rate` |
| **I4** | **File-replay after recycle.** After process recycle, run ids may 404; a downloaded schema-1 file remains the truth via UI load and `python -m mao.replay` (exit 0 valid / 2 invalid). No server upload required. | Yes (ADR-0006 + tests) | Month 1 digest transcripts; Month 3 pack import on same UI |
| **I5** | **Critic → Research retries** are independently capped (`max_research_retries`, default 2). Exhaust without accept → typed stop (`retry_limit`), not infinite loop. | Yes | Policy doc field; chaos reject-until-cap family |
| **I6** | **Allowed handoff graph only.** Edges outside `{O→R, R→C, C→R, C→W}` are `policy_violation` (or hard PolicyError turned into typed terminal). | Yes (`ALLOWED_HANDOFFS`) | Graph listed in policy data; loader rejects unknown edges |
| **I7** | **Closed-set terminals.** Status ∈ `{done, degraded, budget_exhausted}`; stop_reason ∈ `{writer_final, max_handoffs, retry_limit, specialist_error, policy_violation}` (extensions only via ADR + schema together). | Yes | Season docs + pack schema freeze |
| **I8** | **Fake specialists default.** Free path never requires OpenAI or live P2; scorecard `billed_usd=0.0` / provider fake. | Yes | Entire season CI |
| **I9** | **Optional P2 is fail-closed.** Unset/wrong `AGENTIC_RAG_URL` → `capability_missing` (or skip live slice), never invent research. CI leaves URL **unset**. | Yes (boundary goldens) | Month 2 smoke optional only |
| **I10** | **Process-local retention is FIFO, not durable storage.** Bounded in-memory runs (128); multi-instance lookup is **PLANNED**, never claimed LIVE. | Yes (ADR-0005/0006) | Keep honesty in SHIP/CASESTUDY |
| **I11** | **Policy is loadable data.** Orchestrator loads a committed YAML/JSON policy; default document equals today’s hard-coded behavior (characterization tests). Runtime routing reads the document, not a second parallel if-forest. | No (code constants only) | **Month 1 weeks 2–4** + ADR |
| **I12** | **Chaos n ≥ 40** with **easy / medium / hard** difficulty predicates enforced in CI. Labels alone are insufficient. | No (n=4) | Month 1 first **15** + predicates; Month 2 **≥40** |
| **I13** | **Isolation simulation** (n=1000, fixed seed) measures plumbing: `swap_rate=0`, `writer_only_violations=0`, plus `degraded_rate` / `budget_exhausted_rate`. Publish JSON+HTML. Caption: **isolation/plumbing, not agent quality**. | Partial (n=2 concurrent) | **Month 2** |
| **I14** | **Trace pack** carries policy hash, task, seed, schema-1 trace, result; import on file-replay UI; round-trip tests. A third party can unzip without the warm process. | No | **Month 3** |
| **I15** | **Host and scope honesty.** Production demo host is only `https://pax-orchestration.vercel.app` / project `pax-orchestration`. No `pax-mao`. No Redis. No real LLM specialists as default. No multi-tenant durable server store this season. | Process + docs | SHIP / DEMO-DAY / release notes PLANNED list |

### Explicit non-invariants (do not “prove” these)

- Multi-agent **answer quality**, factuality, or model uplift (fakes are control surfaces).
- Multi-instance durable audit storage, Redis, object stores of every run.
- Real LLM specialists or live web tools as the free path.
- Capacity planning from a single Vercel isolate load test.
- That “policy as data” implies a multi-tenant policy SaaS.

---

## 5. Chaos taxonomy and eval plan (n ≥ 40)

### 5.1 Doctrine (master plan §12)

| Tier | Season role |
| --- | --- |
| **0 Ops** | status counts, stop_reason distribution, degraded/budget rates, swap rate |
| **1 Control / isolation** | free CI every PR: handoff success, writer-only, chaos contracts, policy characterization |
| **2 Quality judge** | **out of scope** for free CI; never block clone |

Tier-1 never requires paid APIs. Metrics label **control / isolation**, not quality.

### 5.2 Baseline inventory (do not re-litigate)

| Artifact | n | Role |
| --- | ---: | --- |
| `data/eval/tasks.jsonl` | 12 | Happy / retry / budget routing contracts |
| `data/eval/chaos.jsonl` | 4 | Crash, reject×2, max_handoffs, impersonation |
| `data/eval/research_boundaries.jsonl` | 2 | P2 config-only, zero network |
| Concurrent test | 2 threads | Minimal isolation smoke |

Total free scorecard rows today ≈ **18**. Season target for **chaos** is **n ≥ 40** (task goldens may grow separately; chaos is the isolation product surface).

### 5.3 Chaos scenario taxonomy

Every chaos row belongs to exactly one **family**. Families map to master-plan §8 rules and §33-style typed stops.

| Family id | Intent | Typical expected status / stop |
| --- | --- | --- |
| `specialist_crash` | Research/Critic/Writer raises mid-handle | `degraded` / `specialist_error` |
| `writer_impersonation` | Non-Writer returns `FinalAnswer` | `degraded` / `policy_violation` |
| `illegal_handoff` | Edge outside allowed graph | `degraded` / `policy_violation` |
| `critic_reject_loop` | Bounded rejects then accept, or reject until retry cap | `done` / `writer_final` **or** `budget_exhausted`/`degraded` + `retry_limit` |
| `max_handoffs` | Global ceiling binds before Writer | `budget_exhausted` / `max_handoffs` |
| `writer_crash_after_accept` | Writer fails after Critic accept | `degraded` / `specialist_error` (no memo promotion) |
| `concurrent_isolation` | Paired tasks with unique tokens under interleaving | both `done`; no cross-token in result/trace |
| `policy_budget_matrix` | Same task under policy variants (handoffs/retries) | divergent terminals per matrix cell |
| `replay_integrity` | Export → clear memory → load file / pack | event sequence equality (offline) |

Existing four rows seed the first four families. Season work **extends families**; it does not delete baseline ids.

### 5.4 Difficulty slices (easy / medium / hard)

Difficulty is a **mechanical predicate**, not author opinion. CI fails a slice that collapses to trivial cases.

| Difficulty | Definition (predicate inputs) | Fails when |
| --- | --- | --- |
| **easy** | Single fault inject; default policy; one expected terminal field match (status + stop_reason) | Slice empty |
| **medium** | Fault **plus** budget stress **or** ≥2 accounting fields checked (handoffs_used, retries, writer_finished, agents order) **or** paired expect matrix | ≥80% of medium cases check only status with `max_handoffs≥8` and no fault composition |
| **hard** | Multi-fault, concurrent pair, policy variant switch mid-suite, or replay round-trip after forced retention clear | ≥50% of hard cases are single-fault copy-pastes of easy |

**Month 1 weeks 2–4:** ship **≥15 chaos goldens** covering all baseline families + first medium/hard rows, with predicates implemented as tests.  
**Month 2:** grow to **n ≥ 40**; every difficulty bucket has minimum share (proposed: easy ≥30%, medium ≥40%, hard ≥20% of chaos set). Loader rejects missing families or duplicate ids.

### 5.5 What we do **not** measure in chaos

- Semantic quality of Writer text under fake templates.
- Latency SLAs (load is a separate Month 2 artifact).
- Live P2 research quality when URL unset (skipped).
- “Three agents beat one prompt” without a separate study (out of season).

### 5.6 Runner

Keep `python -m mao.evals.run` as free harness. Extend dataset schema only as needed for `difficulty`, `family`, and policy-id fields. Publish pass_rate, status_counts, stop_reason_counts, writer_finished rate. Label: **control / isolation scorecard, fake specialists, not multi-agent quality**.

---

## 6. Policy as data (Month 1 product surface)

### 6.1 Staff question

Today `OrchestrationPolicy` and `ALLOWED_HANDOFFS` are **Python constants**. Behavior is correct and tested, but the product story is still “read the graph code.” Season moves the **default committed policy document** into `policies/` (or `data/policy/`) so a reviewer can open YAML/JSON without opening the loop.

### 6.2 Default policy document (equals v0.3.0 behavior)

Normative fields (names may snake_case in file; semantics frozen):

```yaml
policy_version: "1.0"
policy_id: "default-v0.3-characterization"
allowed_handoffs:
  - [orchestrator, research]
  - [research, critic]
  - [critic, research]
  - [critic, writer]
budgets:
  max_handoffs: 8
  max_research_retries: 2
authority:
  final_author: writer
  non_done_result_author: null
terminals:
  statuses: [done, degraded, budget_exhausted]
  stop_reasons:
    - writer_final
    - max_handoffs
    - retry_limit
    - specialist_error
    - policy_violation
degraded:
  require_non_empty_explanation: true
  never_promote_intermediate_memo: true
providers:
  default_research: fake
  optional_http_p2: fail_closed
```

**Characterization rule:** loading this document + running the existing unit/golden suite must match baseline `8feb31a` outcomes bit-for-bit on free path (same status, stop_reason, handoffs, retries, event names where already asserted). Any intentional behavior change requires a **new policy_id** and tests — not a silent edit of `default-v0.3-characterization`.

### 6.3 ADR (Month 1 weeks 2–4)

New ADR (proposed **ADR-0007: policy document as orchestration product**):

- Decision: orchestrator constructs `OrchestrationPolicy` (or successor) from loaded document; defaults committed equal today’s behavior.
- Rejected: keep only code constants; invent remote policy service; store policies in Vercel KV.

### 6.4 Implementation order (not Week 1)

1. Commit default policy file + pure loader + hash helper (`policy_hash`).
2. Wire orchestrator to loader; keep public API stable.
3. Characterization tests = existing goldens + explicit “default policy equals baseline” suite.
4. Chaos rows may reference `policy_id` when testing variants (Month 2 matrix).
5. Month 2: Policy UI read-only view + generated capture.
6. Month 3: pack embeds policy file + hash.

---

## 7. Month plan

### Month 1 — Policy as data (Week 1 design → loadable policy + first 15 chaos)

| Week | Deliverable | Stop condition |
| --- | --- | --- |
| **1** | **`docs/SEASON.md` only** (this file). Commit. **No Month 2 implementation in that commit.** | Design committed |
| **2** | Default policy YAML/JSON + loader + ADR-0007 draft; characterization tests green | Policy hash stable; suite matches baseline |
| **3** | First **15 chaos goldens** with difficulty field + predicates; keep existing 4 ids | Chaos suite green; predicates fail if slice trivialized |
| **4** | Digest path: `POST /v1/tasks` → download schema-1 → `python -m mao.replay` transcript archived (vault cli-log pointer or `docs/assets/`); finish Month 1 door | Month 1 exit checklist |

**Month 1 exit criteria (not season OK):**

- [ ] SEASON.md on branch with 15 invariants
- [ ] Policy document LIVE + characterization tests
- [ ] ADR-0007 accepted (or equivalent number)
- [ ] Chaos **n ≥ 15** with easy/medium/hard tags + difficulty predicates
- [ ] Replay digest: POST + download + `python -m mao.replay` documented
- [ ] Host still file-replay honesty (no KV)
- [ ] Digest append for the month

### Month 2 — Simulation, not vibes

1. **1000 fake tasks**, deterministic seed. Metrics (must publish JSON + HTML):
   - `swap_rate` → **0** (no cross-task result/trace token leakage under concurrent workers as configured)
   - `writer_only_violations` → **0**
   - `degraded_rate`, `budget_exhausted_rate` (observed rates under the scenario mix; not forced to zero)
   - Label artifact: **isolation/plumbing**, never “agents are good”
2. **Chaos n ≥ 40** with easy/medium/hard predicates tested in CI.
3. **Policy UI** (read-only default policy + hash) + generated capture (Playwright, SHA-256 manifest).
4. **Optional P2** specialist path remains fail-closed; **CI leaves URL unset**.
5. **Load/soak:** p50/p95 of `POST /v1/tasks` fake path, report **n**, cold-start note. Honesty line: **single isolate**, not multi-region capacity.

**Month 2 exit criteria:**

- [ ] Simulation artifact committed or generated in CI artifact path
- [ ] Chaos n≥40 green with difficulty gates
- [ ] Policy UI + capture
- [ ] Load numbers published with honesty caption
- [ ] Digest append

### Month 3 — Pack + v1.0

1. **Trace pack** (see §9): policy hash, task, seed, trace, result; import on file-replay UI; round-trip tests.
2. **CASESTUDY ≥ 1500 words** (expand existing): policy-as-data vs if-statements, isolation metrics, file-replay vs KV, what remains PLANNED.
3. **DEMO-DAY ~25 min:** policy → chaos → pack → recycle story → replay (see §10).
4. **`gh release create v1.0.0` only if season checklist green.** Release notes list **PLANNED** (no Redis, no real LLM specialists, no multi-instance durable store). Do not retag v0.3.0 as v1.0.0.

**Month 3 / season OK gate:** full checklist in §11.

---

## 8. Isolation simulation contract (design; implement Month 2)

### 8.1 Goal

Prove **plumbing isolation** at n=1000 with a fixed seed — not quality, not SOTA coordination.

### 8.2 Inputs

| Field | Rule |
| --- | --- |
| `n` | 1000 |
| `seed` | fixed integer in script/docs (e.g. `20260814`) |
| `tasks` | deterministic generator: unique token per task, optional chaos inject mix |
| `concurrency` | documented worker count (thread pool or sequential+interleave); same as measurement |
| `research` | always `fake` on free path |

### 8.3 Metrics (required)

| Metric | Pass gate |
| --- | --- |
| `swap_rate` | **= 0** (fraction of tasks whose result/trace contains another task’s unique token) |
| `writer_only_violations` | **= 0** (`done` without Writer authorship, or non-done with specialist authorship) |
| `degraded_rate` | reported (no forced target; scenario mix determines) |
| `budget_exhausted_rate` | reported |
| `pass_rate` on expected terminals for scripted rows | 1.0 for rows with expectations |

### 8.4 Artifacts

- `docs/assets/isolation-sim.json` (or `data/eval/reports/…`) + HTML summary
- Caption in HTML/README: **isolation and accounting under fake specialists — not a quality benchmark**

### 8.5 Honesty

Single-process (or single TestClient / single isolate) results are **not** multi-tenant capacity proof. Hosted p50/p95 include cold starts and do not claim multi-region SLOs.

---

## 9. Trace pack (design; implement Month 3)

### 9.1 Layout

A lawyer-unzippable directory or zip:

```
trace-pack/
  manifest.json       # schema_version, pack_hash, created_with, policy_hash
  policy.yaml         # or policy.json — exact policy used
  task.json           # task text, budget overrides, seed
  result.json         # TaskResult-equivalent terminal fields
  trace.json          # schema-1 event sequence (or export envelope)
  README.txt          # human one-pager: how to verify offline
```

### 9.2 Rules

| Rule | Detail |
| --- | --- |
| Policy hash | SHA-256 of canonical policy bytes; must match `manifest.policy_hash` |
| Seed | Integer; free path remains deterministic for same task+seed+policy |
| No secrets | Pack never embeds env keys or connection strings |
| Import | File-replay UI accepts pack **or** embedded schema-1 trace without server POST |
| Offline verify | `python -m mao.replay` on pack trace member; optional `python -m mao.pack verify` |
| Round-trip | pack → load → fields equal stored result/trace; tests in CI |

### 9.3 Relationship to ADR-0006

Pack is the **season-grade** durability artifact. Single-run schema-1 download remains valid. Pack adds policy identity + seed + explicit verify path for third parties.

---

## 10. DEMO-DAY (~25 minutes, P3 segment)

Aligns with master plan §37 P3 slot; season expands to a self-contained 25-minute story.

| Min | Beat |
| ---: | --- |
| 0–3 | Series placement: P1 retrieve → P2 research loop → **P3 coordination policy** |
| 3–8 | Open default **policy document** (data, not a slide of ifs); show policy hash |
| 8–14 | Run happy path + one **chaos** hard case (crash or impersonation); show typed degraded |
| 14–18 | Unzip **trace pack**; load in UI; match event sequence |
| 18–22 | Recycle story: refresh run id → 404; **file/pack** still replays (ADR-0006 honesty) |
| 22–25 | Isolation sim headline (`swap_rate=0`, n=1000); list PLANNED (no Redis, no real LLMs) |

Host only: **https://pax-orchestration.vercel.app** or localhost free path.

---

## 11. v1.0.0 checklist (season OK requires all)

- [ ] This `docs/SEASON.md` lists 15 invariants and which have tests
- [ ] Policy document LIVE; default equals v0.3 characterization; ADR accepted
- [ ] Chaos **n ≥ 40**, easy/medium/hard predicates, free path pass_rate 1.0
- [ ] Isolation simulation n=1000, `swap_rate=0`, `writer_only_violations=0`, JSON+HTML published
- [ ] Policy UI + generated capture in manifest
- [ ] Load artifact: p50/p95 POST `/v1/tasks` fake, n, cold-start, single-isolate honesty
- [ ] Trace pack + UI import + round-trip tests
- [ ] File-replay still works without inventing server durability
- [ ] Optional P2 remains fail-closed; CI URL unset
- [ ] CASESTUDY ≥ 1500 words, real trade-offs, no invented multi-agent quality
- [ ] DEMO-DAY 25 min script executable from SHIP/DEMO-DAY
- [ ] CI green with empty keys; no secrets in git
- [ ] Release notes v1.0.0 list what is still **PLANNED**
- [ ] Host remains **pax-orchestration** only (never `pax-mao`)
- [ ] Tag **v1.0.0** only once checklist is green

---

## 12. Still PLANNED after v1.0 (honesty list)

- Durable multi-instance run storage (KV, Postgres, object store of every run)
- Redis / shared rate-limit or session fabric
- Real LLM specialists as default (or any paid model on free path)
- Multi-tenant policy SaaS, remote policy registry, ABAC
- Claiming multi-agent **quality** from fake specialists
- Capacity planning from single-isolate p50/p95
- New Vercel project or rename away from `pax-orchestration`
- Cross-repo automatic specialist mesh (P2/P4 as mandatory deps)

---

## 13. Failure taxonomy mapping (master plan §33 + P3 stops)

| Code / stop | P3 meaning this season |
| --- | --- |
| `max_handoffs` / `budget_exhausted` | Global handoff ceiling bound |
| `retry_limit` | Critic→Research cap bound |
| `specialist_error` | Crash/exception in a specialist |
| `policy_violation` | Illegal handoff or non-Writer final |
| `writer_final` | Successful Writer completion |
| `capability_missing` | HTTP P2 research requested without usable URL |
| `validation_error` | Bad request 422 |
| `backend_unavailable` | Opt-in HTTP dependency down → typed degrade/error, not invent |

Amazing portfolios **name** these. Toy demos only show Writer `done`.

---

## 14. Hosted and CI contracts

| Surface | Rule |
| --- | --- |
| Project | **`pax-orchestration`** |
| URL | **https://pax-orchestration.vercel.app** |
| Health | `{"status":"ok"}` |
| Specialists on host | Fake default; no model credits |
| `AGENTIC_RAG_URL` | Opt-in; CI **unset** |
| Durability | Process-local FIFO + **client file / pack**; not KV |
| CI | ruff, mypy, pytest, evals offline |
| Recycle | Expect empty run ids; demos use download / pack |

---

## 15. Work hygiene

| Rule | Detail |
| --- | --- |
| Ownership | A1 owns **only** `multi-agent-orchestration` (P3) |
| No subagents | Season dispatch: do not spawn subagents for this work |
| No OK early | `REPORTE … OK` only after Month 3 checklist green |
| Week 1 | **This file only** — no Month 2 sim code, no pack implementation in the design commit |
| Secrets | Never commit keys; Regla 3 for vault mirrors |
| Branches | Worker branch `a1/p3-v1-season`; integration to main is orchestrator policy |
| Baseline pin | Design assumptions anchored to `8feb31a` / v0.3.0 |

---

## 16. Open questions (resolve before coding Weeks 2–4 if blocking)

1. **Policy file format:** YAML vs JSON vs both (JSON for pack hash stability; YAML for human edit)? Prefer JSON canonical + optional YAML source if tooling is light.
2. **Chaos n count:** does `tasks.jsonl` growth count toward n≥40 or only `chaos.jsonl`? **This design:** chaos file alone must reach ≥40 isolation scenarios; task goldens remain separate routing suite.
3. **Simulation concurrency model:** threads vs sequential with injected interleaving — pick one, document it in the HTML artifact, do not claim the other.
4. **Pack transport:** zip only vs directory fixtures in git for tests (both: zip for demo, directory fixtures for CI).

None of these block Week 1 design commit.

---

## 17. Success phrase (hiring)

> We treat multi-agent **policy as a versioned document**: Writer-only final, handoff budgets, and degraded modes load from data, fail closed under chaos, prove isolation at n=1000 with swap_rate=0, and ship a trace pack you can unzip after the serverless process is gone — without pretending fake specialists are quality or that process memory is a database.
