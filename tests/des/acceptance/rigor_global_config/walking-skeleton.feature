Feature: Developer's rigor preferences follow them across projects
  As a developer working across multiple projects
  I want my rigor preferences to apply automatically in new projects
  So that I can stop manually configuring rigor in every project I open

  @walking_skeleton
  Scenario: Developer's global rigor profile applies in a project with no rigor configured
    Given Ale has set his global rigor profile to "custom" with agent model "opus"
    And project "client-C" has no rigor configuration
    When rigor settings are loaded for project "client-C"
    Then the active rigor profile is "custom"
    And the active agent model is "opus"

  @walking_skeleton
  Scenario: Developer's project-specific rigor takes priority over global preference
    Given Ale has set his global rigor profile to "custom" with agent model "opus"
    And project "nwave-ai" has rigor profile "lean" with agent model "haiku"
    When rigor settings are loaded for project "nwave-ai"
    Then the active rigor profile is "lean"
    And the active agent model is "haiku"

  @walking_skeleton
  Scenario: New user gets sensible defaults without any configuration
    Given Tomasz has never configured rigor anywhere
    And project "first-project" has no rigor configuration
    When rigor settings are loaded for project "first-project"
    Then the active rigor profile is "standard"
    And the active agent model is "sonnet"
    And the active reviewer model is "haiku"
    And the active TDD phases are the canonical 3-phase cycle
