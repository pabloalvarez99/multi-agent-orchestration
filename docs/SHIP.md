# Ship truth

**Status: P3-M4 LIVE on the deterministic free path.** The repository can be cloned,
installed, tested, and run without a key. Library, `POST /v1/tasks`, and JSON CLI execute the
same bounded fake specialists and return a deterministic timeline. The 12-task offline
scorecard needs no network. No model call, remote specialist, or P2 client exists on `main`.

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
| `POST /v1/tasks` and JSON CLI | **LIVE** | response-shape, OpenAPI, budget, and CLI tests |
| CI with `OPENAI_API_KEY` empty | **LIVE** | `.github/workflows/ci.yml` |
| Typed handoff protocol and fake specialists | **LIVE** | model and fake-agent tests |
| Orchestrator and global handoff/retry budgets | **LIVE (library)** | happy, retry, and exhaustion tests |
| Writer-only final enforcement | **LIVE** | type + policy violation test; ADR-0002 |
| Degraded specialist-failure outcomes | **LIVE** | crashing-Critic and impersonation tests; ADR-0003 |
| Ordered JSON-safe multi-agent timeline | **LIVE** | completeness, ordering, privacy, and budget-stop tests |
| 12-task golden evaluation | **LIVE** | three slices; [schema and limits](../data/eval/README.md) |
| Optional P2 integration | **PLANNED** | no outbound research client |
| Tagged release | **PLANNED** | no release claimed |

## What CI proves today

- the package imports and its health route answers;
- deterministic specialists follow the allowed route;
- global handoff and Critic retry ceilings stop the loop;
- only Writer can complete successfully; and
- specialist/policy failures become explicit degraded results;
- API and CLI project the canonical result shape;
- traces are ordered, JSON-safe, and omit full task content;
- all 12 committed golden tasks meet their routing/accounting expectations;
- lint and unit tests run on Python 3.12; and
- the current free path does not need an OpenAI key.

It does not prove answer quality, remote-process isolation, P2 integration, or multi-model
collaboration because those capabilities are not integrated.

## Non-goals at M4

- No claim that several agents outperform one.
- No model calls, shared memory, arbitrary tools, P2/P1 dependency, or hosted demo.
- No remote-agent isolation, P2/P1 dependency, hosted quality score, or cost comparison.
- No silent promotion of target architecture to LIVE documentation.

## Release gate

P3 can be called v0.1.0 only after the optional M5 P2 boundary is either implemented and
tested or explicitly cut from the release; all 12 goldens pass on the release commit; the
LIVE table points to merged tests; CI is green on the exact tag; and fake-provider metrics
are labelled as contract evidence.
