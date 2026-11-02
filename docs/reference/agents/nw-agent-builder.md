# nw-agent-builder

Use when creating new AI agents, validating agent specifications, optimizing requested existing SKILL.md assets, optimizing command definitions, or ensuring compliance with Claude Code best practices. Creates focused, research-validated agents (200-400 lines) with Skills for domain knowledge.

**Wave:** Other
**Model:** inherit
**Max turns:** 40
**Tools:** Read, Write, Edit, Glob, Grep, Task, SendMessage

## Commands

- [`/nw-forge`](../commands/index.md)

## Preloaded skills

- [nw-ab-agent-template](../skills/nw-ab-agent-template.md) — KNOWLEDGE — the canonical agent-spec template (frontmatter + body skeleton). Reference loaded by the create/migrate procedures; no sequence.
- [nw-ab-anti-patterns](../skills/nw-ab-anti-patterns.md) — KNOWLEDGE — agent/skill/command anti-pattern catalog with fixes. Reference scanned by validate-spec; no sequence.
- [nw-ab-critique-dimensions](../skills/nw-ab-critique-dimensions.md) — Review dimensions for validating agent quality - template compliance, safety, testing, and priority validation
- [nw-ab-examples](../skills/nw-ab-examples.md) — KNOWLEDGE — canonical worked examples for agent creation, migration, and command optimization. Reference for the relevant procedures; no sequence.
- [nw-ab-house-style](../skills/nw-ab-house-style.md) — KNOWLEDGE — caveman-native authoring house style + by-construction guarantees (Reasoning Mandate injection, measured-gain compression). Reference for create/migrate; no sequence.
- [nw-ab-validation-checklist](../skills/nw-ab-validation-checklist.md) — KNOWLEDGE (data) — the agent-spec validation checklist. The item definitions the validate-spec procedure RUNS against. No sequence of its own.
- [nw-agent-creation-workflow](../skills/nw-agent-creation-workflow.md) — Detailed 5-phase workflow for creating agents - from requirements analysis through validation and iterative refinement
- [nw-agent-testing](../skills/nw-agent-testing.md) — 5-layer testing approach for agent validation including adversarial testing, security validation, and prompt injection resistance
- [nw-cross-cutting-invariants](../skills/nw-cross-cutting-invariants.md) — Cross-cutting normative invariants — routing core for the software/model boundary doctrine, gate/construction principles and on-demand knowledge lenses. Cite clause ids; never re-declare.
- [nw-design-patterns](../skills/nw-design-patterns.md) — 7 agentic design patterns with decision tree for choosing the right pattern for each agent type
- [nw-typesafe-system-one](../skills/nw-typesafe-system-one.md) — Use Jev System One for every supported, authorized semantic judgment when available: relevance selection, handoff preflight, evidence mapping, finding clustering, and confidence-gated escalation.
