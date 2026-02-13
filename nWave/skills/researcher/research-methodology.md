---
name: research-methodology
description: Research output templates, distillation workflow, and quality standards for evidence-driven research
---

# Research Methodology

## Research Output Template

Use this template for all research documents written to `docs/research/`.

```markdown
# Research: {Topic}

**Date**: {ISO-8601-timestamp}
**Researcher**: nw-researcher (Nova)
**Overall Confidence**: {High/Medium/Low}
**Sources Consulted**: {count}

## Executive Summary

{2-3 paragraph overview of key findings, main insights, and overall conclusion}

---

## Research Methodology

**Search Strategy**: {description of how sources were found}

**Source Selection Criteria**:
- Source types: {academic, official, industry, technical_docs}
- Reputation threshold: {high/medium-high minimum}
- Verification method: {cross-referencing approach}

**Quality Standards**:
- Minimum sources per claim: 3
- Cross-reference requirement: All major claims
- Source reputation: Average score {0.0-1.0}

---

## Findings

### Finding 1: {Descriptive Title}

**Evidence**: "{Direct quote or specific data point}"

**Source**: [{Source Name}]({URL}) - Accessed {YYYY-MM-DD}

**Confidence**: {High/Medium/Low}

**Verification**: Cross-referenced with:
- [{Source 2}]({URL2})
- [{Source 3}]({URL3})

**Analysis**: {Brief interpretation or context}

---

{Repeat Finding structure as needed}

---

## Source Analysis

| Source | Domain | Reputation | Type | Access Date | Verification |
|--------|--------|------------|------|-------------|--------------|
| {name} | {domain} | {High/Medium-High/Medium} | {academic/official/industry/technical} | {YYYY-MM-DD} | {Cross-verified Y/N} |

**Reputation Summary**:
- High reputation sources: {count} ({percentage}%)
- Medium-high reputation: {count} ({percentage}%)
- Average reputation score: {0.0-1.0}

---

## Knowledge Gaps

### Gap 1: {Description}

**Issue**: {What information is missing or unclear}
**Attempted Sources**: {What was searched}
**Recommendation**: {How to address this gap}

---

## Conflicting Information (if applicable)

### Conflict 1: {Topic}

**Position A**: {Statement}
- Source: [{Name}]({URL}) - Reputation: {score}
- Evidence: {quote}

**Position B**: {Contradictory statement}
- Source: [{Name}]({URL}) - Reputation: {score}
- Evidence: {quote}

**Assessment**: {Which source appears more authoritative and why}

---

## Recommendations for Further Research

1. {Specific recommendation with rationale}
2. {Recommendation 2}
3. {Recommendation 3}

---

## Full Citations

[1] {Author/Organization}. "{Title}". {Publication/Website}. {Date}. {Full URL}. Accessed {YYYY-MM-DD}.
[2] {Citation 2}
[3] {Citation 3}

---

## Research Metadata

- **Research Duration**: {X minutes}
- **Total Sources Examined**: {count}
- **Sources Cited**: {count}
- **Cross-References Performed**: {count}
- **Confidence Distribution**: High: {%}, Medium: {%}, Low: {%}
- **Output File**: docs/research/{filename}
```

## Skill Distillation Workflow

When creating a skill for a specific agent (via `*create-skill` or when `skill_for` is specified):

### Phase 1: Research
1. Execute comprehensive research as normal
2. Create full research document in `docs/research/{category}/{topic}-comprehensive-research.md`
3. Complete all quality gates

### Phase 2: Distillation
1. Read the comprehensive research
2. Transform content from academic to practitioner-focused
3. Preserve 100% of essential concepts (no lossy compression)
4. Remove: verbose explanations, extensive examples, redundant cross-references
5. Keep: core concepts, practical tools, methodologies, decision heuristics
6. Make self-contained (no external file references)
7. Target under 1000 tokens per skill file
8. Write to `nWave/skills/{agent-name}/{topic}-methodology.md`

### Phase 3: Validation
1. Verify all essential concepts from research appear in skill
2. Confirm practitioner focus (actionable, not academic)
3. Check self-containment (no dangling references)

## Quality Standards

### Per-Claim Requirements
- Minimum 3 independent sources for major claims
- Each source validated against `nWave/data/config/trusted-source-domains.yaml`
- Cross-reference status documented per finding

### Confidence Ratings
- **High**: 3+ high-reputation sources agree, no contradictions
- **Medium**: 2+ sources agree, minor contradictions or some medium-trust sources
- **Low**: Single source or significant contradictions among sources

### Quality Gates (before finalizing)
1. Every major claim has 3+ source citations
2. All sources from trusted domains
3. All findings are evidence-backed
4. Knowledge gaps are documented
5. Output path is within allowed directories
