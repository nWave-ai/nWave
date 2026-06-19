# Feature: installer-orphan-sweep — slice-03 (verifier orphan report)
# Spec SSOT: docs/feature/installer-orphan-sweep/feature-delta.md (slice-03)
# Evidence:  docs/analysis/installer-upgrade-orphan-analysis-2026-06-11.md
# Driving port: verify_nwave.main(["--json"], claude_config_dir=...) — the
# real verification CLI entry the operator runs; the same
# InstallationVerifier.run_verification() struct feeds the install summary
# (install_nwave.validate_installation). Real filesystem in tmp_path.
#
# Oracle: MANIFEST-BASED — expected set per family directory is the union of
# the family records in that directory's .nwave-manifest.json (the production
# SSOT slices 01/02 shipped). "Unaccounted" = on disk, tracked by no record:
# an informational listing, never a deletion instruction, never a failure.
# The verifier is read-only BY CONTRACT: every scenario closes with the
# universe-bound witness that nothing on disk changed.

Feature: The verifier reports what no asset family accounts for
  As an operator verifying a nWave installation
  I want an expected-vs-actual report per asset family that lists unaccounted files
  So that the next unknown orphan family becomes visible without anything ever being deleted

  @slice-03 @acceptance @driving_port @real-io @contract-shape:unbounded-preservation
  Scenario: The verifier reports every file no asset family accounts for
    Given the current nWave version is installed with every asset family recorded
    And scripts "superseded_tool.py" and "old_migration.py" linger among the installed scripts without any record
    And a folder "stale-flavor" lingers among the installed runtime assets without any record
    When the operator runs the installation verifier
    Then the report lists "superseded_tool.py" and "old_migration.py" as unaccounted in the scripts family
    And the report lists "stale-flavor" as unaccounted in the runtime assets family
    And the verification still passes
    And the verifier has changed nothing on disk and reported nothing else

  @slice-03 @acceptance @driving_port @real-io @contract-shape:unbounded-preservation
  Scenario: A fully accounted installation verifies clean, run after run
    Given the current nWave version is installed with every asset family recorded
    When the operator runs the installation verifier twice
    Then the report confirms every installed file is accounted for
    And both runs report exactly the same
    And the verification still passes
    And the verifier has changed nothing on disk and reported nothing else

  @slice-03 @acceptance @driving_port @real-io @contract-shape:unbounded-preservation
  Scenario: The user's own assets are reported as preserved, never as problems
    Given the current nWave version is installed with every asset family recorded
    And the user keeps a personal script "my_backup_tool.py" alongside the installed scripts
    And the user keeps a personal template "my-team-conventions.md" alongside the installed runtime assets
    And the user keeps a personal skill "nw-custom" among the installed skills
    When the operator runs the installation verifier
    Then the report notes each of the user's assets as preserved and not managed by nWave
    And none of the user's assets is reported as a problem
    And the verification still passes
    And the verifier has changed nothing on disk and reported nothing else
