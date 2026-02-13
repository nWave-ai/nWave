# Feature: Milestone 1 - Plugin Infrastructure Validation
# Based on: journey-plugin-implementation-visual.md lines 22-44
# Phase: 1/6 (COMPLETED)
# Date: 2026-02-03

Feature: Plugin Infrastructure Validation
  As a nWave framework maintainer
  I want to validate that plugin infrastructure is operational
  So that I can build wrapper plugins on a solid foundation

  Background:
    Given the nWave project root is available
    And the Claude config directory is "~/.claude"
    And the current installer version is "1.2.0"

  @milestone-1 @phase-1 @completed @integration-checkpoint
  Scenario: Plugin infrastructure is operational and tested
    # Based on: journey-plugin-implementation-visual.md Milestone 1
    # TUI mockup reference: lines 36-51
    # Status: COMPLETE (commit d86acfa)

    Given design.md Phase 1 specification exists
    And base.py defines InstallationPlugin interface
    And registry.py implements PluginRegistry with topological sort

    When I run pytest on tests/install/test_plugin_registry.py

    Then all 10 unit tests pass
    And Kahn's algorithm correctly orders plugins by dependencies
    And circular dependency detection works (raises error on cycle)
    And priority ordering is validated (higher priority executes first)
    And test coverage is at least 70% for registry.py
    And the plugin infrastructure is ready for wrapper plugin creation
