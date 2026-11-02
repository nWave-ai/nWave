# What's New in nWave v3.14

> **Historical release note.** The L7 `feature-delta.md` carrier, its validator,
> enforcement recipes and `outcomes check-delta` integration described below
> have been retired by the canonical DeliveryContract cutover. They are not
> current authoring or CLI guidance.

## Lean Wave Documentation (L7 single-file)

Each feature now lives in **one** `feature-delta.md` instead of ~26 files across per-wave subdirectories. Section headings carry the wave + content type as schema-typed labels (`## Wave: <WAVE> / [REF|WHY|HOW] <name>`).

**What it does**: Tier-1 `[REF]` content is auto-produced by every wave; Tier-2 `[WHY]` and `[HOW]` are opt-in via `--expand`. Downstream agents grep section headings instead of reading whole subdirectories — large token savings on every wave handoff.

**When to use**: Default. All new features authored after v3.14 use L7.

**When to skip**: Legacy features still on the per-wave layout work as before; migrate at your own pace via the lossless migration script.

See [Feature Delta Format (L7)](../feature-delta-l7-format.md) for the authoring guide and [Wave Directory Structure](../wave-directory-structure/) for the broader layout.

## Feature-Delta Validator

A new CLI command — `nwave-ai validate-feature-delta <path>` — checks structural rules (E1–E5) on any L7 file in <1s. Exits 1 naming the violation, 0 on clean.

**What it does**: Catches silent cross-wave commitment erosion (DISCUSS commits to X, DESIGN downgrades to Y without flagging it). Emits JSON for CI integration. Pure stdlib, no network call, zero side effects.

**Historical use**: this was offered as a CI gate on changes to the retired carrier.

**When to skip**: Vendor-neutral by design — no hooks auto-installed. You opt in to the integration surface that fits your stack.

## Outcomes Registry — Design-Time Deduplication

Catch duplicated rules and operations at **design time**, before code is written. Uses type-shape hashing (Tier-1) + keyword Jaccard (Tier-2) over a YAML registry seeded with shipped outcomes.

**What it does**: Three new CLI subcommands:

| Command | Use |
|---------|-----|
| `nwave-ai outcomes register` | Add a new outcome to the registry |
| `nwave-ai outcomes check` | Check a candidate outcome against the registry (pre-write) |
| `nwave-ai outcomes check-delta` | Check all outcomes mentioned in a feature-delta against the registry |

**When to use**: At DISTILL or DESIGN time, before writing a new validation rule, format check, or business-logic operation. Wired into `nw-distill` and `nw-design` skills.

**When to skip**: Doc-only features, prose-only changes, or single-feature spike work.

See [Your first outcome](../outcomes-first-outcome/) for a 6-step walkthrough and [Outcomes CLI reference](../../reference/outcomes-cli.md) for full subcommand details.

## Document Reading Views

For the current delivery route, nwdes renders full briefs and HTML. See
[Documentation Detail](../configuring-doc-density.md). The v3 density-driven
rendering instructions no longer apply.

## DISTILL + DESIGN — Outcome-Aware

Both `/nw-distill` and `/nw-design` now invoke the outcomes registry as part of their phase work:

- **DISTILL** registers each new acceptance scenario's outcome and runs collision check before locking the scenario.
- **DESIGN** registers each new structural rule or component contract and surfaces collisions before commit.

A registry collision does not auto-block — it surfaces the conflict for human adjudication (link, supersede, or proceed-anyway).

## Skill Maintenance

- Per-wave peer review is now optional and consolidated at the end of DISTILL (was: every wave). Reduces token cost by ~15% on uncontested features.
- Legacy "Expected Outputs" sections excised from 6 wave skills (superseded by L7 schema-typed headings).

## Improvements in v3.14.0-rc1 (2026-05-03)

Two user-observable behavior changes since the v3.14.0 base ship:

- **Uninstall correctness fix** — v3.14.0-rc1 corrected residual framework assets after uninstall. For current removal guidance see [Troubleshooting](../troubleshooting-guide/#uninstall-left-files-behind).
- **Pre-push hook ~50% faster on master** — the local pre-push hook chain dropped from 25-30 min to ~13 min. Two changes: (1) docs/CI/hook-only commits now skip the pytest validation entirely (3-5 min saved per commit); (2) the e2e tier on master pre-push runs only the critical-path smoke subset (4 files, ~41 tests) instead of all 20 e2e files — the full e2e suite continues to gate every PR via CI.

## Upgrading from v3.13

No breaking changes. New features are opt-in:

- L7 layout coexists with the per-wave layout — migrate at your pace.
- Validator is not auto-installed — pick a recipe.
- Outcomes registry is empty by default — populate as you author new outcomes.
- Density defaults to `lean`, override per project.

For older upgrades, see [What's New in v3.5](../whats-new-v35/).
