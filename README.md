# Multi-Agent Orchestration

[![CI](https://github.com/pabloalvarez99/multi-agent-orchestration/actions/workflows/ci.yml/badge.svg)](https://github.com/pabloalvarez99/multi-agent-orchestration/actions/workflows/ci.yml)

Public scaffold for project 3 in a five-system
[AI Engineering portfolio](https://github.com/pabloalvarez99). The intended project will
study bounded specialist handoffs, explicit budgets, isolation, degradation, and inspectable
timelines.

> **Scaffold only:** the repository currently exposes `GET /health`. No agent, orchestrator,
> handoff policy, model call, or multi-agent loop is implemented yet.

The [target architecture](docs/architecture.md) and three proposed ADRs make the intended
authority, Writer-only final rule, budgets, and degraded mode reviewable before code lands.
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
3. **multi-agent-orchestration** — coordination and handoffs (**scaffold only**)
4. RepoMind — code intelligence (**planned; no public implementation**)
5. AI Platform — gateway and operations (**planned**)

## Next boundary

The first implementation milestone will define typed handoff and state contracts before
adding any agent loop. That work is deliberately outside this scaffold release.

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
