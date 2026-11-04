# Feature directory format reference

**Status: 3.x-era reference.** Both layouts below are 3.x formats. The v4
delivery route records a feature in one nwdes handoff
(`docs/feature/{id}/handoff.json`) with rendered briefs and run records; it
writes neither layout. Keep this page to read and maintain existing 3.x
features. See [Migrate from nWave 3.x](../guides/migrating-from-3x.md).

nWave supported two directory layouts for feature documentation: **legacy** (multi-file per wave) and **lean** (single L7 file).

## Quick reference

| Aspect | Legacy | Lean L7 |
|--------|--------|---------|
| **Layout** | `docs/feature/{id}/discuss/`, `design/`, `distill/`, `deliver/` subdirs with separate files | Single `feature-delta.md` per feature |
| **Identifier** | No marker (implicit legacy) | `FORMAT: lean` in dir or file frontmatter |
| **Section typing** | No explicit type labels | `## Wave: <WAVE> / [REF\|WHY\|HOW] <Section>` headings |
| **Concurrent waves** | Manual conflict resolution | Git auto-resolves via wave-owned section ownership |
| **Density control** | Not applicable | `lean` (refs only) or `full` (all sections) |
| **Tooling** | Existing scripts, agents familiar | Heading schema checked by review; no installed validator |
| **Status** | Read-only history | Superseded by the v4 nwdes handoff |

---

## Legacy layout (multi-file)

The legacy layout organizes wave outputs into separate files grouped by wave.

### Directory structure

```
docs/feature/{feature-id}/
├── discover/
│   ├── research-notes.md
│   ├── evidence.md
│   └── opportunity-statement.md
├── discuss/
│   ├── elevator-pitch.md
│   ├── job-statement.md
│   ├── user-stories.md
│   ├── acceptance-criteria.md
│   ├── definition-of-done.md
│   └── dor-validation.md
├── design/
│   ├── component-decomposition.md
│   ├── decisions.md
│   ├── driving-ports.md
│   └── adr-001.md
├── distill/
│   ├── acceptance-scenarios.feature
│   ├── test-strategy.md
│   └── edge-cases.md
├── deliver/
│   ├── implementation-notes.md
│   ├── commits.md
│   └── retrospective.md
└── wave-decisions.md (optional, consolidated decisions across all waves)
```

### Characteristics

- **File-per-concern**: Each artifact (user stories, decisions, scenarios, etc.) is a separate `.md` file.
- **Wave-grouped**: Files live in subdirectories named after the wave they belong to.
- **No sectioning discipline**: Headings are free-form within each file.
- **Merge conflicts**: Parallel waves writing to the same file can create merge conflicts in git.
- **Existing features**: All currently-tracked features in the repo use this layout.

### When to use

- Existing features that are already documented in legacy layout.
- Teams with established conventions for file organization.
- Features where per-file separation helps with parallel authoring (e.g., separate writer per wave).

---

## Lean L7 layout (single-file)

The lean L7 layout consolidates all wave outputs into a single `feature-delta.md` file with schema-typed section headings.

### Directory structure

```
docs/feature/{feature-id}/
├── feature-delta.md        # Single file, all waves, schema-typed headings
└── FORMAT                  # Optional marker containing "lean"
```

Alternatively, the `FORMAT` information can be recorded in YAML frontmatter at the top of `feature-delta.md`:

```yaml
---
format: lean
---

# feature-delta — {feature-id}

## Wave: DISCOVER / [REF] Research findings
...
```

### Single narrative + machine companions (R5, 2026-04-28)

The lean contract is **not** "one file ever". It is "one narrative file plus declared machine companions plus SSOT integration". Some waves legitimately emit machine-parseable companions alongside `feature-delta.md`:

| Wave | Machine companion(s) | Why declared |
|------|----------------------|--------------|
| DEVOPS | `environments.yaml` | DISTILL parses environment matrix to parametrize acceptance scenarios |
| DISTILL | `*.feature` files + `steps/**` modules | Executable Gherkin specs; pytest-bdd discovery requires per-file layout |
| DELIVER | `roadmap.json`, `execution-log.json` | Legacy runtime files for phase tracking; the current `nwdes` route records the handoff and run records instead |
| All waves | `slices/slice-NN-*.md` (when used) | Per-slice briefs are inherently per-file; PO reviewer enforces composition |
| Spikes | Findings in the caller-owned workspace | A spike keeps its artifacts and findings in the caller's persistent workspace, outside the feature directory; nothing is promoted automatically |
| Bug fixes | `bugfix/rca.md` | RCA artifacts kept separate from feature-delta narrative |

