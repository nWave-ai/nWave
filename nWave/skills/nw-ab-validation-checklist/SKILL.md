---
name: nw-ab-validation-checklist
description: "KNOWLEDGE (data) — the agent-spec validation checklist. The item definitions the validate-spec procedure RUNS against. No sequence of its own."
user-invocable: false
---

# nw-ab-validation-checklist (KNOWLEDGE / data)

**Kind**: KNOWLEDGE (data). The canonical checklist: every item it defines, and only those. `nw-ab-validate-spec` runs all of them in order. This skill holds the definitions (SSOT), not the run-sequence; other assets name the checklist, never its item count.

| # | Item | Gate |
|---|------|------|
| 1 | Frontmatter | name, description, model, tools, maxTurns, skills present |
| 2 | Line Count | `wc -l` under 400; domain knowledge in skills |
| 3 | Divergence Only | zero instructions restating Claude defaults |
| 4 | Least Privilege | tools list minimal; no Write/Edit for reviewers |
| 5 | Safety by construction (GDP-0) | tool-surface frontmatter + typed grammar first, not prose; a hook only last-resort with a recorded reason |
| 6 | Affirmative Phrasing | zero negatively-phrased rules |
| 7 | Terminology | one term per concept |
| 8 | Description Quality | description states WHEN to delegate |
| 9 | Success Criteria Format | numbered/checkbox list, not prose |
| 10 | Caveman House Style | dry/declarative, tables + compact lists, lean body |
| 11 | Reasoning Mandate Present | `## Reasoning Mandate` section present |
| 12 | One Job, One Trigger | one job + one trigger; KNOWLEDGE vs PROCEDURE classified; PROCEDURE states trigger + sequence + composition; zero multi-job parameterized switches; existing command + agent NAMES preserved (no rename/proliferation; new command is the rare `/nw-*` exception) |
| 13 | Skill Addressing | apply the source-aware Skill addressing procedure in `nw-agent-creation-workflow`; always-needed skills preload once from frontmatter, conditional skills have precise reachable triggers in one generated index; installed-only source limitations remain explicit, not orphan findings or invented build inputs |
