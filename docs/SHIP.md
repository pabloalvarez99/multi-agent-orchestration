# Ship truth

**Status: P3-M2 LIVE as a library; HTTP is health-only.** The repository can be cloned,
installed, tested, and run without a key. `run_task()` executes deterministic specialists
under handoff/retry budgets; `GET /health` returns `{"status":"ok"}`. No orchestration task
endpoint, timeline, evaluation dataset, model call, or P2 client exists on integrated `main`.

## Try the free path

```bash
python -m venv .venv
python -m pip install -e ".[dev]"
python -m pytest -q
python -m uvicorn mao.main:app --port 8000
curl http://127.0.0.1:8000/health
```

## LIVE table

| Capability | State | Evidence |
| --- | --- | --- |
| Python package and FastAPI process | **LIVE** | package import and app startup |
| `GET /health` | **LIVE** | route and offline test |
| CI with `OPENAI_API_KEY` empty | **LIVE** | `.github/workflows/ci.yml` |
| Typed handoff protocol and fake specialists | **LIVE** | model and fake-agent tests |
| Orchestrator and global handoff/retry budgets | **LIVE (library)** | happy, retry, and exhaustion tests |
| Writer-only final enforcement | **LIVE** | type + policy violation test; ADR-0002 |
| Degraded specialist-failure outcomes | **LIVE** | crashing-Critic and impersonation tests; ADR-0003 |
| Multi-agent timeline | **PLANNED** | target: M3 |
| Golden task evaluation | **PLANNED** | no `data/eval` dataset on `main` |
| Optional P2 integration | **PLANNED** | no outbound research client |
| Tagged release | **PLANNED** | no release claimed |

## What CI proves today

- the package imports and its health route answers;
- deterministic specialists follow the allowed route;
- global handoff and Critic retry ceilings stop the loop;
- only Writer can complete successfully; and
- specialist/policy failures become explicit degraded results;
- lint and unit tests run on Python 3.12; and
- the current free path does not need an OpenAI key.

It does not prove timeline completeness, HTTP task behavior, answer quality, remote-process
isolation, or multi-model collaboration because those capabilities are not integrated.

## Non-goals at M2

- No claim that several agents outperform one.
- No model calls, shared memory, arbitrary tools, P2/P1 dependency, or hosted demo.
- No user-facing task result, writer output, timeline, eval score, or cost comparison.
- No silent promotion of target architecture to LIVE documentation.

## Release gate

P3 can be called v0.1.0 only after the orchestrator, budgets, Writer invariant, degraded
mode, timeline, and offline goldens are merged; the LIVE table points to their tests; CI is
green on the exact tag; and fake-provider metrics are labelled as contract evidence.
