# Feature: Plugin System Walking Skeleton
# Based on: walking-skeleton.md - Minimal E2E Path
# Status: IMPLEMENT FIRST (proves architecture before adding complexity)
# Date: 2026-02-03

Feature: Plugin System Walking Skeleton
  As a developer
  I want to install a single plugin through the plugin infrastructure
  So that I can verify the plugin system works end-to-end before adding complexity

  Background:
    Given the nWave project root is available
    And the Claude config directory is "~/.claude"
    And plugin infrastructure exists (base.py, registry.py)

  @walking-skeleton @priority-critical @phase-2 @milestone-2
  Scenario: Install single plugin through complete infrastructure
    # Based on: walking-skeleton.md - Complete E2E path for ONE plugin
    # TUI mockup reference: walking-skeleton.md lines 410-437
    # Proves: Plugin discovery -> registration -> installation -> verification

    Given plugin infrastructure exists with base classes
    And AgentsPlugin is implemented with install() and verify() methods
    And a clean test installation directory exists
    And agent source files are available at "nWave/agents/nw/"
    And agent source directory contains at least 10 agent .md files

    When I create a PluginRegistry instance
    And I register AgentsPlugin with the registry
    And I create an InstallContext with test directory path
    And I call registry.install_plugin("agents", context)

    Then AgentsPlugin.install() executes successfully
    And agent files are copied to "{test_dir}/.claude/agents/nw/"
    And at least 1 agent .md file exists in the target directory
    And AgentsPlugin.verify() returns success with message "Agents verification passed"
    And the agents directory is accessible and functional
