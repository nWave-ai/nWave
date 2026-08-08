# How to configure documentation density

This guide shows you how to control how much narrative detail nWave includes in wave output. Learn to balance token cost against documentation completeness.

## Prerequisites

- nWave installed via `nwave-ai install` (if not, see the [installation guide](installation-guide/README.md))
- A text editor (vim, nano, VS Code, Notepad, etc.)
- Basic familiarity with JSON files

## Quick start: Change density via config

**Step 1**: Open your config file.

```bash
# macOS / Linux
vim ~/.nwave/global-config.json

# Windows (VS Code)
code $env:APPDATA\.nwave\global-config.json
```

**Step 2**: Find or add the `documentation.density` key.

```json
{
  "documentation": {
    "density": "lean"
  }
}
```

Valid values:
- `"lean"` — minimal prose, refs only (~40% of legacy token cost)
- `"full"` — complete prose, all sections inline

**Step 3**: Save the file and verify.

```bash
nwave-ai doctor
```

You should see: `Documentation density: lean (explicit override)`

---

## Common use cases

### Use case 1: I want lean output by default

**Situation**: You're a solo developer iterating quickly. Token cost matters. You want feature-delta files to include only the essential specs, decisions, and scenarios — no JTBD narrative or persona essays.

**Solution**:

```json
{
  "rigor": {
    "profile": "lean"
  }
}
```

Or explicitly:

```json
{
  "documentation": {
    "density": "lean",
    "expansion_prompt": "always-skip"
  }
}
```

**Result**:
- Every wave produces `feature-delta.md` with only `[REF]` sections (factual content: personas, job statements, specs, decisions, scenarios).
- Optional expansions (JTBD narratives, alternatives considered, migration playbooks) are skipped.
- Each feature-delta file averages **≤60% of legacy token cost**.

**Next step**: If you need more detail on a specific feature, see "Ad-hoc expansion" below.

---

### Use case 2: I want full output for a feature handoff

**Situation**: You're handing off a complex feature to a teammate. You want comprehensive documentation with all the rationale, design alternatives, and migration guidance inline — no surprises.

**Solution**:

```json
{
  "documentation": {
    "density": "full"
  }
}
```

**Result**:
- Every wave produces feature-delta.md with all sections: `[REF]` (facts) + `[WHY]` (rationale) + `[HOW]` (procedures).
- JTBD narratives, alternatives, and migration playbooks are included inline.
- Your teammate reads the complete story in one file.

---

### Use case 3: I want context-aware (smart)

**Situation**: You want nWave to decide per feature. Simple bugfixes get lean output. Complex architectural changes get full output. Token-efficient but complete where it matters.

**Solution**:

```json
{
  "documentation": {
    "expansion_prompt": "smart"
  }
}
```

**Note**: This is experimental in v3.14. Feedback welcome.

**Result**:
- Wave agents analyze the feature complexity and choose density automatically.
- Small fixes lean toward `[REF]` only.
- Large features lean toward `[REF]` + recommended `[WHY]` sections.

---

### Use case 4: I want a scoped expansion menu (`ask-intelligent`)

**Situation**: The full `ask` menu lists every Tier-2 expansion in the catalog, most of which are irrelevant to the wave you just ran. You want to be offered only what this wave actually surfaced.

**Solution**:

```json
{
  "documentation": {
    "expansion_prompt": "ask-intelligent"
  }
}
```

**This is the fresh-install default** (Decision 4, 2026-04-28). A fresh `nwave-ai install` writes `"expansion_prompt": "ask-intelligent"` into `~/.nwave/global-config.json`, and it is also the value the resolver falls back to when neither `documentation.expansion_prompt` nor `rigor.profile` is set.

**Result**:
- **WHEN** a wave ends, the system **SHALL** show a menu containing only those Tier-2 expansions whose trigger fired during that wave — not the whole catalog.
- **WHERE** no trigger fired, no menu is shown and the wave ends at its lean baseline.
- Trigger detection lives in the wave skill prose, not in the density resolver.

**Accepted values**: `ask`, `ask-intelligent`, `always-skip`, `always-expand`, `smart`. **IF** `documentation.expansion_prompt` holds anything else, the density resolver **SHALL** reject the configuration with an error naming the accepted values, rather than silently ignoring the setting.

---

## Ad-hoc expansion (override at wave time)

Even with `density: "lean"` and `expansion_prompt: "always-skip"`, you can request more detail during a specific wave **without** changing your global config.

### Method 1: Use the `--expand` flag

When running a wave, pass the `--expand` flag with a comma-separated list of expansion IDs:

```bash
/nw-discuss my-complex-feature --expand jtbd-narrative,alternatives-considered
```

**Result**: The wave produces lean base content + the two requested expansions. The feature-delta file gains:
- `## Wave: DISCUSS / [WHY] JTBD narrative`
- `## Wave: DISCUSS / [WHY] Alternatives considered`

**Idempotent**: Running expand again on the same feature skips already-present sections (no duplication).

### Method 2: Respond to the wave-end prompt

If `expansion_prompt` is `"ask"` (full catalog) or `"ask-intelligent"` (only triggered items):

```bash
/nw-discuss my-complex-feature
```

At the end of the wave, you see:

