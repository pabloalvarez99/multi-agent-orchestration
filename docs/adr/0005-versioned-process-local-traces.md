# ADR-0005: Version replay traces and retain them process-locally

Status: **Accepted**

## Context

An ordered list is useful while reading one response, but it is not yet a replay contract.
Consumers need to know which schema they received, which run produced it, and whether timing
fields are safe to compare. The public demo also needs a retrieval window without pretending
that a serverless Python process is durable storage.

## Decision

- Every trace envelope declares `trace_schema: 1`.
- Every event carries `event`, `ts_offset_ms`, `actor`, and `payload`; `sequence` remains an
  explicit contiguous index.
- `ts_offset_ms` is a logical offset from run start: event zero is `0`, event one is `1`, and
  so on. It expresses replay order, not wall-clock latency. Process timings remain separate
  debug data and are never used in event equality.
- The task request records a bounded integer `seed`. The credential-free specialists do not
  currently sample, but recording the seed closes the contract for later seeded providers.
- The service retains the last 128 immutable runs in a locked FIFO map. `GET /v1/runs/{id}`
  returns metadata/output and `GET /v1/runs/{id}/trace` returns the versioned event envelope.
- The store keeps a task SHA-256 fingerprint, not a second copy of the submitted task. Writer
  output may repeat user input because it is the user-facing result.

## Why offsets instead of timestamps

Wall-clock timestamps leak deployment timing into otherwise identical fake runs and make
goldens flaky. Logical offsets make same task + seed exactly comparable while keeping the
contract ready for a future replay clock. Operational latency is a different question and is
already represented by specialist timings outside the trace.

## Why this is not a database

The FIFO has no disk, replication, cross-instance coordination, recovery, or retention SLA.
Vercel recycle and ordinary eviction both return `404 run_not_found`. That limitation is
visible in the UI and SHIP rather than hidden behind a durability claim.

## Consequences

- Lawyers, reviewers, and tests can replay a named, versioned sequence without normalizing
  wall time.
- Public schemas can evolve by adding a new trace version rather than silently changing v1.
- Run lookup is useful for a demo and local diagnosis, but production audit retention would
  require an external append-only store with access controls and a deletion policy.
