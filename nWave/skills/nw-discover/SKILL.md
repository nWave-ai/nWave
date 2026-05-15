---
name: nw-discover
description: "Conducts evidence-based product discovery through customer interviews and assumption testing. Use at project start to validate problem-solution fit."
user-invocable: true
argument-hint: '[product-concept] - Optional: --interview-depth=[overview|comprehensive] --output-format=[md|yaml]'
---

# NW-DISCOVER: Evidence-Based Product Discovery

**Wave**: DISCOVER | **Agent**: Scout (nw-product-discoverer)

## Overview

Execute evidence-based product discovery through assumption testing and market validation. First wave in nWave (DISCOVER > DISCUSS > SPIKE > DESIGN > DEVOPS > DISTILL > DELIVER).

Scout establishes product-market fit through rigorous customer development using Mom Test interviewing principles and continuous discovery practices.

## Output Tiers (per D2)

Provenance: feature `lean-wave-documentation` — D2 (schema-typed sections), D10 (one-line expansion descriptions). Tier-1 [REF] sections (always emitted) + Tier-2 EXPANSION CATALOG items (lazy, on-demand) are the two output bands. Full contract + provenance for `[REF]` / `[WHY]` / `[HOW]` heading convention: `nWave/skills/nw-density-resolution-contract/SKILL.md`.

### Tier-1 [REF] — always emitted

Under `## Wave: DISCOVER / [REF] <Section>` headings:

- Persona ID — one-line user identifier mapped to the journey
- Opportunity statement — single-sentence problem/opportunity framing
- Validated assumptions — list with confidence level per item
- Invalidated assumptions — list with evidence reference per item
- Dropped options — alternatives weighed and rejected (one-line each)
- Decision gate (G1-G4) — pass/fail status per gate
- Constraints established — evidence-backed constraints from interviews
- Pre-requisites — dependencies on prior waves or features

### Tier-2 EXPANSION CATALOG — lazy, on-demand (per D10)

Rendered under `## Wave: DISCOVER / [WHY|HOW] <Section>` only when requested via `--expand <id>` (DDD-2), the wave-end menu (`expansion_prompt = "ask"`), `mode = "full"` auto-expansion, or an ad-hoc user request mid-session.

| Expansion ID | Tier label | One-line description |
|---|---|---|
| `discovery-interview-transcripts` | [WHY] | Full interview transcripts with verbatim quotes (Mom Test compliance evidence) |
| `jtbd-analysis` | [WHY] | Jobs-to-be-Done analysis: functional/emotional/social dimensions per job |
| `taste-evaluation-rationale` | [WHY] | Decision rationale for each evaluated opportunity (why fit, why not) |
| `alternative-opportunities` | [WHY] | Alternative product opportunities considered and rejected |
| `four-forces-narrative` | [WHY] | Push/Pull/Anxiety/Habit narrative analysis per primary job |
| `lean-canvas-walkthrough` | [HOW] | Lean canvas section-by-section walkthrough for stakeholder reviews |
| `interview-protocol` | [HOW] | Step-by-step interview script with Mom Test follow-up patterns |
| `expansion-catalog-rationale` | [WHY] | Why this set of expansions, why these defaults, why D10 enforces one-line descriptions |

## Density resolution (per D12)

Call `resolve_density(global_config)` from `scripts/shared/density_config.py` after reading `~/.nwave/global-config.json` (missing/malformed = empty dict). Returns `mode` (`"lean"` | `"full"`) + `expansion_prompt` (`"ask"` | `"always-skip"` | `"always-expand"` | `"smart"`) per the D12 cascade (resolver-internal, DDD-5 — do NOT replicate locally). Branch on `density.mode` for what to emit; branch on `density.expansion_prompt` at wave end for menu behaviour. Full cascade detail, branch semantics, ad-hoc override workflow ("expand X" / "tell me why"): `nWave/skills/nw-density-resolution-contract/SKILL.md`.

## Telemetry (per D4 + DDD-6)

Every expansion choice emits a `DocumentationDensityEvent` (dataclass at `src/des/domain/telemetry/documentation_density_event.py`) via `event.to_audit_event()` → `JsonlAuditLogWriter().log_event(...)`. Schema fields per D4: `feature_id`, `wave`, `expansion_id`, `choice`, `timestamp`. For this wave the schema declares `"wave": "DISCOVER"`. Use helper `scripts/shared/telemetry.py:write_density_event(...)` — do NOT write JSONL directly.

Wave-specific signal: DISCOVER feeding into DISCUSS — downstream `--expand` invocations are a signal the lean baseline is too thin. Full emission rules (one event per `ask` choice; synthetic skip event for `always-skip`; per-item expand event for `full` / `always-expand`): `nWave/skills/nw-density-resolution-contract/SKILL.md`.

## Context Files Required

