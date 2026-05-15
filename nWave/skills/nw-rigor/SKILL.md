---
name: nw-rigor
description: "Selects a quality-vs-token-consumption profile (lean, standard, thorough, exhaustive, custom, inherit) and persists it globally (~/.nwave/global-config.json) or per-project (.nwave/des-config.json). Use when tuning how much rigor wave commands apply."
user-invocable: false
argument-hint: '[profile] - Optional: lean, standard, thorough, exhaustive, custom, inherit. Omit for interactive selection.'
---

# NW-RIGOR: Quality Profile Selection

**Wave**: CROSS_WAVE | **Agent**: Main Instance (self) | **Command**: `/nw-rigor [profile]`

## Overview

Interactive command to select a quality-vs-token-consumption profile. Persists choice to either `~/.nwave/global-config.json` (global scope) or `.nwave/des-config.json` (project scope) under the `rigor` key. All wave commands read this config to adjust agent models, review policy, TDD phases, and mutation testing.

You (the main Claude instance) run this directly. No subagent delegation.

**Note on TDD phase canons (dual-canon, ADR-025, 2026-05-07)**: the canonical TDD cycle is **3-phase v5** (`RED, GREEN, COMMIT`) as described in `nw-tdd-methodology`. The **legacy 5-phase v4** (`PREPARE, RED_ACCEPTANCE, RED_UNIT, GREEN, COMMIT`) is preserved for backward-compat audit-log replay of pre-2026-05-07 commits. The `.nwave/des-config.json` `tdd_phases` field accepts BOTH canons: writers of new logs may emit v5; the validator + schema (`step-tdd-cycle-schema.json`) dispatch on `schema_version` (`"5.0"` → canonical, anything else → legacy). The profile table below shows both canons side-by-side: pick v5 for new features, keep v4 only when extending a feature whose audit log was started under the legacy canon.

## Profile Mappings (Single Source of Truth)

| Setting            | lean                                  | standard [recommended]                                                       | thorough                                                                     | exhaustive                                                                   | inherit                                                                      |
|--------------------|---------------------------------------|------------------------------------------------------------------------------|------------------------------------------------------------------------------|------------------------------------------------------------------------------|------------------------------------------------------------------------------|
| agent_model        | haiku                                 | sonnet                                                                       | opus                                                                         | opus                                                                         | inherit                                                                      |
| reviewer_model     | skip                                  | haiku                                                                        | sonnet                                                                       | opus                                                                         | haiku                                                                        |
| review_enabled     | false                                 | true                                                                         | true                                                                         | true                                                                         | true                                                                         |
| double_review      | false                                 | false                                                                        | true                                                                         | true                                                                         | false                                                                        |
| tdd_phases (v5 canonical, ADR-025)    | [RED, GREEN]                          | [RED, GREEN, COMMIT]                                                         | [RED, GREEN, COMMIT]                                                         | [RED, GREEN, COMMIT]                                                         | [RED, GREEN, COMMIT]                                                         |
| tdd_phases (v4 legacy, audit-replay)  | [RED_UNIT, GREEN]                     | [PREPARE, RED_ACCEPTANCE, RED_UNIT, GREEN, COMMIT]                           | [PREPARE, RED_ACCEPTANCE, RED_UNIT, GREEN, COMMIT]                           | [PREPARE, RED_ACCEPTANCE, RED_UNIT, GREEN, COMMIT]                           | [PREPARE, RED_ACCEPTANCE, RED_UNIT, GREEN, COMMIT]                           |
| refactor_pass      | false                                 | true                                                                         | true                                                                         | true                                                                         | true                                                                         |
| mutation_enabled   | false                                 | false                                                                        | false                                                                        | true                                                                         | false                                                                        |

## Behavior Flow

### Mode Detection

- No argument -> Mode 1 (Interactive Selection)
- Argument is a preset name (lean, standard, thorough, exhaustive, inherit) -> Mode 2 (Quick Switch)
- Argument is `custom` -> Mode 3 (Custom Builder)

### Mode 1: Interactive Selection (no argument)

#### Step 1: Welcome

Read `.nwave/des-config.json`. If missing or `.nwave/` directory absent -> error: "No nWave config directory found. Run nwave install first."

If JSON is invalid -> backup as `.nwave/des-config.json.bak`, reset config to `{}`, note: "Config was corrupted. Backed up and reset."

Display current profile (from `config.rigor.profile`) or "none set" if absent.

