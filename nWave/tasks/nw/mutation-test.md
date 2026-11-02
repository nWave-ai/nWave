---
description: Runs a standalone mutation probe, disabled by default, over a named production delta or the explicit nightly production delta.
argument-hint: '[--delta <base>...<head> | --nightly-delta] [--threshold 80]'
---

# NW-MUTATION-TEST

Load `~/.claude/skills/nw-mutation-test/SKILL.md`. The skill owns target
selection, runner choice and reporting. Do not reconstruct targets from a
feature artifact or progress state. Mutation is disabled by default; this
standalone command is an explicit on-demand opt-in and runs only in a disposable worktree.
