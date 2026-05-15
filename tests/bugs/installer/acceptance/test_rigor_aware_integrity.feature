# Regression — F-3 (RC-C): rigor profile not wired into integrity verification.
# RCA: docs/feature/fix-roadmap-json-drift/discuss/rca.md (Branch C).
#
# Pre-fix drift:
#   src/des/cli/verify_deliver_integrity.py:109-111 reads canonical TDDSchema
#   phases unconditionally (legacy 5-phase by default). Projects using the
#   3-phase ADR-025 canon (rigor.tdd_phases=[RED, GREEN, COMMIT]) trigger
#   spurious "missing phases" errors because the verifier insists on
#   PREPARE / RED_ACCEPTANCE / RED_UNIT entries that the 3-phase contract
#   no longer emits.
#
# Post-fix (F-3):
#   The CLI reads DESConfig.rigor_tdd_phases (already exists at
#   src/des/adapters/driven/config/des_config.py:167-174) and intersects with
#   the canonical TDDSchema phase set. Empty intersection → ValueError with
#   diagnostic naming the offending rigor phases. No rigor override → falls
#   back to canonical TDDSchema (legacy 5-phase, no regression).
#
# Driving port: `des-verify-integrity <project-dir>` CLI invoked via
# subprocess. Driven adapter: real `.nwave/des-config.json` on disk (no
# mocking of DESConfig internals — port-to-port).
#
# State-delta universes per Mandate Paradigm 2026-05-05:
#   A (3-phase rigor + 3-phase log):
#       {cli.exit_code, cli.has_missing_phases_error, cli.stdout_ok}
#       expected post-fix: 0 / False / True
#   B (legacy 5-phase rigor + 5-phase log):
#       {cli.exit_code, cli.has_missing_phases_error, cli.stdout_ok}
#       expected: 0 / False / True (no regression, both pre- and post-fix)
#   C (misconfigured rigor — empty tdd_phases list):
#       {cli.exit_code, cli.stderr_names_offending_phases}
#       expected post-fix: non-zero / True (diagnostic ValueError surfaces)
#   D (no rigor override — default canonical fallback):
#       {cli.exit_code, cli.has_missing_phases_error, cli.stdout_ok}
#       expected: 0 / False / True (default canon, both pre- and post-fix)

Feature: Rigor-aware integrity verifier honours the project's TDD phase profile

  As a framework maintainer
  I need `des-verify-integrity` to validate execution-log entries against the
  rigor-profile phase set declared in `.nwave/des-config.json`
  And to surface a diagnostic error when the rigor profile names phases the
  canonical TDDSchema does not recognise
  So that projects on the 3-phase ADR-025 canon pass integrity verification
  And legacy 5-phase projects continue to verify cleanly with no regression

  @bug-roadmap-schema-drift @driving_port @rca-root-cause-C
  Scenario: Three-phase rigor profile passes integrity verification on three-phase log
    Given a feature dir with a 3-phase rigor profile and execution-log entries for RED GREEN COMMIT
    When the des-verify-integrity CLI runs against the feature dir
    Then the verifier exits with status 0
    And the verifier output reports complete DES traces

  @bug-roadmap-schema-drift @driving_port @rca-root-cause-C
  Scenario: Legacy five-phase rigor profile passes integrity verification on five-phase log
    Given a feature dir with a legacy 5-phase rigor profile and execution-log entries for all 5 phases
    When the des-verify-integrity CLI runs against the feature dir
    Then the verifier exits with status 0
    And the verifier output reports complete DES traces

  @bug-roadmap-schema-drift @driving_port @rca-root-cause-C
  Scenario: Misconfigured rigor with empty tdd_phases surfaces a diagnostic error
    Given a feature dir with a rigor profile declaring tdd_phases as an empty list
    When the des-verify-integrity CLI runs against the feature dir
    Then the verifier exits with non-zero status
    And the verifier stderr names the misconfigured rigor phases

  @bug-roadmap-schema-drift @driving_port @rca-root-cause-C
  Scenario: Default fallback uses canonical TDDSchema when no rigor override present
    Given a feature dir with no rigor override and execution-log entries for the canonical phase set
    When the des-verify-integrity CLI runs against the feature dir
    Then the verifier exits with status 0
    And the verifier output reports complete DES traces
