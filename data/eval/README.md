# Golden orchestration tasks

`tasks.jsonl` contains 12 deterministic scenarios for the credential-free specialist team.
`research_boundaries.jsonl` adds two configuration-only cases for the optional P2 boundary.
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

The task wording is intentionally direct professional English. Retry cases retain the words
`audit`, `validate`, or `verify` because those terms are part of the documented deterministic
fake policy, not hidden labels added after observing a run.

## JSONL schema

| Field | Meaning |
| --- | --- |
| `id` | Stable unique scenario id. |
| `category` | `happy_path`, `critic_retry`, or `budget_stop`. |
| `task` | Exact task submitted to the orchestrator. |
| `max_handoffs` | Global dispatch ceiling for the case. |
| `expected_status` | Expected `done` or `budget_exhausted` result. |
| `expected_agents` | Ordered participants the run must involve. |
| `expected_handoffs` | Exact handoff count. |
| `expected_retries` | Exact Critic → Research retry count. |

The loader rejects malformed records, unknown fields, duplicate ids, fewer than ten tasks,
and missing required categories. Exact behavioral expectations are checked by the runner,
not treated as dataset-integrity rules.

## Metrics and limits

The JSON scorecard reports task pass rate, mean handoffs, retry-task rate, Writer completion
rate, and terminal-status counts, plus per-task mismatches. These values measure routing,
budget, ownership, and accounting conformance on fake specialists. They do not measure answer
quality, factuality, specialist diversity, latency, or multi-model uplift.

When editing a task, run both:

```bash
python -m mao.evals.run --pretty
python -m pytest -q tests/evals
```
