@plugin_skill_deliverable_type @driving_port @enforcement
Feature: A project's deliverable type decides whether step work is policed

  When a project builds application code, every dispatch that mentions a step of
  the plan must carry DES markers or it is blocked -- this keeps app-code work
  under disciplined monitoring. When a project builds a Claude Code plugin or
  skill instead, that same dispatch is waved through by default, because there is
  no test-driven step apparatus to police. The practitioner no longer hand-stamps
  an exemption on every dispatch.

  The decision is exercised through the real enforcement gate
  (PreToolUseService.validate, the driving port). The complete matrix over
  (step-id present x explicit marker x deliverable type) -- including the
  fail-safe rows for an unknown or mis-cased type -- is exercised exhaustively in
  the companion parametrized specification (test_deliverable_type_enforcement.py),
  a finite enumerable domain covered by parametrize rather than property-based
  generation. These scenarios pin the canonical readable cases for stakeholders.

  @contract-shape:pure-function @driving_port
  Scenario: A plugin project runs a planned step without being policed or stamped
    Given a project that builds a "PLUGIN" deliverable
    When an agent is dispatched to run a planned step with no markers
    Then the dispatch is allowed to proceed
    And it is waved through because of the deliverable type
    And no per-dispatch exemption marker was needed

  @contract-shape:pure-function
  Scenario: A skill project runs a planned step without being policed
    Given a project that builds a "SKILL" deliverable
    When an agent is dispatched to run a planned step with no markers
    Then the dispatch is allowed to proceed
    And it is waved through because of the deliverable type

  @contract-shape:pure-function
  Scenario: An application project keeps planned-step work under discipline
    Given a project that builds an "APPLICATION" deliverable
    When an agent is dispatched to run a planned step with no markers
    Then the dispatch is blocked for missing discipline markers

  @contract-shape:pure-function @error
  Scenario: A project with no declared deliverable keeps work under discipline
    Given a project that builds an "UNSET" deliverable
    When an agent is dispatched to run a planned step with no markers
    Then the dispatch is blocked for missing discipline markers

  @contract-shape:pure-function @error
  Scenario: A mis-spelled deliverable type quietly re-imposes discipline
    Given a project that builds a "TYPO" deliverable
    When an agent is dispatched to run a planned step with no markers
    Then the dispatch is blocked for missing discipline markers

  @contract-shape:pure-function @error
  Scenario: A mis-cased deliverable type is not honoured and discipline holds
    Given a project that builds a "MIXEDCASE" deliverable
    When an agent is dispatched to run a planned step with no markers
    Then the dispatch is blocked for missing discipline markers

  @contract-shape:pure-function
  Scenario: An explicit exemption still releases an application dispatch
    Given a project that builds an "APPLICATION" deliverable
    When an agent is dispatched to run a planned step carrying an explicit exemption
    Then the dispatch is allowed to proceed
    And it is waved through because of the explicit marker

  @contract-shape:pure-function
  Scenario: An ordinary dispatch with no planned step is never policed
    Given a project that builds an "APPLICATION" deliverable
    When an agent is dispatched with an ordinary request and no planned step
    Then the dispatch is allowed to proceed
    And it is waved through because there was no planned step
