@attribution-activation-coupling @doctor-report
Feature: The doctor explains why a commit did or did not get the credit
  After the scope change a user needs to diagnose "why no credit here?". The
  doctor reports the hook registration state, this repo's activation state, any
  legacy settings residue, and the deprecated include-co-author flag — read from
  its correct top-level location. The doctor is a diagnostic, never a gate, and
  never mutates the settings.

  # AB-9 — doctor surfaces hook + activation + residue.
  @ab-9 @driving_port @contract-shape:unbounded-preservation
  Scenario: Doctor reports hook, activation, and legacy residue state
    Given a active repo
    And the attribution commit hook is registered
    And an nWave-managed legacy attribution credit in the Claude settings
    When the operator runs the doctor
    Then the doctor reports the hook registration state
    And the doctor reports this repo's activation state
    And the doctor reports the legacy settings residue state

  # AB-9 — DDD-7 bug fix: deprecated flag read from TOP-LEVEL, not nested.
  @ab-9 @error @contract-shape:unbounded-preservation
  Scenario: Doctor reads the deprecated flag from the top level of the settings
    Given a active repo
    And the deprecated include-co-author flag is set the top level
    When the operator runs the doctor
    Then the doctor reads the deprecated flag from the top level

  # AB-11 — doctor over absent settings is fail-open.
  @ab-11 @error @contract-shape:unbounded-preservation
  Scenario: Doctor over an absent Claude settings file fails open
    Given a active repo
    And the Claude settings file is absent
    When the operator runs the doctor
    Then the operation completes without error

  # AB-11 — doctor over corrupt settings is fail-open, leaves it untouched.
  @ab-11 @error @contract-shape:unbounded-preservation
  Scenario: Doctor over a corrupt Claude settings file leaves it untouched
    Given a active repo
    And the Claude settings file is corrupt
    When the operator runs the doctor
    Then the operation completes without error
    And the Claude settings are left untouched
