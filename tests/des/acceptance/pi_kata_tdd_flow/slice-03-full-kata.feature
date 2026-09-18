@adapter-integration
Feature: Solve a kata end-to-end, strictly verified
  As Devon deciding whether to trust a kata's provenance
  I want the full multi-step kata to show an ordered, gate-verified TDD trail
  So that I can merge on verifiable proof the discipline held end-to-end

  # Slice 03 (Story 3, closes the DoD). NEW surface = multi-step decomposition +
  # ordered recording (reused des-log-phase) verified by the UNCHANGED commit
  # gate via the synthesized transcript (KD4). Layer 3 (@real-io
  # @adapter-integration): real tmp git repo + real reused CLIs + real adapter
  # round-trip; example-only (Mandate 11), no PBT (Mandate 9). Engine reused
  # UNCHANGED (K2). The single live-model end-to-end run is @requires_external
  # (skipped); its deterministic analog is asserted model-free below.

  @US-3 @real-io @contract-shape:bounded-change
  Scenario: A multi-step kata records each step's cycle in plan order
    Given a kata "fizzbuzz" decomposed into an ordered step-by-step plan
    When the crafter completes every planned step in order
    Then each step shows RED then GREEN then COMMIT in plan order
    And the Step-Id commit history matches the planned step order

  @US-3 @real-io @error @contract-shape:unbounded-preservation
  Scenario: Skipping a step in a multi-step kata is blocked at the commit boundary
    Given a kata "fizzbuzz" decomposed into an ordered step-by-step plan
    And an earlier step was completed and committed
    And a later step is committed without recording its cycle
    When the skipped step is validated at the commit boundary
    Then the step completion is rejected at the commit boundary with a reason
    And the completed earlier step remains accepted

  # Live-faithful pre-commit regression (step 01-01). The LIVE gate fires on the
  # bash `git commit` tool_call, BEFORE the commit exists. Validating at that
  # order, a complete RED+GREEN+COMMIT cycle must be ALLOWED on phase-completeness
  # alone -- with NO commit-verification attempt (no COMMIT_NOT_VERIFIED, no "no
  # commits yet"). An incomplete cycle must still BLOCK on the missing phases.
  @US-3 @real-io @contract-shape:bounded-change
  Scenario: A complete cycle is allowed at the pre-commit boundary before any commit exists
    Given a kata "fizzbuzz" decomposed into an ordered step-by-step plan
    And the current step records a complete RED then GREEN then COMMIT cycle
    When the step completion is validated at the pre-commit boundary before committing
    Then the step completion is allowed at the pre-commit boundary
    And the commit gate never attempted commit verification

  @US-3 @real-io @error @contract-shape:unbounded-preservation
  Scenario: An incomplete cycle is blocked at the pre-commit boundary before any commit exists
    Given a kata "fizzbuzz" decomposed into an ordered step-by-step plan
    And the current step records only a RED phase
    When the step completion is validated at the pre-commit boundary before committing
    Then the step completion is rejected at the commit boundary with a reason

  @US-3 @real-io @error @contract-shape:unbounded-preservation
  Scenario: A reverted step-id in the manifest surfaces as a blocked commit
    Given a kata "fizzbuzz" with a step "01-02" recorded as a completed increment
    And the kata manifest step-id is reverted to an earlier step mid-kata
    When the step completion is validated at the commit boundary
    Then the step completion is rejected at the commit boundary with a reason

  @US-3 @requires_external @contract-shape:bounded-change
  Scenario: A live pi model solves a real kata end-to-end with a verified trail
    Given a real pi model backend is available
    And the crafter is invoked with the kata "fizzbuzz" in an activated pi project
    When the crafter solves the kata through self-driven strict TDD
    Then the execution log and Step-Id commit history show the strict ordered cycle
    And an attempted step-skip was blocked at the commit boundary
