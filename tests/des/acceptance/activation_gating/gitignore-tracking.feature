@activation_gating @driving_port @gitignore @real-io
Feature: The activation marker becomes trackable by version control

  The marker only matters if it travels with the repository, but nWave's own
  ignore rules hide it twice: the whole ".nwave" directory is excluded at the
  repository root, and everything inside ".nwave" is excluded by the nested
  ignore file. Activating a project repairs both layers so the marker is
  trackable, preserves the nested generation banner, leaves a re-run unchanged,
  and copes with whatever shape the root ignore line happens to take.

  Background:
    Given the project is under version control
    And the global activation mode is "OPT_IN"
    And the nested ignore banner is present

  @contract-shape:bounded-change
  Scenario: The shipped ignore line is repaired so the marker is trackable
    Given the root ignore file uses the "SLASH_TRAILING" variant
    And the project marker is "ENABLED"
    When the gitignore is fixed for the marker
    Then the marker becomes trackable by version control
    And the nested ignore banner is preserved

  @contract-shape:bounded-change
  Scenario: A customized root ignore without an nWave line still tracks the marker
    Given the root ignore file uses the "NO_NWAVE_LINE" variant
    And the project marker is "ENABLED"
    When the gitignore is fixed for the marker
    Then the marker becomes trackable by version control

  @contract-shape:bounded-change
  Scenario: A no-slash ignore variant is recognized and repaired
    Given the root ignore file uses the "NO_SLASH" variant
    And the project marker is "ENABLED"
    When the gitignore is fixed for the marker
    Then the marker becomes trackable by version control

  @contract-shape:bounded-change
  Scenario: A leading-slash ignore variant is recognized and repaired
    Given the root ignore file uses the "LEADING_SLASH" variant
    And the project marker is "ENABLED"
    When the gitignore is fixed for the marker
    Then the marker becomes trackable by version control

  @contract-shape:unbounded-preservation
  Scenario: Fixing an already-fixed ignore file changes nothing
    Given the root ignore file uses the "ALREADY_FIXED" variant
    And the project marker is "ENABLED"
    When the gitignore is fixed for the marker
    And the gitignore is fixed for the marker a second time
    Then the marker becomes trackable by version control
    And the ignore files are unchanged from the first fix
