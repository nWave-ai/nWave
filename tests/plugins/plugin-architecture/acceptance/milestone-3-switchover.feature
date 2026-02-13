# Feature: Milestone 3 - Switchover to Plugin System
# Based on: journey-plugin-implementation-visual.md lines 75-104
# Phase: 3/6
# Date: 2026-02-03

Feature: Switchover to Plugin System
  As a nWave framework maintainer
  I want to switch the installer to use the plugin system
  So that components can be installed through the modular architecture

  Background:
    Given the nWave project root is available
    And the Claude config directory is "~/.claude"
    And the current installer version is "1.2.0"
    And plugin infrastructure exists (base.py, registry.py)

  @milestone-3 @phase-3 @priority-critical @integration-checkpoint
  Scenario: Installer uses PluginRegistry for installation orchestration
    # Based on: journey-plugin-implementation-visual.md Milestone 3
    # TUI mockup reference: lines 151-174
    # Critical change: install_framework() -> registry.install_all()

    Given wrapper plugins are complete (Milestone 2)
    And install_framework() is modified to use PluginRegistry

    When I run install_nwave.py with plugin orchestration
    And registry.install_all(context) is called

    Then all 4 plugins are installed in correct order
    And InstallContext provides all required utilities
    And BackupManager creates backups before installation
    And installation completes successfully
    And verification passes for all components

  @milestone-3 @phase-3 @priority-critical @regression
  Scenario: Behavioral equivalence with monolithic installer
    # Based on: journey-plugin-implementation-visual.md Integration Checkpoint
    # TUI mockup reference: lines 190-203
    # Validation: File tree comparison before/after switchover

    Given a baseline installation from pre-plugin installer exists
    And baseline file tree is captured

    When I run plugin-based installer on clean directory
    And I compare resulting file tree with baseline

    Then the same files are installed to the same locations
    And the same verification passes (InstallationVerifier output identical)
    And file contents are byte-for-byte identical
    And no regressions are detected in installation behavior

  @milestone-3 @phase-3 @error-handling
  Scenario: Plugin installation rolls back on failure
    # Based on: architecture-decisions.md GAP-PROCESS-02 - Rollback strategy

    Given BackupManager is configured and operational
    And 2 plugins install successfully (agents, commands)
    And the 3rd plugin (templates) fails during installation

    When the installation failure is detected
    And rollback procedure is triggered

    Then BackupManager restores from backup
    And agents and commands directories are removed
    And the system state matches pre-installation
    And no partial plugin installations remain
    And the error is logged with details for debugging
