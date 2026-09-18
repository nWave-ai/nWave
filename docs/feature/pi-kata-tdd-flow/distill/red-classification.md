# RED classification — pi-kata-tdd-flow (pre-DELIVER fail-for-right-reason gate)

Run: `pytest tests/des/acceptance/pi_kata_tdd_flow/` (2026-06-24). Result:
**10 failed (RED), 1 skipped (`@requires_external`), 0 false passes.**

Every failing scenario fails with `AssertionError: Not yet implemented -- RED
scaffold` originating from `scripts/install/pi_kata/bootstrap.py:bootstrap_kata_session`
(the first NEW-surface call in every Given/When). Classification:
**MISSING_FUNCTIONALITY** — the assertion fires because the kata-bootstrap behavior
is unimplemented, NOT because of an import/fixture/setup error. Confirmed: zero
ImportError, zero collection error (markers registered including the
`@contract-shape:*` tags), zero fixture error.

| Scenario | Slice | Tags | Failure | Class |
|----------|-------|------|---------|-------|
| Bootstrapping a kata establishes a recorded, gate-ready session | 01 | @US-1 @real-io @contract-shape:bounded-change | scaffold AssertionError | MISSING_FUNCTIONALITY ✅ |
| Bootstrapping outside an activated project leaves the project untouched | 01 | @US-1 @real-io @error @contract-shape:unbounded-preservation | scaffold AssertionError | MISSING_FUNCTIONALITY ✅ |
| Re-bootstrapping an existing session preserves the recorded history | 01 | @US-1 @real-io @contract-shape:unbounded-preservation | scaffold AssertionError (in Given) | MISSING_FUNCTIONALITY ✅ |
| Recording a completed increment leaves an ordered phase trail | 02 | @US-2 @real-io @contract-shape:bounded-change | scaffold AssertionError | MISSING_FUNCTIONALITY ✅ |
| A completed increment with a trailered commit is accepted at the boundary | 02 | @US-2 @real-io @contract-shape:unbounded-preservation | scaffold AssertionError | MISSING_FUNCTIONALITY ✅ |
| An incomplete increment is blocked at the commit boundary with a reason | 02 | @US-2 @real-io @error @contract-shape:unbounded-preservation | scaffold AssertionError | MISSING_FUNCTIONALITY ✅ |
| A malformed commit-context transcript is treated as no DES context | 02 | @US-2 @real-io @error @contract-shape:unbounded-preservation | scaffold AssertionError | MISSING_FUNCTIONALITY ✅ |
| A multi-step kata records each step's cycle in plan order | 03 | @US-3 @real-io @contract-shape:bounded-change | scaffold AssertionError | MISSING_FUNCTIONALITY ✅ |
| Skipping a step in a multi-step kata is blocked at the commit boundary | 03 | @US-3 @real-io @error @contract-shape:unbounded-preservation | scaffold AssertionError | MISSING_FUNCTIONALITY ✅ |
| A reverted step-id in the manifest surfaces as a blocked commit | 03 | @US-3 @real-io @error @contract-shape:unbounded-preservation | scaffold AssertionError | MISSING_FUNCTIONALITY ✅ |
| A live pi model solves a real kata end-to-end with a verified trail | 03 | @US-3 @requires_external @contract-shape:bounded-change | SKIPPED (no model backend) | correctly skipped ✅ |

## Outside-in note for DELIVER
The bootstrap scaffold fires first in every scenario, so the transcript-context
scaffold (`scripts/install/pi_kata/transcript_context.py`) is not yet reached at this
RED snapshot. This is correct outside-in sequencing: DELIVER implements bootstrap
first (Slice 01 GREEN), which then exposes the Slice 02/03 boundary scenarios that
drive the transcript-context assembler. Both scaffolds import cleanly (Mandate 7
satisfied — RED, not BROKEN). After all DELIVER steps, zero `__SCAFFOLD__` markers
should remain in `scripts/install/pi_kata/`.

## Fixture-theater check (Critical Rule 7)
The Slice-01 unactivated-refusal scenario was initially a FALSE PASS (the test caught
the scaffold exception and read it as "refusal", and the filesystem-unchanged
assertion held without production code). FIXED: refusal is now an observable result
contract (`result["status"] == "refused"`), which the bare scaffold cannot satisfy —
the scenario now REDs for MISSING_FUNCTIONALITY. No remaining false passes.

## Regression
pi-harness suite: **21 passed, 1 skipped** — no regression; `@walking_skeleton` green.
`git diff --stat src/des/` empty (K2 honored). No `des-task-active*` leak from the new
suite into the main repo (verified).
