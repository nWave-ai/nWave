# Slice 03 — GREEN + refactor/regression gates + Step-Id provenance (completes DoD)

**Goal (one sentence):** pi enforces green-before-next-test and no-regression-on-commit, and the full RED→GREEN→REFACTOR cycle for a kata is verifiable from the audit log + `Step-Id`-trailered git history.

## IN scope
- Block authoring the next failing test while the suite is red ("reach green first").
- Block commits that leave previously-green tests failing (no-regression / refactor-on-green gate).
- Re-ground the step-completion analog on commit boundaries (D6) — `Step-Id:` trailers on conventional commits, ordered RED→GREEN→REFACTOR.
- Audit-log phase tagging (RED / GREEN / REFACTOR) for each transition.
- A documented, reproducible kata run demonstrating the full DoD.

## OUT scope
- Multi-step roadmap orchestration; other agents/waves (out of feature scope).

## Learning hypothesis
**Disproves** "full-cycle gating works in a subagent-less harness" if the commit-boundary step model can't substitute for `SubagentStop`, or phase ordering can't be reconstructed. **Confirms** the complete DoD: strict one-tiny-test increments, provable from log + commits.

## Acceptance criteria
- New-test-while-red is blocked with a reason.
- Regression-on-commit is blocked until green is restored.
- `git log` shows `Step-Id`-trailered commits in strict RED→GREEN→REFACTOR order; audit log phase sequence matches.
- A kata (e.g. FizzBuzz / Stack) run reproduces the full DoD end-to-end.

## Production-data requirement
Demo on a real kata in a real repo; commits real, not fabricated.

## Effort / reference class
≈ 2–3 days. Reference: `subagent_stop_handler.py` (step-completion logic), `GitCommitVerifier`.

## Dependencies
Slice 02. Resolves provisional decision D6 (DESIGN to confirm the step-completion analog).
