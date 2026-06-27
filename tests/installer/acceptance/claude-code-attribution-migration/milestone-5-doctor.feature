@attribution @real-io @driving_port
Feature: Diagnosis reports the commit-credit state without changing it
  As an nWave developer
  I want a read-only report of my attribution state
  So that I can diagnose credit gaps without risking my configuration

  @contract-shape:unbounded-preservation
  Scenario: Diagnosis reports current credit owner, legacy hook, and deprecated toggle
    Given a developer machine in the nwave_prior state
    When the developer asks nWave to diagnose attribution
    Then the diagnosis names the current credit owner as nwave
    And the diagnosis reports whether a legacy commit hook remains
    And the diagnosis surfaces the deprecated attribution toggle
