# ADR-0003: Make degraded completion explicit and evidence-preserving

- Status: Accepted
- Date: 2026-08-13

## Context

Specialists and optional dependencies fail independently. Treating a missing specialist as
an empty successful response hides the failure; failing every task discards useful evidence
that may be safe to return as a labelled partial.

## Decision

Add a closed-set `degraded` terminal status. The M2 result requires:

- the failed participant or dependency;
- a typed reason;
- which intended checks or transformations did not run;
- the handoff/retry accounting completed before failure.

It cannot be mistaken for a fully reviewed final answer. Missing Critic approval is not
silently accepted, and a Writer failure cannot promote an intermediate memo to final text.
Preserving partial evidence as a structured field and recording a terminal timeline event are
follow-up milestones, not properties of the M2 contract.

## Consequences

- Callers can distinguish an explained degraded result from normal success and budget expiry.
- Failure demos remain inspectable instead of becoming exception screenshots.
- Terminal policy is more complex and needs golden cases for each specialist failure.
- Availability does not outrank the Writer-only and evidence-approval invariants.

## Alternatives considered

- **Fail every specialist error:** simple but loses safe partial evidence.
- **Always continue with the remaining agents:** higher apparent availability, but silently
  changes the workflow contract.
- **Retry indefinitely:** hides provider instability and violates the global budget.
