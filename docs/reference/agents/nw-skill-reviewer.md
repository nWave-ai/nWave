# nw-skill-reviewer

Use to review SKILL.md quality during DISTILL/DELIVER verification when deliverable_type is `plugin` or `skill`. Validates skill structure, scope discipline, frontmatter, and domain-knowledge quality. Thin reviewer — reuses nw-agent-builder skill assets. Runs on Haiku for cost efficiency.

**Wave:** Other
**Model:** haiku
**Max turns:** 20
**Tools:** Read, Glob, Grep

## Skills

- [nw-ab-critique-dimensions](../skills/nw-ab-critique-dimensions.md) — Review dimensions for validating agent quality - template compliance, safety, testing, and priority validation
- [nw-agent-creation-workflow](../skills/nw-agent-creation-workflow.md) — Detailed 5-phase workflow for creating agents - from requirements analysis through validation and iterative refinement
