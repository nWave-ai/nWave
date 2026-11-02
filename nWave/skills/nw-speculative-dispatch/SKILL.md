---
name: nw-speculative-dispatch
description: "Speculative parallel implementation methodology — dispatch N candidate implementations, audit all, score, pick best. Auditability mandate: ALL candidates logged (not just winner)."
user-invocable: false
disable-model-invocation: true
---

# Speculative Dispatch Methodology

Speculative dispatch is a technique where the orchestrator generates N candidate
implementations of the same TDD step in parallel, scores each by measured
properties, and picks the best — while logging every candidate, including
discarded ones, for human audit.

---

## 1. When to Use Speculative Dispatch

**Use speculative dispatch when the decision is ambiguous and at least 3 feasible
candidate strategies exist.**

| Signal | Use speculative dispatch? |
|--------|--------------------------|
| Step has ≥3 plausible implementation strategies | YES |
| Decision is clear from prior context | NO — implement directly |
| Only 1-2 strategies, clear winner | NO — implement directly |
| Performance matters and strategies have measurable trade-offs | YES |
| Domain is novel and "correct" structure is unknown | YES |

Speculative dispatch is orthogonal to TDD stages — it applies at any phase
(RED unit-test authoring, GREEN, COMMIT under the 3-phase canon per ADR-025;
or RED_UNIT, GREEN, COMMIT under the legacy 5-phase contract) where ambiguity
is genuine and 3 candidates are feasible within the time budget.

---

## 2. The Three-Candidate Rule

Generate **exactly 3 candidates** per speculative step by default:

| Role | Strategy |
|------|----------|
| **minimal-change** | Inline, no new abstractions. Lowest complexity, fewest lines. |
| **refactor-heavy** | Extracts helpers, adds guards, defensive patterns. Higher complexity. |
| **pattern-extraction** | Generalises to a factory/template. Highest lines. Justified if reuse follows. |

Three candidates is the minimum viable set for meaningful scoring. More than 5
candidates adds noise without proportional signal. Each candidate must be
behaviourally correct before scoring — incorrect candidates are eliminated before
scoring, not by scoring.

---

## 3. Auditability Mandate

**ALL candidates must be logged — winner AND losers.**

Discarded candidates have audit value. A human reviewer validating the
orchestrator's pick must be able to inspect every alternative considered, not
just the selected one. This is not optional.

### What the audit log captures per candidate

```
candidate_id:     unique name within the step (e.g. "minimal-change")
step_id:          identifies the TDD step these candidates competed on
timestamp_iso:    ISO-8601 when the trace was written
files_modified:   tuple of relative paths modified by this candidate
tests_added:      tuple of test file paths added
tests_pass:       True / False — did the full test suite pass?
rationale:        human-readable explanation of this candidate's approach
```

### Why losers matter

A loser trace explains:
- What the orchestrator tried and why it was discarded.
- Whether the discard was due to test failure (hard signal) or lower score (preference).
- Whether a future reviewer would make the same call.

Without loser traces, the audit log is a winner's narrative — it cannot
be challenged or validated.

---

## 4. Scoring Model

Candidates are ranked by a composite 5-tuple score. Tuple ordering implements
priority naturally: Python's built-in `>` comparison on tuples is sufficient.

```
score(metrics) -> (tests_pass: int, -complexity_delta, -lines_added, 0, -runtime)
```

Priority order (element 0 dominates):

| Priority | Metric | Direction |
|----------|--------|-----------|
| 1 | `tests_pass` | True (1) > False (0). Hard gate — a failing candidate never beats a passing one. |
| 2 | `complexity_delta` | Lower is better. Negated so higher score = simpler. |
| 3 | `lines_added` | Fewer is better. Negated. Tiebreaker when complexity is equal. |
| 4 | reserved | 0 — placeholder for future metrics (coverage delta, type-error count). |
| 5 | `test_runtime_seconds` | Faster is better. Negated. Final tiebreaker. |

**Correctness gate**: a candidate with `tests_pass=False` is ALWAYS dominated by
any candidate with `tests_pass=True`, regardless of all other metrics. This
prevents the orchestrator from ever selecting a broken candidate on the grounds
that it is "simpler".

---

## 5. `pick_best` Rationale Requirements

The `pick_best` function must return a rationale string that:

1. Names the winner candidate_id.
2. Names every loser candidate_id.
3. States the winner's key metrics (tests_pass, complexity_delta, lines_added).
4. States why each loser was discarded (test failure, or specific metric
   comparison).

