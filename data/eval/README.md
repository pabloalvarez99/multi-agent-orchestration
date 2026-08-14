# Golden orchestration tasks

`tasks.jsonl` contains 12 deterministic scenarios for the credential-free specialist team.
`research_boundaries.jsonl` adds two configuration-only cases for the optional P2 boundary.
`chaos.jsonl` contains **≥40** fault-injection contracts with **easy / medium / hard** difficulty
and family tags for isolation (not answer quality).
The evaluation runner executes the same `run_task()` path used by the API and CLI; it makes no
network or provider call and reports `provider="fake"` with `billed_usd=0.0`. Boundary cases
construct specialists but never call `handle`, and report `network_calls=0`: fake remains
local, while HTTP without a URL yields `capability_missing`.

Run it from the repository root:

```bash
python -m mao.evals.run --pretty
```

Exit code `0` means every declared expectation passed, `1` means at least one behavioral
expectation failed, and `2` means the dataset could not be loaded or validated.

## Coverage

| Category | Tasks | Contract exercised |
| --- | ---: | --- |
| `happy_path` | 6 | Research → Critic → Writer completes within three handoffs. |
| `critic_retry` | 3 | Review terms trigger exactly one bounded Critic → Research retry. |
| `budget_stop` | 3 | A narrow global budget stops before Writer and reports `budget_exhausted`. |

## Chaos coverage

| Family | Intent |
| --- | --- |
| `specialist_crash` | Research/Critic/Writer faults → non-empty `degraded` |
| `writer_impersonation` | Non-Writer `FinalAnswer` → `policy_violation` |
| `illegal_handoff` | Research→Writer edge blocked |
| `critic_reject_loop` | Bounded rejects, retry ceiling |
| `max_handoffs` | Global budget typed stop |
| `writer_crash_after_accept` | No intermediate memo promotion |
| `concurrent_isolation` | Distinct tokens do not swap under threads |
| `policy_budget_matrix` | Loadable restrictive policy changes happy path |

Difficulty predicates live in `assert_chaos_difficulty_predicates`: CI fails if all **new** rows
are easy, or if medium/hard slices collapse into weak single-fault clones.

These are deterministic fake faults. They evaluate control-plane behavior, not answer quality.

## Policy characterization

Default policy file: `policies/default-v0.3-characterization.json`.
Restrictive fixture: `policies/fixtures/forbid-research-to-writer.json`.

## Metrics and limits

The JSON scorecard reports task pass rate, mean handoffs, retry-task rate, Writer completion
rate, and terminal-status counts, plus per-task mismatches. Isolation simulation metrics
(`swap_rate`, `writer_only_violations`) are published under `docs/assets/isolation-sim.*` and
are labeled **isolation/plumbing**, not quality.

When editing a task, run both:

```bash
python -m mao.evals.run --pretty
python -m pytest -q tests/evals
```