Brief explanation: "Rigor profiles control how much quality infrastructure nWave applies per wave: agent models, review depth, TDD phases, mutation testing. Higher rigor = better guarantees, higher token cost."

#### Step 1.5: Scope Selection

Display the current project rigor (from `.nwave/des-config.json`) and current global rigor (from `~/.nwave/global-config.json`, if it exists).

Ask via AskUserQuestion:
```
Where do you want to save this configuration?
```
Options:
1. Globally (~/.nwave/global-config.json) — applies to all projects without their own rigor
2. This project only (.nwave/des-config.json) — overrides global for this project

Store the user's choice as `{scope}` and the corresponding file path as `{target_file}`:
- If global: `{target_file}` = `~/.nwave/global-config.json`
- If project: `{target_file}` = `.nwave/des-config.json`

#### Step 2: Comparison Table

Display this table:

```
+-----------+--------+----------+----------+------------+---------+
|           | lean   | standard | thorough | exhaustive | inherit |
+-----------+--------+----------+----------+------------+---------+
| Agent     | haiku  | sonnet   | opus     | opus       | *yours* |
| Reviewer  | --     | haiku    | sonnet   | opus       | haiku   |
| Review    | no     | yes      | double   | double     | yes     |
| TDD       | R->G   | 5-phase  | 5-phase  | 5-phase    | 5-phase |
| Refactor  | no     | yes      | yes      | yes        | yes     |
| Mutation  | no     | no       | no       | yes        | no      |
+-----------+--------+----------+----------+------------+---------+
| Est. cost | lowest | moderate | higher   | highest    | varies  |
| Est. time | fast   | moderate | slower   | slowest    | varies  |
+-----------+--------+----------+----------+------------+---------+
```

Mark "standard" as [recommended]. Below the table, note: "Or choose **custom** to configure each setting individually. Type **inherit** to use your current session model."

#### Step 3: User Selection

Ask user to select via AskUserQuestion (4 options + Other for inherit/custom):

1. standard [recommended]
2. lean
3. thorough
4. exhaustive

Note in the question text: "Type 'custom' to build your own profile, or 'inherit' to use your session model."

If user selects or types "custom" -> jump to Mode 3 (Custom Builder).
If user types "inherit" -> proceed with inherit profile to Step 4.

#### Step 4: Detail View

Show the detail view for the selected profile. Render in a code block for visual clarity.

**lean:**
```
WHAT YOU GET:
  - Haiku agent (fastest, cheapest)
  - RED -> GREEN TDD (skip PREPARE, RED_ACCEPTANCE, COMMIT phases)

WHAT YOU LOSE:
  - No code review
  - No PREPARE phase (no test fixture setup)
  - No RED_ACCEPTANCE phase (no acceptance tests)
  - No COMMIT phase (no refactoring pass)
  - No mutation testing

WHEN TO USE:
  Config changes, documentation, simple bug fixes, spikes/prototypes

ESTIMATED IMPACT:
  Lowest token cost | Fastest per step
```

**standard [recommended]:**
```
WHAT YOU GET:
  - Sonnet agent (balanced quality/speed)
  - Full 5-phase TDD (PREPARE -> RED_ACCEPTANCE -> RED_UNIT -> GREEN -> COMMIT)
  - Haiku reviewer (cost-effective review)
  - Refactoring pass in COMMIT phase

WHAT'S NOT INCLUDED:
  - No double review (single pass only)
  - No mutation testing
  - Not opus-level reasoning

WHEN TO USE:
  Most development work — features, integrations, refactoring

ESTIMATED IMPACT:
  Moderate token cost | Moderate time per step
```

**thorough:**
```
WHAT YOU GET:
  - Opus agent (strongest reasoning)
  - Sonnet reviewer (deeper review analysis)
  - Double review (two independent review passes)
  - Full 5-phase TDD
  - Refactoring pass

WHAT IT COSTS:
  Higher token cost | Slower per step

WHEN TO USE:
  Critical features, security-sensitive code, public APIs, complex algorithms
```

**exhaustive:**
```
WHAT YOU GET:
  - Opus agent and opus reviewer (strongest at every stage)
  - Double review (two independent review passes)
  - Full 5-phase TDD
  - Refactoring pass
  - Mutation testing (>= 80% kill rate gate)

WHAT IT COSTS:
  Highest token cost | Slowest per step

WHEN TO USE:
  Critical production systems, compliance-sensitive code, long-lived core modules
```

