---
description: "Root cause analysis and debugging"
argument-hint: "[problem-description] - Optional: --depth=[3|5|7-whys] --output=[text|diagram|report]"
---

# NW-ROOT-WHY: Toyota 5 Whys Root Cause Analysis

**Wave**: CROSS_WAVE
**Agent**: Rex (nw-troubleshooter)

## Overview

Execute systematic root cause analysis using Toyota's 5 Whys technique with multi-causal investigation and evidence-based validation. Investigates multiple cause branches at each level and validates solutions against all identified root causes.

## Agent Invocation

@nw-troubleshooter

Execute \*investigate-root-cause for {problem-statement}.

**Configuration:**

- investigation_depth: 5
- multi_causal: true
- evidence_required: true

## Usage: DELIVER Wave Retrospective (Phase 3.5)

When invoked as part of `/nw:deliver` Phase 3.5, analyze across 4 categories:

1. **What worked well** (and why -- preserve these practices)
2. **What worked better than before** (and why -- reinforce improvements)
3. **What worked badly** (5 Whys root cause, actionable fix)
4. **What worked worse than before** (5 Whys root cause, prevent regression)

**Inputs**: Evolution document, execution-log.yaml, mutation results, git log.
**Output**: Retrospective section appended to evolution document.
**Skip**: If clean execution (no skips, no failures, no tooling issues), generate brief summary only.

Tag items requiring nWave framework changes as **meta-improvements**.

## Success Criteria

- [ ] All 5 WHY levels investigated with evidence
- [ ] Multi-causal branches explored at each level
- [ ] Root causes identified and validated
- [ ] Solutions address all identified root causes
- [ ] Backward chain validation performed

## Next Wave

**Handoff To**: {invoking-agent-returns-to-workflow}
**Deliverables**: Root cause analysis report with solutions

## Examples

### Example 1: Investigate test flakiness
```
/nw:root-why "Integration tests fail intermittently on CI but pass locally"
```
Rex investigates 5 WHY levels with multi-causal branches, discovers race condition in database cleanup, proposes transaction-isolated test fixtures.

## Expected Outputs

```
docs/analysis/root-cause-analysis-{problem}.md
```
