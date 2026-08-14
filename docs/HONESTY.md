# HONESTY — multi-agent-orchestration v1.0.0 LOCK

**Agent:** A1 (Grok) · **Date:** 2026-08-14  
**Worktree:** `C:\dev\portfolio-workers\a1-p3-v1-lock` · branch `a1/p3-v1-lock`  
**Proven SHA:** `origin/main` = `88a24f23d7d9c880059de95b99cd393f3c42f70b`  
**Tag:** annotated `v1.0.0` → commit `88a24f2` (message: “v1.0.0 — policy as product”)  
**Host:** https://pax-orchestration.vercel.app  
**CI at SHA:** https://github.com/pabloalvarez99/multi-agent-orchestration/actions/runs/31839632766 (`quality` success)  
**Local suite:** `pytest -q` → **70 passed, 1 skipped** (this session)

Source of claim rows: GitHub Release body / `docs/releases/v1.0.0.md` LIVE section, plus mission MUST-REPRODUCE items.

Verdict codes: **PASS** (reproduced), **FAIL** (claim false; must fix), **STRIKE** (claim withdrawn).

| # | Claim | Command | Expected | Observed | Verdict |
|---|-------|---------|----------|----------|---------|
| 1 | Loadable default policy JSON characterizing v0.3 handoff graph and budgets (ADR-0007) | `python -c "from mao.orchestrator import load_default_policy, OrchestrationPolicy, DEFAULT_POLICY_PATH; d=load_default_policy(); p=OrchestrationPolicy(d); print(d.policy_id, d.budgets.max_handoffs, d.budgets.max_research_retries, len(p.allowed_handoffs), p.policy_hash, DEFAULT_POLICY_PATH.is_file())"` + `pytest -q tests/test_policy.py` + read `docs/adr/0007-policy-as-data.md` | File loads; policy_id `default-v0.3-characterization`; max_handoffs=8; max_research_retries=2; edges match v0.3; ADR-0007 present | `default-v0.3-characterization 8 2 4 b8526d4fc898bd12d6974ad0d10c517a3b54bfce87169c319399378fb140302a True`; policy tests PASS; ADR path exists | **PASS** |
| 2 | Restrictive fixture policy flips happy path (`forbid-research-to-writer`) | `pytest -q tests/test_policy.py::test_forbid_research_to_writer_fixture_changes_happy_path` + live `Orchestrator` compare | Default → `done`/`writer_final`; forbid → `degraded`/`policy_violation` | Test PASS. Live: `default done writer_final` · `forbid degraded policy_violation`. Fixture removes Research→Writer edges so the happy-path “Compare hybrid vs dense retrieval” ends `degraded`/`policy_violation` instead of `done`/`writer_final`. | **PASS** |
| 3 | Chaos isolation suite **n ≥ 40** with easy/medium/hard predicates | `python -c "from mao.evals.dataset import load_chaos_dataset, assert_chaos_difficulty_predicates; c=load_chaos_dataset(); assert_chaos_difficulty_predicates(c); print(len(c), sorted({x.difficulty for x in c}))"` + `pytest -q tests/evals/test_evals.py::test_chaos_dataset_covers_isolation_product_contracts tests/evals/test_evals.py::test_chaos_difficulty_predicates_reject_all_easy_new_rows` | File `data/eval/chaos.jsonl` ≥40; difficulties {easy,medium,hard}; predicate test in suite CI runs via `pytest -q` | chaos_n=40; difficulties `['easy','hard','medium']`; both tests PASS; CI workflow runs `pytest -q` with empty keys (run 31839632766 success) | **PASS** |
| 4 | Isolation simulation **n=1000**, `swap_rate=0`, `writer_only_violations=0` (JSON+HTML) | Re-run: `python -c "from mao.sim.isolation import run_isolation_simulation; r=run_isolation_simulation(n=1000, seed=20260814, workers=8); print(r.n, r.swap_rate, r.writer_only_violations)"` + inspect `docs/assets/isolation-sim.json` / `.html` + prove not stub (`ThreadPoolExecutor`, `list(range(n))`, submit `_run_one`) | Real 1000 tasks; swap_rate=0; writer_only_violations=0; committed JSON+HTML | **Re-run report:** `docs/assets/isolation-sim-lock-rerun.json` → **n=1000**, **swap_rate=0.0**, **writer_only_violations=0**, swap_count=0, done_rate=0.915, elapsed≈0.855s; committed assets match; source submits n tasks (not stub) | **PASS** |
| 5 | Policy UI (`/ui/policy`) + generated capture | Hosted `curl -sS -o NUL -w "%{http_code}" https://pax-orchestration.vercel.app/ui/policy`; local body grep; `Get-Item docs/assets/ui-policy.png` | HTTP 200; page shows policy id + hash; capture PNG present | Hosted **HTTP 200**, 2996 bytes; body has `default-v0.3-characterization`, `Policy hash`, source `policies/default-v0.3-characterization.json`; `ui-policy.png` 38367 bytes | **PASS** |
| 6 | Load probe p50/p95 for fake `POST /v1/tasks` (`docs/assets/load.json`, single isolate honesty) | Read `docs/assets/load.json` | n, p50/p95 present; honesty labels single isolate | `n=50`, p50_ms=7.966, p95_ms=21.365, honesty=`single isolate / single process TestClient — not multi-region capacity planning`, research=`fake`, billed_usd=0.0 | **PASS** |
| 7 | Trace pack (JSON / directory / zip) with policy hash, task, seed, trace, result; UI import + round-trip tests | `pytest -q tests/test_pack.py` + CLI build/load actor compare | Round-trip OK; actor sequence identical after load | Tests PASS. Manual: build seed=41 → write JSON → load → verify; **actors_match True**; sequence `orchestrator > orchestrator > research > orchestrator > research > critic > orchestrator > critic > writer > orchestrator > orchestrator` (11 events); committed sample pack under `docs/assets/sample-trace-pack*` | **PASS** |
| 8 | CASESTUDY ≥1500 words; DEMO-DAY 25 min script | `python -c "print(len(Path('docs/CASESTUDY.md').read_text().split()))"`; head `DEMO-DAY.md` | words ≥1500; DEMO-DAY titles 25 minutes | CASESTUDY **1856 words**; DEMO-DAY title “(25 minutes)” and section “22–25 min” | **PASS** |
| 9 | Free path still fake specialists, `$0`, CI with empty keys | `.github/workflows/ci.yml` env + `pytest` goldens + `python -m mao.evals.run` in CI | Empty `OPENAI_API_KEY` / `AGENTIC_RAG_URL`; provider fake; billed 0 | CI sets both keys to `""`; local goldens assert `provider=="fake"` and `billed_usd==0.0`; CI `quality` success on `88a24f2` | **PASS** |
| 10 | Hosted GET `/health` 200 | `curl -sS -w " HTTP:%{http_code}" https://pax-orchestration.vercel.app/health` | 200 + ok body | `{"status":"ok"} HTTP:200` | **PASS** |
| 11 | Hosted GET `/ui/policy` 200 | `curl -sS -o NUL -w "%{http_code}" https://pax-orchestration.vercel.app/ui/policy` | 200 | `HTTP:200` size 2996 | **PASS** |
| 12 | Hosted POST `/v1/tasks` fake 200 | `curl -X POST .../v1/tasks -H Content-Type:application/json --data-binary @tmp-task.json` body `{"task":"Write a short hello about retrieval","budget":{"max_handoffs":8},"seed":41}` + `x-request-id: lock-honesty-001` | 200; status done; writer; fake path | **HTTP 200**; `status=done`, `stop_reason=writer_final`, `result_author=writer`, `agents_involved=[orchestrator,research,critic,writer]`, task_started payload `provider=fake`, `billed_usd=0.0`, `policy_id=default-v0.3-characterization` | **PASS** |
| 13 | Download trace + `python -m mao.replay` exit 0 | `curl -o tmp-trace.json https://pax-orchestration.vercel.app/v1/runs/lock-honesty-001/trace` then `python -m mao.replay tmp-trace.json` | Trace 200; CLI exit 0 | Trace **HTTP 200** (schema-1 envelope, run_id `lock-honesty-001`, 11 events). Replay stdout: `trace_schema=1 run_id=lock-honesty-001` / `events=11` / `actors=orchestrator > orchestrator > research > orchestrator > research > critic > orchestrator > critic > writer > orchestrator > orchestrator` · **EXIT:0** | **PASS** |

