@attribution @real-io @driving_port
Feature: The attribution toggle still reads on, off, and status
  As an nWave developer
  I want the attribution command to keep working the same way
  So that turning credit on or off is unchanged by the migration

  @contract-shape:bounded-change
  Scenario: Turning attribution on applies the dual credit
    Given a developer machine in the fresh state
    And the developer's commit credit is captured before the action
    When the developer runs attribution on
    Then the developer's commits carry the nWave dual credit
    And the action succeeds

  @contract-shape:bounded-change
  Scenario: Turning attribution off removes the credit
    Given a developer machine in the nwave_prior state
    When the developer runs attribution off
    Then the nWave credit is no longer applied to the developer's commits
    And the action succeeds

# NOTE: `attribution status` (pure-read) is behaviorally UNCHANGED by this
# migration (D3/AC7 — CLI signature unchanged; status reads the surviving
# global-config bookkeeping). It is already covered, green, by
# tests/installer/unit/test_attribution_cli.py and is intentionally NOT
# re-authored here as an active-RED AT (re-authoring an already-green,
# unchanged behavior would be a vacuous green / Fixture-Theater violation of
# the pre-DELIVER fail-for-right-reason gate).
