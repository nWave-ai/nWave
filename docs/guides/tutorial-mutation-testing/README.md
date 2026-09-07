# Tutorial: Validating Your Test Suite with Mutation Testing

**Time**: ~12 minutes (6 steps)
**Platform**: macOS, Linux, or Windows
**Prerequisites**: Python 3.10+, Claude Code with nWave installed, [Tutorial 1](../tutorial-first-delivery/) completed
**What this is**: A hands-on walkthrough of `/nw-mutation-test` -- nWave's mutation testing command. You will build a calculator with tests that have 100% code coverage but miss real bugs, then use mutation testing to expose the gaps.

---

## Setup

Run from a directory where you want the tutorial project created (e.g. `~/projects`):

```bash
curl -fsSL https://raw.githubusercontent.com/nWave-ai/nWave/main/docs/guides/tutorial-mutation-testing/setup.py | python3
```

Prefer to read first? See [manual-setup.md](./manual-setup.md).

## After setup you should have

- A `mutation-demo/` directory with `src/calc.py`, `tests/test_calc.py`, `conftest.py`, `.gitignore`
- A `.venv/` virtual environment with `pytest` installed
- A clean git repository with one initial commit
- 8 passing tests (every function tested, every line covered) — the catch is that several assertions are too weak

---

## What You'll Build

A test suite that actually catches bugs -- not just one that looks green.

**Before**: Your calculator has 100% code coverage. Every line is executed. Tests all pass. You feel confident. But a simple change from `+` to `-` in production code does not break a single test. Your tests are theater.

**After**: Mutation testing reveals exactly which assertions are too weak. You strengthen them. Now when production code changes, tests catch it immediately.

**Why this matters**: Code coverage measures which lines run during tests. Mutation testing measures whether your tests actually verify behavior. A test that asserts `result is not None` has coverage but catches nothing. `/nw-mutation-test` finds these gaps by making small changes to your code and checking if tests notice.

---

## Step 1 of 6: Open the project (~1 minute)

After running setup, `cd mutation-demo` and activate the virtualenv:

```bash
cd mutation-demo
source .venv/bin/activate
```

> **Windows users**: Replace `source .venv/bin/activate` with `.venv\Scripts\activate`.

Take a look at `src/calc.py` (a 5-function calculator) and `tests/test_calc.py` (8 tests covering every function). Several of those tests are intentionally weak — that's the lesson.

---

## Step 2 of 6: Confirm the tests look fine (~1 minute)

```bash
pytest tests/ --no-header
```

You should see:

```
tests/test_calc.py ........

8 passed
```

All green. 100% coverage. Looks great. **Is it?**

*Next: you will run mutation testing and discover that "all green" does not mean "well tested."*

---

## Step 3 of 6: Run Mutation Testing (~3 minutes)

In Claude Code, type:

```
/nw-mutation-test
```

> **AI output varies between runs.** Your session will differ from the examples below. That is expected -- the agent analyzes your specific code. What matters is that surviving mutants are reported, not the exact wording.

The mutation testing agent will:

1. Read your source code and tests
2. Generate mutations (small changes to production code)
3. Run tests against each mutation
4. Report which mutations survived (tests did not catch them)

You will see phases scroll by:

```
● nw-mutation-tester(Analyzing source code for mutation targets)
● nw-mutation-tester(Generating mutations for src/calc.py)
● nw-mutation-tester(Running tests against 12 mutations)
● nw-mutation-tester(Compiling mutation report)
```

This takes 2-3 minutes. Wait for the full report.

Two concepts in this step:

1. **Mutation** -- A small, deliberate change to production code. Examples: changing `+` to `-`, `>` to `>=`, replacing `return x` with `return 0`. Each mutation simulates a bug.
2. **Kill rate** -- The percentage of mutations caught by your tests. Higher is better. 100% means every simulated bug was detected.

> **If `/nw-mutation-test` does not start**: Make sure nWave is installed. Run `/nw-help` to verify. Also confirm you are in the `mutation-demo` directory with committed code.

*Next: you will read the mutation report and understand what it reveals.*

---

## Step 4 of 6: Read the Mutation Report (~2 minutes)

After the analysis completes, the agent produces a mutation report. You should see something like:

```
Mutation Testing Report
=======================

Source: src/calc.py
Tests:  tests/test_calc.py

Total mutations:  12
Killed:           5  (tests caught the change)
Survived:         7  (tests missed the change)
Kill rate:        42%

SURVIVING MUTANTS (tests did not catch these):

  src/calc.py line 4: changed `a + b` to `a - b`
    → test_add still passed (assertion only checks `is not None`)

  src/calc.py line 4: changed `a + b` to `a * b`
    → test_add still passed

  src/calc.py line 8: changed `a - b` to `a + b`
    → test_subtract still passed (assertion only checks type)

  src/calc.py line 12: changed `a * b` to `a + b`
    → test_multiply still passed (assertion only checks `> 0`)

  src/calc.py line 22: changed `1 - percent / 100` to `1 + percent / 100`
    → test_discount_price still passed (assertion only checks `is not None`)

  src/calc.py line 22: changed `percent / 100` to `percent / 200`
    → test_discount_price_full still passed (assertion only checks `>= 0`)

  ...

KILLED MUTANTS (good -- tests caught these):

  src/calc.py line 16: changed `a / b` to `a * b`
    → test_divide FAILED (expected 5.0, got 20.0) ✓

  src/calc.py line 15: removed `raise ValueError`
    → test_divide_by_zero FAILED (expected ValueError) ✓

  ...
```

**Your output will differ.** The exact mutations and counts depend on the agent's analysis. What matters is the pattern:

