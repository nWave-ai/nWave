---
name: nw-density-resolution-contract
description: "Shared density-resolution contract for wave skills. Canonical detail on the D12 cascade, density resolver call, ad-hoc override workflow, and DocumentationDensityEvent telemetry emission. Referenced from nw-discover / nw-discuss / nw-design / nw-devops / nw-distill / nw-deliver."
user-invocable: false
disable-model-invocation: true
---

# Density Resolution Contract (shared across wave skills)

This skill is the canonical source for the density-aware behaviour every wave skill must implement. Wave skills inherit it by reference and keep a brief inline summary so phrase-grep contract tests stay green; full detail lives here so the same boilerplate is not duplicated six times.

Provenance: feature `lean-wave-documentation` — D2 (schema-typed sections), D4 (telemetry instrumented day-one), D6 (first-install pedagogical prompt), D10 (one-line expansion descriptions), D12 (rigor cascade), DDD-5 (density resolver shared utility), DDD-6 (telemetry event lives in DES domain).

## Output Tiers (per D2 + D10)

Each wave emits a single `feature-delta.md` whose headings are typed `[REF]` (always emitted) or `[WHY]/[HOW]` (lazy expansions). Tier-1 is the always-on baseline; Tier-2 is the lazily-rendered expansion catalog. The `.feature` file (DISTILL) and other machine artifacts remain the SSOT for executable content; the wave-delta sections are pointers + structured summaries.

- **Tier-1 [REF]** — emitted under `## Wave: <NAME> / [REF] <Section>` headings on every run. Wave-specific list of `[REF]` sections lives in each wave skill.
- **Tier-2 EXPANSION CATALOG** — NOT emitted by default. Rendered only when explicitly requested via `--expand <id>` (DDD-2) or via the wave-end interactive prompt when `expansion_prompt = "ask"`. Each item has a one-line description (per D10) so the menu fits in a single render. Each emitted Tier-2 section is headed `## Wave: <NAME> / [WHY] <Section>` or `## Wave: <NAME> / [HOW] <Section>`. The catalog itself is wave-specific.

## Density resolution (per D12)

Before emitting any Tier-1 section, resolve the active documentation density:

1. **Read** `~/.nwave/global-config.json`. Treat missing/malformed config as empty dict (fall back to defaults).
2. **Call** `resolve_density(global_config)` from `scripts/shared/density_config.py`. The function returns a `Density` value object with fields `mode` (`"lean"` | `"full"`), `expansion_prompt` (`"ask"` | `"always-skip"` | `"always-expand"` | `"smart"`), and `provenance` (the cascade branch that produced this result).
3. **Branch on `density.mode`**:
   - `lean` → emit ONLY Tier-1 `[REF]` sections. Do NOT auto-render Tier-2 items.
   - `full` → emit Tier-1 `[REF]` sections PLUS all Tier-2 expansion items rendered under their `[WHY]` / `[HOW]` headings. This is auto-expansion (no menu).
4. **At wave end**, branch on `density.expansion_prompt`:
   - `"ask"` → present the expansion menu (Tier-2 catalog with one-line descriptions per D10) and append user-selected items as `## Wave: <NAME> / [WHY|HOW] <Section>` headings.
   - `"always-skip"` → no menu, no extra sections (idempotent re-runs, CI mode).
   - `"always-expand"` → equivalent to `mode = "full"` for this run; auto-render every Tier-2 item.
   - `"smart"` → out of scope for v1 (per OQ-3); treat as `"ask"` until heuristic is empirically tuned.

The resolver itself encodes the D12 cascade: explicit `documentation.density` override > `rigor.profile` mapping (`lean`→`lean`, `standard`→`lean`+`ask`, `thorough`→`full`, `exhaustive`→`full`+all-expansions, `custom`→`lean`+`ask`) > hard default `lean`+`ask`. Wave skills MUST NOT replicate the cascade locally — call `resolve_density(global_config)` and trust its output.

**Section heading prefix convention (per D2)**: every emitted section starts with `## Wave: <NAME> / [REF] <Section>` for Tier-1; `## Wave: <NAME> / [WHY] <Section>` or `## Wave: <NAME> / [HOW] <Section>` for Tier-2. Validator `scripts/validation/validate_feature_delta.py` enforces the regex `^## Wave: \w+ / \[(REF|WHY|HOW)\] .+$` on every wave heading.

