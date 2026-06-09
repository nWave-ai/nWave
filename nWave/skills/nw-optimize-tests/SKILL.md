---
name: nw-optimize-tests
description: "Minimizes test count while preserving coverage. Detects byte-identical pairs, parametrize-inflation, language-guarantee tests, AST-shape tests, stale migration nets. Approval gate before any change."
user-invocable: true
argument-hint: '[scope] - Optional: a path (e.g. tests/des/unit/), a feature-id (auto-resolves to tests/<id>/), or omit for full unit suite. --reviewer to chain reviewer agent.'
---

# NW-OPTIMIZE-TESTS: Test Suite Optimization

**Wave**: CROSS_WAVE
**Agent**: Trim (nw-test-optimizer)
**Reviewer**: Trim Review (nw-test-optimizer-reviewer)

## Overview

Dispatches Trim to inventory a test scope, detect duplication and anti-patterns, propose a consolidation plan, and apply it after explicit approval. Coverage is preserved; production code is never modified. Use after a feature lands, when a suite feels slow or noisy, on weekly audit, or whenever overtesting is suspected.

## Context Files Required

- The scope path (passed as argument or auto-detected)
- `~/.claude/skills/nw-test-optimization/SKILL.md` — methodology (loaded by agent)

## Timing Baseline by `workflow.mode`

The timing baseline Trim compares against depends on `workflow.mode`:

- **classic mode** — wall-clock figures recorded in the classic-mode execution-log.json.
- **atdd_pure mode** — under `atdd_pure` there is no step log; use the **AT-completion ledger** phase-boundary timestamps as the timing baseline. Each ledger slice records a phase-boundary timestamp per phase transition, and the deltas between consecutive phase-boundary marks give the per-slice timing baseline Trim measures improvement against.

## Agent Invocation

@nw-test-optimizer

Execute test optimization for `{scope}`.

**Configuration:**
- scope: <path | feature-id | empty for full unit suite>
- approval_required: true  # always; gate is non-negotiable
- mutation_validation: false  # set true for critical scopes (financial, safety, infra)
- reviewer_chain: false  # set true to dispatch nw-test-optimizer-reviewer after apply

## Approval Gate

Trim presents the plan as a markdown table after Phase 3 (PLAN). The orchestrator (or invoking user) responds with one of:

1. **APPROVE** — full plan, all rows
2. **APPROVE WITH EXCLUSIONS** — list row IDs to skip
3. **REJECT** — abort, return findings as deferred report
4. **REPLAN** — provide new scope or constraint

No changes are applied without one of these responses. Trim never assumes approval.

## Reviewer Chain (optional)

If `reviewer_chain: true`:

@nw-test-optimizer-reviewer

Validate the optimization output for `{scope}`.

Reviewer hard-blocks on: production drift, coverage drop without justification, unmapped removal, missing approval gate evidence.

## Success Criteria

- [ ] Baseline numbers recorded (passed count, coverage %)
- [ ] Plan presented before any change
- [ ] Explicit approval received
- [ ] Production files in diff: 0
- [ ] Coverage % preserved (or drop documented per skill 5.3)
- [ ] Atomic commits per consolidation pattern
- [ ] Final report with deltas and SHAs

## Examples

### Example 1: Full unit suite audit
```
/nw-optimize-tests
```
Trim inventories the unit suite, runs md5sum cross-check, scans for anti-patterns, produces a leverage-sorted plan covering byte-identical pairs and parametrize-inflated files.

### Example 2: Scoped to a feature
```
/nw-optimize-tests lean-wave-documentation
```
Trim resolves to `tests/<feature-id>/` paths from the classic-mode execution-log.json if available (or, in atdd_pure mode, from the ledger's recorded test paths), otherwise scopes to test files referencing the feature-id.

### Example 3: Single fat file
```
/nw-optimize-tests tests/build/unit/test_skill_restructuring.py
```
Trim probes the single file (315 collected tests), checks migration-collapse lifecycle (skill 3.5), proposes collapse to ~3 tests.

### Example 4: With reviewer
```
/nw-optimize-tests tests/des/unit/ --reviewer
```
Trim runs the workflow, then dispatches Trim Review for adversarial validation. Reviewer issues YAML verdict.

## Out of Scope

- Authoring new tests (crafter scope, DELIVER wave)
- Production code refactoring (`/nw-refactor`, crafter scope)
- Test infrastructure changes (platform-architect, troubleshooter)

## Expected Outputs

```
git log --oneline {base}..HEAD                  (atomic commits per pattern)
<scope>                                          (test files modified or deleted)
report (returned inline by agent)                (baseline, after, deltas, SHAs)
```
