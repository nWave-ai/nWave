# Slice 03 — Full kata end-to-end, strictly verified (closes the DoD)

**Goal:** Hand the crafter a real kata (e.g. FizzBuzz); it self-decomposes into one-test-per-step increments, drives the full cycle, and the strict RED→GREEN→COMMIT trail is verifiable from the execution log + `Step-Id` commit history.

## IN scope
- Crafter self-decomposition: one tiny failing test per step, sequenced.
- End-to-end multi-step run with per-step phase recording + trailered commits.
- A documented, reproducible kata run (the original pi-harness DoD item 9).
- Verification via existing DES surfaces only.

## OUT scope
- CI automation of the live-model run (`@requires_external` — needs a model backend).
- Hard within-cycle write-block (K2).

## Learning hypothesis
**Disproves** "pi can run a full strict-TDD kata the nWave way" if step ordering can't be reconstructed, the crafter skips decomposition, or the gate has false positives across a multi-step run. **Confirms** the original DoD end-to-end.

## Acceptance criteria
- A kata completes with N steps each showing ordered RED→GREEN→COMMIT.
- `git log` shows `Step-Id`-trailered commits in strict order; audit phase sequence matches.
- An attempted step-skip is blocked at the commit boundary.

## Production-data requirement
Real kata in a real repo with a live model; commits real, not fabricated.

## Dependencies
Slice 02. Live pi model backend (runtime prerequisite).

## Effort / reference
≈ 2–3 days. Reference: pi-harness `tdd-enforcement-gates.feature` (commit gate) + the FizzBuzz worked example in `docs/feature/pi-harness/feature-delta.md`.
