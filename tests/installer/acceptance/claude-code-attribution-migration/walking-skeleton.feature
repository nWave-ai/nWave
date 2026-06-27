@attribution @real-io @driving_port
Feature: Commit credit follows the developer everywhere
  As an nWave developer
  I want my commits to carry the nWave credit through Claude Code's own surface
  So that the credit survives a forced commit and never depends on a fragile hook

  @walking_skeleton @contract-shape:bounded-change
  Scenario: Fresh install applies the dual credit and leaves no legacy hook
    Given a developer machine in the fresh state
    When the developer installs nWave
    Then the developer's commits carry the nWave dual credit
    And no legacy commit hook is left on the machine
