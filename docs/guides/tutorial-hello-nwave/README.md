# Quick Start: Your First Feature in 5 Minutes

**Version**: 1.0.0
**Date**: 2026-02-17

Build a working, tested feature from scratch using nWave. Three commands, five minutes.

**Prerequisites**:
- **Platform**: Linux, macOS, or Windows (WSL2 required)
- nWave installed — `pipx install nwave-ai && nwave-ai install` (in your terminal, not Claude Code)
- Claude Code open in an empty Python project with `pytest` available
- Use a permanent directory (not `/tmp`) — later tutorials build on this project

---

## What You'll Build

An ASCII art banner generator. Give it text, get back block letters in your terminal:

```
$ python -m banner "nWave"

 N   N  W   W   AA   V   V  EEEEE
 NN  N  W   W  A  A  V   V  E
 N N N  W W W  AAAA   V V   EEE
 N  NN  WW WW  A  A   V V   E
 N   N  W   W  A  A    V    EEEEE
```

Three commands. You review at each step. The machine never runs without your approval.

---

## Step 1: Define What You Want

```
/nw-discuss "ASCII art banner generator: a pure Python function that takes a string and returns multi-line ASCII block letters. Only uppercase A-Z and spaces. No external dependencies."
```

The `@product-owner` agent asks clarifying questions — answer simply. When it finishes, you'll find requirements under:

```
docs/feature/{feature-id}/discuss/
```

> **SSOT model**: Product-level documents (journeys, architecture) are in `docs/product/`. Feature-specific artifacts (user stories, wave decisions) are in `docs/feature/{feature-id}/discuss/`.

**What to check**: Open the file. Are the requirements reasonable? Is the scope small? If the agent added too much (colors, fonts, animations), edit the file and remove it. Keep it simple: one function, block letters, A-Z + space.

**Expected time**: ~1 minute

---

## Step 2: Define "Done"

```
/nw-distill
```

The `@acceptance-designer` creates Given-When-Then test scenarios. You'll find them under `tests/`.

**What to check**: You should see 2-4 scenarios like:
- Single letter renders correctly
- Full word renders correctly
- Spaces between words work
- Empty input returns empty output

If there are more than 5 scenarios, ask the agent to consolidate. Fewer scenarios = faster delivery.

**Expected time**: ~1 minute

---

## Step 3: Build It

```
/nw-deliver
```

This is where the magic happens. The `@software-crafter` implements your feature using Outside-In TDD:

1. Reads your acceptance tests
2. Creates a roadmap (one step per scenario)
3. For each step: writes a failing test → makes it pass → cleans up
4. Commits after each green test

**What you'll see**: The agent works through each step. This takes 2-3 minutes for a feature this small. You'll see test runs, code being written, and commits being made.

**When it's done**: All acceptance tests pass. Run them yourself:

```bash
pytest tests/ -v
```

You should see all green.

---

## Try It

Your banner generator is ready. Test it:

```python
python -c "from banner import render; print(render('HI'))"
```

You should see block letters in your terminal.

---

## What Just Happened

Three commands. Three human checkpoints. One working feature with tests.

```
You typed          Agent did                    You checked
─────────          ─────────                    ───────────
/nw-discuss        Wrote requirements           ✓ Scope right?
/nw-distill        Created acceptance tests     ✓ Scenarios cover it?
/nw-deliver        TDD implementation           ✓ Tests pass?
```

The feature is tested, committed, and ready to use.

---

## What's Next

- **Bigger feature**: See [Your First Feature](../tutorial-first-feature/) for a multi-phase workflow with architecture design
- **Existing codebase**: See [Jobs To Be Done Guide](../jobs-to-be-done-guide/) for adding features to brownfield projects
- **Need help?**: Type `/nw-buddy "what should I do next?"` to get contextual guidance from the concierge agent
- **All commands**: See [nWave Commands Reference](../../reference/commands/index.md)
