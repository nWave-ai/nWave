@adapter-integration
Feature: pi forces the crafter through canonical RED to GREEN to refactor
  As Devon handing a problem to the crafter inside pi
  I want every step-skip blocked at the pi tool-call boundary
  So that I can trust the code was built test-first with no regressions

  # Model-free per SPIKE-0 CI caveat (R4): the enforcement WIRING is asserted by
  # the DES engine's decision at each tool-call boundary (pre-write for RED, the
  # subagent-stop step-completion validation at the git-commit boundary). The
  # single step that genuinely needs a live model turn is tagged @requires_external
  # and skipped by default; its deterministic engine-decision analog is asserted
  # here instead.

  @US-2 @real-io
  Scenario: Writing implementation before a failing test is blocked at the write boundary
    Given the crafter is working in an activated pi project
    And no failing test justifies a production-code edit yet
    When the crafter attempts to write production code
    Then the write is blocked at the pi tool-call boundary with a reason
    And the production file is not created

  @US-2 @real-io
  Scenario: Writing the test first is allowed
    Given the crafter is working in an activated pi project
    When the crafter attempts to write a test file
    Then the write is allowed at the pi tool-call boundary

  @US-3
  Scenario: Committing a step that did not complete its phases is blocked at the commit boundary
    Given the crafter is working in an activated pi project
    And the current step has not recorded a completed cycle
    When the crafter attempts to commit the step
    Then the step completion is rejected at the commit boundary with a reason

  @US-3
  Scenario: Committing a step that completed its phases with a trailered commit is allowed
    Given the crafter is working in an activated pi project
    And the current step recorded a completed cycle with a Step-Id trailered commit
    When the crafter attempts to commit the step
    Then the step completion is accepted at the commit boundary

  @US-3 @requires_external
  Scenario: A live pi model turn honors the block on a real production write
    Given a real pi model backend is available
    And the crafter is working in an activated pi project with no failing test
    When the crafter model turn issues a production-code write tool call
    Then pi honors the block and the write does not occur
