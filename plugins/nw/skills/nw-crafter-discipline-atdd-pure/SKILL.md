---
name: nw-crafter-discipline-atdd-pure
description: Crafter discipline contract for the ATDD-pure 7-phase workflow — what the slim crafter does in Phase A (GREEN-the-ATs), Phase B (coverage-driven dead-code elimination), and Phase E (batch L1-L6 refactor), plus hard prohibitions and the Phase B common-cuts taxonomy
user-invocable: false
disable-model-invocation: true
---

# Crafter Discipline — ATDD-pure Protocol

## Scope

This skill defines the **discipline contract** for the slim crafter in the ATDD-pure 7-phase workflow (ADR-027, plan v3 §3-§4). It is loaded when `.nwave/config.yaml` sets `workflow.mode: atdd_pure` and the crafter is dispatched into Phase A, Phase B, or Phase E.

The crafter does NOT author ATs. ATs are the exclusive territory of `nw-acceptance-designer` (DISTILL wave). Back-pressure on AT gaps flows through the Phase C reviewer + Phase D router — never crafter-side AT edits.

Reference: plan v3 `docs/proposals/atdd-pure-workflow-restructure-v3-2026-05-19.md` §3, §4, §7; ADR-027 `docs/architecture/adrs/adr-027-atdd-pure-7-phase-extension.md`.

---

## Phase A — GREEN-the-ATs (crafter instance #1)

**Goal**: take the AT contract authored by DISTILL and produce the **minimum production code** that turns all ATs from RED to GREEN in a single dispatch.

### Inputs
- `.feature` files + step definitions (DISTILL output, immutable to crafter)
- Optional paired unit tests (PBT + state-delta) per `nw-test-design-mandates`
- `files_to_modify` roadmap entry (architect-grounded per `feedback_architect_must_filesystem_ground_roadmap_2026_05_18`)

### Discipline
1. Read **all** ATs end-to-end before writing one line of production code. Hold the AT contract in working memory (~50KB sustainable per spike-2 honest assessment).
2. Implement the **smallest** code shape that satisfies every AT. Single dispatch — no iterative incremental ping-pong.
3. **NO defensive code**: do not write try/except wrappers, dry_run guards, idempotency checks, `validate_prerequisites()` failure branches, `_read_hooks` isinstance guards, type-branching coercion in formatters — **unless an AT explicitly requires it**.
4. **NO architectural anticipation**: write what tests demand, not what "future me might need". Speculative abstractions, premature extension points, configuration knobs without an AT — all forbidden.
5. **NO AT modification**: ATs are read-only. If an AT seems wrong or incomplete, surface to the Phase C reviewer via the verdict pipeline; do NOT edit.

### Empirical anchor
Spike-2 (codex 20 BDD, M cohort): **160 LOC of defensive code** cut in Phase B because no AT asserted them. Phase A had originally written them out of habit — Phase B coverage report exposed them as dead.

### Exit gate
All ATs pass (full suite, not smoke). Output: production code + diff scope confined to `files_to_modify` entries that have been **filesystem-grounded** (paths exist, named symbols are grep-findable in the cited files).

---

## Phase B — Coverage-driven dead-code elimination (same crafter instance)

**Goal**: prove that every line of production code written in Phase A is **required** by at least one AT. Cut everything else.

### Workflow
1. Run `pytest --cov` after Phase A green. Capture line + branch coverage report.
2. For each uncovered line, choose one:
   - **CUT**: delete the line; re-run tests; must stay green.
   - **JUSTIFY**: add to dead-code-justification list with rationale (e.g. monkeypatched module-level symbol that coverage cannot track, `__main__` guard, platform-conditional import).
3. After all cuts applied, re-run the full suite. Suite stays GREEN — no regression tolerated.
4. Target coverage: **≥90% line + branch** (canonical baseline anchor).

### Mechanical character
Phase B is mechanical: the coverage report is the candidate-cuts list. No judgement calls beyond the justification taxonomy.

### Exit gate
1. All ATs still pass.
2. Coverage ≥90% line + branch (or documented misses in justification list).
3. Zero try/except surviving without a paired AT-justified anchor.
4. Zero defensive branches surviving without paired AT.

---

## Phase E — Batch L1-L6 refactor (crafter instance #2, SEPARATE)

**Goal**: apply all L1-L6 refactor transformations atomically in a single editing session, then run the test suite once.

### Separation principle
Phase E **MUST** run in a **separate crafter instance** from Phase A (Ale 2026-05-19 mandate, plan v3 §3). Phase A crafter holds the "minimal-to-GREEN" context; Phase E crafter holds the "refactor-for-quality" context. Mixing the two contexts dilutes both. Dispatch as `Agent(subagent_type='nw-software-crafter')` with a clean session.

### Batch protocol
1. Read all production files modified in Phase A + the test suite.
2. Plan all L1-L6 transformations as a single coherent edit set:
   - **L1**: rename for clarity
   - **L2**: extract method / inline temp
   - **L3**: introduce parameter object / extract class
   - **L4**: replace conditional with polymorphism / strategy
   - **L5**: introduce interface / port boundary cleanup
   - **L6**: eliminate duplication across modules
