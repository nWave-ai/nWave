@activation_gating @driving_port @cli
Feature: The nwave-ai CLI is the single source of truth for activation

  The developer controls activation entirely through the CLI: enable or disable
  a project, set the global mode, and ask for the current status. Setting the
  mode preserves every other global setting. Status is read-only. Bad arguments
  produce a usage error, never a silent success. Shell completion offers exactly
  the published commands and never leaks internal hook vocabulary.

  Background:
    Given the global activation mode is "OPT_IN"
    And the nested ignore banner is present
    And the root ignore file uses the "SLASH_TRAILING" variant

  @contract-shape:bounded-change
  Scenario: Enabling a project records its activation and makes the marker trackable
    Given the project is under version control
    And the project marker is "ABSENT"
    When the operator enables this project
    Then the activation command succeeds
    And the project marker is written
    And the marker becomes trackable by version control

  @contract-shape:bounded-change
  Scenario: Disabling a project records a deliberate, sticky opt-out
    Given the project marker is "ENABLED"
    When the operator disables this project
    Then the activation command succeeds
    And the marker still reflects the deliberate opt-out

  @contract-shape:bounded-change
  Scenario: Setting the global mode to everywhere preserves other settings
    Given the project marker is "ABSENT"
    When the operator sets the global mode to "ALL"
    Then the activation command succeeds
    And the global mode is recorded as "ALL"

  @contract-shape:bounded-change
  Scenario: Setting the global mode back to opt-in preserves other settings
    When the operator sets the global mode to "OPT_IN"
    Then the activation command succeeds
    And the global mode is recorded as "OPT_IN"

  @contract-shape:pure-function
  Scenario: Status reports the global mode and the resolved project state
    Given the project marker is "ENABLED"
    When the operator asks for the activation status
    Then the activation command succeeds
    And the status report names the resolved project state

  @contract-shape:unbounded-preservation
  Scenario: An unrecognized activation command is rejected with a usage error
    When the operator runs an unrecognized activation command
    Then the activation command reports a usage error

  @contract-shape:pure-function
  Scenario: Bash completion lists the published commands and hides hook vocabulary
    When shell completion is generated for "BASH"
    Then the completion lists exactly the published activation commands
    And the completion omits any internal hook vocabulary

  @contract-shape:pure-function
  Scenario: Zsh completion lists the published commands and hides hook vocabulary
    When shell completion is generated for "ZSH"
    Then the completion lists exactly the published activation commands
    And the completion omits any internal hook vocabulary

  @contract-shape:bounded-change
  Scenario: An existing project is migrated silently on its first session
    Given the project marker is "ABSENT"
    And the project shows "EXECUTION_LOG" prior-use
    When the session adopts the project via "PRIOR_USE"
    Then the adoption outcome is "ADOPTED"
    And the project marker is written
