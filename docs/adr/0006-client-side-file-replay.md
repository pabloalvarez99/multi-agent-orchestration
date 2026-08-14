# ADR-0006: Client-side file replay instead of Vercel KV / Postgres this week

Status: **Accepted**

## Context

Schema-1 traces already exist, and `GET /v1/runs/{id}` is useful while a serverless
instance is warm. A hiring manager can still break the story in under a minute: recycle
the function (or land on another isolate) and the same run ID returns `404`. That is
honest process-local state, not a fake database.

Week 2 needs the demo to survive “the server forgot” without inventing durable server
storage or lying about multi-instance retention.

## Decision

- Keep process-local FIFO retention exactly as ADR-0005 defines it.
- Add **client-side durability**: download a schema-1 export while the run is retained,
  then reload the timeline from that file in the browser or via
  `python -m mao.replay path.json`.
- Do **not** introduce Vercel KV, Postgres, Redis, S3, or any other shared store in this
  release.
- File load never POSTs the file to the server. Invalid documents fail in the browser or
  as a typed CLI error (exit 2), never as an HTTP 500 from an upload endpoint.

## Options considered

| Option | Why not this week |
|--------|-------------------|
| **Vercel KV / Upstash Redis** | Adds a paid or free-tier external dependency, secrets, and a retention policy the free path does not need. It also invites a durability claim that outruns the rest of the portfolio series. |
| **Postgres / Neon / Supabase** | Same cost and secret surface, plus schema migration and multi-tenant access control for what is still a demo of *coordination policy*, not audit storage. |
| **Blob / object storage of every run** | Durable but still a server claim; requires write path, auth, and lifecycle rules. Overkill for proving actor sequences. |
| **Pretend the FIFO is enough** | Hiring managers recycle once and the story dies. |

Client-side file replay is the narrow fix: the artifact that already exists (the versioned
trace) becomes portable. The server remains forgetful; the **file** is the durable copy.

## Consequences

- DEMO-DAY can show: run → download → refresh (404) → load file → identical actor sequence.
- SHIP and CASESTUDY keep the recycle caveat; they gain an explicit offline recovery path.
- A later ADR may introduce append-only audit storage with access control when the product
  needs multi-instance lookup. That is a different problem than “prove the policy timeline
  after the process dies.”
