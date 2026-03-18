---
name: nw-ai-workflow-tutorials
description: AI workflow tutorial patterns — non-deterministic output handling, outcome-based verification, and agent workflow step design
disable-model-invocation: true
---

# AI Workflow Tutorial Patterns

Tutorials for AI-powered tools face a unique challenge: output is non-deterministic. Traditional tutorials show exact expected output; AI workflow tutorials define success by outcome.

## The Non-Determinism Contract

State this early in any AI workflow tutorial:

```markdown
> **AI output varies between runs.** Your output will look different from
> the examples in this tutorial. That is normal. We define success by
> what your code *does*, not what the agent *says*.
```

## Timing Expectations

AI agents work in cycles with processing pauses. Users interpret silence as failure. Always set timing expectations:

```markdown
## Step 3: Let the Agent Work (~5 minutes)

\`\`\`
/nw:deliver "feature description"
\`\`\`

This takes 3-5 minutes. The agent works in phases with 20-60 second
pauses between visible output. This is normal processing, not a hang.
```

Provide a "is it stuck?" diagnostic:
```markdown
> **If you see no output for 2+ minutes**: Check the status bar at
> the bottom of Claude Code. A pulsing indicator means it is still
> working. If the indicator is gone, press Enter to prompt it.
```

## Output Reading Guide

Teach users to read agent output by annotating a realistic example:

```markdown
### Reading the Output

You will see phases scroll by. Here is what each means:

\`\`\`
● nw-solution-architect(...)     <- Planning what to build
  ⎿  Done (3 tool uses · 25s)   <- Phase complete, took 25 seconds

● nw-software-crafter(...)       <- Writing and testing code
  ⎿  Done (10 tool uses · 1m)   <- This is the longest phase

● nw-software-crafter-reviewer(...)  <- Independent quality check
  ⎿  Done (8 tool uses · 42s)
\`\`\`
```

## Messages You Can Safely Ignore

Internal coordination messages confuse new users. Provide an explicit safe-to-ignore list:

```markdown
### Messages you can safely ignore

These lines appear during normal operation and are not errors:

- `PreToolUse:Task hook error` -- DES validation checkpoint
- `DES_MARKERS_MISSING` -- Internal formatting check, auto-retries
- `⎿ SubagentStop` -- Agent coordination signal

Think of these as the agent's internal quality gates. They ensure
every step follows the engineering protocol.
```

## Success Verification

Replace exact-output matching with outcome-based verification:

**Traditional tutorial (deterministic)**:
```markdown
You should see:
\`\`\`
Hello, World!
\`\`\`
```

**AI workflow tutorial (non-deterministic)**:
```markdown
**Verify success:**

\`\`\`bash
pytest tests/ -v
\`\`\`

All tests should pass. The exact number of tests may vary (the agent
sometimes adds extra tests beyond your originals). What matters: zero
failures.

\`\`\`bash
ls src/auth/
\`\`\`

You should see at least: `__init__.py`, `handlers.py`, `models.py`.
File names may differ slightly. The agent chose names based on its
analysis of your requirements.
```

## Progressive Trust Building

Structure AI workflow tutorials to build trust incrementally:

### Level 1: Micro-success (Step 1-2)
- Trivially small task where AI succeeds visibly
- User can verify independently within 30 seconds
- Example: generate a single function from one test

### Level 2: Small feature (Step 3-4)
- Multi-step task with checkpoint verification
- User starts to trust the process
- Example: implement a module with 3-5 tests

### Level 3: Full workflow (Step 5+)
- Complete feature delivery end-to-end
- User understands how to verify and intervene
- Example: full TDD delivery with review and mutation testing

## Handling Divergence

When user output differs from the tutorial:

```markdown
### What if my output looks different?

The agent generates code based on your specific tests and context.
Common variations:

| Tutorial shows | You might see | Both are correct because |
|---------------|---------------|------------------------|
| `class AuthHandler` | `def handle_auth()` | Function vs class is a style choice; tests verify behavior |
| 3 implementation steps | 2 or 4 steps | Agent may split or combine based on complexity |
| `jwt.encode(...)` | `create_token(...)` | Naming varies; the test contract is what matters |

**The rule**: if `pytest tests/ -v` passes, the implementation is correct
regardless of how it differs from the examples.
```

## Recovery Patterns

AI workflows can fail or produce unexpected results. Provide escape hatches:

```markdown
> **If tests fail after delivery**: Run `/nw:deliver` again with the same
> description. The agent detects existing code and failing tests, then
> fixes them. This is a resume, not a restart.

> **If the agent seems confused**: Start fresh with `git stash` to save
> your current state, then `git checkout step-2` to reset to the last
> known-good checkpoint.

> **If you want to start over entirely**: `git checkout main` returns
> to the original starter state.
```
