@adapter-integration
Feature: Self-driven per-test cycle with phase recording
  As Devon reading the kata's audit trail afterwards
  I want the crafter to record RED then GREEN then COMMIT for each tiny increment
  So that every step leaves auditable, gate-verified proof it was test-first

  # Slice 02 (Story 2). Chained narrative (Pillar 2): each scenario's Given
  # reuses the prior scenario's Given+When step methods. NEW surface = the
  # synthesized-transcript commit-context assembler (ADR-PKT-001 KD4) feeding the
  # UNCHANGED subagent-stop engine, plus phase recording via the reused
  # des-log-phase. Layer 3 (@real-io @adapter-integration): real tmp git repo +
  # real reused CLIs + real adapter round-trip; example-only (Mandate 11), no
  # PBT (Mandate 9). Engine reused UNCHANGED (K2). Fresh step-id per cycle
  # (SPIKE constraint 3). Block delivered via stdout decision=block at exit 0
  # (SPIKE constraint 1).

  @US-2 @real-io @contract-shape:bounded-change
  Scenario: Recording a completed increment leaves an ordered phase trail
    Given a bootstrapped kata session for "fizzbuzz" on step "01-01"
    When the crafter records a completed increment for step "01-01"
    Then the step shows phases RED then GREEN then COMMIT in order
    And only that step's phase trail changed

  @US-2 @real-io @contract-shape:unbounded-preservation
  Scenario: A completed increment with a trailered commit is accepted at the boundary
    Given a kata step "01-01" recorded a completed increment
    And the increment was committed with Step-Id and Task-Id trailers
    When the step completion is validated at the commit boundary
    Then the step completion is accepted at the commit boundary
    And the commit-context transcript carried the four required DES markers

  @US-2 @real-io @error @contract-shape:unbounded-preservation
  Scenario: An incomplete increment is blocked at the commit boundary with a reason
    Given a bootstrapped kata session for "fizzbuzz" on step "01-01"
    And the step recorded only the failing-test phase
    When the step completion is validated at the commit boundary
    Then the step completion is rejected at the commit boundary with a reason
    And no increment is recorded as accepted

  @US-2 @real-io @error @contract-shape:unbounded-preservation
  Scenario: A malformed commit-context transcript is treated as no DES context
    Given a kata step "01-01" recorded a completed increment
    And the increment was committed with Step-Id and Task-Id trailers
    And the commit-context transcript markers are malformed
    When the step completion is validated at the commit boundary
    Then the boundary finds no DES context to verify