**inherit:**
```
WHAT YOU GET:
  - Your session model for agents (nWave inherits, does not override)
  - Haiku reviewer
  - Full 5-phase TDD
  - Single review pass
  - Refactoring pass

WHAT THIS MEANS:
  nWave respects your model choice and controls the process around it.
  If your session runs opus, agents get opus. If sonnet, agents get sonnet.

WHEN TO USE:
  When you have strong opinions about which model to use,
  or your organization controls model selection externally.
```

#### Step 5: Confirm

Ask user to confirm via AskUserQuestion:
1. Yes, apply this profile
2. No, go back to selection (return to Step 2)
3. Cancel (exit without saving)

#### Step 6: Save to Config

1. If `{scope}` is global AND the directory `~/.nwave/` does not exist, create it with `parents=True`
2. Read `{target_file}` (handle missing file or corrupt JSON: start with `{}`)
3. Parse JSON
4. Set `config["rigor"]` to the full profile object:
   ```json
   {
     "profile": "{selected}",
     "agent_model": "...",
     "reviewer_model": "...",
     "tdd_phases": [...],
     "review_enabled": true/false,
     "double_review": true/false,
     "mutation_enabled": true/false,
     "refactor_pass": true/false
   }
   ```
5. Write back to `{target_file}`, preserving all other top-level keys (audit_logging_enabled, skill_tracking, update_check, etc.)

#### Step 7: Summary

Display all resolved settings:

```
Rigor profile saved: {name}

  Resolved settings:
  +-----------------------+---------------------------------------------------+
  | agent_model           | {value}                                           |
  | reviewer_model        | {value}                                           |
  | tdd_phases            | {value}                                           |
  | review_enabled        | {value}                                           |
  | double_review         | {value}                                           |
  | mutation_enabled      | {value}                                           |
  | refactor_pass         | {value}                                           |
  +-----------------------+---------------------------------------------------+

  Config: {target_file} ({scope})
  All wave commands will use these settings.
```

### Mode 2: Quick Switch (with argument)

#### Step 1: Validate Argument

If argument is not one of: lean, standard, thorough, exhaustive, custom, inherit -> error: "Unknown profile '{name}'. Available: lean, standard, thorough, exhaustive, custom, inherit"

If argument is `custom` -> redirect to Mode 3 (Custom Builder).

Read `.nwave/des-config.json`. If missing -> same error as Mode 1 Step 1.

#### Step 1.5: Scope Selection

Same as Mode 1 Step 1.5. Ask scope question, store `{scope}` and `{target_file}`.

#### Step 2: Show Diff

Display what changes from current profile to target profile:

```
Switching from {current} -> {target}:

  agent_model:      sonnet -> haiku
  reviewer_model:   haiku -> skip
  review_enabled:   true -> false
  tdd_phases:       5-phase -> R->G
  refactor_pass:    true -> false
  mutation_enabled: (unchanged) false
```

If downgrading (moving to a less rigorous profile), highlight what user will lose:

```
You will LOSE:
  - Code review (reviewer_model: skip)
  - PREPARE, RED_ACCEPTANCE, COMMIT phases
  - Refactoring pass
```

If no current profile is set, show the target profile settings without diff.

#### Step 3: Confirm

Ask user to confirm via AskUserQuestion:
1. Yes, switch to {target}
2. No, keep current profile

#### Step 4: Save + Summary

Same as Mode 1 Steps 6 and 7. Uses `{target_file}` from Step 1.5.

### Mode 3: Custom Builder (`/nw-rigor custom` or selected from interactive)

Build a profile setting by setting. Each question uses AskUserQuestion with sensible defaults (standard values pre-selected). After all questions, show summary and confirm.

#### Step 1: Config Check

Same as Mode 1 Step 1 (read config, handle missing/corrupt).

#### Step 1.5: Scope Selection

Same as Mode 1 Step 1.5. Ask scope question, store `{scope}` and `{target_file}`.

#### Step 2: Agent Model

Ask via AskUserQuestion:
```
Which model should agents use? (crafter, architect, acceptance-designer)
```
Options:
1. sonnet (Recommended) — balanced quality and speed
2. haiku — fastest, lowest cost
3. opus — strongest reasoning, highest cost
4. inherit — use your current session model

#### Step 3: Reviewer Model

Ask via AskUserQuestion:
```
Which model for peer reviewers?
```
Options:
1. haiku (Recommended) — cost-effective review
2. sonnet — deeper analysis
3. opus — most thorough review
4. skip — no peer review

