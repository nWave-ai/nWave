# How to author a feature using the L7 single-file model

> **Transition notice (added 2026-08-10)**: this guide is accurate for
> repositories using the current `feature-delta.md` compatibility runtime.
> `feature-delta.md` is being migrated away from as the target model: the
> current v4 delivery route records features in an nwdes handoff
> (`docs/feature/<id>/handoff.json` in your repository) instead. Do not
> start new work by treating feature-delta as the target model.

This guide teaches you how to write or migrate a feature to the lean L7 single-file model: one `feature-delta.md` per feature with schema-typed section headings.

## Prerequisites

- A text editor or IDE (VS Code, vim, etc.)
- Basic markdown knowledge
- Familiarity with the [Feature directory format reference](../reference/feature-format.md)
- Understanding of nWave's six waves: DISCOVER, DISCUSS, DESIGN, DEVOPS, DISTILL, DELIVER
- New to nWave? Read [Wave Directory Structure](wave-directory-structure/) first to understand how artifacts are organized.

## Quick start: The L7 section heading pattern

Every section in a lean `feature-delta.md` follows this pattern:

```markdown
## Wave: <WAVE> / [<TYPE>] <Section name>
```

**Examples**:

```markdown
## Wave: DISCUSS / [REF] User stories
## Wave: DISCUSS / [WHY] JTBD narrative
## Wave: DESIGN / [REF] Component decomposition
## Wave: DESIGN / [HOW] Migration playbook
## Wave: DISTILL / [REF] Acceptance scenarios
```

**Rules**:

| Part | Valid values | Example |
|------|---|---|
| `<WAVE>` | DISCOVER, DISCUSS, DESIGN, DEVOPS, DISTILL, DELIVER | `DISCUSS` |
| `<TYPE>` | `[REF]`, `[WHY]`, `[HOW]` | `[REF]` = reference/factual; `[WHY]` = rationale/explanation; `[HOW]` = procedure/instruction |
| `<Section name>` | Human-readable title | `User stories`, `Decisions`, `Acceptance scenarios` |

---

## Understanding section types

### `[REF]` — Reference / Factual content

Use `[REF]` for specification, requirements, facts, and outcomes that do **not** explain rationale.

**What belongs here**:
- Persona definitions
- Job-to-be-done elevator pitch
- User stories (elevator pitch + AC only; rationale goes in `[WHY]`)
- Acceptance criteria
- Locked decisions and decision tables
- Acceptance scenarios (gherkin)
- Architecture diagrams and component lists
- API specs
- Test execution results
- Definition of done

**Example**:

```markdown
## Wave: DISCUSS / [REF] User stories

### US-1: Lean-by-default wave output

**Elevator Pitch**: Marco runs `/nw-discuss` on a small feature and gets a feature-delta.md containing only `[REF]` sections so the wave hands off ≤30% of legacy token volume to DESIGN.

**Acceptance criteria**:
- AC-1: `/nw-discuss` produces feature-delta.md with only [REF] sections
- AC-2: Token count ≤60% of legacy baseline
- AC-3: All Tier-1 fields are present
```

### `[WHY]` — Rationale / Explanation

Use `[WHY]` for context, justification, alternatives weighed, and lessons learned.

**What belongs here**:
- Persona narrative (extended goals, frustrations, environment)
- Full JTBD analysis (four forces: push, pull, anxiety, habit)
- Design alternatives considered and why rejected
- Architecture rationale and trade-offs
- Research findings and synthesis
- Risk analysis
- Lessons learned and retrospectives

**Example**:

```markdown
## Wave: DISCUSS / [WHY] JTBD narrative

**Push forces** (pain in status quo):
- Legacy multi-file docs create token bloat for downstream agents
- Merge conflicts in parallel waves slow coordination

**Pull forces** (attraction to new state):
- Consolidated single file → agent grep efficiency
- Wave-owned sections → auto-merge friendly

**Anxiety** (resistance to change):
- Learning curve for authors unfamiliar with L7 schema
- Migration burden on existing 10+ features

**Habit** (inertia):
- Team used to `discuss/`, `design/` subdirectory pattern
```

### `[HOW]` — Procedure / Instruction

Use `[HOW]` for steps, procedures, integration guides, and operational tasks.

**What belongs here**:
- Migration playbooks
- Integration steps
- Manual procedures
- Troubleshooting guides
- Operational run-books
- Configuration steps
- Deployment procedures

**Example**:

```markdown
## Wave: DELIVER / [HOW] Migration playbook

1. Back up the legacy feature directory: `git checkout -b backup/my-feature`
2. Run the migration script: `python scripts/migrate_to_l7.py docs/feature/my-feature`
3. Review the generated `feature-delta.md` for accuracy
4. Commit: `git add docs/feature/my-feature/feature-delta.md && git commit -m "..."`
5. Review the headings and content against the format described here.
```

