# Portfolio series

> Production-shaped AI systems: free-path demos, real architecture, measurable behavior,
> honest scope.

| # | Project | Maturity question | State |
| --- | --- | --- | --- |
| P1 | [production-rag v0.1.0](https://github.com/pabloalvarez99/production-rag/releases/tag/v0.1.0) | Can retrieval answer with grounded citations, refuse, and measure itself offline? | **v0.1.0 LIVE** |
| P2 | [agentic-rag-research v0.1.0](https://github.com/pabloalvarez99/agentic-rag-research/releases/tag/v0.1.0) | Can one agent use retrieval under budgets with explicit stops and a trace? | **v0.1.0 / M6 LIVE** |
| **P3** | [**multi-agent-orchestration v0.1.0**](https://github.com/pabloalvarez99/multi-agent-orchestration/releases/tag/v0.1.0) | Can specialists hand work off under shared policy, isolation, and budgets? | **v0.1.0 LIVE** |
| P4 | [RepoMind](https://github.com/pabloalvarez99/repomind) | Can code answers cite stable `path:line` evidence? | **M5 LIVE; JSON CLI + 14-case fixture eval** |
| P5 | AI Platform | Can the services be operated behind auth, limits, and aggregate health? | **PLANNED** |

P3 begins where P2 deliberately stops. P2 owns a single bounded research loop; P3 studies
coordination policy across Research, Critic, and Writer without copying P2's planner or P1's
retrieval stack. The optional dependency direction is P3 → P2 → P1, and every link must remain
off by default so each repository still clones and tests for free.

The [architecture](architecture.md) describes the target. [SHIP.md](SHIP.md) is the truth
about what is runnable now.
