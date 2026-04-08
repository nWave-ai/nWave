# Tutorial: Debugging with 5 Whys

**Time**: ~13 minutes (7 steps)
**Platform**: macOS, Linux, or Windows
**Prerequisites**: Python 3.10+, Claude Code with nWave installed, [Tutorial 1](../tutorial-first-delivery/) completed
**What this is**: An interactive walkthrough of `/nw-root-why` -- nWave's systematic root cause analysis command. You will take a buggy CSV processor, observe the symptom, and trace it to the real root cause using the 5 Whys methodology.

---

## Setup

Run from a directory where you want the tutorial project created (e.g. `~/projects`):

```bash
curl -fsSL https://raw.githubusercontent.com/nWave-ai/nWave/main/docs/guides/tutorial-debugging/setup.py | python3
```

Prefer to read first? See [manual-setup.md](./manual-setup.md).

## After setup you should have

- A `csv-processor/` directory with `src/processor.py` (intentionally buggy), `tests/sample.csv`, `tests/test_processor.py`, `conftest.py`, and `.gitignore`
- A `.venv/` virtual environment with `pytest` installed
- A clean git repository with one initial commit
- A failing test suite — **3 tests fail** by design; that's the bug you'll investigate

---

## What You'll Build

A root cause analysis of a subtle CSV processing bug -- traced from symptom to fix using structured "why?" questioning.

**The symptom**: A CSV processor reports it processed 8 rows, but the output file only contains 5. Three rows silently vanish. The tests catch this, but the cause is not obvious.

**The root cause**: (You will discover this yourself in Step 5 -- no spoilers here.)

**Why this matters**: Most debugging starts by staring at the symptom and guessing. The 5 Whys method forces you to trace the causal chain: each "why?" peels back one layer until you reach the root. `/nw-root-why` automates this -- it reads your code, builds an evidence chain, and produces a structured analysis with a fix recommendation.

---

## Step 1 of 7: Open the buggy project (~1 minute)

After running setup, `cd csv-processor` and activate the virtualenv:

```bash
cd csv-processor
source .venv/bin/activate
```

> **Windows users**: Replace `source .venv/bin/activate` with `.venv\Scripts\activate`.

The project contains an intentionally buggy `src/processor.py` and a test suite that catches the bug. **Don't read the source code yet** -- the whole point of the tutorial is to investigate the failure systematically rather than guessing from the code.

---

## Step 2 of 7: Run the tests and see them fail (~1 minute)

```bash
pytest tests/ --no-header
```

You should see:

```
FAILED tests/test_processor.py::test_process_csv_row_count
FAILED tests/test_processor.py::test_summarize_total
FAILED tests/test_processor.py::test_summarize_count

3 failed, 1 passed
```

