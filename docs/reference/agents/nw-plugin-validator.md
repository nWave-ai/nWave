# nw-plugin-validator

Use to validate Claude Code plugin structure and schema during DISTILL/DELIVER verification when deliverable_type is `plugin`. Validates plugin manifest, directory layout, hook/command/agent registration, and Claude Code plugin schema compliance. No existing agent knows the plugin schema. Runs on Haiku for cost efficiency.

**Wave:** Other
**Model:** haiku
**Max turns:** 20
**Tools:** Read, Glob, Grep

## Skills

- [nw-agent-creation-workflow](../skills/nw-agent-creation-workflow.md) — Detailed 5-phase workflow for creating agents - from requirements analysis through validation and iterative refinement
