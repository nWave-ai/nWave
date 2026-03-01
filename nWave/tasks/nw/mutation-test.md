---
description: "Runs feature-scoped mutation testing to validate test suite quality. Use after implementation to verify tests catch real bugs (kill rate >= 80%)."
argument-hint: "[feature-id] - Optional: --threshold=[75|80|85] --language=[auto|python|java|javascript]"
---

# NW-MUTATION-TEST: Feature-Scoped Mutation Testing

**Wave**: QUALITY_GATE
**Agent**: Crafter (nw-software-crafter)

## Overview

Run mutation testing against implementation files from the current feature. Extracts targets from execution-log.json|generates feature-scoped configs|delegates to software-crafter. Uses cosmic-ray (Python)|PIT (Java)|Stryker (JS/TS/C#).

## Context Files Required

- `docs/feature/{feature-id}/deliver/execution-log.json` - Implementation file extraction
- `scripts/mutation/generate_scoped_configs.py` - Automated config generation (if available)

## Pre-Invocation

Orchestrator performs before delegating:

1. Read `execution-log.json`, extract implementation files from `completed_steps[].files_modified.implementation`
2. Verify all extracted files exist on disk
3. Detect project language from config files (pyproject.toml, pom.xml, package.json, etc.)
4. Confirm test suite passes: run `pytest -x {test_scope}` (or equivalent)
5. Ensure mutation venv exists for Python: `.venv-mutation/` with cosmic-ray installed

## Agent Invocation

@nw-software-crafter

Execute mutation testing for project {feature-id}.

**Context to pass inline (agent has no Skill access):**
- Project ID
- Implementation file list (from execution-log.json)
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
/nw:mutation-test des-hook-enforcement tests/des/
```
Reads execution-log.json, runs `generate_scoped_configs.py des-hook-enforcement`, delegates to software-crafter with per-component configs. Agent runs cosmic-ray, produces mutation-report.md.

### Example 2: Python project without config generator
```bash
/nw:mutation-test auth-upgrade tests/auth/
```
Extracts files manually from execution-log.json, creates single cosmic-ray config with `module-path = [file1, file2, ...]` and `test-command = "pytest -x tests/auth/"`, delegates to agent.

### Example 3: Non-Python project
```bash
/nw:mutation-test payment-gateway tests/payment/
```
Detects `package.json`, selects Stryker, delegates with Stryker-specific instructions.

## Success Criteria

- [ ] Implementation files extracted from execution-log.json
- [ ] All implementation files verified on disk
- [ ] Mutation testing executed without errors
- [ ] Per-file breakdown in mutation-report.md
- [ ] Kill rate meets threshold (>= 80% PASS, 70-80% WARN, < 70% FAIL)
- [ ] Source files restored to HEAD after mutation run (git checkout -- src/ tests/)

## Post-Mutation Safety (mandatory)

After EVERY mutation run (success, failure, or interruption), restore source files:

    git checkout -- src/ tests/

Mutation tools apply mutations directly to source files. An interrupted run can leave corrupted code (e.g. `is not None` -> `is  None`). Agent MUST restore source files even if the run errors out.

## Quality Gate

Kill rate thresholds: >= 80% PASS (proceed)|70-80% WARN (review surviving mutants)|< 70% FAIL (add tests first).

Skip conditions: no mutation tool for language|project opts out via `.mutation-config.yaml`|test suite broken. Python projects require mutation testing; all skips need documented justification.

## Next Wave

**Handoff To**: Phase 8 - Finalize (orchestrator continues develop.md workflow)
**Deliverables**: `docs/feature/{feature-id}/deliver/mutation/mutation-report.md`

## Expected Outputs

```
docs/feature/{feature-id}/deliver/mutation/
  mutation-report.md
  cosmic-ray-*.toml                (ephemeral)
```
