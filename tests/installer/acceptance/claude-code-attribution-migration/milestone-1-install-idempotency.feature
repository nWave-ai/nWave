@attribution @real-io @driving_port
Feature: Re-installing never disturbs an already-applied or hand-edited credit
  As an nWave developer
  I want repeated installs to be safe
  So that upgrading nWave never duplicates or overwrites my commit credit

  @contract-shape:unbounded-preservation
  Scenario: Re-install retires a leftover nWave-applied credit
    Given a developer machine in the nwave_prior state
    And the developer's commit credit is captured before the action
    When the developer installs nWave again
    Then the leftover nWave-applied credit is cleaned up

  @error @contract-shape:unbounded-preservation
  Scenario: Re-install over a developer's own credit preserves it
    Given a developer machine in the user_custom state
    When the developer installs nWave again
    Then the developer's own credit "my custom trailer" is preserved
