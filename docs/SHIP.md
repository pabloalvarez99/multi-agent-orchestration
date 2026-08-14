# Ship truth

**Status: P3 v0.1.0 LIVE.** The
repository can be cloned, tested, and run without a key. The fake team remains the default
for library, API, CLI, UI, and 12-task scorecard. An explicitly selected HTTP Research agent
can call P2 when `AGENTIC_RAG_URL` is configured and fails closed otherwise.

## Try the free path

```bash
python -m venv .venv
python -m pip install -e ".[dev]"
python -m pytest -q
python -m uvicorn mao.main:app --port 8000
curl http://127.0.0.1:8000/health
# browser console: http://127.0.0.1:8000/
```

## LIVE table

| Capability | State | Evidence |
| --- | --- | --- |
| Python package and FastAPI process | **LIVE** | package import and app startup |
| `GET /health` | **LIVE** | route and offline test |
| `POST /v1/tasks` and JSON CLI | **LIVE** | response-shape, OpenAPI, budget, and CLI tests |
| CI with OpenAI and P2 URL settings empty | **LIVE** | ruff, mypy, pytest, and evals workflow |
| Typed handoff protocol and fake specialists | **LIVE** | model and fake-agent tests |
| Orchestrator and global handoff/retry budgets | **LIVE (library)** | happy, retry, and exhaustion tests |
| Writer-only final enforcement | **LIVE** | type + policy violation test; ADR-0002 |
| Degraded specialist-failure outcomes | **LIVE** | crashing-Critic and impersonation tests; ADR-0003 |
| Ordered JSON-safe multi-agent timeline | **LIVE** | completeness, ordering, privacy, and budget-stop tests |
| 12-task golden evaluation | **LIVE** | three slices; [schema and limits](../data/eval/README.md) |
| HTTP-absent evaluation slice | **LIVE** | two configuration cases, zero network calls |
| Optional P2 integration | **LIVE (opt-in)** | mocked success/error/timeout tests; ADR-0004 |
| Accessible trace UI and request IDs | **LIVE** | GET, submit, terminal-state, and no-network tests |
| Non-root Docker + standalone Compose | **LIVE** | local build and container smoke |
| Tagged `v0.1.0` release | **LIVE** | public release targets the exact green release commit |

## What CI proves today

- the package imports and its health route answers;
- deterministic specialists follow the allowed route;
- global handoff and Critic retry ceilings stop the loop;
- only Writer can complete successfully; and
- specialist/policy failures become explicit degraded results;
- API and CLI project the canonical result shape;
- traces are ordered, JSON-safe, and omit full task content;
- all 12 committed golden tasks meet their routing/accounting expectations;
- ruff, strict mypy, unit tests, and both eval slices run on Python 3.12; and
- the current free path does not need an OpenAI key.

It does not prove answer quality, remote-process isolation, live P2 availability, or
multi-model collaboration. HTTP tests prove the boundary contract, not quality uplift.

## Non-goals for v0.1.0

- No claim that several agents outperform one.
- No hosted model default, shared memory, arbitrary tools, or hosted demo.
- No remote-agent isolation, hosted quality score, or cost comparison.
- No silent promotion of target architecture to LIVE documentation.

## Release gate

The release was prepared only after the implementation gates completed. The tag targets the
exact release commit whose CI ran ruff, strict mypy, pytest, and both free-path eval slices.
Release notes separate LIVE capability from PLANNED claims.