**Machine companion rule**: only files whose downstream consumer is a parser (validator, agent, runtime) qualify. Loose human-readable markdown does NOT qualify and MUST live inside `feature-delta.md` as a `## Wave: <NAME> / [REF|WHY|HOW] <Section>` block.

**Validator**: none is installed. `scripts/validation/validate_feature_layout.py` no longer exists in this repository; the heading schema is checked by review against the table above. This rule was motivated by an internal audit of over-testing patterns in generated feature layouts (2026-04-28).

**SSOT integration** (separate concern): durable product files live under `docs/product/`. `/nw-discover` bootstraps `vision.md`, `jobs.yaml` and `kpi-contracts.yaml`; `/nw-diverge` updates `jobs.yaml`.

### Section heading schema

Every section heading in a lean L7 file follows this pattern:

```
## Wave: <WAVE> / [<TYPE>] <Section name>
```

**Components**:

- **`<WAVE>`**: One of `DISCOVER`, `DISCUSS`, `DESIGN`, `devOPS`, `DISTILL`, `DELIVER`
- **`<TYPE>`**: One of three:
  - **`[REF]`**: Reference/factual content — definitions, specs, acceptance criteria, locked decisions, user stories (Elevator Pitch only), scenarios, deliverables.
  - **`[WHY]`**: Explanatory/rationale content — persona narrative, JTBD analysis, design alternatives weighed, architecture rationale, retrospective insights.
  - **`[HOW]`**: Procedural/instructional content — migration guides, integration steps, manual processes, troubleshooting guides.

- **`<Section name>`**: Human-readable title (e.g., `User stories`, `Acceptance scenarios`, `Decisions`, `Persona narrative`).

### Examples

**Lean output** (default, when density is `lean`):

```markdown
## Wave: DISCUSS / [REF] Persona

Marco — solo developer iterating on nWave.

## Wave: DISCUSS / [REF] Job-to-be-done

When I run /nw-discuss on a small feature, I want the wave to produce only load-bearing content so my session stays under token budget.

## Wave: DISCUSS / [REF] User stories

### US-1: Lean-by-default wave output

Elevator Pitch: Marco runs /nw-discuss and gets a feature-delta.md with only [REF] sections.

...

## Wave: DESIGN / [REF] Component decomposition

| # | Component | Path | Change type | Owner wave consumer |
|---|---|---|---|---|
| C1 | Wave skill — DISCUSS | nWave/skills/nw-discuss/SKILL.md | Edit | DISCUSS |
```

**Full output** (when density is `full`):

```markdown
## Wave: DISCUSS / [REF] Persona

Marco — solo developer iterating on nWave.

## Wave: DISCUSS / [WHY] Persona narrative

Marco's goals: fast iteration, low token cost, scale to bigger features...

## Wave: DISCUSS / [REF] Job-to-be-done

When I run /nw-discuss on a small feature...

## Wave: DISCUSS / [WHY] JTBD narrative

Four forces analysis: push (token bloat), pull (context efficiency), anxiety (missing decisions), habit (legacy multi-file)...
```

### Wave-owned section ownership (D3)

Critical rule for concurrent waves: **each wave owns its own wave heading**. No wave appends sections to another wave's heading.

**Valid concurrent edits**:
```markdown
## Wave: DISCUSS / [REF] Decisions (wave A writes here)

...

## Wave: DESIGN / [REF] Decisions (wave B writes here)

...
```

**Invalid (violates D3)**:
```markdown
## Wave: DISCUSS / [REF] Decisions

... (initial content by DISCUSS)

More content added by DESIGN ← WRONG: DESIGN cannot append to DISCUSS's section
```

When two waves write independently under their own headings, git auto-resolves the merge cleanly.

### Characteristics

