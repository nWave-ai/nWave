# Test Scenarios: Wizard Commands

**Feature**: wizard-commands
**Date**: 2026-02-21
**Status**: Draft
**Covers**: US-001, US-002, US-003, US-004

## Test Strategy

The wizard commands (`/nw:new`, `/nw:continue`, `/nw:ff`) are markdown task files interpreted by Claude Code at runtime. There is no Python application logic to invoke through driving ports. The testable surface is:

1. **File existence and frontmatter validity** -- command files exist with correct YAML frontmatter
2. **Catalog registration** -- commands are registered in `framework-catalog.yaml` with matching metadata
3. **Wave detection rule consistency** -- the artifact-to-wave mapping tables in `continue.md` and `ff.md` match the requirements specification
4. **Project ID derivation logic** -- a pure string transform that could be extracted and unit tested, but since it lives as prose instructions in markdown (not Python), we validate its specification through content assertions on the task files

## Test Categories

### Category 1: Command File Presence and Frontmatter (extending existing pattern)

The existing `tests/plugins/test_command_frontmatter.py` validates all command files. The three new commands must be added to `EXPECTED_COMMANDS`.

| Test | AC Coverage | Type |
|------|-------------|------|
| All 21 command files exist with valid YAML frontmatter | AC-001, AC-010, AC-024, NFR-02 | Acceptance |
| Catalog descriptions match frontmatter descriptions | NFR-02 | Acceptance |
| Catalog argument_hints match frontmatter argument-hints | NFR-02 | Acceptance |

### Category 2: Wizard Command File Structure Validation

New tests specific to the three wizard command files.

| Test | AC Coverage | Type |
|------|-------------|------|
| new.md exists with `description` and `argument-hint` in frontmatter | AC-001 | Unit |
| continue.md exists with `description` and `argument-hint` in frontmatter | AC-010 | Unit |
| ff.md exists with `description` and `argument-hint` in frontmatter | AC-024 | Unit |
| new.md contains project ID derivation instructions (prefix stripping, stop words, kebab-case, 5-segment limit) | AC-018 through AC-021 | Unit |
| continue.md contains wave detection rules for all 6 waves | AC-011 | Unit |
| ff.md contains wave detection rules for all 6 waves | AC-025 | Unit |
| Wave detection rules in continue.md and ff.md reference the same artifact paths | AC-025 | Unit |
| continue.md references execution-log.yaml for DELIVER progress | AC-014 | Unit |
| ff.md documents DISCOVER skip-by-default behavior | AC-030 | Unit |
| ff.md documents --from flag behavior | AC-028 | Unit |
| ff.md documents failure handling with /nw:continue suggestion | AC-029 | Unit |

### Category 3: Catalog Registration

| Test | AC Coverage | Type |
|------|-------------|------|
| framework-catalog.yaml contains `new` command entry | NFR-02 | Unit |
| framework-catalog.yaml contains `continue` command entry | NFR-02 | Unit |
| framework-catalog.yaml contains `ff` command entry | NFR-02 | Unit |
| All three wizard commands have `description` in catalog | NFR-02 | Unit |

### Category 4: Wave Detection Rule Consistency

| Test | AC Coverage | Type |
|------|-------------|------|
| continue.md mentions all 6 wave names (DISCOVER through DELIVER) | AC-011 | Unit |
| ff.md mentions all 6 wave names | AC-025 | Unit |
| Both files reference `docs/discovery/problem-validation.md` for DISCOVER | AC-011, AC-025 | Unit |
| Both files reference `docs/feature/{id}/discuss/requirements.md` for DISCUSS | AC-011, AC-025 | Unit |
| Both files reference `docs/feature/{id}/design/architecture-design.md` for DESIGN | AC-011, AC-025 | Unit |
| Both files reference `docs/feature/{id}/deliver/platform-architecture.md` for DEVOP | AC-011, AC-025 | Unit |
| Both files reference `docs/feature/{id}/distill/test-scenarios.md` for DISTILL | AC-011, AC-025 | Unit |
| Both files reference `execution-log.yaml` for DELIVER | AC-011, AC-025 | Unit |

### Category 5: Error Handling Specification Coverage

| Test | AC Coverage | Type |
|------|-------------|------|
| new.md documents vague description handling | AC-009 | Unit |
| new.md documents name conflict handling | AC-007 | Unit |
| continue.md documents empty projects scenario | AC-015 | Unit |
| continue.md documents skipped waves warning | AC-016 | Unit |
| continue.md documents corrupted artifact detection | AC-017 | Unit |
| ff.md documents mid-pipeline failure handling | AC-029 | Unit |

## Error Path Ratio

- Total scenarios: 28
- Error/edge scenarios: 12 (Categories 4-5 partial + Category 5)
- Error path ratio: 43% (exceeds 40% target)

## Implementation Sequence

1. Update `EXPECTED_COMMANDS` in `tests/plugins/test_command_frontmatter.py` to include "continue", "ff", "new" (3 additions, total 21)
2. Create `tests/plugins/test_wizard_command_files.py` with wizard-specific content validation tests
3. All tests in the new file start as `@pytest.mark.skip` except the first walking skeleton test
4. First enabled test: wizard command files exist with valid frontmatter (walking skeleton)

## Traceability

| AC | Test Coverage |
|----|--------------|
| AC-001 | new.md frontmatter existence |
| AC-007 | new.md name conflict handling content |
| AC-009 | new.md vague description handling content |
| AC-010 | continue.md frontmatter existence |
| AC-011 | continue.md wave detection rules content |
| AC-014 | continue.md execution-log.yaml reference |
| AC-015 | continue.md empty projects content |
| AC-016 | continue.md skipped waves content |
| AC-017 | continue.md corrupted artifact content |
| AC-018-021 | new.md project ID derivation content |
| AC-024 | ff.md frontmatter existence |
| AC-025 | ff.md wave detection rules content |
| AC-028 | ff.md --from flag content |
| AC-029 | ff.md failure handling content |
| AC-030 | ff.md DISCOVER skip-by-default content |
| NFR-02 | Catalog registration + frontmatter format compliance |

Note: AC-002 through AC-006, AC-008, AC-012, AC-013, AC-022, AC-023, AC-026, AC-027 describe runtime conversational behaviors that are interpreted by Claude Code from markdown instructions. These cannot be tested through automated tests -- they are validated through manual demonstration with stakeholders.
