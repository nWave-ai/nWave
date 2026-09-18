@adapter-integration
Feature: Self-bootstrap a DES-tracked kata session
  As Devon handing the crafter a kata inside pi
  I want invoking the crafter to set up its own DES session automatically
  So that the whole cycle is recorded and verifiable with zero manual setup

  # Slice 01 (Story 1). NEW surface = the kata-session bootstrap helper that the
  # pi registered command delegates to (ADR-PKT-001 KD1/KD2): it runs the reused
  # des-init-log and writes the kata manifest + session marker. Layer 3
  # (@real-io @adapter-integration): real filesystem + real reused des-init-log,
  # example-only (Mandate 11), no PBT (Mandate 9). Engine reused UNCHANGED (K2).

  @US-1 @real-io @contract-shape:bounded-change
  Scenario: Bootstrapping a kata establishes a recorded, gate-ready session
    Given an activated pi project with no kata session yet
    When the crafter is invoked with the kata "fizzbuzz"
    Then a kata session is initialized for "fizzbuzz" with first step "01-01"
    And the kata session is recorded under the kata's deliver directory
    And no manual setup command was required

  @US-1 @real-io @error @contract-shape:unbounded-preservation
  Scenario: Bootstrapping outside an activated project leaves the project untouched
    Given a project that is not activated for the kata harness
    When the crafter is invoked with the kata "fizzbuzz"
    Then the kata bootstrap is refused
    And no kata session is created
    And the project filesystem is otherwise unchanged

  @US-1 @real-io @contract-shape:unbounded-preservation
  Scenario: Re-bootstrapping an existing session preserves the recorded history
    Given an activated pi project with an existing kata session for "fizzbuzz"
    When the crafter is invoked with the kata "fizzbuzz"
    Then the existing kata session for "fizzbuzz" is preserved unchanged
    And no duplicate kata session is created
