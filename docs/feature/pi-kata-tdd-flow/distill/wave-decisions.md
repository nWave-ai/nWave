# DISTILL wave-decisions — pi-kata-tdd-flow

Provenance: `/nw-distill` 2026-06-24 (Quinn, nw-acceptance-designer). Density = lean
(Tier-1 only). Builds ON the shipped pi-harness — EXTEND not rewrite.

## Reconciliation gate
PASSED — 0 contradictions (orchestrator-run, K1–K4 ↔ KD1–KD4 ↔ SPIKE). DEVOPS
artifacts absent → default env matrix (clean / with-pre-commit / with-stale-config),
WARN only. KPI contracts present in feature-delta (soft gate).

## Language / port / policy modes
- `[lang-mode] python` (pyproject.toml).
- `[port-mode] inherited` — `tests/common/state_delta.py` present; no bootstrap.
- `[policy-mode] inherit` — `docs/architecture/atdd-infrastructure-policy.md` present;
  the three pi ports (extension load, plugin lifecycle, adapter round-trip) already
  cover this feature's surface. NEW kata-bootstrap + transcript-context helpers are
  exercised through the SAME driving rows (real subprocess + real FS) — no new policy
  row required. Confirmed apply-if-exists.

## Tier decision
**Tier A only.** Per Mandate 10: although Slice 02 has ≥3 chained scenarios (Pillar 2
active), the input space is NOT domain-rich — it is config-shaped (a fixed kata id,
ordinal `NN-NN` step ids, a fixed RED→GREEN→COMMIT canon, enumerable verdicts
allow/block/refused). The observable space is a small closed set, so Tier B
(state-machine PBT over generative inputs) adds ceremony without coverage. State &
transition coverage (C2) is met example-based at layer 3 per Mandate 11.

## PBT mode (Mandate 9)
**Example-only, zero PBT.** All scenarios are layer 3 (`@real-io @adapter-integration`:
real subprocess + real tmp git repo + real reused DES CLIs). Layer 3+ is example-only;
sad paths enumerated explicitly (Mandate 11). The falsifier-gate confirms it: the input
domain (kata id, step id, phase set, verdicts) is finite + enumerable → parametrize/
example, never PBT.

## Mandate-12 SSOT — four mechanical criteria
1. **Domain types module exists** — `steps/domain_types.py` (TddPhase, PhaseStatus,
   CommitVerdict, CycleCompleteness enums + Kata/StepId dataclasses + COMPLETE_CYCLE +
   REQUIRED_DES_MARKERS). PASS.
2. **Composition methods consume typed params** — `kata_support.record_phase` takes a
   `TddPhase` enum, not a raw str; `record_complete_cycle` iterates the typed
   `COMPLETE_CYCLE`. PASS.
3. **No business logic in step bodies** — step bodies delegate to `kata_support.*`
   (the composition root) or assert on observable results; no control flow beyond the
   error-result branch. PASS.
4. **Step-reuse-ratio (INFORMATIONAL, not a gate)** — measured below.

### Step-reuse-ratio (natural ceiling, informational)
- Gherkin Given/When/Then/And occurrences across the 3 .feature files: ~46.
- Unique step decorators across the 3 step modules + reused: ~38.
- **Ratio ≈ 1.2× — the natural ceiling for this config-shaped feature.** Below 4× is
  EXPECTED and compliant: the journey is a short fixed canon with little parameter
  reuse surface; forcing a higher ratio would collapse readable domain Gherkin into
  ratio-maximizing templates and degrade Pillar 1. Criteria 1–3 met → compliant.

## Self-completeness audit (Phase 2.5)
Canonical 15-item checklist, no domain-extension opt-in. **Verdict: COMPLETE (14/15).**
- One documented gap: **C7a (degraded-resource)** — no read-only-FS / partial-write
  failure scenario at DISTILL. Classified `AT_GAP_IN_DELIVERY_SCOPE`: the ADR assigns
  the manifest atomic-write / partial-write robustness to DELIVER's H3 observation test
  (reverted-manifest is covered here; full degraded-FS belongs to DELIVER). NOT a
  SPECIFICATION_AMBIGUITY — all C2/C5/C6/C7 upstream artifacts present (ADR-PKT-001 +
  slices + SPIKE findings).
- N/A-with-rationale (count as passing): C1b (no numeric boundary domain), C5a/C5b
  (no mode flags), C7c (single pi agent, no concurrency claim).
- Zero SPECIFICATION_AMBIGUITY blockers → no upstream routing emitted.

## Deferred items
- **Outcomes registration** — `nwave-ai outcomes register` errors:
  `FileNotFoundError docs/product/outcomes/schema.json`. The kata-bootstrap operation
  (OUT candidate: kind=operation, input `(project_root, kata_id)`, output
  `{status, manifest}`) is DEFERRED until the registry schema is present. Non-blocking
  per DISTILL outcomes procedure.

## Earned-trust / constraints honored
- Zero `src/des/**` change (K2): reuse des-init-log, des-log-phase, subagent-stop,
  GitCommitVerifier, marker parser UNCHANGED. `git diff --stat src/des/` empty.
- 4 SPIKE constraints in step bodies: (1) block via stdout decision=block at exit 0;
  (2) exact four DES markers via the transcript-context assembler; (3) fresh step-id
  per cycle (no reuse); (4) manifest project-id/step-id/cwd aligned with
  execution-log resolution.
- All test state under `tmp_path`; verified no `des-task-active*` leak from the new
  suite into the main repo.

## Final review gate outcome (2026-06-24)

Consolidated review: **Eclipse (DISCUSS) APPROVED** (0/0/0); **Architect (DESIGN) APPROVED** (0/0/0/0 — K2/zero-engine-change held, reuse analysis + SPIKE validation confirmed); **Sentinel (DISTILL) CONDITIONALLY_APPROVED** (0 blockers / 1 high / 0 low). Forge N/A (no DEVOPS).

### Sentinel HIGH resolution — Mandate 8 / CM-E (state-delta at layer 3)
Finding: Slice 01 uses `assert_state_delta`; Slice 02/03 assert directly on observables (`execution-log.json` content, git `Step-Id` trailers, adapter stdout JSON `decision`).
**Adjudication (orchestrator):** ACCEPTED-WITH-ACTION. Those observables are PORT-EXPOSED external contracts (the "good universe" the mandate wants), not internal-field coupling — the tests are not refactoring-hostile. At layer-3 example-based subprocess tests the state-delta universe-guard payoff is smaller (skill's own Mandate 9 note). The pattern is acceptable for DISTILL hand-off.
**DELIVER action item (A-PKT-1):** during DELIVER, wrap the Slice 02/03 observable assertions in `assert_state_delta` (universe = {`execution-log.json` phase trail, `git Step-Id trailers`, `adapter stdout decision`}) IF cheap, for consistency with Slice 01; otherwise keep the documented exemption. Non-blocking.
Tier B note (informational): Tier-A-only decision was made during DISTILL authoring (config/cycle-shaped, input space not domain-rich) — confirmed intentional, not post-hoc.

**Gate status: CLEARED for DELIVER** — all verdicts APPROVED or CONDITIONALLY_APPROVED with the one HIGH converted to a documented DELIVER-scoped action item (A-PKT-1).
