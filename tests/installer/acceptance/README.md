# nWave Framework Acceptance Tests

E2E acceptance tests for nWave framework features, following Outside-In TDD principles.

---

## 📁 Test Organization

### DES Tests → `tests/des/acceptance/`

**All Deterministic Execution System (DES) tests have been moved to `tests/des/acceptance/`.**

See: [`tests/des/acceptance/`](../des/acceptance/) for:
- US-001 through US-009 test suites
- Complete DES acceptance test coverage
- DES-specific fixtures and configuration

---

## Purpose

This directory contains acceptance tests for **nWave framework features** (not DES):
- Framework rationalization and command template compliance
- Version update workflow and safety mechanisms
- Command validation and quality gates

---

## Test Structure

```
tests/acceptance/
├── conftest.py                              # Shared pytest fixtures
├── acceptance-tests.feature                 # BDD: Framework rationalization
├── test_validator_acceptance.py             # Command template compliance
├── test_command_noncompliant.md             # Test fixture for validator
├── features/
│   └── version-update-experience/           # BDD: Version update workflow
│       ├── us-001-check-version.feature
│       ├── us-002-update-safely.feature
│       ├── us-003-breaking-changes.feature
│       ├── us-004-backup-cleanup.feature
│       ├── us-005-commit-enforcement.feature
│       ├── us-006-prepush-validation.feature
│       ├── us-007-changelog-generation.feature
│       ├── test_version_steps.py
│       ├── test_update_steps.py
│       └── test_git_workflow_steps.py
└── README.md                                # This file
```

---

## Running Tests

### Run All Acceptance Tests (Framework + Version Update)
```bash
pytest tests/acceptance/
```

### Run Specific Feature Tests
```bash
# Command validator tests
pytest tests/acceptance/test_validator_acceptance.py

# Version update workflow tests
pytest tests/acceptance/features/version-update-experience/
```

### Run with Verbose Output
```bash
pytest tests/acceptance/ -v
```

---

## Test Suites

### 1. Framework Rationalization (`acceptance-tests.feature`)

**Feature**: nWave Framework Rationalization for Open Source Publication

**Purpose**: Validates command template compliance and agent-builder capabilities

**Key Scenarios**:
- Command template compliance validation
- Agent-builder command creation capability
- Agent-builder-reviewer validates template compliance
- Non-compliant command detection and feedback

**Test File**: `test_validator_acceptance.py`

**Status**: ✅ IMPLEMENTED

---

### 2. Command Template Validator (`test_validator_acceptance.py`)

**Purpose**: Validates that nWave command files follow template guidelines

**Validates**:
- ✅ Command size is 50-60 lines
- ✅ Zero workflow duplication (commands delegate, not implement)
- ✅ Explicit context bundling present
- ✅ Agent invocation pattern used correctly
- ✅ Critical violations block approval
- ✅ Actionable feedback for non-compliant commands

**Test Fixture**: `test_command_noncompliant.md`

**Status**: ✅ PASSING

---

### 3. Version Update Experience (`features/version-update-experience/`)

**Feature**: Safe version update workflow for nWave framework

**User Stories** (7 total):
1. **US-001**: Check version - Verify current version and check for updates
2. **US-002**: Update safely - Backup before update with rollback capability
3. **US-003**: Breaking changes - Detect and warn about breaking changes
4. **US-004**: Backup cleanup - Automatic cleanup of old backup directories
5. **US-005**: Commit enforcement - Block update if uncommitted changes exist
6. **US-006**: Pre-push validation - Validate tests pass before pushing updates
7. **US-007**: Changelog generation - Auto-generate changelog from commit history

**Test Files**:
- `test_version_steps.py` - Version checking and display
- `test_update_steps.py` - Update and backup workflow
- `test_git_workflow_steps.py` - Git-based validations

**Status**: ✅ IMPLEMENTED (mixed pass/skip status)

---

## Test Philosophy

### Outside-In TDD Principles

1. **Start with acceptance test** (RED) - Defines "done" from business perspective
2. **Step down to unit tests** (inner loop) - Drive implementation details
3. **Return to acceptance test** (GREEN) - Verify business requirement satisfied
4. **ONE test at a time** - No multiple failing E2E tests blocking commits

### Business-Focused Tests

- **Given-When-Then structure** - Clear business scenarios (BDD)
- **Domain language** - Uses personas and real-world scenarios
- **Business value** - Each test documents WHY it matters
- **No implementation details** - Tests validate behavior, not code structure

### Expected Test Lifecycle

```
┌─────────────────────────────────────────┐
│ DISTILL Wave                            │
│ - Create acceptance test (FAILING)      │
│ - Test documents business requirement   │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│ DELIVER Wave                            │
│ - Implement via Outside-In TDD          │
│ - Unit tests drive implementation       │
│ - Acceptance test turns GREEN naturally │
└─────────────────────────────────────────┘
```

---

## Fixtures

### Shared Fixtures (`conftest.py`)

Provides pytest fixtures shared across all acceptance tests in this directory.

---

## For DES Tests

**Looking for DES acceptance tests?**

All Deterministic Execution System tests have been relocated to:
- **Location**: `tests/des/acceptance/`
- **Test Count**: 12 user story test files (US-001 through US-009)
- **Status**: 39 passing, 71 skipped
- **Documentation**: See `tests/des/acceptance/README.md` (if exists) or `docs/design/deterministic-execution-system-design.md`

---

## References

### Framework Rationalization
- **Design Document**: `docs/design/framework-rationalization.md` (if exists)
- **Command Template**: Internal documentation in command files

### Version Update Workflow
- **Feature Documentation**: `tests/acceptance/features/version-update-experience/README.md`
- **User Stories**: Documented in `.feature` files

### Outside-In TDD Resources
- **BDD Methodology**: `nWave/skills/acceptance-designer/bdd-methodology.md`
- **ATDD Patterns**: `nWave/data/methodologies/atdd-patterns.md`
- **Outside-In TDD Reference**: `nWave/data/methodologies/outside-in-tdd-reference.md`

---

**Last Updated**: 2026-01-28 (DES tests relocated to `tests/des/acceptance/`)