Three tests fail. One passes (`test_process_csv_skips_empty_amount` -- the only behavior that's currently working as intended). This is your starting point: a bug report you can reproduce.

*Next: zoom in on one specific failure to see what's actually wrong.*

---

## Step 3 of 7: Observe the Symptom (~1 minute)

Before running root cause analysis, understand exactly what is wrong. Run the failing test with more detail:

```bash
pytest tests/test_processor.py::test_process_csv_row_count -v --no-header --tb=short
```

You should see output like:

```
FAILED tests/test_processor.py::test_process_csv_row_count - AssertionError:
  Expected 7 rows, got 5: ['Alice', 'Bob', 'Carol', 'Eve', 'Grace']
```

Notice what is missing: **Frank** and **Heidi** are gone. Dave is correctly skipped (empty amount). But Frank and Heidi have valid data.

At this point, you could stare at the code, add print statements, and guess. Instead, you will let `/nw-root-why` trace the causal chain systematically.

*Next: you will run `/nw-root-why` and watch the 5 Whys investigation unfold.*

---

## Step 4 of 7: Run the Root Cause Analysis (~3 minutes)

In Claude Code, type:

```
/nw-root-why "process_csv returns 5 rows instead of 7. Frank and Heidi are missing from the output."
```

> **AI output varies between runs.** Your session will differ from the examples below. That is expected -- the agent investigates your specific code and may phrase findings differently. What matters is the structure (5 Whys chain, evidence, root cause), not the exact wording.

The troubleshooter agent (Sherlock) will investigate. You will see phases scroll by:

```
● nw-troubleshooter(Reading codebase and test output)
● nw-troubleshooter(Why #1: Why are Frank and Heidi missing?)
● nw-troubleshooter(Why #2: Why does the CSV reader merge those rows?)
● nw-troubleshooter(Why #3: Why does the quoted comma cause this?)
● nw-troubleshooter(Why #4: Why is the field parsed incorrectly?)
● nw-troubleshooter(Why #5: Root cause identified)
```

This takes 2-3 minutes. The agent reads the source code, the test data, and the test output, then applies the 5 Whys methodology to build an evidence chain.

Two concepts in this step:

1. **5 Whys** -- A root cause analysis technique. You ask "why?" repeatedly (typically 5 times) until you move past symptoms to the actual cause. Each level peels back one layer of the problem.
2. **Evidence chain** -- Each "why?" is backed by specific code references, not speculation. The agent cites line numbers and variable values.

> **If `/nw-root-why` does not start**: Make sure nWave is installed. Run `/nw-help` to verify. Also confirm you are in the `csv-processor` directory with the committed code.

*Next: you will read the root cause analysis document.*

---

## Step 5 of 7: Read the Analysis (~2 minutes)

After the investigation completes, the agent produces a root cause analysis. You should see a document like:

```
Root Cause Analysis: Missing rows in CSV processing
====================================================

SYMPTOM: process_csv() returns 5 rows instead of expected 7.
         Frank and Heidi are missing from output.

WHY #1: Why are Frank and Heidi missing from the results?
  → They are not in the `results` list after the for-loop completes.
  Evidence: Only 5 rows appended to results.

WHY #2: Why are they not appended?
  → The `if not cleaned.get("amount")` check filters them out.
  Evidence: For these rows, cleaned["amount"] evaluates to falsy.

WHY #3: Why does Frank's amount evaluate to falsy?
  → Frank's row is: Frank,10.00,"food, drinks"
  The CSV has a quoted field containing a comma: "food, drinks"
  The CSV reader correctly parses this, but the resulting row has
  3 header columns and the data maps correctly.
  However, the NEXT row (Grace) is also parsed correctly...
  Wait — examining more carefully:

  The actual issue: the CSV line `Frank,10.00,"food, drinks"`
  produces a row where the DictReader maps fields based on the
  header. With header [name, amount, category], Frank's row
  parses correctly. But the stripped dict shows the amount IS
  present.

  Re-examining: the newline after the CSV content or the field
  values themselves must cause a different mapping...

WHY #4: Why does the field mapping go wrong?
  → [Agent traces to the specific parsing behavior]

WHY #5: ROOT CAUSE
  → [The agent identifies the actual root cause in your code]

RECOMMENDATION:
  [Specific fix with code suggestion]
```

**Your output will differ.** The agent explores the actual code path and may take a different investigative route. What matters is:

- Each "why?" goes deeper than the previous one
- Evidence cites specific code (line numbers, variable values)
- The root cause is a specific code defect, not a vague description
- A concrete fix is recommended

**What just happened?** The agent systematically traced the bug from symptom (missing rows) through the processing pipeline to the root cause. Instead of guessing, it followed the data through each function and identified exactly where and why the rows disappeared.

> **If the analysis seems off-track**: The 5 Whys are generated by AI and may occasionally follow a wrong branch. If the agent's analysis does not match the test output, you can re-run with more detail: `/nw-root-why "test_process_csv_row_count fails: Expected 7 rows, got 5. Frank and Heidi missing. See tests/sample.csv line 7 for Frank's row."`

*Next: you will ask the agent to apply the fix.*

---

## Step 6 of 7: Apply the Fix (~2 minutes)

Tell the agent to fix the root cause:

```
Apply the recommended fix from the root cause analysis.
```

The software crafter will modify `src/processor.py` based on the root cause analysis. You will see:

```
● nw-software-crafter(Applying fix to process_csv)
  — Running tests... 4 passed ✓
```

**Verify success:**

```bash
pytest tests/ -v --no-header
```

You should see:

```
tests/test_processor.py::test_process_csv_row_count PASSED
tests/test_processor.py::test_process_csv_skips_empty_amount PASSED
tests/test_processor.py::test_summarize_total PASSED
tests/test_processor.py::test_summarize_count PASSED

4 passed
```

Check what changed:

```bash
git diff src/processor.py
```

The diff should show a targeted fix -- not a rewrite of the entire file, but a specific change to the code path that caused rows to be dropped.

Commit the fix:

```bash
git add -A && git commit -m "fix: handle CSV fields with embedded commas correctly"
```

> **If tests still fail after the fix**: Run `git diff` to see what the agent changed. If the fix is incomplete, provide the failing test output back to the agent: "Tests still fail after your fix. Here is the output: [paste output]. Please investigate further."

*Next: you will review the 5 Whys methodology and when to use it.*

---

## Step 7 of 7: Review and Takeaways (~2 minutes)

### What You Built

You traced a subtle CSV parsing bug from symptom to root cause using structured analysis:

1. **Observed the symptom** -- 5 rows instead of 7, specific rows missing
2. **Ran `/nw-root-why`** -- The agent applied 5 Whys to build an evidence chain
3. **Read the analysis** -- Each "why?" went deeper, backed by code evidence
4. **Applied the fix** -- Targeted change, all tests green

### The 5 Whys in Practice

```
Typical debugging:              5 Whys debugging:

1. See error                    1. See error (symptom)
2. Add print statements         2. Why does this happen? (evidence)
3. Guess at cause               3. Why does THAT happen? (deeper)
4. Apply speculative fix        4. Why? (deeper still)
5. Hope it worked               5. Why? (root cause found)
6. New bug appears later        6. Fix the root cause, not the symptom
```

The key difference: typical debugging fixes symptoms. The 5 Whys forces you to keep asking until you find the cause that, once fixed, prevents the entire chain from occurring.

### When to Use `/nw-root-why`

- A test fails and the cause is not obvious from the traceback
- A bug keeps recurring after you "fix" it (you are fixing symptoms)
- Multiple seemingly unrelated failures that might share a root cause
- You inherited code and need to understand a failure without full context

### When NOT to Use It

- The error message already tells you exactly what is wrong (e.g., `NameError: name 'foo' is not defined`)
- Simple typos or syntax errors
- You already know the root cause and just need to implement the fix

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `/nw-root-why` does not start | Make sure nWave is installed. Run `/nw-help` to verify. |
| Agent analysis seems wrong | Provide more context in the bug description. Include the exact test output and the specific file/line where the symptom appears. |
| Agent finds a cause but the fix does not work | Re-run with the new information: `/nw-root-why "After applying [fix], test still fails with [new output]"`. The first root cause may have been a contributing factor, not the sole cause. |
| Analysis stops at 3 Whys | Not all bugs need 5 levels. If the root cause is found at level 3, that is fine. The number 5 is a guideline, not a rule. |
| Agent suggests rewriting the entire file | Ask it to make the minimal fix: "Apply only the minimal change needed to fix the root cause. Do not refactor." |
| `ModuleNotFoundError` when running tests | Make sure you created `conftest.py` with the sys.path insert. Run `cat conftest.py` to verify. |
| All tests pass from the start | Check that `tests/sample.csv` contains `"food, drinks"` (with quotes and comma). The quoted comma in Frank's row is what triggers the bug. |

---

**Last Updated**: 2026-02-18
