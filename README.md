# Multi-Agent Orchestration

[![CI](https://github.com/pabloalvarez99/multi-agent-orchestration/actions/workflows/ci.yml/badge.svg)](https://github.com/pabloalvarez99/multi-agent-orchestration/actions/workflows/ci.yml)

Project 3 in a five-system [AI Engineering portfolio](https://github.com/pabloalvarez99):
deterministic Research, Critic, and Writer specialists coordinated under explicit handoff and
retry budgets, with Writer-only final output and typed degraded outcomes.

> **M4 LIVE on the deterministic free path.** `run_task()`, `POST /v1/tasks`, and the JSON CLI
> execute the bounded in-process fake team with an ordered timeline. A 12-task offline golden
> scorecard measures routing contracts. No model call, remote specialist, or P2 client is
> claimed.

The [target architecture](docs/architecture.md) and three accepted ADRs make the intended
authority, Writer-only final rule, budgets, and degraded mode implemented through M2, plus
the M3 timeline and M4 evaluation boundary.
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

curl -s -X POST http://127.0.0.1:8000/v1/tasks \
  -H "content-type: application/json" \
  -d '{"task":"Audit retrieval risk","budget":{"max_handoffs":8}}'
```

Run the actual free orchestration path as a library:

```python
from mao.orchestrator import run_task

result = run_task("Audit retrieval risk")
print(result.model_dump_json(indent=2))
# status=done, one bounded Critic -> Research retry, Writer-authored result
```

The CLI and offline scorecard use the same path:

```bash
python -m mao.task --task "Compare hybrid vs dense retrieval"
python -m mao.evals.run --pretty
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
   (**v0.1.0 / M6 live**)
3. **multi-agent-orchestration** — coordination and handoffs (**M4 live; release planned**)
4. [RepoMind](https://github.com/pabloalvarez99/repomind) — AST-aware code intelligence
   with grounded `path:line` answers (**M5 live; JSON CLI + 14-case fixture eval**)
5. AI Platform — gateway and operations (**planned**)

## Next boundary

M5 adds an optional P2 research boundary without changing the default fake path. A tagged
release remains M6; neither is implied by the M4 API/evaluation surface.

## Documentation map

- [Architecture](docs/architecture.md) — current scaffold, target topology, contracts,
  budgets, isolation, timeline, evaluation boundary, and milestones.
- [ADR-0001](docs/adr/0001-specialist-roles.md) — narrow specialist authority.
- [ADR-0002](docs/adr/0002-writer-only-final.md) — Writer is the sole final speaker.
- [ADR-0003](docs/adr/0003-degraded-mode.md) — explicit evidence-preserving degradation.
- [SHIP](docs/SHIP.md) — LIVE/PLANNED truth and release gate.
- [Portfolio](docs/PORTFOLIO.md) — P1 → P5 maturity ladder.
- [Golden task schema](data/eval/README.md) — curation, coverage, metrics, and limits.

## License

[MIT](LICENSE)
