# P3 demo day — policy → chaos → pack → recycle → replay (25 minutes)

This script demonstrates **policy as data**, isolation chaos, and **client-side durability**
with deterministic fake specialists. It spends `$0`, needs no API key, and does not evaluate
model quality. Host only: <https://pax-orchestration.vercel.app> (project `pax-orchestration`,
never `pax-mao`).

## 0–3 min — series placement

Open the portfolio series narrative if needed, then land on P3: coordination policy, not three
prompts in a trench coat. State the staff question you will answer:

> Is the policy data, or is it if-statements?

Point at v1.0 surfaces: loadable policy, chaos n≥40, isolation sim n=1000, trace pack.

## 3–8 min — policy document (data)

1. Open <https://pax-orchestration.vercel.app/ui/policy> (or localhost `/ui/policy`).
2. Show `policy_id=default-v0.3-characterization`, max handoffs/retries, allowed edges, and the
   **policy hash**.
3. Mention ADR-0007: algorithm stays in code; configuration is a committed JSON document that
   characterizes v0.3 behavior. A fixture that removes the Critic→Writer edge changes happy path
   to typed `policy_violation`.

## 8–14 min — happy path + chaos

1. Run the prefilled compare task; show Writer-owned `done`, ordered trace, `policy_id` /
   `policy_hash` on `task_started`.
2. Run or cite a chaos story: Critic crash → non-empty `degraded` / `specialist_error`; or
   Research impersonation → `policy_violation` with `result_author=null`.
3. Scorecard: `python -m mao.evals.run --pretty` (local) — chaos n≥40 with easy/medium/hard;
   free path `billed_usd=0.0`.

## 14–18 min — trace pack (lawyer-unzippable)

```bash
python -m mao.pack build --task "Compare hybrid vs dense retrieval" --seed 41 \
  --out /tmp/mao-pack.json
python -m mao.pack verify /tmp/mao-pack.json
# or unzip docs/assets/sample-trace-pack.zip
```

Show `manifest.policy_hash`, task, seed, result, schema-1 trace. On the console, **Load trace
JSON** with the pack file (browser normalizes `pack.trace`).

## 18–22 min — recycle honesty + file replay

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

While warm: **Download export JSON**. After recycle / isolate switch, `GET /v1/runs/{id}` is
`404` — that is honest process-local FIFO, not a database.

```bash
python -m mao.replay /tmp/demo-day-trace.json   # exit 0
```

UI **Load trace JSON** renders without posting the file to the server (ADR-0006).

## 22–25 min — isolation sim + PLANNED

Open `docs/assets/isolation-sim.html` (or JSON): **n=1000**, `swap_rate=0`,
`writer_only_violations=0`, label **isolation/plumbing — not multi-agent quality**.

Load note: `docs/assets/load.json` p50/p95 for `POST /v1/tasks` fake on a **single isolate** —
not multi-region capacity planning.

Close with PLANNED: no Redis, no real LLM specialists as default, no multi-instance durable
server store, no quality claim from fakes. Host remains **pax-orchestration**.

## Optional local free path

```bash
pip install -e ".[dev]"
uvicorn mao.main:app --port 8000
# open http://127.0.0.1:8000/ and /ui/policy
```