- **Surviving mutants** point to weak assertions. The test runs the code but does not verify the result.
- **Killed mutants** point to strong assertions. The test checks exact values or specific behavior.

Notice the correlation: `test_divide` and `test_divide_by_zero` check exact values and catch mutations. `test_add`, `test_subtract`, and `test_multiply` use vague assertions and miss everything.

**What just happened?** The agent simulated bugs in your production code and found that most of your tests would not notice. A 42% kill rate means 58% of potential bugs go undetected. Code coverage lied -- the tests execute every line but verify almost nothing.

> **If the report shows a high kill rate (>80%)**: The agent may have generated fewer mutations or different ones. That is fine -- focus on any surviving mutants it found, even if there are only a few.

*Next: you will fix the weak tests to catch the mutations.*

---

## Step 5 of 6: Strengthen the Tests (~2 minutes)

Replace the weak assertions with exact value checks. Update `tests/test_calc.py`:

```python
# tests/test_calc.py
from src.calc import add, subtract, multiply, divide, discount_price
import pytest


def test_add():
    assert add(2, 3) == 5.0  # exact value -- kills `+` to `-` and `+` to `*`


def test_subtract():
    assert subtract(10, 4) == 6.0  # exact value -- kills `-` to `+`


def test_multiply():
    assert multiply(3, 4) == 12.0  # exact value -- kills `*` to `+`


def test_divide():
    assert divide(10, 2) == 5.0  # already strong


def test_divide_by_zero():
    with pytest.raises(ValueError):
        divide(10, 0)  # already strong


def test_discount_price():
    assert discount_price(100, 20) == 80.0  # exact: 100 * 0.80 = 80


def test_discount_price_full():
    assert discount_price(100, 100) == 0.0  # exact: 100% off = 0


def test_discount_invalid_percent():
    with pytest.raises(ValueError):
        discount_price(100, -10)  # already strong
```

Run the tests to confirm they still pass:

```bash
pytest tests/ -v --no-header
```

You should see:

```
tests/test_calc.py::test_add PASSED
tests/test_calc.py::test_subtract PASSED
tests/test_calc.py::test_multiply PASSED
tests/test_calc.py::test_divide PASSED
tests/test_calc.py::test_divide_by_zero PASSED
tests/test_calc.py::test_discount_price PASSED
tests/test_calc.py::test_discount_price_full PASSED
tests/test_calc.py::test_discount_invalid_percent PASSED

8 passed
```

**What changed?** Every assertion now checks the exact computed value. If any operation is mutated (`+` becomes `-`, `*` becomes `+`, etc.), the test will fail because the result will not match.

Commit the fix:

```bash
git add -A && git commit -m "fix: strengthen test assertions to catch mutations"
```

> **If a test fails**: Check your expected values. `add(2, 3)` should be `5.0`, `subtract(10, 4)` should be `6.0`, `multiply(3, 4)` should be `12.0`, `discount_price(100, 20)` should be `80.0`.

*Next: you will re-run mutation testing to verify the improvement.*

---

## Step 6 of 6: Verify the Improvement (~2 minutes)

Run mutation testing again:

```
/nw-mutation-test
```

This time, the report should show a significantly higher kill rate:

```
Mutation Testing Report
=======================

Source: src/calc.py
Tests:  tests/test_calc.py

Total mutations:  12
Killed:           11
Survived:         1
Kill rate:        92%
```

**Your exact numbers will differ**, but the kill rate should be substantially higher than the first run. Most or all of the previously surviving mutants should now be killed.

**Verify success**: Compare the two runs:

| Metric | Before | After |
|--------|--------|-------|
| Kill rate | ~42% | ~92%+ |
| Surviving mutants | ~7 | ~1 or 0 |

If any mutants survive, the report tells you exactly which line and which change was not caught. You can add more targeted tests for those specific cases.

### What You Learned

1. **Code coverage is not test quality.** 100% line coverage with weak assertions catches nothing. Mutation testing measures whether tests verify behavior.
2. **Strong assertions check exact values.** `assert result == 5.0` catches mutations. `assert result is not None` catches nothing.
3. **Mutation testing finds the gaps.** Each surviving mutant is a specific location where a bug could hide undetected.

### When to Use `/nw-mutation-test`

- After writing a test suite -- to verify it actually catches bugs
- Before a major release -- to find testing blind spots
- When inheriting a codebase -- to assess test suite quality
- After refactoring tests -- to confirm you did not weaken them

### When NOT to Use It

- On trivial code (getters, setters) -- the mutations are obvious
- When you have no tests yet -- write tests first, then validate them
- During rapid prototyping -- mutation testing is for code you intend to keep

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `/nw-mutation-test` does not start | Make sure nWave is installed. Run `/nw-help` to verify. |
| Report shows 0 mutations | The agent could not identify mutation targets. Check that `src/calc.py` contains actual logic (arithmetic, conditionals), not just pass-through code. |
| Kill rate is already 100% on first run | The agent may have generated fewer mutations. This is fine -- it means your tests are strong for the mutations that were tested. |
| Tests fail after updating assertions | Check your expected values match the function logic. `add(2, 3)` returns `5.0`, not `5` (Python float arithmetic). |
| Agent takes more than 5 minutes | Mutation testing runs your test suite multiple times. If tests are slow, it takes longer. For this tutorial the suite is small and should finish in under 3 minutes. |
| Mutation testing seems to hang (>5 minutes) | The agent may still be working. If Claude Code stops responding, press Ctrl+C and run `/nw-mutation-test` again. |
| `ModuleNotFoundError` when running tests | Make sure you created `conftest.py` in the project root with the sys.path insert. Run `cat conftest.py` to verify. |

---

**Last Updated**: 2026-02-18