---

## Migrating from legacy layout

Use the automated migration script to convert existing features to L7.

### Step 1: Backup

```bash
git checkout -b backup/my-feature
```

### Step 2: Run the migration script

```bash
python scripts/migrate_to_l7.py docs/feature/my-feature
```

**What it does**:
1. Reads all files from `docs/feature/my-feature/{discover,discuss,design,devops,distill,deliver}/`
2. Classifies each artifact by type (user story, decision, scenario, etc.)
3. Writes `feature-delta.md` with proper `## Wave: ... / [TYPE]` headings
4. Demotes optional content (JTBD narrative, persona essays, migration guides) to `[WHY]/[HOW]` sections (lean-compatible)
5. Creates a `FORMAT` marker containing `"lean"`

### Step 3: Review

```bash
# See what was migrated
git diff docs/feature/my-feature/feature-delta.md

# Check for migration warnings
cat docs/feature/my-feature/feature-delta.md | grep "review-needed"
```

If you see `<!-- review-needed -->` comments, sections with unclear classification are marked. Review and manually organize as needed.

### Step 4: Review the format

Check the headings against the examples in this guide. This document format
does not have a current CLI validation gate.

### Step 5: Commit

```bash
git add docs/feature/my-feature/
git commit -m "docs(feature/my-feature): migrate to lean L7 single-file format"
```

### Step 6: Rollback (if needed)

If anything goes wrong:

```bash
git reset --hard origin/master
```

Legacy subdirectories are untouched by the script, so you can inspect and retry.

---

## Migration script options

```bash
python scripts/migrate_to_l7.py --help
```

### `--dry-run`

Preview what would be migrated without writing:

```bash
python scripts/migrate_to_l7.py docs/feature/my-feature --dry-run
```

### `--force`

Overwrite an existing `feature-delta.md`:

```bash
python scripts/migrate_to_l7.py docs/feature/my-feature --force
```

### `--preserve-legacy`

Keep legacy `discuss/`, `design/`, etc. subdirectories after migration (default; shown for clarity):

```bash
python scripts/migrate_to_l7.py docs/feature/my-feature --preserve-legacy
```

### `--no-preserve-legacy`

Delete legacy subdirectories after migration:

```bash
python scripts/migrate_to_l7.py docs/feature/my-feature --no-preserve-legacy
```

---

## Authoring new features in L7

When you create a new feature from scratch, use L7 from the start.

### Step 1: Create the directory

```bash
mkdir -p docs/feature/my-new-feature
```

### Step 2: Create the file

Create `docs/feature/<feature-id>/feature-delta.md` with the L7 heading pattern.

Or use the template (if available):

```bash
cp docs/templates/feature-delta-template.md docs/feature/my-new-feature/feature-delta.md
```

Edit to fill in your feature details.

### Step 3: Organize by wave

As each wave executes, add its sections under the appropriate `## Wave: ...` heading.

**Important rule (D3)**: Each wave owns its own heading. One wave does not append to another wave's `## Wave:` heading.

```markdown
## Wave: DISCUSS / [REF] User stories

... (DISCUSS adds content here)

## Wave: DISCUSS / [WHY] JTBD narrative

... (DISCUSS may add optional expansions here)

## Wave: DESIGN / [REF] Component decomposition

... (DESIGN adds its own wave heading — never appends to DISCUSS's heading)
```

### Step 4: Review the format

After each wave, review the headings and section content against this guide.

### Step 5: Commit

```bash
git add docs/feature/my-new-feature/feature-delta.md
git commit -m "docs(feature/my-new-feature): DISCUSS wave"
```

---

## Concurrent wave authoring (parallel worktrees)

When multiple waves run on separate worktrees, L7 handles merge cleanly via wave-owned sections.

### Setup

```bash
# Create worktree for DESIGN wave
git worktree add ../feature-design feature/my-feature

# Create worktree for DISTILL wave
git worktree add ../feature-distill feature/my-feature
```

### Wave A (DESIGN)

In `../feature-design`:

```markdown
## Wave: DESIGN / [REF] Component decomposition

| # | Component | Path | Change type |
|---|---|---|---|
| C1 | Wave skill — DISCUSS | nWave/skills/nw-discuss/SKILL.md | Edit |
```

Commit: `git commit -m "docs(feature): DESIGN wave"`

### Wave B (DISTILL)

In `../feature-distill`:

```markdown
## Wave: DISTILL / [REF] Acceptance scenarios

Scenario: Lean wave produces only [REF] sections
  Given ...
  When ...
  Then ...
```

Commit: `git commit -m "docs(feature): DISTILL wave"`

### Merge

In the main worktree:

```bash
git merge ../feature-design
git merge ../feature-distill
```

**Result**: Both `## Wave: DESIGN ...` and `## Wave: DISTILL ...` sections coexist cleanly with no conflicts. Git recognizes they're in separate headings.

