# P3 demo day — cold URL or clone to degraded in 20 minutes

This script demonstrates policy and failure isolation with deterministic fake specialists.
It spends `$0`, needs no API key, and does not evaluate model quality.

## 0–3 minutes — prove the public edge

Open <https://pax-orchestration.vercel.app>. A cold serverless instance may take a few
seconds. Submit the prefilled task and point out the Writer-owned result, bounded counters,
logical event offsets, and Replay panel.

```bash
curl https://pax-orchestration.vercel.app/health
curl -X POST https://pax-orchestration.vercel.app/v1/tasks \
  -H "content-type: application/json" \
  -H "x-request-id: demo-day-run" \
  -d '{"task":"Audit retrieval risk","seed":41,"budget":{"max_handoffs":8}}'
curl https://pax-orchestration.vercel.app/v1/runs/demo-day-run/trace
```

If the last lookup lands on another serverless instance, explain the visible limitation:
retention is process-local, not a database. The POST response still contains the full trace.

## 3–9 minutes — clone and verify the free path

```bash
git clone https://github.com/pabloalvarez99/multi-agent-orchestration.git
cd multi-agent-orchestration
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -e ".[dev]"
ruff check .
mypy src/mao
pytest -q
```

## 9–14 minutes — inspect deterministic replay

```bash
python -m mao.task --task "Audit retrieval risk" --seed 41 --max-handoffs 8
python -m mao.task --task "Audit retrieval risk" --seed 41 --max-handoffs 8
```

The event lists are identical: schema 1 uses logical `ts_offset_ms` rather than wall-clock
timestamps. Runtime specialist timings remain separate debug values.

## 14–18 minutes — force and explain degradation

```bash
python -m mao.evals.run --pretty
pytest -q tests/evals tests/api/test_tasks.py
```

In `chaos_results`, show:

- `critic-crash-degrades`: non-empty `degraded` + `specialist_error`;
- `critic-rejects-twice-writer-finishes`: two retries, seven handoffs, Writer final;
- `global-budget-typed-stop`: `budget_exhausted` + `max_handoffs`;
- `research-cannot-impersonate-writer`: `policy_violation`, no fake final promoted.

## 18–20 minutes — close with the boundary

Use the [authority matrix](docs/SHIP.md#authority-and-stop-matrix) and
[ADR-0005](docs/adr/0005-versioned-process-local-traces.md). The interview claim is narrow:
P3 makes coordination policy replayable and failures typed. Durable cross-instance audit
storage, remote specialist isolation, and hosted-model quality are not claimed.
