# Slice 02 — RED gate: block implementation before a failing test

**Goal (one sentence):** pi blocks production-code `write`/`edit` when no failing test exists, forcing the crafter to write the test first.

## IN scope
- DES extension `tool_call` handler returns `{ block: true, reason }` for production-code edits when the adapter reports no failing test.
- Allow path: production edit permitted once a failing test for the behavior exists.
- Both decisions recorded in the audit log with phase = RED.
- Reason text usable by the agent to self-correct (write the test first).

## OUT scope
- GREEN / refactor / regression gates (slice 03).
- Commit provenance (slice 03).

## Learning hypothesis
**Disproves** "tool_call blocking yields a usable crafter UX" if the block confuses the agent, causes retry loops, or the reason isn't actionable. **Confirms** the core DoD guarantee ("skipping isn't allowed") at its single strongest point.

## Acceptance criteria
- Impl-before-test `write`/`edit` is blocked, file unchanged, reason surfaced.
- Impl-after-failing-test `write`/`edit` is allowed.
- Block and allow both appear in the audit log.

## Taste test note
This is the "single hard gate" the user explicitly chose to exceed — it ships standalone value but is NOT the finish line; full-cycle gating completes in slice 03.

## Effort / reference class
≈ 1–2 days. Reference: `pre_write_handler.py` / `pre_tool_use_handler.py` decision logic.

## Dependencies
Slice 01.
