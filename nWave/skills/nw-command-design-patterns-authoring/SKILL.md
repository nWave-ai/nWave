---
name: nw-command-design-patterns-authoring
description: The v2.8+ new-command installation contract - which three files to produce and their frontmatter when creating a brand-new command
user-invocable: false
disable-model-invocation: true
---

# New-Command Authoring & Installation Format (KNOWLEDGE)

**Kind**: KNOWLEDGE (reference). Composed by `nw-command-design-patterns` core. Fires when: a brand-NEW command is being created and the question is "which files do I produce, in what format, where" (the v2.8+ install contract). Distinct from classification (sizing an existing command) and reduction (trimming a bloated one). No forced sequence.

## Command Installation Format (v2.8+)

Since v2.8.0, commands are installed as **skills**, not as separate command files. The installer reads from `nWave/skills/nw-{command-name}/SKILL.md`, NOT from `nWave/tasks/nw/{command-name}.md`. The legacy `tasks/nw/*.md` path is still supported but is NOT auto-installed.

**When creating a new command, produce THREE files:**

1. **`nWave/skills/nw-{name}/SKILL.md`** — the installable command skill. Frontmatter MUST include:
   ```yaml
   ---
   name: nw-{name}
   description: "One-line description for slash command menu"
   user-invocable: true
   argument-hint: "[args] - Example: \"example usage\""
   ---
   ```
   Body: the full command definition (same content as the declarative template).

2. **`nWave/tasks/nw/{name}.md`** — legacy task file (kept for backward compat + reference). Same content, simpler frontmatter (just `description` + `argument-hint`).

3. **`nWave/skills/nw-{name}-methodology/SKILL.md`** (optional) — deep methodology knowledge for the agent. Frontmatter:
   ```yaml
   ---
   name: nw-{name}-methodology
   description: "Methodology knowledge for {name}"
   user-invocable: false
   disable-model-invocation: true
   ---
   ```

**The skill file (`nWave/skills/nw-{name}/SKILL.md`) is the PRIMARY deliverable.** Without it, the command won't appear in the `/nw-` menu after installation. The task file is secondary.

Also update `nWave/framework-catalog.yaml` with the command entry under the appropriate wave section.
