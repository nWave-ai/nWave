# Feature: Milestone 4 - DES Plugin Integration
# Based on: journey-plugin-implementation-visual.md lines 106-135
# Phase: 4/6
# Date: 2026-02-03

Feature: DES Plugin Integration
  As a nWave framework maintainer
  I want to add DES as a plugin to the nWave installer
  So that DES can be installed/uninstalled independently without modifying installer code

  Background:
    Given the nWave project root is available
    And the Claude config directory is "~/.claude"
    And the current installer version is "1.2.0"
    And plugin infrastructure exists (base.py, registry.py)

  @milestone-4 @phase-4 @priority-high
  Scenario: DES plugin installs successfully
    # Based on: journey-plugin-implementation-visual.md Milestone 4
    # TUI mockup reference: lines 212-232
    # Prerequisites: DES scripts and templates MUST exist (GAP-PREREQ-01, 02)

    Given wrapper plugins are operational (Milestone 2)
    And plugin orchestration is active (Milestone 3)
    And DES source exists at "src/des/"
    And DES scripts exist at "nWave/scripts/des/"
    And DES templates exist at "nWave/templates/"
    And DESPlugin declares dependencies: ["templates", "utilities"]

    When I create DESPlugin and register it with PluginRegistry
    And I call registry.install_all(context)

    Then DES is installed AFTER templates and utilities (dependency resolution)
    And DES module is copied to "~/.claude/lib/python/des/"
    And DES scripts are copied to "~/.claude/scripts/"
    And DES templates are copied to "~/.claude/templates/"
    And DES installation completes without installer changes

  @milestone-4 @phase-4 @priority-high
  Scenario: DES module is importable after installation
    # Based on: journey-plugin-implementation-visual.md Milestone 4 validation
    # CLI command reference: lines 264-265
    # Integration checkpoint: line 130 (DES module importable)

    Given DESPlugin installation is complete

    When I run subprocess import test: "python3 -c 'import sys; sys.path.insert(0, \"~/.claude/lib/python\"); from des.application import DESOrchestrator; print(\"DES OK\")'"

    Then the import succeeds without errors
    And the output contains "DES OK"
    And DES module is functional and accessible
    And DESOrchestrator class can be instantiated

  @milestone-4 @phase-4 @priority-high
  Scenario: DES scripts are executable and functional
    # Based on: architecture-decisions.md GAP-PREREQ-01 - DES scripts
    # Integration checkpoint: line 131 (DES scripts executable)

    Given DESPlugin installation is complete
    And DES scripts are installed at "~/.claude/scripts/"

    When I check file permissions on check_stale_phases.py
    And I check file permissions on scope_boundary_check.py

    Then both scripts have executable permissions (chmod +x)
    And both scripts can be executed: "python3 ~/.claude/scripts/check_stale_phases.py"
    And scripts execute without import errors
    And scripts output help or status messages correctly

  @milestone-4 @phase-4 @error-handling
  Scenario: DESPlugin fails gracefully when prerequisites missing
    # Based on: architecture-decisions.md GAP-PREREQ-01 - HIGH risk scenario

    Given DES source exists at "src/des/"
    But DES scripts do NOT exist at "nWave/scripts/des/"
    And DES templates do NOT exist at "nWave/templates/"

    When I attempt to install DESPlugin

    Then installation returns PluginResult with success=False
    And error message contains "DES scripts not found: nWave/scripts/des/"
    And error message contains "DES templates not found: nWave/templates/"
    And no partial DES files are installed
    And the error is logged with clear remediation steps