3. Apply ALL planned edits in one editing session — no interleaved test runs. The L1-L6 cascade governs planning order only.
4. Single test run at the end.
5. If RED: diagnose breakage and fix the **production** code — do NOT modify tests to make them pass. A test that must change means either (a) the refactor altered observable behavior — revert that transformation — or (b) the test encoded an implementation detail — flag to the operator before touching it. **Do NOT retry incremental** (`feedback_refactor_batch_when_test_suite_slow_2026_05_19`).

### Rationale
Batch-then-verify is the **unconditional default** for refactoring (`feedback_refactor_batch_when_test_suite_slow_2026_05_19`, strengthened 2026-05-20 — the prior "only when suite slow" conditional is removed). The cascade orders planning, not test runs. Incremental L1→test→L2→test wastes wall-clock on identical-result test runs; batch protocol cuts wait-time by ~5-6× per spike-2 anchor (6 L-transformations + 1 test run vs 6 test runs). The legacy incremental variant lives in `nw-progressive-refactoring` as explicit opt-in only.

### Exit gate
1. Full suite GREEN.
2. Diff is internally consistent (no half-applied refactors).
3. No production behavior change (ATs unchanged in count and content).

---

## Terminating Test Run — cross-cutting invariant

After ANY code modification — Phase A GREEN implementation, Phase B coverage cleanup, Phase E refactor batch, a bug fix, or any other production-code edit — the full relevant test suite MUST be run at the end of that modification before the work is considered done. **No code change is "complete" without a terminating test run.**

This invariant is owned by the crafter/workflow, NOT delegated to pre-commit hooks. Customers may skip `pre-commit install`, use different CI, or a different OS — an invariant that depends on target-machine setup is broken by definition (`feedback_target_machine_independence_2026_05_15`). The agent runs the suite itself; hooks, if installed, are a redundant convenience layer.

Applies to every phase: Phase A exit gate (all ATs pass), Phase B exit gate (suite stays green after cuts), Phase E exit gate (single suite run after the batch). The rule is the union — every modification terminates in a green suite.

**The terminating run IS `run_contract_gate`.** The terminating command is NOT a crafter-picked subset (`pytest tests/des/` or similar) — that is the exact RCA "verification narrower than the contract" defect (`docs/analysis/rca-slice-shipped-broken-verification-narrower-than-contract-2026-05-20.md`). The canonical terminating command is:

```
python -m des.cli.run_contract_gate --repo .
```

`run_contract_gate` runs `pytest -m "unit or integration or acceptance"` over the WHOLE tree (the exact pre-push contract scope) and emits a `gate_scope_digest`. The crafter MUST carry that digest into the `G_COMMIT` commit as a `Gate-Scope:` trailer. This is not skill text alone: the `G_COMMIT` DES `exit_gate` (E2, slice-14) re-derives a fresh digest via `run_contract_gate --collect-only` and refuses the commit if the `Gate-Scope:` trailer is absent or mismatching — the skill prose and the mechanical exit gate are enforcement-paired, so a narrower terminating run is mechanically caught, not merely discouraged.

---

## Phase B common-cuts taxonomy (empirical from spike-2 + spike-3)

The following code categories are routinely cut in Phase B because no AT asserts them. Each cut MUST be justified by absence of AT asserting it. If the reviewer flags a cut as a behavior-loss bug → route to acceptance-designer via Phase D `AT_GAP_IN_DELIVERY_SCOPE`, NOT to crafter to restore defensive code.

| # | Category | Why cut | Anchor |
|---|----------|---------|--------|
| 1 | Outer `try/except` wrappers | No AT injects runtime exceptions; bare-except swallows real bugs | spike-2 |
| 2 | `dry_run` guards | No AT sets `dry_run=True`; the flag is speculative API surface | spike-2 |
| 3 | `source.exists()` / `path.exists()` pre-flight guards | No AT runs install with source absent; failure surfaces via the actual operation | spike-2 |
| 4 | No-op early-returns on uninstall | No AT calls `uninstall()` without prior install; idempotency claim has no test | spike-2 |
| 5 | `verify()` failure branches | No AT asserts contract regression; the branch is unreachable in tested paths | spike-3 |
| 6 | `isinstance` defensive checks on JSON shape | No AT produces non-dict JSON root; the check guards against impossible state | spike-3 |
| 7 | Type-branching coercion in formatters | No AT uses non-str values; coercion masks upstream type errors | spike-3 |

### Reviewer routing rule
If Phase C reviewer flags a Phase B cut as a substantive gap:
- Reviewer emits `AT_GAP_IN_DELIVERY_SCOPE` finding (per plan v3 §7.1).
- Phase D router routes back to **acceptance-designer** to add the missing AT (per plan v3 §7.2 Routing.LOOP_TO_A_GREEN_ATS after AT added).
- Crafter does NOT restore the defensive code on reviewer say-so alone; an AT must exist first.

