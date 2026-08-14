# Multi-Agent Orchestration

[![CI](https://github.com/pabloalvarez99/multi-agent-orchestration/actions/workflows/ci.yml/badge.svg)](https://github.com/pabloalvarez99/multi-agent-orchestration/actions/workflows/ci.yml)

Project 3 in a five-system [AI Engineering portfolio](https://github.com/pabloalvarez99):
deterministic Research, Critic, and Writer specialists coordinated under explicit handoff and
retry budgets, with Writer-only final output and typed degraded outcomes.

> **M2 library LIVE; HTTP remains health-only.** `run_task()` executes the bounded in-process
> fake team. The FastAPI app still exposes only `GET /health`; no task endpoint, timeline,
> golden evaluation, model call, or remote specialist is claimed.

The [target architecture](docs/architecture.md) and three accepted ADRs make the intended
authority, Writer-only final rule, budgets, and degraded mode implemented through M2.
[SHIP.md](docs/SHIP.md) remains the shorter source of truth for what is runnable.

## Run the free path

No API key or hosted provider is used.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
uvicorn mao.main:app --reload
```

```bash
curl http://127.0.0.1:8000/health
# {"status":"ok"}
```

Run the actual free orchestration path as a library:

```python
from mao.orchestrator import run_task

result = run_task("Audit retrieval risk")
print(result.model_dump_json(indent=2))
# status=done, one bounded Critic -> Research retry, Writer-authored result
```

## Verify

```bash
ruff check .
pytest -q
```

## Portfolio series

1. [production-rag](https://github.com/pabloalvarez99/production-rag) — hybrid RAG,
   grounded citations, refusal, and offline evaluation (**live: v0.1.0**)
2. [agentic-rag-research](https://github.com/pabloalvarez99/agentic-rag-research) — bounded
   plan/retrieve/critique research loop with API, CLI, optional P1 HTTP, and offline evals
   (**M5 live; release planned**)
3. **multi-agent-orchestration** — coordination and handoffs (**M2 library live; HTTP health-only**)
4. RepoMind — code intelligence (**planned; no public implementation**)
5. AI Platform — gateway and operations (**planned**)

## Next boundary

M3 adds an append-only deterministic timeline. A task API, offline golden evaluation, and
optional P2 research boundary remain later milestones; none is implied by the library path.

## Documentation map

- [Architecture](docs/architecture.md) — current scaffold, target topology, contracts,
  budgets, isolation, timeline, evaluation boundary, and milestones.
- [ADR-0001](docs/adr/0001-specialist-roles.md) — narrow specialist authority.
- [ADR-0002](docs/adr/0002-writer-only-final.md) — Writer is the sole final speaker.
- [ADR-0003](docs/adr/0003-degraded-mode.md) — explicit evidence-preserving degradation.
- [SHIP](docs/SHIP.md) — LIVE/PLANNED truth and release gate.
- [Portfolio](docs/PORTFOLIO.md) — P1 → P5 maturity ladder.

## License

[MIT](LICENSE)
