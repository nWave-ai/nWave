Feature: Marco can expand rationale on demand without re-running the wave
  As Marco working on a complex feature
  I want to request specific rationale sections at wave end without re-running the wave
  So that I pay tokens only for the context I actually need

  Background:
    Given Marco's nWave home is a fresh temporary directory
    And the global configuration records the default density as "lean"

  @US-7 @driving_port
  Scenario: nw-buddy reads the configuration reference before answering a density question
    Given the nw-buddy skill content is installed
    And the global-config reference document exists with a documentation density schema entry
    When Marco asks nw-buddy why his feature-delta.md is so short
    Then the nw-buddy skill content imperatively requires reading the global-config reference before answering configuration questions
    And the global-config reference document defines both the "lean" and "full" valid values
    And the configuring-doc-density guide cross-references the global-config reference

  @US-7 @driving_port
  Scenario: nw-buddy explains the expansion mechanism when Marco asks for more detail
    Given the nw-buddy skill content is installed
    When Marco asks nw-buddy how to see more detail in his feature documentation
    Then the nw-buddy skill content describes the expand mechanism for wave commands
    And the nw-buddy skill content mentions the wave-end interactive prompt
    And the nw-buddy skill content lists at least three example expansion identifiers

  @US-7 @driving_port @error
  Scenario: nw-buddy degrades gracefully when the configuration reference is missing
    Given the nw-buddy skill content is installed
    And the global-config reference document is absent
    When Marco asks nw-buddy a density-related question
    Then the nw-buddy skill content states that the configuration reference is unavailable when the document is missing
    And the nw-buddy skill content directs Marco to the troubleshooting path
    And the nw-buddy skill content does not provide fabricated valid values

  @property @driving_port @real-io
  Scenario: Telemetry schema is consistent across all wave-end documentation density events
    Given Marco has run any combination of wave-end choices producing documentation density events
    When the events are read from Marco's audit trail
    Then every documentation density event carries the keys "feature_id", "wave", "expansion_id", "choice", and "timestamp"
    And every choice value is one of "expand" or "skip"
    And every wave value is one of "DISCOVER", "DISCUSS", "DESIGN", "DEVOPS", "DISTILL", or "DELIVER"
