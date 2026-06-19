@activation_gating @driving_port @resolution
Feature: nWave decides whether it is active for a project from a marker and a mode

  The activation decision is a pure rule over two inputs: the per-project marker
  ("enabled_for_repo") and the global mode ("opt-in" or "all"). The marker wins
  in both directions; a deliberate opt-out is sticky; with no marker the global
  mode decides; and a missing or unreadable global mode falls back to the
  non-invasive "opt-in" default.

  The complete nine-row truth table is exercised exhaustively in the companion
  parametrized specification (test_activation_resolution.py) — a finite,
  enumerable domain, so it is covered by parametrize rather than property-based
  generation. These scenarios pin the canonical readable cases for stakeholders.

  @contract-shape:pure-function
  Scenario: An opted-out project stays silent even when the world is opted in
    Given the project marker is "DISABLED"
    And the global activation mode is "ALL"
    When the activation state is resolved for this project
    Then the project is resolved "INACTIVE"

  @contract-shape:pure-function
  Scenario: An activated project comes alive even under the silent default
    Given the project marker is "ENABLED"
    And the global activation mode is "OPT_IN"
    When the activation state is resolved for this project
    Then the project is resolved "ACTIVE"

  @contract-shape:pure-function
  Scenario: An unmarked project under the silent default stays inactive
    Given the project marker is "ABSENT"
    And the global activation mode is "OPT_IN"
    When the activation state is resolved for this project
    Then the project is resolved "INACTIVE"

  @contract-shape:pure-function
  Scenario: An unmarked project under a corrupt global config falls back to silent
    Given the project marker is "ABSENT"
    And the global activation mode is "CORRUPT"
    When the activation state is resolved for this project
    Then the project is resolved "INACTIVE"