- **Single file**: All wave outputs consolidated.
- **Schema-typed headings**: Every heading declares its content type via `[REF]/[WHY]/[HOW]` prefix.
- **Density-aware**: Lean mode emits only `[REF]`; full mode emits `[REF]` + `[WHY]` + `[HOW]`.
- **Expansion-ready**: Optional `[WHY]` and `[HOW]` sections can be added post-wave via `--expand` flag.
- **Auto-merge friendly**: Wave-owned sections in separate headings avoid conflicts.
- **Agent-grep friendly**: Downstream agents can grep for specific section types and waves.

### When to use

- **New features (3.x)**: greenfield features used lean L7; the v4 route records new features in the nwdes handoff instead.
- **Token-conscious workflows**: Teams minimizing context bloat.
- **Parallel wave execution**: Features running multiple waves on separate worktrees.
- **Audit compliance**: Teams requiring clear traceability of who wrote what in which wave.

---

## Migration: legacy to lean L7 (retired)

The opt-in migration script (`scripts/migrate_to_l7.py`) no longer exists in
this repository. To move 3.x feature work to the v4 route, restart it from the
original request with `nwdes feature new`; there is no converter for the old
files ([Migrate from nWave 3.x](../guides/migrating-from-3x.md)).

---

## Bimodal navigation for users

### How to tell which layout a feature uses

1. **Check the directory**: Does it have `feature-delta.md` in the root, or does it have `discuss/`, `design/`, `distill/` subdirectories?

2. **Check the FORMAT marker**: If present, `docs/feature/{id}/FORMAT` will contain either `legacy` or `lean`.

3. **Grep for wave headings**: Lean files use `## Wave: DISCUSS / [REF]` pattern; legacy files use arbitrary headers in wave subdirs.

### How to find what you're looking for

**In a legacy feature**:
- User stories → `discuss/user-stories.md`
- Decisions → `design/decisions.md` or `wave-decisions.md`
- Test scenarios → `distill/acceptance-scenarios.feature`

**In a lean feature**:
- User stories → `feature-delta.md` heading `## Wave: DISCUSS / [REF] User stories`
- Decisions → `feature-delta.md` heading `## Wave: DESIGN / [REF] Decisions`
- Test scenarios → `feature-delta.md` heading `## Wave: DISTILL / [REF] Acceptance scenarios`

**Search tip**: Both layouts support standard text search (grep, VS Code find).
```bash
grep -r "US-1" docs/feature/my-feature/
```

---

## Schema validation (developer)

No installed command validates lean L7 files; the current delivery route ships
no feature-delta validator. Check headings by review against the schema above.
A heading is valid when it has the form `## Wave: <WAVE> / [REF|WHY|HOW] <Section>`,
the wave is one of the six named waves and no heading repeats within a wave.

### Common heading failures

| Error | Cause | Fix |
|-------|-------|-----|
| `Malformed heading: missing [TYPE] prefix` | `## Wave: DISCUSS / User stories` (missing `[REF]`) | Add the type: `## Wave: DISCUSS / [REF] User stories` |
| `Invalid wave name: ANALYSE` | `## Wave: ANALYSE / ...` (typo) | Correct to one of: DISCOVER, DISCUSS, DESIGN, DEVOPS, DISTILL, DELIVER |
| `Invalid type: [EXPLANATION]` | `## Wave: DISTILL / [EXPLANATION] ...` (wrong token) | Use `[REF]`, `[WHY]`, or `[HOW]` |
| `Section appears twice` | Two `## Wave: DISCUSS / [REF] Decisions` headings | Merge or rename one heading |

---

## Future extensions (roadmap)

- **Automatic density inheritance**: Features created with `rigor: "lean"` default to lean L7; features with `rigor: "thorough"` default to full density.
- **Per-feature density override**: Override global density on a per-feature basis without editing `global-config.json`.
- **Migration automation**: Detect legacy features at CI time and suggest migration.
- **IDE support**: VS Code extension for lean L7 syntax highlighting and schema validation.

---

## Related documentation

- **User guide**: [How to author a feature using the L7 single-file model](../guides/feature-delta-l7-format.md)
- **Config reference**: [nWave Global Config Reference](./global-config.md)
- **How-to guide**: [How to configure documentation density](../guides/configuring-doc-density.md)
