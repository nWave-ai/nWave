# Feature: Integration Checkpoints - Cross-Milestone Validation
# Based on: journey-plugin-implementation-visual.md Integration Checkpoints
# Purpose: Validate integration between milestones
# Date: 2026-02-03

Feature: Integration Checkpoints
  As a nWave framework maintainer
  I want to validate integration between milestones
  So that I can catch integration issues early before proceeding

  Background:
    Given the nWave project root is available
    And the Claude config directory is "~/.claude"
    And plugin infrastructure exists (base.py, registry.py)

  @integration-checkpoint @phase-2
  Scenario: Phase 2 Integration Checkpoint - Plugins and Infrastructure Work Together
    # Based on: journey-plugin-implementation-visual.md lines 129-134

    Given plugin infrastructure is operational (Milestone 1)
    And all 4 wrapper plugins are implemented (Milestone 2)

    When I register all 4 plugins with PluginRegistry
    And I call registry.install_all(context) in test environment

    Then plugins call existing methods correctly
    And no behavioral changes occur (same output as monolithic)
    And circular import prevention is validated (no import errors)
    And unit tests for each plugin pass

  @integration-checkpoint @phase-3
  Scenario: Phase 3 Integration Checkpoint - Switchover Maintains Behavior
    # Based on: journey-plugin-implementation-visual.md lines 190-203

    Given plugin orchestration is active in install_framework()
    And baseline file tree from pre-plugin installer exists

    When I run plugin-based installer
    And I compare file tree with baseline

    Then same files are installed (path comparison matches)
    And same verification passes (InstallationVerifier output identical)
    And BackupManager still works (backups created successfully)
    And no regressions detected (file tree and verification identical)

  @integration-checkpoint @phase-4
  Scenario: Phase 4 Integration Checkpoint - DES Integrates with Plugin System
    # Based on: journey-plugin-implementation-visual.md lines 260-267

    Given wrapper plugins are operational (Milestone 2)
    And plugin orchestration is active (Milestone 3)
    And DES plugin is implemented (Milestone 4)

    When I install all 5 plugins

    Then DES module is importable (subprocess import test passes)
    And DES scripts are executable (chmod +x validated)
    And DES templates are installed (pre-commit config exists)
    And dependencies are respected (DES installed after utilities)

  @integration-checkpoint @phase-5
  Scenario: Phase 5 Integration Checkpoint - Full Ecosystem Functions
    # Based on: journey-plugin-implementation-visual.md lines 318-322

    Given all 5 plugins are operational
    And documentation is complete

    When I run complete test suite (unit + integration)
    And I run verification on fresh installation

    Then test suite passes (unit + integration + regression)
    And documentation is reviewed and approved
    And backward compatibility is validated (upgrade scenarios)
    And the system is production-ready