---

## Schema validation troubleshooting

### Error: "Malformed heading: missing [TYPE] prefix"

**Cause**: You wrote:

```markdown
## Wave: DISCUSS / User stories
```

**Fix**: Add the type:

```markdown
## Wave: DISCUSS / [REF] User stories
```

### Error: "Invalid wave name: ANALYSE"

**Cause**: Typo in wave name.

**Fix**: Use one of: DISCOVER, DISCUSS, DESIGN, DEVOPS, DISTILL, DELIVER.

### Error: "Invalid type: [EXPLANATION]"

**Cause**: Wrong type token.

**Fix**: Use one of: `[REF]`, `[WHY]`, `[HOW]`.

### Error: "Section appears twice under Wave DISCUSS"

**Cause**: Two headings with the same wave and section name:

```markdown
## Wave: DISCUSS / [REF] Decisions

...

## Wave: DISCUSS / [REF] Decisions

...
```

**Fix**: Merge into one heading or rename the duplicate.

---

## Section types and documentation preferences

`[REF]`, `[WHY]`, and `[HOW]` identify the purpose of a section. Choose
sections from the facts the document must retain, not from
`documentation.density`: that retained preference does not change wave
output. There is no shipped `--expand` CLI flag that adds a section.

`documentation.expansion_prompt` affects only an assistant's optional
explanation **after a completed wave**. It does not edit `feature-delta.md`
or generate `[WHY]`/`[HOW]` sections. Ask the assistant directly for more
detail; change accepted documents through their normal authoring process.

If an authored feature uses an `[REF] Expansion catalog`, its entries are
references to documented optional sections, not an automatically populated
menu or a commitment that every wave produces one.

---

## Grep cookbook for downstream agents

Wave agents consume feature-delta files via grep. Use these patterns to find what you need:

```bash
# Find all decisions for a wave
grep "^## Wave: DESIGN / \[REF\] Decisions" -A 50 feature-delta.md | head -100

# Find all acceptance scenarios
grep "^## Wave: DISTILL / \[REF\] Acceptance scenarios" -A 100 feature-delta.md

# Find all rationale sections
grep "^## Wave: .* / \[WHY\]" feature-delta.md

# Find all procedural sections
grep "^## Wave: .* / \[HOW\]" feature-delta.md

# Extract just the Expansion catalog
grep "^## Wave: DISCUSS / \[REF\] Expansion catalog" -A 20 feature-delta.md
```

---

## Common authoring mistakes to avoid

1. **Mixing reference and rationale in one section**: Separate `[REF]` from `[WHY]`. If a section has both, split it:

   **Wrong**:
   ```markdown
   ## Wave: DISCUSS / [REF] User stories

   ### US-1: Lean output

   We chose lean because token bloat degrades context...
   ```

   **Right**:
   ```markdown
   ## Wave: DISCUSS / [REF] User stories

   ### US-1: Lean output

   Elevator Pitch: Marco gets lean output...

   ## Wave: DISCUSS / [WHY] JTBD narrative

   We chose lean because token bloat degrades context...
   ```

2. **One wave appending to another wave's section**: Each wave owns its heading. Do not append:

   **Wrong**:
   ```markdown
   ## Wave: DISCUSS / [REF] User stories

   ... (DISCUSS content)

   ... (DESIGN appends here) ← VIOLATION
   ```

   **Right**: Create a separate heading:
   ```markdown
   ## Wave: DISCUSS / [REF] User stories

   ...

   ## Wave: DESIGN / [REF] Design notes on US-1

   ...
   ```

3. **Inconsistent section naming**: Use consistent names across waves. Do not create:

   ```markdown
   ## Wave: DISCUSS / [REF] User stories
   ## Wave: DESIGN / [REF] User story analysis  ← different name, same concept
   ```

   Instead, reference the upstream section:

   ```markdown
   ## Wave: DESIGN / [REF] Design decisions for User stories

   Based on DISCUSS / [REF] User stories (US-1, US-2, ...), we decided:
   ```

4. **Too much procedure in `[REF]`: Procedures belong in `[HOW]`:

   **Wrong**:
   ```markdown
   ## Wave: DELIVER / [REF] Implementation

   1. Update the skill file at nWave/skills/nw-discuss/SKILL.md
   2. Add the --expand argument parser
   ...
   ```

   **Right**:
   ```markdown
   ## Wave: DELIVER / [HOW] Implementation guide

   1. Update the skill file at nWave/skills/nw-discuss/SKILL.md
   2. Add the --expand argument parser
   ...
   ```

---

## Related documentation

- **[Feature directory format reference](../reference/feature-format.md)** — bimodal layout details and schema
- **[Legacy documentation density preferences](configuring-doc-density.md)** — diagnostic-only; do not change wave output
- **[nWave Global Config Reference](../reference/global-config.md)** — all configuration options
