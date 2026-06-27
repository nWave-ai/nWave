@attribution @real-io @driving_port
Feature: Applying the credit degrades gracefully on a hostile machine
  As an nWave developer on an unusual machine
  I want credit application to fail safely
  So that a missing or corrupt configuration never breaks my install

  @error @contract-shape:unbounded-preservation
  Scenario: Claude Code not installed yet leaves the machine untouched
    Given a developer machine in the claude_absent state
    When the developer installs nWave
    Then nWave declines to change the developer's machine and explains why
    And no commit-attribution hook is left on the machine

  @error @contract-shape:unbounded-preservation
  Scenario: A corrupt Claude configuration is not stomped on install
    Given a developer machine in the malformed state
    And the developer's commit credit is captured before the action
    When the developer installs nWave
    Then the corrupt configuration is left exactly as it was
    And no commit-attribution hook is left on the machine
