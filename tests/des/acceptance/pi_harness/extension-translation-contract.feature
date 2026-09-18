@adapter-integration
Feature: The pi extension translates pi events into DES decisions without deciding anything itself
  As the maintainer of one canonical enforcement engine
  I want the pi extension to be a pure protocol translator
  So that every allow/block verdict comes from the unchanged Python DES engine

  # Model-free: the translator contract is exercised by inspecting the rendered
  # extension's event-to-action mapping and by a direct DES adapter round-trip
  # with constructed payloads (SPIKE-0 Half-1 pattern). No live LLM turn.

  @US-2 @real-io
  Scenario: A production write is translated to the RED gate and the engine's block is relayed verbatim
    Given the rendered pi extension for an activated project
    When a production-code write tool call is presented to the translator
    Then the translator selects the pre-write gate action
    And a guarded write presented to the DES engine is answered with a block and a reason
    And the extension relays that block and reason without inventing its own

  @US-2 @real-io
  Scenario: An allowed write is relayed as allow
    Given the rendered pi extension for an activated project
    When an allowed write tool call is presented to the DES engine
    Then the DES engine answers allow and the translator blocks nothing

  @US-3
  Scenario: A commit tool call is translated to the step-completion validation
    Given the rendered pi extension for an activated project
    When a git commit tool call is presented to the translator
    Then the translator selects the step-completion validation action

  @US-3
  Scenario: A test-run result is translated to the suite-state recording action
    Given the rendered pi extension for an activated project
    When a test-run result is presented to the translator
    Then the translator selects the suite-state recording action

  @US-2
  Scenario: A non-mutating read tool call is passed through untouched
    Given the rendered pi extension for an activated project
    When a read-only tool call is presented to the translator
    Then the translator selects no DES action and blocks nothing

  @US-2 @error
  Scenario: A translator failure never blocks a legitimate tool call
    Given the rendered pi extension for an activated project
    When the DES engine cannot be reached during a tool call
    Then the translator fails open and blocks nothing

  @US-2
  Scenario: The extension contains no allow or block decision of its own
    Given the rendered pi extension for an activated project
    Then the extension defines no enforcement decision beyond relaying the engine's verdict
