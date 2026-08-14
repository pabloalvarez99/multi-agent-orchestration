# Ship truth

**Status: P3-M0 LIVE; health-only scaffold.** The repository can be cloned, installed, tested,
and started without a key. `GET /health` returns `{"status":"ok"}`. No orchestration task
endpoint or agent loop is available on integrated `main`.

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
| Typed handoff protocol and fake specialists | **PLANNED on `main`** | target: M1 |
| Orchestrator and global handoff budget | **PLANNED** | target: M2 |
| Writer-only final enforcement | **PLANNED** | ADR-0002 |
| Degraded specialist-failure outcomes | **PLANNED** | ADR-0003 |
| Multi-agent timeline | **PLANNED** | target: M3 |
| Golden task evaluation | **PLANNED** | no `data/eval` dataset on `main` |
| Optional P2 integration | **PLANNED** | no outbound research client |
| Tagged release | **PLANNED** | no release claimed |

## What CI proves today

- the scaffold imports and its health route answers;
- lint and unit tests run on Python 3.12; and
- the current free path does not need an OpenAI key.

It does not prove handoff correctness, budget enforcement, degradation, trace completeness,
answer quality, or model isolation because those capabilities are not integrated.

## Non-goals at M0

- No claim that several agents outperform one.
- No model calls, shared memory, arbitrary tools, P2/P1 dependency, or hosted demo.
- No user-facing task result, writer output, timeline, eval score, or cost comparison.
- No silent promotion of target architecture to LIVE documentation.

## Release gate

P3 can be called v0.1.0 only after the orchestrator, budgets, Writer invariant, degraded
mode, timeline, and offline goldens are merged; the LIVE table points to their tests; CI is
green on the exact tag; and fake-provider metrics are labelled as contract evidence.
