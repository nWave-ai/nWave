# Feature: Project-Local Audit Logs Bug Detection
# Bug: Audit logs go to global location ~/.claude/des/logs/ instead of project-local
# Evidence: AuditLogger.__init__() hardcodes log_dir = home_dir / ".claude" / "des" / "logs"
# Expected: Default should be .nwave/des/logs/ with configuration override capability
# Date: 2026-02-04

Feature: Project-Local Audit Logs
  As a developer
  I want audit logs to be project-local by default
  So that each project has isolated audit trails for compliance and debugging

  Background:
    Given the test environment is initialized
    And a temporary project directory exists

  # ============================================================================
  # BUG DETECTION SCENARIOS - These tests FAIL with current buggy code
  # When bugs are fixed, these tests will PASS
  # ============================================================================

  @bug-2 @priority-critical
  Scenario: Audit logs should default to project-local directory
    # Current Behavior (BUG): Logs go to ~/.claude/des/logs/audit-YYYY-MM-DD.log
    # All projects share the same audit log, causing cross-contamination
    # Expected Behavior: Logs go to .nwave/des/logs/audit-YYYY-MM-DD.log

    Given I am in project directory "/tmp/test-project"
    And no audit log configuration is set
    When the DES audit logger initializes
    Then audit logs should be written to ".nwave/des/logs/"
    And audit logs should NOT be written to "~/.claude/des/logs/"

  @bug-2 @priority-critical
  Scenario: Each project should have isolated audit trails
    # Bug impact: Audit logs from different projects are mixed in global location
    # Makes compliance auditing and debugging difficult

    Given I am in project directory "/tmp/project-alpha"
    And the DES audit logger writes an event for project-alpha
    And I am in project directory "/tmp/project-beta"
    And the DES audit logger writes an event for project-beta
    Then project-alpha audit events should only appear in project-alpha logs
    And project-beta audit events should only appear in project-beta logs
    And the global audit log location should not contain either project's events

  @bug-2 @priority-high
  Scenario: Audit log location should be configurable via environment variable
    # Feature request tied to bug: No way to override location currently
    # Expected: DES_AUDIT_LOG_DIR environment variable should control location

    Given environment variable "DES_AUDIT_LOG_DIR" is set to "/custom/logs"
    When the DES audit logger initializes
    Then audit logs should be written to "/custom/logs/"
    And audit logs should NOT be written to "~/.claude/des/logs/"
    And audit logs should NOT be written to ".nwave/des/logs/"

  @bug-2 @priority-high
  Scenario: Audit log location should be configurable via config file
    # Feature request: Support configuration file for audit log location

    Given a DES config file exists with audit_log_dir set to "/config/logs"
    When the DES audit logger initializes
    Then audit logs should be written to "/config/logs/"

  @bug-2 @priority-high
  Scenario: Environment variable should override config file
    # Configuration precedence: ENV > config file > project-local default

    Given environment variable "DES_AUDIT_LOG_DIR" is set to "/env/logs"
    And a DES config file exists with audit_log_dir set to "/config/logs"
    When the DES audit logger initializes
    Then audit logs should be written to "/env/logs/"
    And audit logs should NOT be written to "/config/logs/"

  @bug-2 @priority-medium
  Scenario: Project-local log directory should be created automatically
    # Expected behavior: If .nwave/des/logs/ doesn't exist, create it

    Given I am in project directory "/tmp/new-project"
    And the directory ".nwave/des/logs/" does not exist
    When the DES audit logger initializes
    And the DES audit logger writes an event
    Then the directory ".nwave/des/logs/" should be created
    And the audit log file should exist in ".nwave/des/logs/"

  @bug-2 @priority-medium
  Scenario: Audit log rotation should work in project-local directory
    # Verify daily rotation works with new location

    Given I am in project directory "/tmp/test-project"
    And today is "2026-02-04"
    When the DES audit logger writes an event
    Then the audit log file should be named "audit-2026-02-04.log"
    And the file should be in ".nwave/des/logs/"

  @bug-2 @priority-low
  Scenario: Backward compatibility with existing global logs
    # Migration consideration: Don't break existing installations

    Given existing audit logs exist at "~/.claude/des/logs/"
    And environment variable "DES_AUDIT_LOG_MIGRATION" is set to "preserve"
    When the DES audit logger initializes
    Then existing global logs should remain accessible
    And new logs should go to project-local directory