- docs/project-brief.md — Initial product vision (if available)
- docs/market-context.md — Market research and competitive landscape (if available)

## Previous Artifacts

None (DISCOVER is the first wave).

## Wave Decisions Summary

Before completing DISCOVER, produce `docs/feature/{feature-id}/discover/wave-decisions.md`:

1. **Record Key Decisions** — List each decision as `[D1] {decision}: {rationale} (see: {source-file})`. Gate: every major discovery choice has a rationale entry.
2. **Record Constraints** — List each constraint established from evidence. Gate: all constraints have an evidence source.
3. **Record Validated Assumptions** — List each assumption confirmed, with confidence level. Gate: confidence level stated for each.
4. **Record Invalidated Assumptions** — List each assumption disproved, with evidence reference. Gate: evidence reference present for each invalidation.

This summary enables downstream waves to quickly assess DISCOVER outcomes without reading all artifacts.

## Document Update (Back-Propagation)

DISCOVER is the first wave but it DOES write to SSOT. It has no prior wave to back-propagate to, but it seeds the SSOT for downstream waves:

1. **Seed journeys** — Write initial `docs/product/journeys/{name}.yaml` with the persona, opportunity statement, and the discovered job(s) traced from interviews. DISCUSS will refine and lock this schema.
2. **Seed personas (optional)** — When persona-narrative expansion is triggered, write `docs/product/personas/{name}.yaml` with the validated persona profile. Otherwise leave to DISCUSS.
3. **No prior-wave Changed-Assumptions section** — DISCOVER produces evidence; it does not contradict prior decisions because there are none. The Changed-Assumptions pattern starts in DISCUSS.

Per D5 (lean-wave-documentation): DISCOVER's `docs/product/journeys/` feeder artifact stays Tier-1 — these are seed artifacts for the product SSOT, not feature-delta sections.

## Agent Invocation

1. **Dispatch Agent** — Invoke `@nw-product-discoverer` with `Execute *discover for {product-concept-name}`. Gate: agent dispatched.
2. **Provide Context Files** — Pass `docs/project-brief.md` and `docs/market-context.md` if available. Gate: available context files referenced.
3. **Apply Configuration** — Set `interactive: high`, `output_format: markdown`, `interview_depth: comprehensive`, `evidence_standard: past_behavior`. Gate: configuration confirmed.

## Peer Review Gate

1. **Dispatch Reviewer** — Invoke `@nw-product-discoverer-reviewer` before handoff to DISCUSS. Gate: reviewer dispatched, all discovery artifacts available.
2. **Verify Review Scope** — Reviewer checks: evidence quality (past behavior, not future intent), interview coverage and threshold compliance, assumption validation rigor (G1-G4 gates), lean canvas coherence with interview findings. Gate: all four dimensions assessed.
3. **Handle Rejection** — On REJECTION: revise artifacts per reviewer findings and re-submit. Gate: max 2 attempts; escalate to user if unresolved.
4. **Confirm Approval** — Block handoff to DISCUSS until reviewer returns APPROVED. Gate: explicit approval received.

## Success Criteria

Refer to Scout's quality gates in ~/.claude/agents/nw/nw-product-discoverer.md.

- [ ] All 4 decision gates passed (G1-G4)
- [ ] Minimum interview thresholds met per phase
- [ ] Evidence quality standards met (past behavior, not future intent)
- [ ] Peer review approved by @nw-product-discoverer-reviewer
- [ ] Handoff accepted by product-owner (DISCUSS wave)

## Next Wave

**Handoff To**: nw-product-owner (DISCUSS wave)
**Deliverables**: See Scout's handoff package specification in agent file

## Examples

### Example 1: New SaaS product discovery
```
/nw-discover invoice-automation
```
Scout conducts customer development interviews, validates problem-solution fit through Mom Test questioning, and produces a lean canvas with evidence-backed assumptions.

## Outputs

**Single narrative file**: `docs/feature/{feature-id}/feature-delta.md` — all DISCOVER findings (Tier-1 [REF] sections + any rendered Tier-2 expansions) live here.

**Machine artifacts**: none unique to DISCOVER (no parseable companions are produced).

**SSOT updates** (per Recommendation 3 / back-propagation contract):
- `docs/product/journeys/{name}.yaml` — initial drafts seeding the journey schema (DISCUSS refines)
- `docs/product/personas/{name}.yaml` — optional, only when persona-narrative expansion is rendered

Legacy multi-file outputs (`problem-validation.md`, `opportunity-tree.md`, `solution-testing.md`, `lean-canvas.md`, `interview-log.md`, `wave-decisions.md` as separate files) are NOT produced — that content lives in `feature-delta.md` under `## Wave: DISCOVER / [REF|WHY|HOW] <Section>` headings. Validator: `scripts/validation/validate_feature_layout.py`.
