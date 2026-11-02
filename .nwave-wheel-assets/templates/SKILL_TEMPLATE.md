# nWave Skill Template

Version: 1.0 (2026-02-28)
Extracted from analysis of 98 production skill files across 18 skill directories.

## What is a Skill?

A skill file contains deep domain knowledge that an agent loads on-demand during specific
workflow phases. Skills are NOT workflow instructions -- they are reference material that
informs how an agent executes its workflow.

**Skills encode**: methodologies, frameworks, patterns, criteria, decision heuristics,
evaluation rubrics, domain-specific knowledge.

**Skills do NOT contain**: workflow steps, agent configuration, tool instructions,
persona definitions, or frontmatter configuration for agents.

## Frontmatter Schema

```yaml
---
name: {skill-name}                        # REQUIRED. kebab-case, matches filename
description: {one-line purpose}           # REQUIRED. What knowledge this skill provides
agent: nw-{agent-name}                    # OPTIONAL. Cross-ref: owner agent (for shared skills)
---
```

Standard fields: `name` and `description` (required). The `agent` field is optional — used when a skill
is cross-referenced by another agent to document ownership (e.g., a reviewer loading a specialist's skill).
All content goes in the markdown body, not in frontmatter.

## Naming Conventions

| Pattern | Examples | When |
|---------|----------|------|
| `{methodology}-methodology` | `tdd-methodology`, `research-methodology`, `leanux-methodology` | Core methodology skill |
| `{domain}-{topic}` | `architecture-patterns`, `bdd-requirements`, `source-verification` | Domain knowledge |
| `{action}-{scope}` | `collapse-detection`, `quality-validation`, `opportunity-mapping` | Detection/validation skill |
| `critique-dimensions` | `critique-dimensions` | Review criteria (used by reviewers) |
| `review-criteria` | `review-criteria` | Review standards (used by reviewers) |
| `review-workflow` | `review-workflow` | Review process (used by reviewers) |

### File Location

Skills are stored in: `nWave/skills/{agent-name}/{skill-name}.md`

At install time, they are deployed to: `~/.claude/skills/nw/{agent-name}/{skill-name}.md`

## Body Template

```markdown
---
name: {skill-name}
description: {One-line description of what knowledge this provides}
---

# {Skill Title}

## {Primary Section}

{Core knowledge content. Use concise, practitioner-focused language.}

### {Subsection}

{Detailed knowledge. Tables, decision trees, criteria lists preferred over prose.}

## {Second Section}

{Additional knowledge domain.}

### {Pattern / Framework / Methodology}

{Structured content: numbered steps, tables, code examples.}

## {Practical Application}

{Decision heuristics, evaluation criteria, templates.}
```

---

## Content Guidelines

### Depth and Focus

Skills should be deep, not broad. A skill covers one coherent knowledge domain.

| Aspect | Guideline |
|--------|-----------|
| Scope | One methodology, one framework, one domain area |
| Depth | Practitioner-level -- enough to apply, not academic survey |
| Self-contained | No external references -- all needed knowledge inline |
| Token budget | Target under 5000 tokens per skill file |

### Content Types (by Purpose)

| Type | Typical Sections | Examples |
|------|------------------|----------|
| Methodology | Overview, Phases, Decision Points, Validation | `tdd-methodology`, `five-whys-methodology` |
| Patterns | Pattern Catalog, Decision Tree, Examples, Trade-offs | `architecture-patterns`, `data-architecture-patterns` |
| Criteria | Dimensions, Scoring Rubric, Output Format, Thresholds | `critique-dimensions`, `review-criteria` |
| Framework | Principles, Decision Tree, Application Guide, Examples | `divio-framework`, `bdd-methodology` |
| Reference | Catalog, Decision Matrix, Templates | `authoritative-sources`, `test-refactoring-catalog` |

### Formatting Preferences

- **Tables over prose**: Decision matrices, criteria lists, pattern catalogs
- **Code examples**: Short, illustrative (not full implementations)
- **Decision trees**: For methodology selection or classification
- **Templates**: For output formats (YAML, markdown)
- **Pipe-delimited lists**: For related items on one line (`item1|item2|item3`)

---

## Size Guidelines

| Category | Lines (min) | Lines (median) | Lines (max) | Notes |
|----------|-------------|----------------|-------------|-------|
| Review criteria | 40 | 80 | 120 | Dimensions + scoring |
| Methodology | 60 | 100 | 180 | Process + templates |
| Patterns | 80 | 130 | 250 | Catalog + examples |
| Framework | 50 | 100 | 200 | Principles + application |
| Language-specific | 100 | 200 | 350 | FP/PBT per language |

### Extraction Threshold

Extract content from an agent into a skill when:
- Domain knowledge exceeds 50 lines in the agent definition
- Knowledge is reusable across multiple agents
- Knowledge is likely to grow (e.g., pattern catalog)
- Agent definition approaches 400-line limit

### Splitting Threshold

Split a skill into multiple skills when:
- Skill exceeds 300 lines
- Skill covers 2+ clearly separable knowledge domains
- Different workflow phases need different subsets

---

## Skill Directory Inventory

| Agent | Skills | Notes |
|-------|--------|-------|
| software-crafter | 10 | Largest set; TDD, refactoring, hexagonal, PBT |
| functional-software-crafter | 21 | FP principles + PBT per language + TLA+ |
| product-owner | 16 | JTBD, UX patterns, LeanUX, BDD |
| solution-architect | 4 | Architecture patterns, stress analysis, roadmap |
| platform-architect | 7 | CI/CD, infrastructure, deployment, production |
| researcher | 4 | Research methodology, sources, safety |
| troubleshooter | 3 | 5 Whys, investigation, post-mortem |
| acceptance-designer | 3 | BDD, test design mandates, critique |
| documentarist | 3 | DIVIO, collapse detection, quality |
| data-engineer | 4 | Technology selection, query, security, architecture |
| agent-builder | 6 | Creation workflow, patterns, testing, critique |
| product-discoverer | 3 | Discovery, interviewing, opportunity mapping |
| Reviewer directories | 1-3 each | Review criteria, dimensions, output format |

---

## Cross-Reference Pattern

Some reviewer agents load skills from their paired specialist's directory. Document this in the reviewer's frontmatter with comments:

```yaml
skills:
  - tdd-review-enforcement           # reviewer-specific
  - review-dimensions                 # cross-ref: from software-crafter/
  - tdd-methodology                   # cross-ref: from software-crafter/
```

And in the reviewer's Skill Loading section, include the path:

```markdown
**How**: Use the Read tool to load skill files from two directories:
- `~/.claude/skills/nw/{specialist-name}/` -- shared skills
- `~/.claude/skills/nw/{specialist-name}-reviewer/` -- reviewer-specific skills
```

---

## Example: Minimal Skill (Review Criteria)

```markdown
---
name: review-criteria
description: Review dimensions, scoring rubric, and structured output format for {domain} review
---

# Review Criteria

## Review Dimensions

### Dimension 1: {Name}
Score 0-10. Evaluates {what}.
- 9-10: {excellent criteria}
- 7-8: {good criteria}
- 5-6: {acceptable criteria}
- 3-4: {below standard}
- 0-2: {fundamental problems}

### Dimension 2: {Name}
{Same structure}

## Scoring Rubric

| Dimension | Weight | Threshold |
|-----------|--------|-----------|
| {name} | {weight} | {minimum to pass} |

## Output Format

```yaml
review:
  dimensions:
    - name: "{dimension}"
      score: {0-10}
      findings: [{severity, description, evidence, remediation}]
  overall_score: {0-10}
  verdict: "APPROVED|REVISE|REJECTED"
```

## Verdict Decision Matrix

- APPROVED: overall >= 7, no dimension below 5
- REVISE: overall 4-6 or any dimension below 5
- REJECTED: overall <= 3 or any critical blocker
```

## Example: Methodology Skill

```markdown
---
name: five-whys-methodology
description: Toyota 5 Whys methodology with multi-causal branching, evidence requirements, and validation techniques
---

# Five Whys Methodology

## Philosophical Foundation

{Brief origin and core tenets}

## Multi-Causal Investigation

{How to handle multiple root causes}

## WHY Level Definitions

### WHY 1: Symptom Investigation
{What to investigate at this level}

### WHY 2-5: Progressive Deepening
{Each level with evidence requirements}

## Validation and Verification

### Evidence Requirements
{What counts as evidence}

### Backwards Chain Validation
{How to verify root causes}

## Branch Documentation Format

{Template for documenting findings}
```

---

## Anti-Patterns

| Anti-Pattern | Signal | Fix |
|---|---|---|
| Workflow in skill | Step-by-step agent instructions | Move to agent definition; skill has knowledge only |
| Persona in skill | "You are {Name}" | Persona belongs in agent definition |
| Tool instructions | "Use Read tool to..." | Tool usage belongs in agent definition |
| Too broad | Covers 3+ unrelated topics | Split into focused skills |
| Too shallow | Generic advice without practitioner depth | Add decision trees, criteria, templates |
| External references | "See {URL} for details" | Make self-contained; include needed content |
| Duplicate content | Same knowledge in skill and agent | Keep in skill; agent references via Load |