A rationale that omits any candidate is an audit violation. Reviewer agents
check that all candidate_ids appear in the rationale string.

---

## 6. Storage Layout

```
<root>/
  .nwave/
    speculative/
      <step_id>/
        traces.jsonl      # one JSONL line per candidate, in write order
```

- One file per step. All candidates for a step share the file.
- Append-only. Never overwrite. Each `write_trace` call appends one line.
- `read_traces(step_id, root=root)` returns all candidates for the step.
- Human-readable with `jq` or any JSONL viewer.

### Inspection example

```bash
cat .nwave/speculative/ws-prepended-with/traces.jsonl | python -m json.tool
```

---

## 7. Stage Cascade Fit

Speculative dispatch is stage-agnostic. It applies at any TDD phase where a
genuine implementation choice exists:

| Stage (3-phase canon / legacy 5-phase) | Application |
|----------------------------------------|------------|
| RED (unit-test authoring) / RED_UNIT | Competing test decompositions (example-based vs property, flat vs parametrised). |
| GREEN | Competing implementations of a non-trivial function. |
| COMMIT | Competing refactor strategies (extract method vs extract module vs inline). |

Do not apply speculative dispatch to mechanical steps (adding an import,
renaming a variable, fixing a typo). Reserve it for decisions with measurable
trade-offs.

---

## 8. Integration with nwave_ai.speculative

Two modules provide the walking-skeleton implementation:

```python
from nwave_ai.speculative.audit import CandidateTrace, write_trace, read_traces
from nwave_ai.speculative.score import CandidateMetrics, score, pick_best
```

### Workflow

```python
# 1. Build and run candidates (external to this module)
#    Each candidate modifies files, runs tests, records outcome.

# 2. Write a trace for each candidate — ALL of them, pass or fail
trace = CandidateTrace(
    candidate_id="minimal-change",
    step_id="step-42",
    timestamp_iso=datetime.utcnow().isoformat() + "Z",
    files_modified=("src/foo.py",),
    tests_added=("tests/test_foo.py",),
    tests_pass=True,
    rationale="Single-expression — no new abstractions.",
)
write_trace(trace, root=Path("."))

# 3. Build metrics for each candidate
metrics_map = {
    "minimal-change": CandidateMetrics(
        tests_pass=True, complexity_delta=1, lines_added=3, test_runtime_seconds=0.5
    ),
    ...
}

# 4. Recover all traces and pick best
traces = read_traces("step-42", root=Path("."))
winner, rationale = pick_best(traces, metrics_map)

# 5. Apply winner's changes; discard losers (but keep audit log)
print(f"Selected: {winner.candidate_id}")
print(f"Rationale: {rationale}")
```

---

## 9. Anti-Patterns

| Anti-pattern | Problem |
|--------------|---------|
| Logging only the winner | Destroys audit trail. Reviewers cannot validate the pick. |
| Scoring before correctness gate | A failing candidate may win on complexity. Never allowed. |
| Fewer than 3 candidates | Two candidates is a coin flip, not speculative dispatch. |
| More than 5 candidates | Noise overwhelms signal; budget exceeded. |
| Selecting by single metric | Composite score required; single-metric selection misses trade-offs. |
| Discarding traces after pick | Audit log is permanent. Delete only on explicit retention-policy trigger. |

---

## 10. Empirical Baseline (walking skeleton)

Walking skeleton verified 2026-05-05. The test that produced these numbers has since been removed as dead code (commit `3bf327a3f`, "remove Tier-1 dead code ... speculative"); the figures below are a historical baseline, not a re-runnable check, and nothing in the current tree reproduces them:

Three candidates implement `prepended_with(value, prefix) -> bool`:

| candidate_id | tests_pass | complexity_delta | lines_added | selected |
|---|---|---|---|---|
| minimal-change | True | 1 | 2 | YES |
| pattern-extraction | True | 4 | 10 | no |
| refactor-heavy | True | 5 | 12 | no |

Rationale produced:
```
Selected: minimal-change (tests_pass=True, complexity_delta=1, lines_added=2).
Discarded candidates:
  - refactor-heavy: tests_passed, complexity_delta=5, lines_added=12.
  - pattern-extraction: tests_passed, complexity_delta=4, lines_added=10.
```

All three candidate_ids appear in the rationale. Auditability mandate satisfied.
