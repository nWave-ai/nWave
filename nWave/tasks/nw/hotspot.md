---
description: "Git change frequency hotspot analysis — find the most-changed files in your codebase"
argument-hint: "[--top=N] [--since=6m] [--json] [--rank report.md] [--detail file]"
---

# NW-HOTSPOT: Code Crime Scene Hotspot Lens

**Wave**: CROSS_WAVE
**Execution**: Inline (no agent — Claude executes git commands directly)
**Inspiration**: Adam Tornhill's "Your Code as a Crime Scene"

## Overview

Analyze git change frequency to identify the most-changed files in a codebase. Pure git churn — no complexity metrics. Use as a **pre-filter** to scope analysis or a **post-filter** to prioritize existing findings.

## How It Works

Run `git log --name-only` over the configured time period, count commits per file, rank by frequency.

## Modes

### 1. Analyze (default)

Show the most-changed files in the repo. Output is inline only — no files persisted.

```
/nw:hotspot
/nw:hotspot --top=20
/nw:hotspot --since=12m
```

**Steps:**
1. Run: `git log --since={since} --format=format: --name-only | sort | uniq -c | sort -rn`
2. Exclude deleted files (verify each file still exists with `test -f`)
3. For each file, get last changed date: `git log -1 --format="%ar" -- {file}`
4. Display ranked table (top N):

```
 Rank │ Commits │ Last Changed │ File
──────┼─────────┼──────────────┼─────────────────────────
    1 │      87 │ 2 days ago   │ src/services/payment.ts
    2 │      64 │ 1 week ago   │ src/api/controllers/user.ts
    3 │      51 │ 3 days ago   │ src/models/order.ts
```

5. Show summary: total files changed in period, time period, top N shown

**Defaults:** `--top`: 15, `--since`: 6 months

### 2. Rank (post-filter)

Overlay churn data on an existing analysis report to prioritize findings.

```
/nw:hotspot --rank code-smell-detector-report.md
```

**Steps:**
1. Run the same git churn analysis
2. Read the specified report file
3. Extract file paths mentioned in the report
4. Annotate each file with its commit count
5. Re-sort findings by churn (highest first). Findings without extractable file paths go at the bottom.
6. Show noise reduction: "X of Y findings are in low-churn files (< 20 commits)"

### 3. Detail (deep-dive)

Deep-dive into a single file's change history.

```
/nw:hotspot --detail src/services/payment.ts
```

**Steps:**
1. Monthly commit breakdown over the period
2. Top contributors to the file
3. Co-change coupling: top 5 files that frequently change alongside this one
4. Last 10 commit messages for context

### 4. JSON export (pre-filter composition)

```
/nw:hotspot --top=10 --json
```

Output: `[{"path": "src/services/payment.ts", "commits": 87, "last_changed": "2 days ago"}, ...]`

## Parameters

| Flag | Default | Description |
|------|---------|-------------|
| `--top` | 15 | Number of files to show |
| `--since` | 6m | Time period (e.g., 3m, 12m, 2024-01-01) |
| `--json` | false | Output as JSON array |
| `--rank` | - | Path to existing report to re-rank by churn |
| `--detail` | - | Path to single file for deep-dive |

## Edge Cases

- **No commits in period**: Display "No commits found since {date}" rather than an empty table
- **File renames**: Counted as separate files (no `--follow`; keeps it simple and fast)
- **Empty repo / not a git repo**: Display error and exit

## Usage from Other Skills

### Pre-filter (scope downstream analysis)

Run `/nw:hotspot --top=10 --json` first, then pass the file list to:
- **code-smell-detector**: "Analyze only these files: {hotspot list}"
- **cognitive-load-analyzer**: "Focus analysis on these files: {hotspot list}"
- **refactoring-expert**: "Prioritize recommendations for these files"

### Post-filter (rank existing findings)

Run `/nw:hotspot --rank {report.md}` after any analysis to prioritize by churn.

### In nWave workflows

- Before `/nw:refactor` — identify which files to refactor first
- Before `/nw:review` — focus review effort on high-churn areas
- Before `/nw:root-why` — check if the problematic area is a known hotspot

## Next Wave

**Usage Context**: Inline utility, composable with any analysis skill
**Handoff To**: Invoking context (no sequential handoff)

## Examples

### Quick scan of a legacy codebase
```
/nw:hotspot
```

### Scope a code smell analysis to hotspots
```
/nw:hotspot --top=10 --json
```

### Prioritize an existing refactoring report
```
/nw:hotspot --rank code-refactoring-report.md
```

### Investigate a specific troubled file
```
/nw:hotspot --detail src/services/payment.ts
```

## Expected Outputs

No persistent files. Output is displayed inline. JSON mode outputs a JSON array for composition with other tools.
