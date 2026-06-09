---
name: nw-root-why
description: "Root cause analysis and debugging"
user-invocable: true
argument-hint: '[problem-description] - Optional: --depth=[3|5|7-whys] --output=[text|diagram|report]'
---

# NW-ROOT-WHY: Toyota 5 Whys Root Cause Analysis

**Wave**: CROSS_WAVE
**Agent**: Rex (nw-troubleshooter)

## Overview

Systematic root cause analysis using Toyota's 5 Whys with multi-causal investigation and evidence-based validation. Investigates multiple cause branches at each level|validates solutions against all identified root causes.

## Agent Invocation

@nw-troubleshooter

Execute \*investigate-root-cause for {problem-statement}.

**Configuration:**
- investigation_depth: 5
- multi_causal: true
- evidence_required: true

## Workflow-mode context (ADR-028)

The inputs RCA reads depend on `.nwave/config.yaml:workflow.mode`. Under `classic` mode, RCA reads `roadmap.json` + `execution-log.json` as the phase record. Under `atdd_pure` mode those artifacts are unreachable: RCA instead reads the per-slice ATs and the AT-completion ledger at `.nwave/telemetry/atdd-pure/` for the phase-boundary record — that is, in `atdd_pure` mode each slice's failure evidence comes from its slice ATs and the ledger, not from `execution-log.json`.

## Usage: DELIVER Wave Retrospective (Phase 3.5)

When invoked as part of `/nw-deliver` Phase 3.5, execute in order:

1. **Gather Inputs** — Read the evolution document, mutation results, and git log. In `classic` mode also read `roadmap.json` + `execution-log.json`; in `atdd_pure` mode read the per-slice ATs and the AT-completion ledger instead. Gate: all available inputs loaded.
2. **Analyze What Worked Well** — Identify practices that succeeded and document why — preserve these. Gate: at least one practice documented with rationale.
3. **Analyze What Improved** — Identify what worked better than before and why — record as reinforcements. Gate: delta from prior execution captured.
4. **Analyze What Worked Badly** — Apply 5 Whys root cause analysis to failures; produce actionable fix per root cause. Gate: each failure has a root cause and fix.
5. **Analyze What Regressed** — Apply 5 Whys to anything worse than before; produce prevention action. Gate: each regression has a root cause and prevention action.
6. **Tag Meta-Improvements** — Mark any items requiring nWave framework changes as **meta-improvements**. Gate: all framework-level issues flagged.
7. **Append Retrospective** — Write retrospective section to evolution document. If clean execution (no skips, no failures, no tooling issues), generate brief summary only. Gate: evolution document updated.

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
/nw-root-why "Integration tests fail intermittently on CI but pass locally"
```
Rex investigates 5 WHY levels with multi-causal branches, discovers race condition in database cleanup, proposes transaction-isolated test fixtures.

## Expected Outputs

```
docs/analysis/root-cause-analysis-{problem}.md
```
