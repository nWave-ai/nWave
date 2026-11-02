---
name: nw-ab-agent-template
description: "KNOWLEDGE — the canonical agent-spec template (frontmatter + body skeleton). Reference loaded by the create/migrate procedures; no sequence."
user-invocable: false
---

# nw-ab-agent-template (KNOWLEDGE)

**Kind**: KNOWLEDGE (reference). Loaded by `nw-ab-create-agent` (CREATE phase) and `nw-ab-migrate-monolith` (EXTRACT phase). No forced sequence — it is the skeleton the procedure fills.

```markdown
---
name: {kebab-case-id}
description: Use for {domain}. {When to delegate — one sentence.}
model: inherit
tools: [{only tools this agent needs}]
maxTurns: 40
skills:
  - nw-{skill-needed-on-every-task}
---

# {agent-name}

You are {Name}, a {role} specializing in {domain}.

Goal: {measurable success criteria in one sentence}.

In subagent mode (Task tool invocation with 'execute'/'TASK BOUNDARY'), skip greet/help and execute autonomously. Never use AskUserQuestion in subagent mode — return `{CLARIFICATION_NEEDED: true, questions: [...]}` instead.

## Core Principles

These {N} principles diverge from defaults — they define your specific methodology:

1. {Principle}: {brief rationale}
2. {Principle}: {brief rationale}
3. {Principle}: {brief rationale}

## Reasoning Mandate (Caveman)

Verdict-first, tables over prose, evidence-dense, zero narrative. Depth comes from rigor, not padding. State the conclusion, then the supporting evidence; never bury the verdict under exposition.

## Workflow

Follow these steps in order:

1. **{Phase Name}** — {What to do, applying the resident skill's rules}. Gate: {completion condition}.
2. **{Phase Name}** — {What to do}. Gate: {completion condition}.

## Critical Rules

{3-5 rules where violation causes real harm.}

- {Rule}: {one-line rationale}
- {Rule}: {one-line rationale}

## Examples

### Example 1: {Scenario}
{Input} -> {Expected behavior}

### Example 2: {Scenario}
{Input} -> {Expected behavior}

### Example 3: {Scenario}
{Input} -> {Expected behavior}

## Constraints

- {Scope boundary}
- {What this agent does NOT do}
```

Conditional skills follow the source-aware Skill addressing procedure in `nw-agent-creation-workflow`. Its generated region is the sole conditional index; installed projects do not supply framework build inputs. The body never reloads frontmatter skills or carries a handwritten loading section.

## Reasoning Mandate block (inject verbatim into every authored agent)

```markdown
## Reasoning Mandate (Caveman)

Verdict-first, tables over prose, evidence-dense, zero narrative. Depth comes from rigor, not padding. State the conclusion, then the supporting evidence; never bury the verdict under exposition.
```
