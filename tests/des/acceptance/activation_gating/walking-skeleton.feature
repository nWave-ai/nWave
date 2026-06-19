@activation_gating @walking_skeleton @driving_port @real-io
Feature: A developer activates nWave for one project and leaves all others silent

  nWave installs its hooks globally, so today they fire in every repository the
  developer opens. The activation gate makes nWave non-invasive: only a project
  the developer has activated runs nWave logic; every other project is silent.

  The walking skeleton proves the whole loop end to end through the production
  composition root: the developer activates a project, the marker is written and
  made trackable by version control, and a subsequent hook in that project is
  dispatched normally — while an unactivated project's hook is allowed through
  without ever blocking.

  Background:
    Given the project is under version control
    And the global activation mode is "OPT_IN"
    And the nested ignore banner is present
    And the root ignore file uses the "SLASH_TRAILING" variant

  @contract-shape:bounded-change
  Scenario: Developer activates a project and its hooks come to life, trackably
    Given the project marker is "ABSENT"
    When the operator enables this project
    Then the activation command succeeds
    And the project marker is written
    And the marker becomes trackable by version control
    And the nested ignore banner is preserved
