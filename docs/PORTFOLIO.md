# Portfolio series

> Production-shaped AI systems: free-path demos, real architecture, measurable behavior,
> honest scope.

| # | Project | Maturity question | State |
| --- | --- | --- | --- |
| P1 | [production-rag](https://github.com/pabloalvarez99/production-rag) | Can retrieval answer with grounded citations, refuse, and measure itself offline? | **v0.1.0 LIVE** |
| P2 | [agentic-rag-research](https://github.com/pabloalvarez99/agentic-rag-research) | Can one agent use retrieval under budgets with explicit stops and a trace? | **M5 LIVE; release planned** |
| **P3** | **multi-agent-orchestration** | Can specialists hand work off under shared policy, isolation, and budgets? | **M2 library LIVE; HTTP health-only** |
| P4 | RepoMind | Can code answers cite stable `path:line` evidence? | **PLANNED; no public implementation** |
| P5 | AI Platform | Can the services be operated behind auth, limits, and aggregate health? | **PLANNED** |

P3 begins where P2 deliberately stops. P2 owns a single bounded research loop; P3 studies
coordination policy across Research, Critic, and Writer without copying P2's planner or P1's
retrieval stack. The optional dependency direction is P3 → P2 → P1, and every link must remain
off by default so each repository still clones and tests for free.

The [architecture](architecture.md) describes the target. [SHIP.md](SHIP.md) is the truth
about what is runnable now.
