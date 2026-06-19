Feature: Density mode is decided once at install and surfaced by doctor
  As Marco running nWave on his laptop
  I want a single density choice persisted at install time and visible from doctor
  So that I can audit and change my doc-density behaviour without grepping config files

  Background:
    Given Marco's nWave home is a fresh temporary directory

  @US-3 @driving_port
  Scenario: First-install prompts once for density and persists Marco's choice
    Given the nWave global configuration file does not exist
    When Marco runs install interactively and answers "lean"
    Then the global configuration records the default density as "lean"
    And the global configuration records the expansion prompt as "ask-intelligent"
    And running install a second time does not prompt Marco again

  @US-3 @driving_port
  Scenario: Non-interactive install defaults to lean density
    Given a continuous-integration host with no terminal and no existing global configuration
    When the pipeline runs install in non-interactive mode
    Then the global configuration records the default density as "lean"
    And the install completes without prompting

  @US-3 @driving_port @error
  Scenario: Upgrade path on existing configuration writes lean default silently with one notice
    Given an existing global configuration without a documentation block
    When Marco runs install interactively
    Then the global configuration records the default density as "lean"
    And the global configuration records the expansion prompt as "ask-intelligent"
    And Marco does not see an interactive density prompt
    And Marco sees exactly one informational line referencing the global configuration path

  @US-6 @driving_port @error
  Scenario: Doctor falls back to lean default and surfaces the no-config provenance
    Given the nWave global configuration file does not exist
    When Marco runs doctor
    Then Marco sees the line "Documentation density: lean (default (no config))"

  @US-5 @driving_port
  Scenario: Validator script exits zero on well-formed lean feature delta
    Given Marco has a well-formed lean feature-delta.md for feature "small-feat-x"
    When Marco runs the feature-delta schema validator on it
    Then the validator exits successfully
    And the validator reports the section count grouped by [REF], [WHY], and [HOW]

  @US-5 @driving_port @error
  Scenario: Schema validator fails on a malformed wave heading
    Given Marco has a feature-delta.md containing a heading "## Wave: DESIGN / Architecture" missing the schema prefix
    When Marco runs the feature-delta schema validator on it
    Then the validator exits non-zero
    And Marco sees the malformed heading reported with its line number and the failing rule

  # --- D12 rigor inheritance (AC-3.f, AC-3.g) ----------------------------------
  # custom is equivalent to override-path when documentation.density set, else default lean

  @US-3
  Scenario: Doctor reports density inherited from rigor.profile=thorough
    Given Marco's `~/.nwave/global-config.json` has `rigor.profile = "thorough"` set
    And no `documentation.density` key is present in the config
    When Marco runs `nwave-ai doctor`
    Then stdout contains `Documentation density: full (inherited from rigor.profile=thorough)`

  @US-3
  Scenario: Explicit density override wins over rigor.profile mapping
    Given Marco's `~/.nwave/global-config.json` has `documentation.density = "lean"` AND `rigor.profile = "thorough"` set
    When Marco runs `nwave-ai doctor`
    Then stdout contains `Documentation density: lean (explicit override)`

  @US-3
  Scenario Outline: density resolves from rigor.profile cascade
    Given Marco's `~/.nwave/global-config.json` has `rigor.profile = "<profile>"` set
    And no `documentation.density` key is present
    When Marco's wave skill calls `density_config.resolve_density(global_config)`
    Then the returned density is "<density>"
    And the returned expansion_prompt is "<prompt>"

    Examples:
      | profile    | density | prompt           |
      | lean       | lean    | always-skip      |
      | standard   | lean    | ask-intelligent  |
      | thorough   | full    | always-expand    |
      | exhaustive | full    | always-expand    |
      | custom     | lean    | ask-intelligent  |
