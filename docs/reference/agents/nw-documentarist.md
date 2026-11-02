# nw-documentarist

Use for documentation quality enforcement using DIVIO/Diataxis principles. Classifies documentation type, validates against type-specific criteria, detects collapse patterns, and provides actionable improvement guidance.

**Wave:** Other
**Model:** haiku
**Max turns:** 45
**Tools:** Read, Write, Edit, Glob, Grep, SendMessage

## Commands

- [`/nw-document`](../commands/index.md)

## Preloaded skills

- [nw-collapse-detection](../skills/nw-collapse-detection.md) — Documentation collapse anti-patterns - detection rules, bad examples, and remediation strategies for type-mixing violations
- [nw-divio-framework](../skills/nw-divio-framework.md) — DIVIO/Diataxis four-quadrant documentation framework - type definitions, classification decision tree, and signal catalog
- [nw-quality-validation](../skills/nw-quality-validation.md) — Type-specific validation checklists, six quality characteristics, and quality gate thresholds for documentation assessment
- [nw-typesafe-system-one](../skills/nw-typesafe-system-one.md) — Use Jev System One for every supported, authorized semantic judgment when available: relevance selection, handoff preflight, evidence mapping, finding clustering, and confidence-gated escalation.