```
Expand any of these?

1. jtbd-narrative       Full Job-to-be-Done analysis with four forces
2. persona-narrative    Extended persona (goals, frustrations, environment)
3. alternatives-considered  Design alternatives weighed and rejected
4. migration-playbook   Procedural notes for migrating existing surfaces

Select (1,2,3,4) or press Enter to skip:
```

**Enter** a number to add that expansion (e.g., `1` adds JTBD narrative). **Press Enter** with no input to skip all. You can select one or more:

```
Select (1,2,3,4) or press Enter to skip: 1,3
```

Adds JTBD narrative + alternatives-considered to the same wave's feature-delta.

### Finding available expansions

Each wave's feature-delta lists available expansions in the `[REF] Expansion catalog` section.

```bash
grep -A 20 "Expansion catalog" docs/feature/my-feature/feature-delta.md
```

Available expansion IDs per wave:
- **DISCUSS**: `jtbd-narrative`, `persona-narrative`, `alternatives-considered`, `research-synthesis`, etc.
- **DESIGN**: `adr-rationale`, `alternatives-technical`, etc.
- **DISTILL**: `edge-cases-deep-dive`, etc.
- **DELIVER**: `retrospective`, `lessons-learned`, etc.

---

## Rigor profiles and density inheritance

Your `rigor` profile affects the default density if you don't explicitly set `documentation.density`.

### Profile cascade table

| Profile | If `density` unset | If `density` unset |
|---------|---|---|
| `lean` | → density: `"lean"` | → expansion_prompt: `"always-skip"` |
| `standard` | → density: `"lean"` | → expansion_prompt: `"ask-intelligent"` |
| `thorough` | → density: `"full"` | → expansion_prompt: `"always-expand"` |
| `exhaustive` | → density: `"full"` | → expansion_prompt: `"always-expand"` |
| `custom` | → density: `"lean"` (fallback) | → expansion_prompt: `"ask-intelligent"` (fallback) |

**No `rigor.profile`, no `documentation` block** (fresh install): density `"lean"`, expansion_prompt `"ask-intelligent"`.

**What this means**:

- Start with `rigor: "lean"` for solo iteration. Lean density + auto-skip expansions by default.
- Move to `rigor: "standard"` for team work. Lean density + interactive expansion menu.
- Use `rigor: "thorough"` for regulated environments. Full density + all expansions inline.

**Override**: Explicit `documentation.density` **always** wins, even if `rigor` suggests otherwise:

```json
{
  "rigor": {
    "profile": "thorough"
  },
  "documentation": {
    "density": "lean"
  }
}
```

This combination means: high ceremony (thorough wave validation) but minimal prose (lean output).

---

## Verification: Check your density setting

```bash
nwave-ai doctor
```

Look for the line:

```
Documentation density: lean (explicit override)
```

or

```
Documentation density: lean (inherited from rigor profile: standard)
```

or

```
Documentation density: full (default)
```

The suffix tells you where the setting came from:
- `(explicit override)` — you set `documentation.density` directly
- `(inherited from rigor profile: ...)` — derived from your `rigor.profile`
- `(default)` — no override, using fallback

---

## Troubleshooting

### Q: I set `density: "lean"` but the output still has lots of narrative. Why?

**A**: Check two things:

1. **Is `expansion_prompt: "always-expand"`?** If so, all expansions are auto-included even in lean mode.

   ```bash
   # Fix: Change to ask or always-skip
   nwave-ai doctor | grep expansion_prompt
   ```

2. **Are you running with `--expand <ids>`?** The flag overrides density for that run.

   ```bash
   # You ran: /nw-discuss my-feature --expand jtbd-narrative
   # This adds JTBD narrative on top of lean base.
   # To get pure lean, don't use --expand flag.
   ```

### Q: My config file doesn't exist. What's the default?

**A**: Run `nwave-ai install` again. The first-run prompt will ask for density preference:

```
Documentation density: lean (experienced developer) / full (first feature)?
```

Pick one. It's saved and never prompted again (idempotent).

### Q: Can I have different density for different features?

**A**: Not in v3.14. The global config applies to all features. Per-feature overrides are on the roadmap.

### Q: What if I'm running in CI (non-interactive)?

**A**: When there's no terminal (TTY), interactive prompts are skipped. nWave defaults to `always-skip` behavior for expansions, even if `expansion_prompt` is `"ask"` or `"ask-intelligent"`. Lean output is still produced. To include specific expansions in CI:

```bash
/nw-discuss my-feature --expand jtbd-narrative
```

The `--expand` flag works in non-interactive contexts.

### Q: My teammate wants full documentation. Should they change the global config or use `--expand`?

**A**: Depends on their workflow:

- **One-time**: Use `--expand <ids>` for that wave.
- **Permanent preference**: Change `documentation.density` in `~/.nwave/global-config.json`.
- **Team default**: Coordinate on a rigor profile in project-level documentation and share the recommended `global-config.json` template.

---

## Related guides

- **[nWave Global Config Reference](../reference/global-config.md)** — detailed reference for all config keys
- **[Feature directory format reference](../reference/feature-format.md)** — understand `[REF]`, `[WHY]`, `[HOW]` section types
- **[How to author a feature using the L7 single-file model](feature-delta-l7-format.md)** — writing lean feature-delta files
