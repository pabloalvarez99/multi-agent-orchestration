# ADR-0002: Only Writer may produce final user-facing text

- Status: Accepted
- Date: 2026-08-13

## Context

Research notes and criticism are intermediate artifacts. If any specialist can return a
final-looking string, the API can accidentally expose unreviewed evidence, internal concerns,
or contradictory voices.

## Decision

Represent agent output as a discriminated union. Research and Critic may return only handoff
variants. The final-answer variant requires the literal author `writer`; the orchestrator
validates that invariant before completing a task.

Writer may summarize only evidence accepted by Critic. It cannot invoke tools, introduce new
facts, or silently turn a failure memo into an answer.

## Consequences

- Final formatting, evidence validation, and future redaction have one enforcement point.
- Tests can make Research or Critic attempt a final and prove it is rejected.
- Writer becomes a required availability dependency for a normal success.
- A Writer failure must produce a typed degraded outcome, never expose an intermediate memo.

## Alternatives considered

- **Any agent can answer:** fewer transitions, but no review or provenance guarantee.
- **Orchestrator writes the answer:** collapses policy and content authority into one role.
- **Critic edits and publishes:** couples approval to authorship and weakens separation of
  duties.
