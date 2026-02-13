# Feature: Milestone 6 - Deploy and Validate
# Based on: journey-plugin-implementation-visual.md lines 168-197
# Phase: 6/6
# Date: 2026-02-03

Feature: Deploy and Validate
  As a nWave framework maintainer
  I want to deploy the plugin system to production
  So that users can benefit from the modular architecture

  Background:
    Given the nWave project root is available
    And the Claude config directory is "~/.claude"
    And plugin infrastructure exists (base.py, registry.py)

  @milestone-6 @phase-6 @priority-low
  Scenario: Version bump and deployment succeed
    # Based on: journey-plugin-implementation-visual.md Milestone 6
    # TUI mockup reference: lines 340-357
    # Version strategy: architecture-decisions.md GAP-ARCH-00

    Given all tests pass (unit + integration)
    And documentation is complete
    And version in pyproject.toml is "1.4.0"

    When I bump version to "1.7.0" for production release
    And I update CHANGELOG.md with migration notes
    And I create release notes
    And I tag release: "git tag v1.7.0"

    Then version in pyproject.toml is "1.7.0"
    And CHANGELOG.md documents all changes from 1.2.0 -> 1.7.0
    And release notes include DES feature announcement
    And git tag v1.7.0 exists
    And the release is ready for deployment

  @milestone-6 @phase-6 @priority-low @e2e
  Scenario: End-to-end user journey completes successfully
    # Based on: journey-plugin-implementation-visual.md CLI Journey
    # TUI mockup reference: lines 245-282
    # Complete user perspective validation

    Given user downloads nWave installer v1.7.0
    And user has no existing nWave installation

    When user runs: "python scripts/install/install_nwave.py"
    And installation completes

    Then user sees output: "Installing 5 plugins..."
    And user sees progress: "[1/5] Installing: agents"
    And user sees progress: "[2/5] Installing: commands"
    And user sees progress: "[3/5] Installing: templates"
    And user sees progress: "[4/5] Installing: utilities"
    And user sees progress: "[5/5] Installing: des"
    And user sees: "Installation complete"
    And user can verify installation: "python scripts/install/install_nwave.py --verify"
    And verification table shows all components OK with counts

  @milestone-6 @phase-6 @priority-low
  Scenario: DES is available for production use after installation
    # Based on: journey-plugin-implementation-visual.md - Success criteria
    # CLI command reference: lines 280-282

    Given user has successfully installed nWave v1.7.0 with DES plugin
    And user creates a new nWave project

    When user runs: "/nw:develop 'new feature'"

    Then DES audit trail is created: ".des/audit/audit-2026-02-03.log"
    And DES log contains: "TASK_INVOCATION_STARTED" event
    And DES tracks execution phases (RED_UNIT, GREEN, REFACTOR, etc.)
    And DES enforces scope boundaries during development
    And DES detects stale phases on commit (pre-commit hook)
    And user experiences zero friction with DES integration

  @quality-gate @phase-6
  Scenario: All success criteria are met for production release
    # Based on: journey-plugin-implementation.yaml lines 16-21

    Given plugin system is fully implemented
    And all integration checkpoints pass

    When I validate success criteria

    Then DES module is importable after installation (100% success)
    And all integration tests pass (fresh + upgrade scenarios)
    And zero breaking changes for existing installations
    And plugin dependency resolution works (topological sort correct)
    And documentation is complete and clear
    And user can install DES with zero friction