This closes the loop: **defensive code requires AT-justification, not author intuition** (per [[feedback_load_skills_before_touching_code_2026_05_15]] + plan v3 §6.7 SSOT-via-types mandate).

---

## Hard prohibitions

Each prohibition cites the memory rule that grounds it. Violation requires **explicit Ale approval** before proceeding — no exceptions.

| Prohibition | Memory rule anchor |
|---|---|
| `git commit --no-verify` (bypassing pre-commit hooks) | [[feedback_load_skills_before_touching_code_2026_05_15]] + plan v3 §9 mechanical guard |
| `# noqa` (ruff suppression without targeted rule) | [[feedback_load_skills_before_touching_code_2026_05_15]] |
| `# type: ignore` (mypy suppression without targeted rule) | [[feedback_load_skills_before_touching_code_2026_05_15]] |
| `@pytest.mark.skip` / `@pytest.mark.xfail` without ticket reference | [[feedback_load_skills_before_touching_code_2026_05_15]] |
| `suppress_health_check=[...]` in Hypothesis settings | [[feedback_load_skills_before_touching_code_2026_05_15]] (2026-05-15 anchor: 1-line "mechanical fix" without root-cause analysis) |
| `git push --force` / `--force-with-lease` | [[feedback_load_skills_before_touching_code_2026_05_15]] |
| `git reset --hard` on any branch with uncommitted work | [[feedback_never_revert_user_work_unauthorized]] (2026-04-30 anchor: 3,343 LOC reverted unilaterally) |
| `git clean -fd` on the working tree | [[feedback_never_revert_user_work_unauthorized]] |
| Authoring or modifying `.feature` files / step definitions | Separation principle, plan v3 §3 + [[feedback_atdd_ssot_via_types_services_dsl_2026_05_18]] |
| Modifying ATs to "make crafter's life easier" | Same — back-pressure goes through Phase C → Phase D, not direct edit |
| Speculative production code without paired AT | Plan v3 §3 + §6 AT-completeness gate |
| Skipping Phase B coverage cleanup to "save time" | Plan v3 §4 — Phase B is a hard exit gate, not optional |

### Escalation protocol
If a prohibition appears blocking: stop, surface to operator with concrete diagnosis (what failed + what bypass was tempting + why root-cause matters). Wait for explicit approval. Never bypass silently.

---

## Token-budget guidance

| Phase | Working memory load | Sustainable budget |
|---|---|---|
| Phase A | Full AT contract + paired unit test pinning + roadmap `files_to_modify` | ~50KB (spike-2 honest assessment) |
| Phase B | Coverage report + production diff from Phase A | ~20KB (mechanical, list-driven) |
| Phase E | Full production tree + test tree + L1-L6 transformation plan | ~80KB (batch refactor needs full context) |

If Phase A working set exceeds ~80KB, the feature is mis-cohorted (likely L not M) — surface to operator before proceeding. Token waste from over-large context dominates any progress benefit.

---

## Verification protocol (before COMMIT)

Run mechanically before emitting any commit:

1. ☐ All ATs pass (full suite invocation, not smoke / not subset).
2. ☐ Coverage ≥90% line + branch (or documented misses with justification).
3. ☐ No surviving `try/except` without paired AT-justified anchor.
4. ☐ No surviving defensive branch without paired AT.
5. ☐ `git diff --name-only` confirms only files in roadmap `files_to_modify` were touched.
6. ☐ Conventional commit message with `Step-Id:` trailer (per ADR-025 §3 commit gate).
7. ☐ No prohibited bypass flags used (grep diff for `--no-verify`, `# noqa`, `# type: ignore`, `@pytest.mark.skip`, `suppress_health_check`).
8. ☐ Reviewer verdict-hash trailer present and valid (per plan v3 §8 HMAC-SHA256 spec).

Any unchecked box blocks COMMIT. Surface diagnosis to operator; do not bypass.

---

## Cross-references

- **ADR-027** — 7-phase extension architectural decision: `docs/architecture/adrs/adr-027-atdd-pure-7-phase-extension.md`
- **Plan v3** — executable specification: `docs/proposals/atdd-pure-workflow-restructure-v3-2026-05-19.md`
- **nw-tdd-methodology** — 3-phase canonical TDD (sibling skill; classic mode default)
- **nw-test-design-mandates** — PBT + state-delta paradigm (applies to Phase A paired unit tests)
- **nw-at-completeness-check** — Phase C reviewer taxonomy (7-category C1-C7, plan v3 §6)
- **nw-refactor** — L1-L6 transformation catalogue (unconditional batch-then-verify default per `feedback_refactor_batch_when_test_suite_slow_2026_05_19`)
- **Memory anchors**: `feedback_refactor_batch_when_test_suite_slow_2026_05_19`, `feedback_load_skills_before_touching_code_2026_05_15`, `feedback_never_revert_user_work_unauthorized`, `feedback_atdd_ssot_via_types_services_dsl_2026_05_18`, `feedback_architect_must_filesystem_ground_roadmap_2026_05_18`
