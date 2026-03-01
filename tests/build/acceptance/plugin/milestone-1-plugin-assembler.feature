# Feature: Plugin Assembler with Metadata Generation
# Based on: architecture-design.md - Roadmap Step 01-01
# Acceptance Criteria:
#   - Plugin directory contains .claude-plugin/plugin.json with version from pyproject.toml
#   - All 23 agent files present in plugin/agents/
#   - All 98+ skill files present in plugin/skills/ preserving directory structure
#   - All 22 command files present in plugin/commands/nw/
# Date: 2026-02-27

Feature: Plugin Assembler with Metadata Generation
  As a developer distributing nWave
  I want the build pipeline to assemble all nWave components into a plugin directory
  So that the plugin contains every agent, skill, and command ready for Claude Code

  Background:
    Given the nWave source tree is available
    And a clean output directory for the plugin build
    And default build configuration for the nWave source tree

  # --- Happy Path: Metadata Generation ---

  Scenario: Plugin metadata includes version from project configuration
    When the plugin assembler builds the plugin
    Then the plugin metadata version matches the project version
    And the plugin metadata name is "nw"

  Scenario: Plugin metadata includes required marketplace fields
    When the plugin assembler builds the plugin
    Then the plugin metadata contains a description
    And the plugin metadata contains keywords for discoverability

  # --- Happy Path: Agent Assembly ---

  Scenario: All agent definitions are included in the plugin
    When the plugin assembler builds the plugin
    Then the plugin contains all 23 agent definitions
    And every agent file is readable and properly structured

  Scenario: Agent files preserve body content with skill refs rewritten
    When the plugin assembler builds the plugin
    Then every agent body is identical to the source
    And agents with skills have their frontmatter rewritten to bundle refs

  # --- Happy Path: Skill Assembly ---

  Scenario: All skill files are included preserving directory structure
    When the plugin assembler builds the plugin
    Then the plugin contains all skill files from the source tree
    And skill files are organized by agent name
    And the directory structure mirrors the source layout

  Scenario: Skill files are present with SKILL.md entry points
    When the plugin assembler builds the plugin
    Then every source skill file is present in the plugin
    And each skill directory has a SKILL.md entry point

  # --- Happy Path: Command Assembly ---

  Scenario: All command definitions are included in the plugin
    When the plugin assembler builds the plugin
    Then the plugin contains all command definitions
    And command files reside in the commands directory

  Scenario: Command files support the nw namespace for slash commands
    When the plugin assembler builds the plugin
    Then every command file produces a "/nw:" prefixed slash command

  # --- Happy Path: Version Synchronization ---

  Scenario: Version flows from single source of truth
    Given the project version is "2.18.0"
    When the plugin assembler builds the plugin
    Then the plugin metadata version is "2.18.0"

  # --- Error Paths ---

  Scenario: Build fails when source tree is missing agents directory
    Given the source tree is missing the agents directory
    When the plugin assembler attempts to build the plugin
    Then the build fails with a missing agents error
    And no partial plugin directory is created

  Scenario: Build fails when source tree is missing skills directory
    Given the source tree is missing the skills directory
    When the plugin assembler attempts to build the plugin
    Then the build fails with a missing skills error

  Scenario: Build fails when project version cannot be read
    Given the project configuration file is missing
    When the plugin assembler attempts to build the plugin
    Then the build fails with a version read error

  Scenario: Build fails when source tree is missing commands directory
    Given the source tree is missing the commands directory
    When the plugin assembler attempts to build the plugin
    Then the build fails with a missing commands error

  # --- Edge Cases ---

  Scenario: Build succeeds with minimum viable source tree
    Given a source tree with exactly 1 agent, 1 skill, and 1 command
    When the plugin assembler builds the plugin
    Then the plugin directory is created successfully
    And the plugin metadata is valid

  Scenario: Build handles agent files with special characters in names
    Given an agent file named "nw-solution-architect.md" exists in the source
    When the plugin assembler builds the plugin
    Then the agent file appears in the plugin with its original name

  @property
  Scenario: Every source agent appears exactly once in the plugin
    Given any valid nWave source tree
    When the plugin assembler builds the plugin
    Then every agent in the source has exactly one corresponding file in the plugin
    And no extra agent files are introduced

  @property
  Scenario: Plugin version always matches source version
    Given any valid project version string
    When the plugin assembler builds the plugin
    Then the plugin metadata version is identical to the source version