#### Step 4: Double Review

Ask via AskUserQuestion:
```
Run peer review twice (two independent passes)?
```
Options:
1. No (Recommended) — single review pass
2. Yes — two independent review passes (higher cost)

Only show this question if reviewer_model is not "skip". If "skip", set double_review = false automatically.

#### Step 5: TDD Phases

Ask via AskUserQuestion:
```
Which TDD phases should agents execute?
```
Options:
1. Full 5-phase (Recommended) — PREPARE, RED_ACCEPTANCE, RED_UNIT, GREEN, COMMIT
2. Minimal (RED→GREEN) — RED_UNIT and GREEN only (fastest, skips setup and refactoring)

#### Step 6: Refactoring Pass

Ask via AskUserQuestion:
```
Include a dedicated refactoring pass after implementation?
```
Options:
1. Yes (Recommended) — L1-L4 refactoring in COMMIT phase
2. No — skip refactoring pass

Only show if TDD phases is "Full 5-phase". If minimal, set refactor_pass = false automatically.

#### Step 7: Mutation Testing

Ask via AskUserQuestion:
```
Enable mutation testing (>= 80% kill rate gate)?
```
Options:
1. No (Recommended) — skip mutation testing
2. Yes — run mutmut after implementation, gate at 80% kill rate

#### Step 8: Summary + Confirm

Display the assembled profile:

```
Custom profile:

  +-----------------------+---------------------------------------------------+
  | agent_model           | {value}                                           |
  | reviewer_model        | {value}                                           |
  | double_review         | {value}                                           |
  | tdd_phases            | {value}                                           |
  | refactor_pass         | {value}                                           |
  | mutation_enabled      | {value}                                           |
  +-----------------------+---------------------------------------------------+
```

Ask to confirm via AskUserQuestion:
1. Yes, apply this custom profile
2. Start over (return to Step 2)
3. Cancel (exit without saving)

#### Step 9: Save + Summary

Same as Mode 1 Steps 6 and 7. Uses `{target_file}` from Step 1.5. Save with `"profile": "custom"`.

## Error Handling

| Error | Response |
|-------|----------|
| Missing `.nwave/` directory | "No nWave config directory found. Run nwave install first." |
| Invalid JSON in des-config.json | Backup as `.bak`, reset to `{}`, proceed with notice |
| Unknown profile name | "Unknown profile '{name}'. Available: lean, standard, thorough, exhaustive, custom, inherit" |
| inherit with undetectable session model | Fallback to sonnet with notice: "Could not detect session model. Defaulting agent_model to sonnet." |

## Success Criteria

- [ ] Current profile displayed (or "none set")
- [ ] Scope question asked (global vs project) in all 3 modes
- [ ] Comparison table shown with all 5 profiles
- [ ] User selected and confirmed a profile
- [ ] Config written to `{target_file}` (read-modify-write, other keys preserved)
- [ ] `~/.nwave/` directory auto-created with `parents=True` on first global save
- [ ] Summary of all resolved settings displayed (including scope and target file path)

## Examples

### Example 1: Interactive first-time selection
```
/nw-rigor
```
No current profile set. Shows comparison table, user picks "standard", sees detail view, confirms. Config written with full rigor block.

### Example 2: Quick switch to lean
```
/nw-rigor lean
```
Current profile is "standard". Shows diff: loses review, loses PREPARE/COMMIT phases, loses refactoring pass. Agent drops from sonnet to haiku. User confirms. Config updated.

### Example 3: Quick switch up
```
/nw-rigor thorough
```
Current profile is "standard". Shows diff: sonnet->opus agent, haiku->sonnet reviewer, double review enabled. No losses to highlight (pure upgrade). User confirms. Config updated.

### Example 4: Custom profile builder
```
/nw-rigor custom
```
Walks through 6 questions: agent model (opus), reviewer (haiku), double review (no), TDD (full 5-phase), refactoring (yes), mutation (yes). Saves as custom profile with opus agent, haiku reviewer, single review, full TDD, refactoring, and mutation testing — a combination no preset offers.

### Example 5: Invalid profile name
```
/nw-rigor turbo
```
Error: "Unknown profile 'turbo'. Available: lean, standard, thorough, exhaustive, inherit"

### Example 6: No nWave installed
```
/nw-rigor
```
No `.nwave/` directory found. Shows: "No nWave config directory found. Run nwave install first." Stops.
