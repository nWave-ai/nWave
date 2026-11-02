# nw-troubleshooter

Use for investigating system failures, recurring issues, unexpected behaviors, or complex bugs requiring systematic root cause analysis with evidence-based investigation.

**Wave:** Other
**Model:** inherit
**Max turns:** 45
**Tools:** Read, Write, Edit, Glob, Grep, Bash, Task, WebSearch, WebFetch, SendMessage

## Commands

- [`/nw-root-why`](../commands/index.md)

## Preloaded skills

- [nw-code-analysis-port](../skills/nw-code-analysis-port.md) — KNOWLEDGE — resolve code facts (who-calls-X / where-defined-or-read / call-graph / change-scope / file-atoms) through the vendor-neutral CLI `code-fact`, degrading LOUD through bundled adapters (AST, TextSearch). Trigger: any time an agent designs, writes, analyzes, or reviews code or tests and needs a structural code fact.
- [nw-five-whys-methodology](../skills/nw-five-whys-methodology.md) — Toyota 5 Whys methodology with multi-causal branching, evidence requirements, and validation techniques
- [nw-investigation-techniques](../skills/nw-investigation-techniques.md) — Evidence collection methods, problem categorization, analysis techniques, and solution design patterns
- [nw-post-mortem-framework](../skills/nw-post-mortem-framework.md) — Blameless post-mortem structure, incident timeline reconstruction, response evaluation, and organizational learning
- [nw-typesafe-system-one](../skills/nw-typesafe-system-one.md) — Use Jev System One for every supported, authorized semantic judgment when available: relevance selection, handoff preflight, evidence mapping, finding clustering, and confidence-gated escalation.
