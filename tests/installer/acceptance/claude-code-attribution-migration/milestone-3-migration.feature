@attribution @real-io @driving_port
Feature: Upgrading dismantles the old commit hook
  As an nWave developer with the legacy hook installed
  I want the upgrade to retire the old hook and adopt the new credit surface
  So that I am never left with two competing credit mechanisms

  @error @contract-shape:bounded-change
  Scenario: Installing over a legacy hook retires it and adopts the dual credit
    Given a developer machine in the legacy_hook state
    When the developer installs nWave
    Then the legacy commit hook is dismantled
    And the developer's commits carry the nWave dual credit instead