### Ad-hoc override — user request mid-session

Even when `density.mode = "lean"` and `density.expansion_prompt = "always-skip"`, the user may ask DURING the wave session for specific expansions:

- "expand jtbd" / "expand jtbd-narrative" / "more on jtbd"
- "add alternatives considered"
- "show migration playbook"
- "tell me why" (interpretive — append the WHY rationale section relevant to the most recent decision)
- "more on <X>" (where `<X>` is one of the expansion catalog items for this wave)

When the user makes such a request:

1. Append the corresponding `[WHY]` or `[HOW]` section to `feature-delta.md` under the current wave's heading.
2. Emit a `DocumentationDensityEvent` with `choice="expand"` and `expansion_id=<the requested item>` to `JsonlAuditLogWriter`.
3. Do NOT modify `~/.nwave/global-config.json`. The override is ONE-SHOT for this wave only.

If the user's request matches NO item in the wave's Expansion Catalog, respond with the catalog list (one-line description per item per D10) and ask for clarification — do NOT improvise an expansion outside the catalog.

## Telemetry (per D4 + DDD-6)

Every expansion choice — whether the user expanded an item or skipped the menu — emits a structured event to the existing `JsonlAuditLogWriter` driven adapter.

**Event type**: `DocumentationDensityEvent` (dataclass at `src/des/domain/telemetry/documentation_density_event.py`).

**Schema fields** (per D4) — substitute the active wave name in the `wave` field:

```
{
  "feature_id": "<feature-id>",
  "wave": "<WAVE-NAME>",
  "expansion_id": "<id-from-catalog-or-'*'-for-skip-all>",
  "choice": "skip" | "expand",
  "timestamp": "<ISO-8601 datetime>"
}
```

**Emission pattern**:

1. Construct a `DocumentationDensityEvent(feature_id=..., wave="<WAVE>", expansion_id=..., choice=..., timestamp=...)`.
2. Call `event.to_audit_event()` to convert to the open `AuditEvent` shape (`event_type="DOCUMENTATION_DENSITY"` and the schema fields nested under `data`).
3. Dispatch via `JsonlAuditLogWriter().log_event(audit_event)`.

The wave-skill harness invokes the helper `scripts/shared/telemetry.py:write_density_event(...)` which performs all three steps. Wave skills MUST NOT bypass the helper or write JSONL directly — every density telemetry event flows through the shared helper to keep the audit-log schema consistent.

**When to emit**:

- One event per user choice in the expansion menu when `expansion_prompt = "ask"` (`choice = "expand"` for selected items, `choice = "skip"` with `expansion_id = "*"` if the user skips the entire menu).
- One synthetic `choice = "skip"` event with `expansion_id = "*"` when `expansion_prompt = "always-skip"` (records the skipped menu opportunity).
- One `choice = "expand"` event per Tier-2 item rendered when `mode = "full"` or `expansion_prompt = "always-expand"`.

This telemetry feeds the propagation success metric: when downstream waves consume a lean upstream feature-delta and produce no `--expand`, the `[REF]` baseline plus machine artifacts is sufficient.

## How wave skills reference this contract

Each wave skill keeps a short inline summary that:

1. Names the wave (e.g. `## Wave: DISTILL / [REF] <Section>`) and lists its own Tier-1 sections + Tier-2 expansion catalog (wave-specific content).
2. Re-states the `## Density resolution` heading + the resolver call + the `lean`/`full` mode branches + `expansion_prompt` key + the path `~/.nwave/global-config.json` + the resolver path `scripts/shared/density_config.py` (phrase-grep contract).
3. Re-states the `## Telemetry` heading + `DocumentationDensityEvent` + `JsonlAuditLogWriter` + `to_audit_event` + the schema fields (`feature_id`, `expansion_id`, `choice`, `timestamp`) + the wave-specific `"wave": "<WAVE>"` literal (phrase-grep contract).
4. Cites provenance decisions: `D2`, `D4`, `D10`, `D12`, `DDD-5`, `DDD-6`.
5. References this shared skill for the full how-to instead of duplicating the explanation.

The contract phrases are pinned by `tests/des/unit/skills/test_wave_skills_density_aware.py`; any wave skill missing a phrase fails that test. The shared skill is the source of truth for the BEHAVIOUR; the wave skills are the source of truth for the WAVE-SPECIFIC content (Tier-1 list, Tier-2 catalog, wave heading prefix).
