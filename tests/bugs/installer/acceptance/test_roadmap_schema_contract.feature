# Regression — F-1 (RC-A): roadmap.json schema-vs-implementation drift.
# RCA: docs/feature/fix-roadmap-json-drift/discuss/rca.md (Branch A).
#
# Schema source of truth: nWave/templates/roadmap-schema.json
#   - step.criteria expected as list[str], counted against constraints.max_criteria_per_step
#   - roadmap.phases is an ARRAY (top-level "phases") — not an integer
#
# Pre-fix drift:
#   - src/des/cli/roadmap.py::_build_skeleton emits step.criteria = "TODO: ..." (string)
#     and roadmap.phases = <int> (collides with top-level phases array semantics)
#   - src/des/domain/roadmap_validator.py::_validate_step_criteria splits a STRING on ";"
#     instead of treating a list as a list. List-form roadmaps silently produce one
#     synthetic "criterion" containing the str(list) repr — wrong counts, wrong words.
#
# Post-fix (F-1):
#   - Skeleton emits criteria=[] and DOES NOT emit roadmap.phases int field.
#   - Validator accepts list[str] natively; legacy string path emits exactly ONE
#     LEGACY_CRITERIA_STRING warning per offending step, never an error.
#
# Driving port: `des-roadmap` CLI invoked via subprocess (`init`, `validate`).
#
# State-delta universe per Mandate Paradigm 2026-05-05:
#   A (skeleton): {step.criteria_type, roadmap.has_phases_int_field, exit_code}
#   B (validator on legacy string): {exit_code, warnings_contains_legacy_criteria_code,
#                                    errors_is_empty}

Feature: Roadmap schema contract — skeleton emits list, validator heals legacy string

  As a framework maintainer
  I need `des-roadmap init` to emit roadmap.json conforming to the schema source-of-truth
  And `des-roadmap validate` to accept list-form criteria and degrade gracefully on legacy strings
  So that newly-authored roadmaps no longer drift from the schema
  And existing on-disk roadmaps continue to validate without regression

  @bug-roadmap-schema-drift @driving_port @rca-root-cause-A
  Scenario: Skeleton emits criteria as a list and omits the legacy phases-int field
    Given the des-roadmap CLI is available on PATH
    When the CLI runs "init --project-id fixture-skeleton --phases 1 --steps 01:1"
    Then the CLI exits with status 0
    And the emitted skeleton declares step criteria as a JSON list
    And the emitted skeleton omits the legacy roadmap.phases integer field

  @bug-roadmap-schema-drift @driving_port @rca-root-cause-A
  Scenario: Validator warns once on legacy string criteria without erroring
    Given a legacy roadmap fixture with step criteria stored as a single string
    When the des-roadmap CLI validates the fixture
    Then the CLI exits with status 0
    And the validator output contains a LEGACY_CRITERIA_STRING warning
    And the validator output contains no error lines
