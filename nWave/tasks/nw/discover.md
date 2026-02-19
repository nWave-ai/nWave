---
description: "Conducts evidence-based product discovery through customer interviews and assumption testing. Use at project start to validate problem-solution fit."
argument-hint: "[product-concept] - Optional: --interview-depth=[overview|comprehensive] --output-format=[md|yaml]"
---

# NW-DISCOVER: Evidence-Based Product Discovery

**Wave**: DISCOVER
**Agent**: Scout (nw-product-discoverer)

## Overview

Execute evidence-based product discovery through assumption testing and market validation. First wave in nWave (DISCOVER > DISCUSS > DESIGN > DEVOP > DISTILL > DELIVER).

Scout establishes product-market fit through rigorous customer development using Mom Test interviewing principles and continuous discovery practices.

## Context Files Required

- docs/project-brief.md - Initial product vision (if available)
- docs/market-context.md - Market research and competitive landscape (if available)

## Previous Artifacts

None (DISCOVER is the first wave).

## Agent Invocation

@nw-product-discoverer

Execute \*discover for {product-concept-name}.

**Context Files:**

- docs/project-brief.md (if available)
- docs/market-context.md (if available)

**Configuration:**

- interactive: high
- output_format: markdown
- interview_depth: comprehensive
- evidence_standard: past_behavior

## Success Criteria

Refer to Scout's quality gates in ~/.claude/agents/nw/nw-product-discoverer.md.

- [ ] All 4 decision gates passed (G1-G4)
- [ ] Minimum interview thresholds met per phase
- [ ] Evidence quality standards met (past behavior, not future intent)
- [ ] Handoff accepted by product-owner (DISCUSS wave)

## Next Wave

**Handoff To**: nw-product-owner (DISCUSS wave)
**Deliverables**: See Scout's handoff package specification in agent file

## Examples

### Example 1: New SaaS product discovery
```
/nw:discover invoice-automation
```
Scout conducts customer development interviews, validates problem-solution fit through Mom Test questioning, and produces a lean canvas with evidence-backed assumptions.

## Expected Outputs

```
docs/discovery/
  problem-validation.md
  opportunity-tree.md
  solution-testing.md
  lean-canvas.md
  interview-log.md
```
