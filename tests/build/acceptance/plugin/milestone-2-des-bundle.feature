# Feature: DES Bundle with Hooks Generation
# Based on: architecture-design.md - Roadmap Step 01-02
# Acceptance Criteria:
#   - DES module importable from plugin scripts/des/
#   - hooks.json registers PreToolUse, PostToolUse, SubagentStop, SessionStart, SubagentStart
#   - DES enforcement returns allow/block decisions with error messages on phase violations
#   - DES runtime templates bundled in plugin
# Date: 2026-02-27

Feature: DES Bundle with Hooks Generation
  As a developer distributing nWave
  I want the plugin to include a self-contained DES enforcement engine
  So that TDD phase enforcement works without any external dependencies

  Background:
    Given the nWave source tree is available
    And a clean output directory for the plugin build
    And default build configuration for the nWave source tree

  # --- Happy Path: DES Module Bundling ---

  Scenario: DES module is importable from the plugin directory
    When the plugin assembler builds the plugin
    Then the DES module exists in the plugin scripts directory
    And the DES module can be imported as a standalone package

  Scenario: DES imports are rewritten for standalone operation
    When the plugin assembler builds the plugin
    Then the DES module runs without depending on the original source layout

  Scenario: DES module works without external packages
    When the plugin assembler builds the plugin
    Then the DES module has no external package dependencies

  # --- Happy Path: Hooks Generation ---

  Scenario: Hook registrations cover all DES enforcement events
    When the plugin assembler builds the plugin
    Then the hook configuration registers a handler for tool validation
    And the hook configuration registers a handler for task completion
    And the hook configuration registers a handler for subagent lifecycle
    And the hook configuration registers a handler for session startup

  Scenario: Hook commands use plugin-relative paths
    When the plugin assembler builds the plugin
    Then every hook command references the plugin root variable
    And no hook command references a home directory path

  # --- Happy Path: DES Templates ---

  Scenario: DES runtime templates are bundled in the plugin
    When the plugin assembler builds the plugin
    Then the TDD cycle schema template exists in the plugin
    And the roadmap schema template exists in the plugin

  # --- Error Paths ---

  Scenario: Build fails when DES source directory is missing
    Given the source tree is missing the DES source directory
    When the plugin assembler attempts to build the plugin
    Then the build fails with a missing DES source error

  Scenario: Build fails when import rewriting produces invalid syntax
    Given a DES source file with an unrewritable import pattern
    When the plugin assembler attempts to build the plugin
    Then the build fails with an import rewriting error
    And the error message identifies the problematic file

  Scenario: Build fails when hook template references are invalid
    Given a hook configuration template with a missing command path
    When the plugin assembler attempts to build the plugin
    Then the build fails with a hook configuration error

  # --- Edge Cases ---

  Scenario: Plugin does not ship compiled Python files
    When the plugin assembler builds the plugin
    Then the plugin does not ship compiled Python files

  @property
  Scenario: DES import rewriting is complete for any source tree
    Given any valid nWave source tree
    When the plugin assembler builds the plugin
    Then the DES module runs without depending on the original source layout
    And every rewritten DES file is syntactically valid Python

  @property
  Scenario: Hook configuration always contains all required event types
    Given any valid nWave source tree
    When the plugin assembler builds the plugin
    Then the configuration contains handlers for all five DES event types