## Hosted transcripts (verbatim excerpts)

### GET /health
```
{"status":"ok"}
HTTP:200
```

### GET /ui/policy
```
HTTP:200 bytes:2996
# body contains:
# <h2 id="policy-heading">default-v0.3-characterization</h2>
# <h3 id="hash-heading">Policy hash</h3>
# Source policies/default-v0.3-characterization.json
```

### POST /v1/tasks (fake)
```
HTTP:200
status=done stop_reason=writer_final result_author=writer
agents_involved=["orchestrator","research","critic","writer"]
policy_id=default-v0.3-characterization
policy_hash=b8526d4fc898bd12d6974ad0d10c517a3b54bfce87169c319399378fb140302a
provider=fake billed_usd=0.0 seed=41
x-request-id: lock-honesty-001
```

### GET /v1/runs/lock-honesty-001/trace
```
HTTP:200
{"trace_schema":1,"run_id":"lock-honesty-001","events":[...11 events...]}
```

### python -m mao.replay tmp-trace.json
```
trace_schema=1 run_id=lock-honesty-001
events=11
actors=orchestrator > orchestrator > research > orchestrator > research > critic > orchestrator > critic > writer > orchestrator > orchestrator
EXIT:0
```

## Isolation sim re-run (this session)

| Field | Value |
|-------|-------|
| Command | `run_isolation_simulation(n=1000, seed=20260814, workers=8)` |
| Report path | `docs/assets/isolation-sim-lock-rerun.json` (local lock evidence; committed peer: `docs/assets/isolation-sim.json` + `.html`) |
| n | **1000** (real: `order=list(range(n))` + `ThreadPoolExecutor` submit `_run_one` per index) |
| swap_rate | **0.0** |
| writer_only_violations | **0** |
| swap_count | 0 |
| done_rate | 0.915 |
| budget_exhausted_rate | 0.085 |
| elapsed | ~0.855 s (fake specialists) |

## Counts

| Verdict | Count |
|---------|------:|
| PASS | 13 |
| FAIL | 0 |
| STRIKE | 0 |

## Fixes / strikes

- **None.** All LIVE claims reproduced; no code changes required for lock.
- **Fixes (SHAs):** n/a
- **Blocked:** none

## Forbidden (confirmed not claimed as LIVE)

Release PLANNED / non-goals still honest: no Redis, no durable multi-instance server storage claim, no real-LLM free path, no multi-tenant policy SaaS. Server runs remain process-local FIFO (file replay + packs are the durable story).

## Notes

- Tag object `4cd054c…` is the **annotated tag**; peeled commit is `88a24f2` (matches `origin/main`).
- Difficulty predicates are enforced by `assert_chaos_difficulty_predicates` in tests collected under CI `pytest -q` (not a separate workflow job name, but present in the suite CI executes).
