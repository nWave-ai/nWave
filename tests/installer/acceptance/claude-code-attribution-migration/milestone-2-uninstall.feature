@attribution @real-io @driving_port
Feature: Uninstall removes only the credit nWave applied
  As an nWave developer
  I want uninstall to be surgical
  So that removing nWave never touches my other Claude Code preferences

  @contract-shape:bounded-change
  Scenario: Uninstall removes the nWave credit and keeps unrelated preferences
    Given a developer machine in the theme_only state
    And nWave attribution was previously applied by an earlier nWave run
    And the developer's commit credit is captured before the action
    When the developer uninstalls nWave
    Then the nWave credit is no longer applied to the developer's commits
    And the developer's unrelated preferences are left intact

  @error @contract-shape:unbounded-preservation
  Scenario: Uninstall leaves a credit the developer edited after install untouched
    Given a developer machine in the user_custom state
    And nWave attribution was previously applied by an earlier nWave run
    And the developer later rewrites their credit to "new custom value"
    When the developer uninstalls nWave
    Then the developer's own credit "new custom value" is preserved
    And nWave notes the credit was user-modified and left it untouched
