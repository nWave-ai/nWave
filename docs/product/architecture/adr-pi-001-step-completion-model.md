# ADR-PI-001: Step-completion / cycle-boundary enforcement model for the subagent-less pi harness

## Status
Accepted (2026-06-23). Resolves DISCUSS decision D6 (PROVISIONAL → DESIGN).

## Context
DES enforces TDD step completion in Claude Code on the `SubagentStop` hook event:
when the crafter subagent returns, `SubagentStopService.validate()` reads the
step's phase events from `execution-log.json` (`StepCompletionValidator`) and
verifies a git commit carrying `Step-Id: {step}` AND `Task-Id: {feature}`
(`GitCommitVerifier`, `--all-match`). On failure it blocks.

pi (the target harness, v0.79.9) is **subagent-less**. It emits no `SubagentStop`.
The firm mappings PreToolUse→`tool_call` and PostToolUse→`tool_result` are
SPIKE-0-proven; the step-completion analog was deferred to DESIGN.

Key finding from reading the engine: `SubagentStopService.validate()` is a **pure
validation over `(execution_log_path, project_id, step_id, cwd)`**. It has no
dependency on the subagent mechanism — the subagent boundary is only the
*trigger cadence*. Therefore the design problem reduces to: which pi event(s)
should trigger the existing validation, and how is suite state (failing test
exists / green / regression) observed without a subagent transcript.

Quality drivers: correctness (100% step-skip block rate, KPI), maintainability
(zero adapter fork D5), reliability (fail-open on translator errors), reuse of
existing verification surfaces (D3).

## Decision
Adopt **Option C — Hybrid**:
- **Within-cycle ordering** is gated on `tool_call`: `pre-write` blocks
  production edits when no failing test exists (RED gate; already in skeleton).
- **Suite state** is captured on the `tool_result` of the bash test-run tool and
  recorded as a phase event via the existing DES phase-logging CLI
  (`des-log-phase` / `post-tool-use`) — no new log format.
- **Step completion** is validated at the **`git commit` `tool_call` boundary**
  by invoking the unchanged `subagent-stop` action; a failed validation returns
  `{block:true,reason}` and pi aborts the commit.
- **`turn_end`/`agent_end`** runs a read-only reconciliation that flags an
  abandoned/out-of-order cycle but never blocks.

Cycle state lives in the existing `.nwave/des/` session area, keyed by
project/step; the translator only reads it, the Python engine remains the sole
authoritative writer.

## Alternatives Considered

### Option A — Commit-boundary only
Treat each `Step-Id`-trailered git commit (made via the bash tool) as the sole
step-completion signal; validate at commit time with `GitCommitVerifier` +
test-run state.
- Pros: single, unambiguous, blockable boundary (a `tool_call`); maps cleanly to
  the existing commit verification; minimal event surface.
- Cons: provides **no within-cycle ordering** — the crafter could write
  implementation before any failing test and only be caught at commit. Violates
  D2's "full RED→GREEN→REFACTOR gating, not a single gate". Rejected as the *sole*
  model, but adopted as the step-completion *half* of the hybrid.

### Option B — turn_end / agent_end only
Validate accumulated phase state when the agent finishes a turn/run.
- Pros: catches the whole cycle in one place; no per-tool overhead.
- Cons: pi honoring a **block** at `turn_end`/`agent_end` is **unverified**
  (SPIKE only proved `tool_call` blocks); a missed turn_end would strand
  enforcement; turn granularity is coarser than a step. Too risky as a gate.
  Retained only as a non-blocking safety-net reconciliation.

### Option C — Hybrid (CHOSEN)
`tool_call` gates within-cycle ordering; commit-boundary validates step
completion + no-regression; turn_end reconciles.
- Pros: full-cycle gating (D2); every gate rides a proven-blockable `tool_call`;
  reuses `SubagentStopService` and `GitCommitVerifier` unchanged (D5, D3); suite
  state via existing phase CLI (D3).
- Cons: more event subscriptions in the translator (still pure translation, no
  decision logic); depends on the crafter committing through the bash tool (true
  for the kata workflow; the commit boundary is also the DoD provenance surface).

### Decision matrix

| Criterion | A: commit-only | B: turn_end-only | C: hybrid (chosen) |
|-----------|----------------|------------------|--------------------|
| Full RED→GREEN→REFACTOR gating (D2) | No (no within-cycle ordering) | Partial (coarse turn granularity) | **Yes** |
| Gate rides a proven-blockable event | Yes (commit `tool_call`) | No (turn_end block unverified) | **Yes** |
| Zero adapter fork (D5) | Yes | Yes | **Yes** |
| Reuses existing surfaces (D3) | Yes | Partial | **Yes** |
| Robust to abandoned/out-of-order cycle | No | Partial | **Yes** (turn_end reconciliation) |

## Consequences
- Positive: one canonical enforcement engine; verdicts byte-identical to Claude
  Code; provenance (Step-Id/Task-Id trailers + JSONL phases) identical across
  harnesses; the gate always rides a blockable event.
- Positive: testable model-free — the commit-boundary block can be exercised by
  a direct adapter round-trip without an LLM backend.
- Negative: enforcement assumes commits go through pi's bash tool; a commit made
  outside pi bypasses the live gate (caught post-hoc by the same verifier in CI).
- Negative: translator subscribes to more events; mitigated by the thin-translator
  enforcement test (no decision logic permitted).
- Trade-off (sensitivity point): `turn_end` reconciliation is best-effort; it
  improves detection of abandoned cycles but is explicitly not a correctness gate.
