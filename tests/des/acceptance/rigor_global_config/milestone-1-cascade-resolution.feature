Feature: Rigor configuration cascade resolution
  As a developer working across multiple projects
  I want rigor configuration to resolve through a predictable cascade
  So that my global preferences apply everywhere unless a project explicitly overrides them

  The cascade order is: project rigor -> global rigor -> standard defaults.
  When a project has a rigor key, the entire global rigor block is ignored (full block override).

  Background:
    Given a temporary project directory exists
    And a temporary global configuration directory exists

  # --- Happy Path: Cascade levels ---

  Scenario: Project rigor present -- global rigor is completely ignored
    Given the project config has rigor profile "lean" with agent model "haiku"
    And the global config has rigor profile "custom" with agent model "opus"
    When rigor settings are loaded
    Then the active rigor profile is "lean"
    And the active agent model is "haiku"

  Scenario: No project rigor -- cascade to global rigor
    Given the project config has no rigor key
    And the global config has rigor profile "custom" with agent model "opus"
    When rigor settings are loaded
    Then the active rigor profile is "custom"
    And the active agent model is "opus"

  Scenario: No project rigor, no global config file -- use standard defaults
    Given the project config has no rigor key
    And no global config file exists
    When rigor settings are loaded
    Then the active rigor profile is "standard"
    And the active agent model is "sonnet"
    And the active reviewer model is "haiku"
    And the active TDD phases are the canonical 3-phase cycle

  Scenario: No project rigor, global config has no rigor key -- use standard defaults
    Given the project config has no rigor key
    And the global config has no rigor key
    When rigor settings are loaded
    Then the active rigor profile is "standard"
    And the active agent model is "sonnet"

  # --- Full block override verification ---

  Scenario: Project rigor overrides all global fields without merging
    Given the project config has rigor profile "lean" with agent model "haiku" and reviewer model "haiku"
    And the global config has rigor profile "thorough" with agent model "opus" and reviewer model "sonnet" and double review enabled
    When rigor settings are loaded
    Then the active rigor profile is "lean"
    And the active agent model is "haiku"
    And the active reviewer model is "haiku"
    And double review is disabled

  Scenario: Global rigor fields apply completely when project has no rigor
    Given the project config has no rigor key
    And the global config has rigor profile "thorough" with agent model "opus" and reviewer model "sonnet" and double review enabled
    When rigor settings are loaded
    Then the active rigor profile is "thorough"
    And the active agent model is "opus"
    And the active reviewer model is "sonnet"
    And double review is enabled

  # --- Error paths: corrupted and missing files ---

  Scenario: Corrupted global config file -- silent fallback to defaults
    Given the project config has no rigor key
    And the global config file contains invalid content
    When rigor settings are loaded
    Then the active rigor profile is "standard"
    And the active agent model is "sonnet"
    And no error is raised

  Scenario: Unreadable global config file -- silent fallback to defaults
    Given the project config has no rigor key
    And the global config file has restricted permissions
    When rigor settings are loaded
    Then the active rigor profile is "standard"
    And no error is raised

  # --- Edge cases ---

  Scenario: Project config has empty rigor block -- treated as project rigor present
    Given the project config has an empty rigor block
    And the global config has rigor profile "custom" with agent model "opus"
    When rigor settings are loaded
    Then the active rigor profile is "standard"
    And the active agent model is "sonnet"

  Scenario: Global config has partial rigor -- missing fields get standard defaults
    Given the project config has no rigor key
    And the global config has rigor with only profile "custom" and agent model "opus"
    When rigor settings are loaded
    Then the active rigor profile is "custom"
    And the active agent model is "opus"
    And the active reviewer model is "haiku"
    And the active TDD phases are the canonical 3-phase cycle
    And mutation testing is disabled

  @property
  Scenario: Cascade resolution never raises an exception regardless of config state
    Given any combination of project config and global config states
    When rigor settings are loaded
    Then the result is always a valid set of rigor settings
    And no exception is raised

  Scenario: Global config path is injectable for testing
    Given a custom global config path pointing to a test directory
    And that test directory has rigor profile "exhaustive" with agent model "opus"
    And the project config has no rigor key
    When rigor settings are loaded with the custom global path
    Then the active rigor profile is "exhaustive"
    And the active agent model is "opus"
