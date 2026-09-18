# Slice 02 — Self-driven single TDD step with phase recording

**Goal:** The crafter completes one tiny increment and records RED→GREEN→COMMIT for that step via `des-log-phase`, with a `Step-Id`/`Task-Id`-trailered commit.

## IN scope
- Crafter-skill (pi-runnable) instructions to: write a failing test → record `RED`; minimal impl → green → record `GREEN`; commit with trailers → record `COMMIT`.
- Phase recording via `des-log-phase` from pi's bash.
- Reuse the shipped commit gate (`git commit` → `subagent-stop`) for verification.

## OUT scope
- Self-decomposing a whole kata into many steps (Slice 03).
- Hard within-cycle write-block (K2, out).

## Learning hypothesis
**Disproves** "the single pi agent can drive + record the cycle without an orchestrator" if the agent won't reliably record phases from the skill alone, or the commit gate rejects a genuinely-complete step. **Confirms** the per-step driving half.

## Acceptance criteria
- One increment → RED, GREEN, COMMIT recorded in order for the step.
- Commit carries `Step-Id` + `Task-Id`.
- A deliberately incomplete step is blocked at commit (gate reuse).

## Dependencies
Slice 01.

## Effort / reference
≈ 2 days. Reference: the orchestrator DES `OUTCOME_RECORDING` template (the per-step recording this replaces for pi), `subagent_stop_handler`.
