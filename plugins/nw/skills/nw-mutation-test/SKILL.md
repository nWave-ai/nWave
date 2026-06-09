---
name: nw-mutation-test
description: "Runs feature-scoped mutation testing to validate test suite quality. Use after implementation to verify tests catch real bugs (kill rate >= 80%)."
user-invocable: true
argument-hint: '[feature-id] - Optional: --threshold=[75|80|85] --language=[auto|python|java|javascript]'
---

# NW-MUTATION-TEST: Feature-Scoped Mutation Testing

**Wave**: QUALITY_GATE
**Agent**: Crafter (nw-software-crafter)

## Overview

Run mutation testing against implementation files from the current feature. Extracts targets — from the classic-mode execution-log.json, or from the ledger `at_ids` under `atdd_pure` (see Target extraction by `workflow.mode`)|generates feature-scoped configs|delegates to software-crafter. Uses cosmic-ray (Python)|PIT (Java)|Stryker (JS/TS/C#).

## Mutation Testing Strategy

Projects declare a strategy via `## Mutation Testing Strategy` in `CLAUDE.md`: `per-feature` | `nightly-delta` | `pre-release` | `disabled`.

**Default (when unspecified): `nightly-delta`** — the recommended mode. CI runs mutmut nightly against modules changed since the last run (the delta), keeping per-feature delivery gates fast. `/nw-mutation-test` performs an explicit, on-demand feature-scoped run regardless of strategy; under `nightly-delta` the in-wave Phase 5 gate is skipped and the work is handled by the CI nightly pipeline.

### Target extraction by `workflow.mode`

How implementation files are selected depends on `workflow.mode`:

- **classic mode** — targets come from the classic-mode `execution-log.json` (`completed_steps[].files_modified.implementation`).
- **atdd_pure mode** — there is no step log. Scope mutants by the slice's `at_ids` read from the **AT-completion ledger**: each ledger slice records the `at_ids` it satisfied and the implementation files those ATs drove, and only those files are mutated for the slice.

## Context Files Required

- `docs/feature/{feature-id}/deliver/execution-log.json` (classic mode) - Implementation file extraction; under `atdd_pure` the AT-completion ledger replaces it as the extraction source
- `scripts/mutation/generate_scoped_configs.py` - Automated config generation (if available)

## Pre-Invocation

Orchestrator performs before delegating:

1. **Extract files** — In classic mode read `execution-log.json` and extract implementation files from `completed_steps[].files_modified.implementation`; in atdd_pure mode read the ledger and extract the files the slice's `at_ids` drove. Gate: file list non-empty.
2. **Verify on disk** — Check all extracted files exist on disk. Gate: zero missing files.
3. **Detect language** — Scan config files (pyproject.toml, pom.xml, package.json, etc.) to select tool. Gate: language identified.
4. **Confirm tests pass** — Run `pytest -x {test_scope}` (or equivalent). Gate: exit code 0, no failures.
5. **Ensure mutation venv** — For Python, verify `.venv-mutation/` exists with cosmic-ray installed. Gate: `cosmic-ray --version` succeeds.

## Agent Invocation

@nw-software-crafter

Execute mutation testing for project {feature-id}.

**Context to pass inline (agent has no Skill access):**
- Project ID
- Implementation file list (classic mode: from execution-log.json; atdd_pure mode: from the ledger `at_ids`)
- Test scope path (e.g., `tests/des/`)
- Kill rate threshold (default: 80%)
- Language and tool selection

**Configuration:**
- threshold: 80 (percentage, minimum kill rate)
- approach: feature-scoped (one config per component, scoped test commands)
- config_generator: `scripts/mutation/generate_scoped_configs.py` (preferred over manual)

**Output file:** `docs/feature/{feature-id}/deliver/mutation/mutation-report.md`

## Examples

### Example 1: Python project with config generator
```bash
/nw-mutation-test des-hook-enforcement tests/des/
```
Reads the classic-mode execution-log.json, runs `generate_scoped_configs.py des-hook-enforcement`, delegates to software-crafter with per-component configs. Agent runs cosmic-ray, produces mutation-report.md.

### Example 2: Python project without config generator
```bash
/nw-mutation-test auth-upgrade tests/auth/
```
Extracts files manually from the classic-mode execution-log.json, creates single cosmic-ray config with `module-path = [file1, file2, ...]` and `test-command = "pytest -x tests/auth/"`, delegates to agent.

### Example 3: Non-Python project
```bash
/nw-mutation-test payment-gateway tests/payment/
```
Detects `package.json`, selects Stryker, delegates with Stryker-specific instructions.

## Success Criteria

- [ ] Implementation files extracted from the mode source (classic: execution-log.json; atdd_pure: ledger `at_ids`)
- [ ] All implementation files verified on disk
- [ ] Mutation testing executed without errors
- [ ] Per-file breakdown in mutation-report.md
- [ ] Kill rate meets threshold (>= 80% PASS, 70-80% WARN, < 70% FAIL)
- [ ] Source files restored to HEAD after mutation run (git checkout -- src/ tests/)

## Post-Mutation Safety (mandatory)

After EVERY mutation run (success, failure, or interruption):

1. **Restore source files** — Run `git checkout -- src/ tests/`. Gate: working tree clean (no mutations remain).
2. **Verify no corruption** — Confirm test suite still passes after restore. Gate: `pytest -x {test_scope}` exits 0.

Mutation tools apply mutations directly to source files. An interrupted run can leave corrupted code (e.g. `is not None` -> `is  None`). Agent MUST execute these steps even if the run errors out.

## Quality Gate

Kill rate thresholds:

1. **>= 80% PASS** — Proceed to next wave.
2. **70-80% WARN** — Review surviving mutants, document findings, proceed with caution.
3. **< 70% FAIL** — Add tests targeting surviving mutants before proceeding.

Skip conditions (each requires documented justification in mutation-report.md):

1. **No tool for language** — No mutation framework available for detected language.
2. **Project opt-out** — `.mutation-config.yaml` has `skip: true` with justification.
3. **Broken test suite** — Pre-invocation step 4 fails; fix tests before mutation testing.

Note: Python projects require mutation testing. All skips need documented justification.

## Next Wave

**Handoff To**: Phase 8 - Finalize (orchestrator continues develop.md workflow)
**Deliverables**: `docs/feature/{feature-id}/deliver/mutation/mutation-report.md`

## Expected Outputs

```
docs/feature/{feature-id}/deliver/mutation/
  mutation-report.md
  cosmic-ray-*.toml                (ephemeral)
```
