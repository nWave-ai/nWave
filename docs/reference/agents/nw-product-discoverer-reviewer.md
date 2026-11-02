# nw-product-discoverer-reviewer

Use as peer reviewer for product-discoverer outputs -- validates evidence quality, sample sizes, decision gate compliance, bias detection, and discovery anti-patterns. Runs on Haiku for cost efficiency.

**Wave:** Other
**Model:** haiku
**Max turns:** 40
**Tools:** Read, Glob, Grep, Task, Bash, Write, SendMessage

## Preloaded skills

- [nw-pdr-review-criteria](../skills/nw-pdr-review-criteria.md) — Evidence quality validation and decision gate criteria for product discovery reviews
- [nw-typesafe-system-one](../skills/nw-typesafe-system-one.md) — Use Jev System One for every supported, authorized semantic judgment when available: relevance selection, handoff preflight, evidence mapping, finding clustering, and confidence-gated escalation.
