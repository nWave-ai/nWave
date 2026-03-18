---
name: nw-tutorial-structure
description: Tutorial structure blueprint — section ordering, step templates, and progressive disclosure patterns for evidence-based tutorial design
disable-model-invocation: true
---

# Tutorial Structure Blueprint

## Template

Every tutorial follows this structure. Sections are ordered by reader priority, not author convenience.

### Header Block

```markdown
# Tutorial: {Title}

**Time**: ~{N} minutes
**Prerequisites**: {explicit list}
**What you need installed**: {versions}
```

Time estimate is the sum of step estimates. Prerequisites list specific knowledge ("familiar with Git basics") not vague levels ("intermediate developer").

### What You'll Build

Show the end result before any instruction. Use before/after when applicable.

- Screenshot, terminal output, or diagram of the finished product
- One sentence: what the reader will have at the end
- One sentence: why this is useful

This section sells the tutorial. If a reader is not excited here, they leave.

### Setup (target: under 2 minutes)

Preferred order of setup approaches:
1. `git clone` a starter repo (best: zero ambiguity)
2. Single install command + init
3. Step-by-step project creation (worst: most dropout)

After setup, immediately verify it worked:
```markdown
Run this to confirm setup succeeded:
\`\`\`bash
{verification command}
\`\`\`

You should see:
\`\`\`
{expected output}
\`\`\`
```

### Steps (the core)

Each step follows the **action -> verify -> understand** pattern:

```markdown
## Step N: {Verb Phrase} (~{M} minutes)

{1-2 sentence context -- what we are doing and why}

\`\`\`{language}
{code to execute}
\`\`\`

You should see:
\`\`\`
{expected output}
\`\`\`

**What just happened?** {2-3 sentence explanation of what the code did
and why it matters.}

> **If you see {common error}**: {fix}
```

Rules for steps:
- Each step has a time estimate
- Max 3 new concepts per step
- Every step has a verification checkpoint
- Troubleshooting is inline, not deferred to an appendix
- Steps build on each other -- never reference a concept not yet introduced

### What Just Happened (reflection)

After all steps complete, a summary section:
- List what the reader built (concrete artifacts)
- List what they did NOT have to do (value proposition)
- Connect to the bigger picture

### Next Steps

- 2-3 specific next actions with links
- Ordered by natural progression (not by product catalog)
- Each next step has a one-line description of what the reader will learn

## Step Sizing Guidelines

| Step Duration | Appropriate For |
|--------------|-----------------|
| ~1 minute | Single command + verify |
| ~2 minutes | Small code change + verify + brief explanation |
| ~3-5 minutes | Multi-file change or AI agent execution |
| ~5+ minutes | Split into sub-steps |

Total tutorial target: 5-15 minutes. Tutorials over 20 minutes should be split into a series.

## Signposting Patterns

Use these throughout:

- **Progress**: "Step 3 of 7" in every step header
- **Time**: "~2 minutes" in every step header
- **Preview**: "In the next step, you'll add authentication" at end of each step
- **Completion**: "You're done. Here's what you built:" at the end

## Series Structure

When a topic requires multiple tutorials:

```markdown
| Part | What you'll build | Time |
|------|-------------------|------|
| 1. First Delivery (this tutorial) | ASCII art converter | ~10 min |
| 2. Requirements Gathering | Feature spec from conversation | ~8 min |
| 3. Full Workflow | End-to-end with all agents | ~15 min |
```

Each part is independently completable. Part N assumes completion of Part N-1 but includes a "Start here" checkpoint (git branch/tag).
