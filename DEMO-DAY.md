# P3 demo day — run, download, forget, reload (15 minutes)

This script demonstrates policy isolation and **client-side durability** with deterministic
fake specialists. It spends `$0`, needs no API key, and does not evaluate model quality.

## 0–3 minutes — public edge + warm run

Open <https://pax-orchestration.vercel.app>. Submit the prefilled task. Point out Writer-owned
result, bounded counters, logical offsets, and the Replay panel.

```bash
curl -sS https://pax-orchestration.vercel.app/health
curl -sS -X POST https://pax-orchestration.vercel.app/v1/tasks \
  -H "content-type: application/json" \
  -H "x-request-id: demo-day-run" \
  -d '{"task":"Audit retrieval risk","seed":41,"budget":{"max_handoffs":8}}' \
  | tee /tmp/demo-day-task.json
curl -sS -D - -o /tmp/demo-day-trace.json \
  https://pax-orchestration.vercel.app/v1/runs/demo-day-run/trace
```

While the instance is warm, also click **Download export JSON** in the UI (or save
`/v1/runs/{id}/trace`). That file is the durable artifact.

## 3–7 minutes — prove the hole, then recover offline

Refresh until `GET /v1/runs/demo-day-run` returns `404` (recycle, another isolate, or FIFO
eviction — all honest). Do **not** claim the server still has the run.

```bash
curl -sS -i https://pax-orchestration.vercel.app/v1/runs/demo-day-run
# expect 404 run_not_found after the process forgot

python -m mao.replay /tmp/demo-day-trace.json
# exit 0 · same actor sequence as the warm response
```

On the hosted page, use **Load trace JSON** and choose the downloaded file. The Replay panel
and ordered timeline render with **no server round-trip after load**. Timeline actors match
the warm GET.

## 7–11 minutes — clone free path + concurrent isolation

```bash
git clone https://github.com/pabloalvarez99/multi-agent-orchestration.git
cd multi-agent-orchestration
python -m venv .venv
# Windows: .venv\Scripts\activate
python -m pip install -e ".[dev]"
pytest -q tests/test_replay.py tests/test_concurrency.py tests/test_http_p2.py
```

Show: two concurrent fake tasks do not swap Writer text; recycle-equivalent
(`RunStore.clear`) still allows file replay; HTTP Research unset → `capability_missing`,
5xx → degraded without Writer.

## 11–15 minutes — chaos scorecard + close

```bash
python -m mao.evals.run --pretty
```

Chaos cases: Critic crash → non-empty `degraded`; two rejects → Writer still finishes;
`max_handoffs` typed stop; Research cannot impersonate Writer.

Close with [ADR-0005](docs/adr/0005-versioned-process-local-traces.md) (process-local FIFO)
and [ADR-0006](docs/adr/0006-client-side-file-replay.md) (file is the durable copy, not KV).
Interview claim: coordination policy is replayable after the server forgets — without
pretending Vercel is a database.
