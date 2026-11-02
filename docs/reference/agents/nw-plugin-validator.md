# nw-plugin-validator

Use to validate Claude Code plugin structure and schema during DISTILL/DELIVER verification when deliverable_type is `plugin`. Validates plugin manifest, directory layout, hook/command/agent registration, and Claude Code plugin schema compliance. No existing agent knows the plugin schema. Runs on Haiku for cost efficiency.

**Wave:** Other
**Model:** haiku
**Max turns:** 40
**Tools:** Read, Glob, Grep, Write, SendMessage

## Preloaded skills

- [nw-typesafe-system-one](../skills/nw-typesafe-system-one.md) — Use Jev System One for every supported, authorized semantic judgment when available: relevance selection, handoff preflight, evidence mapping, finding clustering, and confidence-gated escalation.
