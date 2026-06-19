@activation_gating @driving_port @auto-marking
Feature: nWave silently adopts projects that already use it, without ever prompting

  Existing projects must keep working after the upgrade with zero friction. When
  a project shows evidence of real nWave work, the session adopts it silently —
  writing the marker, no prompt. A brand-new project's first real agent dispatch
  also adopts the project and lets that very dispatch proceed (detect-and-adopt,
  not skip). A mere install (a bare config left behind) is NOT evidence, or the
  gate would be meaningless. And a deliberate opt-out is sticky — no adoption
  path may ever overwrite it.

  Background:
    Given the global activation mode is "OPT_IN"
    And the nested ignore banner is present
    And the root ignore file uses the "SLASH_TRAILING" variant

  @contract-shape:bounded-change
  Scenario: A project with real prior work is adopted silently at session start
    Given the project marker is "ABSENT"
    And the project shows "AUDIT_LOG_NONEMPTY" prior-use
    When the session adopts the project via "PRIOR_USE"
    Then the adoption outcome is "ADOPTED"
    And the project marker is written

  @contract-shape:bounded-change
  Scenario: A project with feature artifacts is adopted at session start
    Given the project marker is "ABSENT"
    And the project shows "FEATURE_DELTA" prior-use
    When the session adopts the project via "PRIOR_USE"
    Then the adoption outcome is "ADOPTED"
    And the project marker is written

  @contract-shape:bounded-change
  Scenario: A project with a DELIVER wave directory is adopted at session start
    Given the project marker is "ABSENT"
    And the project shows "DELIVER_DIR" prior-use
    When the session adopts the project via "PRIOR_USE"
    Then the adoption outcome is "ADOPTED"
    And the project marker is written

  @contract-shape:unbounded-preservation
  Scenario: A freshly installed project with no real work is not adopted
    Given the project marker is "ABSENT"
    And the project shows "BARE_DES_CONFIG" prior-use
    When the session adopts the project via "PRIOR_USE"
    Then the adoption outcome is "NOT_WARRANTED"
    And no project marker is written

  @contract-shape:unbounded-preservation
  Scenario: A project with no evidence at all is not adopted
    Given the project marker is "ABSENT"
    And the project shows "NONE" prior-use
    When the session adopts the project via "PRIOR_USE"
    Then the adoption outcome is "NOT_WARRANTED"
    And no project marker is written

  @contract-shape:bounded-change
  Scenario: A brand-new project's first agent dispatch adopts it and proceeds
    Given the project marker is "ABSENT"
    When an nWave agent is dispatched in this project
    Then the project is adopted and the agent dispatch proceeds
    And the project marker is written

  @contract-shape:unbounded-preservation
  Scenario: A deliberate opt-out is never overwritten by prior-use adoption
    Given the project marker is "DISABLED"
    And the project shows "AUDIT_LOG_NONEMPTY" prior-use
    When the session adopts the project via "PRIOR_USE"
    Then the adoption outcome is "NO_OP_STICKY"
    And the marker still reflects the deliberate opt-out

  @contract-shape:unbounded-preservation
  Scenario: A deliberate opt-out survives a real agent dispatch
    Given the project marker is "DISABLED"
    When an nWave agent is dispatched in this project
    Then the marker still reflects the deliberate opt-out

  @contract-shape:unbounded-preservation
  Scenario: Adoption on a read-only project fails open without crashing
    Given the project marker is "ABSENT"
    And the project shows "AUDIT_LOG_NONEMPTY" prior-use
    And the project filesystem is "READ_ONLY"
    When the session adopts the project via "PRIOR_USE"
    Then no project marker is written
