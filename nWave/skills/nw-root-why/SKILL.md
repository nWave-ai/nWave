---
name: nw-root-why
description: "Root cause analysis and debugging"
user-invocable: true
argument-hint: '[problem-description] - Optional: --depth=[3|5|7-whys] --output=[text|diagram|report]'
---

> **Code facts** — resolve structural facts about code through `code-fact` CLI (vendor-neutral, bundled adapters: AST then TextSearch). Degrade LOUD. Never ad-hoc grep. Example: `code-fact query.callers-of SYMBOL --root ROOT`.

# NW-ROOT-WHY: Toyota 5 Whys Root Cause Analysis

**Wave**: CROSS_WAVE
**Agent**: Rex (nw-troubleshooter)

## Overview

Systematic root cause analysis using Toyota's 5 Whys with multi-causal investigation and evidence-based validation. Investigates multiple cause branches at each level|validates solutions against all identified root causes.

## Design-time counterexamples

RCA applies to design-time evidence at par with runtime failures: a
model-checker violation, a refuted invariant, a failing property, or a
theorem that only passes in conditional form. For these, the first RCA
question is representational — which type or schema made the failing state
expressible? A conditional theorem's hypothesis names the constraint the
design should enforce by construction. Route the cure through `nw-design`'s
Counterexample discipline; a law added over an unchanged representation
without recorded justification is a symptom patch, not a root-cause fix.
This applies whether the counterexample came from a proof assistant, a
model checker, or a property test in the project's own language — no prover
is a prerequisite for this RCA question.

## Agent Invocation

@nw-troubleshooter

Execute \*investigate-root-cause for {problem-statement}.

**Configuration:**
- investigation_depth: 5
- multi_causal: true
- evidence_required: true

## Usage: DELIVER Wave Retrospective (Phase 3.5)

When invoked as part of `/nw-deliver` Phase 3.5, execute in order:

1. **Analyze What Worked Well** — Identify practices that succeeded and document why — preserve these. Gate: at least one practice documented with rationale.
2. **Analyze What Improved** — Identify what worked better than before and why — record as reinforcements. Gate: delta from prior execution captured.
3. **Analyze What Worked Badly** — Apply 5 Whys; the root cause names the producer/type that admitted the failing state (GDP-0) — a fix that adds a check instead is a symptom patch unless that producer cannot change, with the reason recorded. Gate: each failure has a representational root cause and fix.
4. **Analyze What Regressed** — Apply 5 Whys to anything worse than before; produce prevention action. Gate: each regression has a root cause and prevention action.
5. **Tag Meta-Improvements** — Mark any items requiring nWave framework changes as **meta-improvements**. Gate: all framework-level issues flagged.
6. **Append Retrospective** — Write retrospective section to evolution document. If clean execution (no skips, no failures, no tooling issues), generate brief summary only. Gate: evolution document updated.

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
