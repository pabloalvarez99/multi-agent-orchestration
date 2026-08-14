# Ship truth

**Status: P3 v0.3.0 LIVE.** The
repository can be cloned, tested, and run without a key. The fake team remains the default
for library, API, CLI, UI, and 18-case scorecard. An explicitly selected HTTP Research agent
can call P2 when `AGENTIC_RAG_URL` is configured and fails closed otherwise.

**Hosted free path LIVE:** <https://pax-orchestration.vercel.app>. It runs the deterministic
fake specialists and spends no model credits. Expect serverless cold starts; metrics and
retained runs are in-process only and disappear when the instance is recycled.

## Try the free path

Open <https://pax-orchestration.vercel.app> or reproduce it locally:

```bash
python -m venv .venv
python -m pip install -e ".[dev]"
python -m pytest -q
python -m uvicorn mao.main:app --port 8000
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/metrics
# browser console: http://127.0.0.1:8000/
```

## LIVE table

| Capability | State | Evidence |
| --- | --- | --- |
| Python package and FastAPI process | **LIVE** | package import and app startup |
| Public Vercel console/API | **LIVE** | [`pax-orchestration.vercel.app`](https://pax-orchestration.vercel.app); root adapter + production smoke |
| `GET /health` | **LIVE** | route and offline test |
| `POST /v1/tasks` and JSON CLI | **LIVE** | response-shape, OpenAPI, budget, and CLI tests |
| CI with OpenAI and P2 URL settings empty | **LIVE** | ruff, mypy, pytest, and evals workflow |
| Typed handoff protocol and fake specialists | **LIVE** | model and fake-agent tests |
| Orchestrator and global handoff/retry budgets | **LIVE (library)** | happy, retry, and exhaustion tests |
| Writer-only final enforcement | **LIVE** | type + policy violation test; ADR-0002 |
| Degraded specialist-failure outcomes | **LIVE** | crashing-Critic and impersonation tests; ADR-0003 |
| Typed terminal reasons | **LIVE** | `writer_final`, `max_handoffs`, `retry_limit`, `specialist_error`, `policy_violation` |
| Ordered JSON-safe multi-agent timeline | **LIVE** | completeness, ordering, privacy, and budget-stop tests |
| 12-task golden evaluation | **LIVE** | three slices; [schema and limits](../data/eval/README.md) |
| Four chaos goldens | **LIVE** | crash, reject twice, global budget, Writer impersonation; `$0`, offline |
| HTTP-absent evaluation slice | **LIVE** | two configuration cases, zero network calls |
| Optional P2 integration | **LIVE (opt-in)** | mocked success/error/timeout tests; ADR-0004 |
| Accessible trace UI and request IDs | **LIVE** | GET, submit, terminal-state, and no-network tests |
| Prometheus text metrics | **LIVE** | content type, stable metric names, and post-task counter test |
| Timeline JSON download | **LIVE** | attachment header and exact in-memory event sequence test |
| Schema-1 export + file replay | **LIVE (client-side)** | UI load, `python -m mao.replay`, fixture equality, recycle-clear test |
| Versioned replay endpoints | **LIVE (process-local)** | schema 1, run metadata/trace endpoints, typed 404, FIFO eviction test |
| Concurrent task isolation | **LIVE** | two threads, Writer text and traces do not swap |
| Deterministic event offsets | **LIVE** | same task + seed produces the exact event sequence; ADR-0005 |
| Per-specialist elapsed timings | **LIVE (debug)** | injected-clock accounting test and result-page test |
| Generated UI captures | **LIVE** | Playwright script, pinned inputs, committed SHA-256 manifest |
| Non-root Docker + standalone Compose | **LIVE** | local build and container smoke |
| Tagged `v0.2.0` release | **LIVE** | GitHub Release object + hosted free path on `8155274` |
| Tagged `v0.3.0` release | **LIVE** | offline file replay, isolation under load, ADR-0006 |

## Authority and stop matrix

| Role | Allowed actions | Forbidden actions | Stop reasons it can surface |
| --- | --- | --- | --- |
| Orchestrator | validate routes, dispatch, count budgets, record trace/status | write a successful final answer, reset counters | `max_handoffs`, `retry_limit`, `specialist_error`, `policy_violation` |
| Research | return evidence handoff to Critic | return user-facing `FinalAnswer`, route directly to Writer | `specialist_error`, `policy_violation` |
| Critic | accept to Writer or reject to Research up to two times | answer user, exceed retry budget | `retry_limit`, `specialist_error`, `policy_violation` |
| Writer | return the sole successful user-facing `FinalAnswer` | hand off, change budgets or status | `writer_final`, `specialist_error` |

Non-done responses carry a system-owned typed stop explanation (`result_author=null`), never
an intermediate specialist memo presented as an answer.

## Generated UI evidence

| Writer completes | Global budget stops |
| --- | --- |
| [![Done path with Writer output and ordered trace](assets/ui-done.png)](assets/ui-done.png) | [![Budget-exhausted path before Writer](assets/ui-budget.png)](assets/ui-budget.png) |

### Bounded Critic retry

[![Seventeen-event Research, Critic, Writer timeline with one retry and visible request ID](assets/ui-trace.png)](assets/ui-trace.png)

### Versioned replay

[![Replay panel with schema 1 and retained-run links](assets/ui-replay.png)](assets/ui-replay.png)

### Offline file replay (after the server forgets)

[![Load trace JSON panel for client-side schema-1 replay](assets/ui-replay-from-file.png)](assets/ui-replay-from-file.png)

*Deterministic fake specialists. Not a quality claim.* The script uses the real localhost app
and fake form path. It pins viewport, locale, task text, and budgets, disables motion, and
normalizes only the displayed request ID to `capture-fixed-request-id`; production request IDs
remain unique. It also normalizes displayed debug timings to `0.100 ms`; production timings
use a monotonic process clock. Two consecutive generation runs produced byte-identical PNGs recorded in
[`ui-captures.sha256`](assets/ui-captures.sha256).

```bash
python -m pip install -e ".[docs]"
playwright install chromium
python scripts/capture_ui.py
```

The live P2 smoke is still opt-in and is not involved in these captures. The hosted demo uses
the fake team and does not claim hosted-model quality.

## What CI proves today

- the package imports and its health route answers;
- deterministic specialists follow the allowed route;
- global handoff and Critic retry ceilings stop the loop;
- only Writer can complete successfully; and
- specialist/policy failures become explicit degraded results;
- API and CLI project the canonical result shape;
- traces are ordered, JSON-safe, and omit full task content;
- `/metrics` exposes process, request, terminal-status, and handoff signals without a backend;
- UI traces download as JSON attachments, and specialist timings remain debug-only;
- schema-1 exports reload offline via UI file input and `python -m mao.replay`;
- retained runs expose schema 1 metadata and events until process recycle or FIFO eviction;
- concurrent fake tasks keep Writer text and traces isolated in one process;
- all 12 committed golden tasks meet their routing/accounting expectations;
- all four chaos goldens preserve non-empty terminal output and declared ownership;
- ruff, strict mypy, unit tests, and all routing/boundary/chaos evals run on Python 3.12; and
- the current free path does not need an OpenAI key.

It does not prove answer quality, remote-process isolation, live P2 availability, or
multi-model collaboration. HTTP tests prove the boundary contract, not quality uplift.

## Non-goals for v0.3.0

- No claim that several agents outperform one.
- No durable multi-instance server store (KV/Postgres). File replay is client-side only.
- No hosted model default, durable shared memory, or arbitrary tools.
- No remote-agent isolation, hosted quality score, or cost comparison.
- No silent promotion of target architecture to LIVE documentation.

## Release gate

The release was prepared only after the implementation gates completed. The tag targets the
exact release commit whose CI ran ruff, strict mypy, pytest, and both free-path eval slices.
Release notes separate LIVE capability from PLANNED claims.
