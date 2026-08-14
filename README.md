# Multi-Agent Orchestration

[![CI](https://github.com/pabloalvarez99/multi-agent-orchestration/actions/workflows/ci.yml/badge.svg)](https://github.com/pabloalvarez99/multi-agent-orchestration/actions/workflows/ci.yml)

Project 3 in a five-system [AI Engineering portfolio](https://github.com/pabloalvarez99):
deterministic Research, Critic, and Writer specialists coordinated under explicit handoff and
retry budgets, with Writer-only final output and typed degraded outcomes.

> **M5 and the v0.1.0 runtime surface are LIVE.** The fake team remains the default for the
> library, API, CLI, browser console, and 12-task scorecard. Research can optionally cross the
> public P2 HTTP boundary when `AGENTIC_RAG_URL` is explicitly configured. No model key is
> required and the default path makes no network call. The public tag remains pending until
> the release commit has green CI.

The [architecture](docs/architecture.md) and four accepted ADRs make the intended
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

Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) for the accessible task console. It
shows terminal status, Writer output, participants, handoff/retry accounting, request ID, and
the ordered trace.

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

## Optional P2 Research

The remote specialist is opt-in. An empty setting never changes the fake default:

```bash
export AGENTIC_RAG_URL="http://127.0.0.1:8001"
curl -s -X POST http://127.0.0.1:8000/v1/tasks \
  -H "content-type: application/json" \
  -d '{"task":"Compare hybrid and dense retrieval","research":"http"}'
```

P3 sends one bounded `POST /v1/research` with P2's fake retriever by default. Missing
configuration is a typed `409 capability_missing`; timeout, transport, HTTP, or response
contract failures terminate as `degraded`. The P2 trace is not copied into the final result.

## Docker

```bash
docker compose up --build
# UI: http://127.0.0.1:8000/  API: http://127.0.0.1:8000/docs
```

The image uses Python 3.12 slim and runs Uvicorn as an unprivileged user. This compose file
operates P3 alone; it is not the portfolio-wide P5 topology.

## Verify

```bash
ruff check .
mypy src/mao
pytest -q
python -m mao.evals.run
```

## LIVE surface

| Capability | State |
| --- | --- |
| Fake Research → Critic → Writer workflow, budgets, Writer-only final | **LIVE** |
| JSON API, CLI, accessible UI, request IDs, ordered trace | **LIVE** |
| Optional P2 HTTP Research, fail-closed to `degraded` | **LIVE (opt-in)** |
| 12 fake goldens + two no-network boundary cases, billed `$0` | **LIVE** |
| Ruff + mypy + pytest + evals in empty-key CI | **LIVE** |
| Non-root Docker image and standalone Compose | **LIVE** |
| Hosted models, remote-process isolation, multi-agent quality uplift | **PLANNED / not claimed** |
| Public `v0.1.0` GitHub tag and release | **PENDING green release SHA** |

## Portfolio series

1. [production-rag v0.1.0](https://github.com/pabloalvarez99/production-rag/releases/tag/v0.1.0) — hybrid RAG,
   grounded citations, refusal, and offline evaluation (**LIVE**)
2. [agentic-rag-research v0.1.0](https://github.com/pabloalvarez99/agentic-rag-research/releases/tag/v0.1.0) — bounded
   plan/retrieve/critique research loop with API, CLI, optional P1 HTTP, and offline evals
   (**LIVE**)
3. **multi-agent-orchestration** — coordination, optional P2 Research, and trace UI
   (**M5 LIVE; v0.1.0 release candidate**)
4. [RepoMind](https://github.com/pabloalvarez99/repomind) — AST-aware code intelligence
   with grounded `path:line` answers (**M5 live; JSON CLI + 14-case fixture eval**)
5. AI Platform — gateway and operations (**planned**)

## Next boundary

The remaining M6 action is the public `v0.1.0` tag and GitHub release on an exact green SHA.
Remote specialist isolation, hosted model quality, and claims that agents beat a single model
remain future work.

## Documentation map

- [Architecture](docs/architecture.md) — current scaffold, target topology, contracts,
  budgets, isolation, timeline, evaluation boundary, and milestones.
- [ADR-0001](docs/adr/0001-specialist-roles.md) — narrow specialist authority.
- [ADR-0002](docs/adr/0002-writer-only-final.md) — Writer is the sole final speaker.
- [ADR-0003](docs/adr/0003-degraded-mode.md) — explicit evidence-preserving degradation.
- [ADR-0004](docs/adr/0004-optional-p2-boundary.md) — optional P2 boundary that fails closed.
- [SHIP](docs/SHIP.md) — LIVE/PLANNED truth and release gate.
- [Portfolio](docs/PORTFOLIO.md) — P1 → P5 maturity ladder.
- [Golden task schema](data/eval/README.md) — curation, coverage, metrics, and limits.

## License

[MIT](LICENSE)
