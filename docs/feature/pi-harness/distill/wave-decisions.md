# DISTILL Decisions — pi-harness

> nw-acceptance-designer (Quinn), 2026-06-23. Density = lean (Tier-1 only; Tier-2
> not auto-expanded). Continues from DISCUSS/SPIKE/DESIGN (D1–D14).

## Reconciliation gate

**Wave-Decision Reconciliation: PASSED — 0 contradictions** across
DISCUSS / DESIGN / (no DEVOPS wave → default env matrix `clean | with-pre-commit |
with-stale-config`, WARN only). Run by orchestrator before dispatch; re-affirmed.

## Phase 0 detection

- `[lang-mode] python` (pyproject.toml).
- `[policy-mode] inherit` — `docs/architecture/atdd-infrastructure-policy.md` was
  ABSENT; bootstrapped this run with the three port rows for this feature.
- `[port-mode] inherit` — state-delta port present at `nwave_ai/state_delta/`
  (Python pilot) + `tests/common/state_delta.py`; no bootstrap needed.

## Tier decision (Mandate 10)

**Tier A only.** Tier B (state-machine PBT) NOT added. Rationale: the feature is
config-shaped (single-shot installer lifecycle) + thin-translator contract +
model-free gate wiring. The TDD cycle IS a state machine, but the SUT here is the
*installer/translator wiring*, not a domain-rich journey with a large input space.
Tier B `InMemoryComposition` would model the DES engine — which is REUSED UNCHANGED
and owns its own suite (D5, out of scope). Per Mandate 10 "skip when config-shaped /
only observable is did-it-wire". The crafter's RED→GREEN→commit state machine is
documented (C2a) and exercised example-based at layer 3 (Mandate 9/11).

## PBT mode (Mandate 9 / 11)

All new scenarios run at **layer 3** (subprocess / real-FS adapter / rendered-template
inspection). Per Mandate 9, layer 3+ is **example-only — no PBT machinery**. Sad
paths enumerated explicitly (Mandate 11). The unbounded-domain PBT that the
falsifier-gate would otherwise prefer is N/A: the input domains here are finite +
enumerable (4 lifecycle ops, fixed tool-name set, present/absent config dir).

## Universe / state-delta (Mandate 8)

State-mutating installer steps assert via `assert_state_delta` over a port-exposed
universe: `extension.present`, `extension.content`, `manifest.present`,
`operator_file.present`, `operator_file.content`. No internal struct fields. The
operator-file-untouched guarantee rides implicit-unchanged (the slot is in the
universe but absent from `expected`). Translation-contract + gate scenarios assert
on exit code + stdout JSON (port-exposed adapter outputs), traditional assertions
permitted at this layer.

## AT-completeness audit (Phase 2.5)

15-item mechanical checklist → **14/15 passing → COMPLETE** (≥13). Gaps & N/A:

| Item | Verdict | Note |
|------|---------|------|
| C1b boundary | N/A-pass | config-shaped, no numeric/size partitions |
| C3 0/1/N | partial-pass | singleton artifacts by design; reinstall = apply-twice |
| C5a/C5b mode-flag | N/A-pass | no flag matrix in thin slice (D7 crafter-only) |
| C6c closed error set | partial-pass | PluginResult(success=False)+message, not typed enum |
| C7b interruption | **GAP** | `AT_GAP_IN_DELIVERY_SCOPE`, LOW — single-shot installer; mid-transaction interruption not modeled in thin slice |

No `SPECIFICATION_AMBIGUITY` blockers — C2 state machine from ADR-pi-001, C5 N/A
per D7, C6 contract derivable, C7 default env matrix. No upstream routing needed.

## Step-reuse ratio (Mandate-12 criterion 4, informational)

Not gated. Natural ceiling for this config-shaped feature is low (each lifecycle
op + each error contract has a distinct domain-readable Given/When/Then). Pillar 1
(readability) outranks ratio per ADR-026. No `domain_types.py` enum module created:
the domain nouns here (lifecycle op names, tool names) are few and the step bodies
delegate to the production plugin / real adapter subprocess — no inline business
logic (criterion 3 satisfied). For a thin slice this is the calibrated outcome.

## Deferred / blocked items

- **Outcomes registry**: `nwave-ai outcomes register` FAILS —
  `docs/product/outcomes/schema.json` absent (`FileNotFoundError`). Registration
  of `OUT-PI-1` (pi_des_plugin install, kind=operation) **deferred**, not blocking
  (per DISTILL outcomes procedure: note when CLI errors). Re-run after the
  outcomes schema is bootstrapped in `docs/product/outcomes/`.
- **C7b interruption AT**: deferred LOW, in-scope for a later slice.
- **`@requires_external` live-model e2e**: 1 scenario skip-by-default (SPIKE-0 R4 —
  no pi model backend in CI). Its deterministic engine-decision analog is asserted
  at the adapter round-trip.
- **R1 pi config-dir location**: plugin scaffold uses `PI_CONFIG_DIR` override +
  `~/.pi/agent` default (per SPIKE-0 + ADR-pi-002); DELIVER/DEVOPS confirms and the
  plugin must emit a non-fatal warning when absent (brief R1). Acceptance tests pin
  the override so they are location-independent.

## Upstream changes

None. No DISCUSS/DESIGN/SPIKE decision revised. SSOT untouched except the new
infrastructure-policy bootstrap + this DISTILL delta.

## Final review gate outcome (2026-06-23)

Consolidated wave review: **Sentinel APPROVED** (0/0/0); **Architect CONDITIONALLY_APPROVED**
(0 crit / 2 high / 2 med / 1 low); **Eclipse → APPROVED** after DISCUSS doc fixes (worked
FizzBuzz examples, concrete elevator-pitch outputs, "green = test-run bash tool_result exit 0",
D6 commit-boundary wording). Forge N/A (no DEVOPS wave).

**Architect HIGH Issue 2 (unproven driving ports): RESOLVED** by SPIKE-1
(`spike/findings-spike-1-driving-ports.md`) — bash `tool_call` blockable + `command`
inspectable + `tool_result.exitCode` present, all type-confirmed in pi 0.79.9.

### DELIVER-scoped action items (Architect conditions, accepted)
- **A1 (was HIGH Issue 1) — translator-purity guard.** DELIVER MUST add a test asserting the
  rendered `pi-des-extension.ts` contains NO allow/block decision logic beyond relaying the
  engine's exit-2 + reason (pure relay). Prevents decision logic leaking into the TS.
- **A2 (was MED Issue 3) — out-of-harness commit.** Add a scenario: a `Step-Id` commit made
  outside pi is still caught post-hoc by `GitCommitVerifier`/`StepCompletionValidator` in CI.
- **A3 (was MED Issue 4) — skill-dir + `resources_discover` shape.** Confirm the exact pi skill
  directory + `resources_discover` `skillPaths` return shape against pi 0.79.9 during DELIVER
  (de-risked: those types live in the same `dist/core/extensions/types.d.ts` SPIKE-1 inspected).
