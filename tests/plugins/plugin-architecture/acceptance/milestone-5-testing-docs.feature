# Feature: Milestone 5 - Testing and Documentation
# Based on: journey-plugin-implementation-visual.md lines 137-166
# Phase: 5/6
# Date: 2026-02-03

Feature: Testing and Documentation
  As a nWave framework maintainer
  I want comprehensive testing and documentation for the plugin system
  So that the system is production-ready and maintainable

  Background:
    Given the nWave project root is available
    And the Claude config directory is "~/.claude"
    And the current installer version is "1.2.0"
    And plugin infrastructure exists (base.py, registry.py)

  @milestone-5 @phase-5 @priority-medium
  Scenario: Full installation with all plugins succeeds
    # Based on: journey-plugin-implementation-visual.md Milestone 5
    # TUI mockup reference: lines 285-303
    # Integration checkpoint: Complete test coverage

    Given all 5 plugins are registered (agents, commands, templates, utilities, des)
    And a clean installation directory exists

    When I run install_nwave.py with full plugin installation
    And I call registry.install_all(context)

    Then all 5 plugins install in correct dependency order
    And test coverage is at least 80% (pytest-cov)
    And all unit tests pass (plugin isolation tests)
    And all integration tests pass (fresh install + upgrade scenarios)
    And verification reports all components as OK

  @milestone-5 @phase-5 @priority-medium
  Scenario: Selective installation excludes plugins correctly
    # Based on: Plugin architecture extensibility - selective installation

    Given all 5 plugins are registered
    And user specifies --exclude flag: "des"

    When I run install_nwave.py --exclude des

    Then 4 plugins are installed (agents, commands, templates, utilities)
    And DES plugin is NOT installed
    And DES module is NOT found at "~/.claude/lib/python/des/"
    And verification reports DES as "Not Installed (excluded)"
    And the installation is otherwise complete and functional

  @milestone-5 @phase-5 @priority-medium
  Scenario: Selective uninstallation removes only specified plugins
    # Based on: Plugin architecture extensibility - plugin uninstall

    Given all 5 plugins are installed
    And user specifies plugin to uninstall: "des"

    When I run install_nwave.py --uninstall des

    Then DES plugin is uninstalled
    And DES module is removed from "~/.claude/lib/python/des/"
    And DES scripts are removed from "~/.claude/scripts/"
    And other plugins remain installed (agents, commands, templates, utilities)
    And verification reports DES as "Not Installed"
    And other components verify successfully

  @milestone-5 @phase-5 @error-handling @priority-medium
  Scenario: Selective uninstallation fails when plugin has dependents
    # Based on: architecture-decisions.md - Dependency validation on uninstall
    # Addresses reviewer feedback: Error path for selective operations

    Given all 5 plugins are installed
    And DESPlugin declares dependencies on ["templates", "utilities"]
    And user attempts to uninstall "utilities" (has dependent: DES)

    When I run install_nwave.py --uninstall utilities

    Then uninstallation is blocked with error code 1
    And error message contains "Cannot uninstall 'utilities': required by DES"
    And error lists all dependent plugins: "DES depends on utilities"
    And no files are removed (operation aborts safely)
    And all plugins remain installed and functional
    And utilities plugin is still present at "~/.claude/scripts/"

  @milestone-5 @phase-5 @regression
  Scenario: Upgrade from monolithic installer preserves existing installation
    # Based on: architecture-decisions.md - Backward compatibility validation

    Given a monolithic installer (v1.2.0) installation exists
    And agents, commands, templates, utilities are installed

    When I upgrade to plugin-based installer (v1.3.0)
    And I run install_nwave.py upgrade

    Then existing components are detected and preserved
    And BackupManager creates backup before upgrade
    And DES plugin is added without affecting existing components
    And verification passes for all components (old + new)
    And no existing functionality is broken
