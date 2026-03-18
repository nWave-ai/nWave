---
name: nw-research-methodology
description: Research output templates, distillation workflow, and quality standards for evidence-driven research
disable-model-invocation: true
---

# Research Methodology

## Research Output Template

Use for all research documents in `docs/research/`.

```markdown
# Research: {Topic}

**Date**: {ISO-8601} | **Researcher**: nw-researcher (Nova) | **Confidence**: {High/Medium/Low} | **Sources**: {count}

## Executive Summary
{2-3 paragraph overview of key findings, main insights, and overall conclusion}

## Research Methodology
**Search Strategy**: {how sources were found}
**Source Selection**: Types: {academic/official/industry/technical_docs} | Reputation: {high/medium-high min} | Verification: {cross-referencing approach}
**Quality Standards**: Target 3 sources/claim (min 1 authoritative) | All major claims cross-referenced | Avg reputation: {0.0-1.0}

## Findings

### Finding 1: {Descriptive Title}
**Evidence**: "{Direct quote or specific data point}"
**Source**: [{Source Name}]({URL}) - Accessed {YYYY-MM-DD}
**Confidence**: {High/Medium/Low}
**Verification**: [{Source 2}]({URL2}), [{Source 3}]({URL3})
**Analysis**: {Brief interpretation or context}

{Repeat Finding structure as needed}

## Source Analysis
| Source | Domain | Reputation | Type | Access Date | Cross-verified |
|--------|--------|------------|------|-------------|----------------|
| {name} | {domain} | {High/Medium-High/Medium} | {academic/official/industry/technical} | {YYYY-MM-DD} | {Y/N} |

Reputation: High: {count} ({%}) | Medium-high: {count} ({%}) | Avg: {0.0-1.0}

## Knowledge Gaps
### Gap 1: {Description}
**Issue**: {missing/unclear info} | **Attempted**: {sources searched} | **Recommendation**: {how to address}

## Conflicting Information (if applicable)
### Conflict 1: {Topic}
**Position A**: {Statement} — Source: [{Name}]({URL}), Reputation: {score}, Evidence: {quote}
**Position B**: {Contradictory statement} — Source: [{Name}]({URL}), Reputation: {score}, Evidence: {quote}
**Assessment**: {Which source more authoritative and why}

## Recommendations for Further Research
1. {Specific recommendation with rationale}

## Full Citations
[1] {Author}. "{Title}". {Publication}. {Date}. {URL}. Accessed {YYYY-MM-DD}.

## Research Metadata
Duration: {X min} | Examined: {count} | Cited: {count} | Cross-refs: {count} | Confidence: High {%}, Medium {%}, Low {%} | Output: docs/research/{filename}
```

## Skill Distillation Workflow

When creating a skill (via `*create-skill` or `skill_for` specified):

### Phase 1: Research
Execute comprehensive research, create full doc in `docs/research/{category}/{topic}-comprehensive-research.md`, complete quality gates.

### Phase 2: Distillation
1. Read comprehensive research
2. Transform: academic -> practitioner-focused
3. Preserve 100% essential concepts (no lossy compression)
4. Remove: verbose explanations, extensive examples, redundant cross-refs
5. Keep: core concepts, practical tools, methodologies, decision heuristics
6. Make self-contained (no external refs) | Target <1000 tokens/file
7. Write to `~/.claude/skills/nw/{agent-name}/{topic}-methodology.md`

### Phase 3: Validation
Verify all essential concepts present | Confirm practitioner focus | Check self-containment

## Quality Standards

### Per-Claim Requirements (Adaptive to Turn Budget)

Source requirements adapt to available turn budget:
- **Ideal**: 3+ independent sources per major claim
- **Acceptable**: 2 credible sources when budget is constrained
- **Minimum**: 1 authoritative source (official docs, RFC, specification) with explicit confidence note
- **Never**: 0 sources -- unsourced claims must be flagged as "[unverified]"

When budget runs low, prioritize BREADTH (cover all claims with minimum sources) over DEPTH (exhaust sources for one claim while ignoring others).

Additional requirements:
- Each source validated against trusted source config from prompt context
- Cross-reference status documented per finding

### Confidence Ratings
- **High**: 3+ high-reputation sources agree, no contradictions
- **Medium**: 2+ agree, minor contradictions or some medium-trust
- **Low**: single source or significant contradictions

### Quality Gates (before finalizing)
1. Every major claim has citations (3+ ideal, 2 acceptable, 1 authoritative minimum) | 2. All sources from trusted domains
3. All findings evidence-backed | 4. Knowledge gaps documented | 5. Output in allowed directories
6. Claims with fewer than 3 sources have confidence rating adjusted accordingly
