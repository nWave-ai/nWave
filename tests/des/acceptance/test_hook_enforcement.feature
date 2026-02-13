Feature: Hook Enforcement Audit Trail
  As Priya (Tech Lead)
  I want hook enforcement events to include feature_name and step_id
  So that I can trace audit events back to specific features and steps during PR review

  Background:
    Given the audit log writer is initialized
    And the system time is "2026-02-07T19:00:00Z"

  Scenario: SubagentStop hook logs PASSED event with feature_name and step_id
    Given I am validating step "01-01" in feature "audit-log-refactor"
    And all 7 TDD phases are complete
    And there are no scope violations
    When the subagent stop hook validates the step
    Then the audit log contains a PASSED event
    And the PASSED event has feature_name "audit-log-refactor"
    And the PASSED event has step_id "01-01"

  Scenario: SubagentStop hook logs FAILED event with feature_name and step_id
    Given I am validating step "02-01" in feature "user-auth-feature"
    And only 3 TDD phases are complete
    When the subagent stop hook validates the step
    Then the audit log contains a FAILED event
    And the FAILED event has feature_name "user-auth-feature"
    And the FAILED event has step_id "02-01"

  Scenario: SubagentStop hook logs SCOPE_VIOLATION with feature_name and step_id
    Given I am validating step "03-02" in feature "payment-gateway"
    And all 7 TDD phases are complete
    And there is a scope violation for file "src/unrelated/OrderService.py"
    When the subagent stop hook validates the step
    Then the audit log contains a SCOPE_VIOLATION event
    And the SCOPE_VIOLATION event has feature_name "payment-gateway"
    And the SCOPE_VIOLATION event has step_id "03-02"

  Scenario: PreToolUse hook logs ALLOWED event with feature_name and step_id
    Given I am invoking a Task for step "04-01" in feature "api-refactor"
    And the task has max_turns set to 30
    When the pre-tool-use hook validates the task invocation
    Then the audit log contains a ALLOWED event
    And the ALLOWED event has feature_name "api-refactor"
    And the ALLOWED event has step_id "04-01"
