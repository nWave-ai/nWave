# Feature: Milestone 2 - Wrapper Plugins Implementation
# Based on: journey-plugin-implementation-visual.md lines 46-73
# Phase: 2/6
# Date: 2026-02-03

Feature: Wrapper Plugins Implementation
  As a nWave framework maintainer
  I want to implement wrapper plugins for existing installation methods
  So that the monolithic installer can be modularized incrementally

  Background:
    Given the nWave project root is available
    And the Claude config directory is "~/.claude"
    And the current installer version is "1.2.0"
    And plugin infrastructure exists (base.py, registry.py)

  @milestone-2 @phase-2 @priority-critical
  Scenario: All wrapper plugins are implemented and functional
    # Based on: journey-plugin-implementation-visual.md Milestone 2
    # TUI mockup reference: lines 85-104
    # Integration checkpoint: lines 129-134

    Given plugin infrastructure is operational (Milestone 1 complete)
    And module-level functions are extracted from install_nwave.py
    And circular import prevention is validated

    When I create AgentsPlugin wrapper around install_agents_impl()
    And I create CommandsPlugin wrapper around install_commands_impl()
    And I create TemplatesPlugin wrapper around install_templates_impl()
    And I create UtilitiesPlugin wrapper around install_utilities_impl()

    Then all 4 wrapper plugins call existing methods correctly
    And no behavioral changes occur (same output as pre-plugin)
    And no circular import errors are detected
    And each plugin has unit tests that pass
    And each plugin implements fallback verification logic

  @milestone-2 @phase-2 @priority-critical
  Scenario: Plugin dependency resolution works correctly
    # Based on: walking-skeleton.md expansion - Multi-plugin orchestration
    # Proves: Topological sort with dependencies between plugins

    Given PluginRegistry contains 4 registered plugins
    And AgentsPlugin has dependencies: []
    And CommandsPlugin has dependencies: []
    And TemplatesPlugin has dependencies: []
    And UtilitiesPlugin has dependencies: []

    When I call registry.get_installation_order()

    Then installation order respects plugin priorities
    And plugins are returned in deterministic order
    And no circular dependencies are detected
    And the order is [agents, commands, templates, utilities]

  @milestone-2 @phase-2 @error-handling
  Scenario: Plugin installation handles circular dependencies gracefully
    # Based on: journey-plugin-implementation-visual.md Integration Checkpoint
    # Error scenario: Circular dependency detection

    Given PluginA declares dependencies: ["PluginB"]
    And PluginB declares dependencies: ["PluginA"]

    When I register both plugins with PluginRegistry
    And I call registry.get_installation_order()

    Then a CircularDependencyError is raised
    And the error message contains both plugin names
    And the error message explains the circular dependency path
    And no plugins are installed (operation aborts safely)

  @milestone-2 @phase-2 @error-handling
  Scenario: Plugin installation fails gracefully when prerequisites missing
    # Based on: architecture-decisions.md - Fallback verification
    # Error scenario: Plugin installation failure handling

    Given AgentsPlugin is registered
    And agent source files do NOT exist at "nWave/agents/nw/"

    When I call registry.install_plugin("agents", context)

    Then the installation returns PluginResult with success=False
    And the error message contains "Agent source files not found"
    And the installation is marked as failed in plugin registry
    And no partial files are created in target directory
