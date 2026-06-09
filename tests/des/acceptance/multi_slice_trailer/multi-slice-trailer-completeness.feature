Feature: A batched commit is certified against every slice it lists
  As an nWave operator shipping interleaved ATDD-pure slices
  I want the slice-commit-completeness exit gate to accept a commit that lists
    multiple Slice-Id trailers and verify completeness for each listed slice
  So that an interleaved multi-slice session can ship one honest batched commit
    without the gate falsely rejecting it for a missing single Slice-Id

  # Regression suite for friction F-07
  # (docs/analysis/atdd-pure-dogfooding-friction-2026-05-20.md).
  #
  # The per-slice G_COMMIT contract assumed one commit per slice carrying a
  # single `Slice-Id: slice-NN` trailer. But the whole-tree-stashing pre-commit
  # hook forces interleaved multi-slice / multi-fix work to batch into ONE
  # commit -- which then has no clean single Slice-Id and
  # `verify_slice_commit_completeness` rejects it
  # (`MalformedInput: commit carries no Slice-Id:/Step-Id: trailer`, or it
  # verifies only the first trailer and silently ignores the rest).
  #
  # Intended fix this suite pins: the exit gate ACCEPTS a commit carrying
  # MULTIPLE `Slice-Id:` trailer lines (one per slice the batched commit
  # covers) and verifies slice-commit completeness for EACH listed slice.
  # A single-`Slice-Id:` commit keeps working unchanged; a zero-trailer commit
  # is still correctly rejected `MalformedInput`.
  #
  # Regression contract:
  #   - the two MULTIPLE-trailer scenarios FAIL on master (the current gate
  #     reads only the first `Slice-Id:` trailer -- multi-trailer handling is
  #     absent -> MISSING_FUNCTIONALITY). They PASS once the F-07 fix lands.
  #   - the SINGLE-trailer and NONE-trailer scenarios are no-regression pins:
  #     they already pass on master and MUST keep passing after the fix.
  #
  # SUT exit-gate state model (C2): the gate evaluates one batched G_COMMIT
  # commit and resolves to ACCEPTED or REJECTED. Two input axes drive it:
  #   trailer shape   in {SINGLE, MULTIPLE, NONE}
  #   slice coverage  in {COMPLETE, ONE_MISSING}
  # The materially-distinct decision-table rows (C5): a complete multi-trailer
  # commit ACCEPTS and reports per-slice; a complete single-trailer commit
  # ACCEPTS (the pre-F-07 pin); a zero-trailer commit REJECTS `MalformedInput`
  # (the pin that the fix must not loosen); a multi-trailer commit with one
  # listed slice deficient REJECTS and names that slice.
  #
  # Driving port: the `verify_slice_commit_completeness` CLI, invoked via its
  # argv entry point against a real git repository under tmp_path. Layer 3
  # (subprocess / FS / git acceptance) -> example-only, no PBT (Mandate 9/11).
  # The CLI has a pure-read git contract: the PASS scenario asserts via
  # assert_state_delta that evaluating the gate mutates no git state -- no new
  # commit, no working-tree change (Mandate 8).

  @driving_port @contract-shape:pure-function
  Scenario: A batched commit listing multiple slices is certified when every listed slice is complete
    Given a deliver repository for an interleaved multi-slice session
    And the operator has authored each slice's acceptance-test files and production code
    When the operator commits a batched commit carrying multiple Slice-Id trailers with every listed slice's acceptance-test files
    And the slice-commit-completeness exit gate is evaluated
    Then the exit gate accepts the batched commit
    And the exit-gate result reports completeness for every listed slice
    And the exit gate leaves the repository unchanged

  @driving_port @contract-shape:pure-function
  Scenario: A commit carrying a single Slice-Id trailer is still certified
    Given a deliver repository for an interleaved multi-slice session
    And the operator has authored each slice's acceptance-test files and production code
    When the operator commits a batched commit carrying a single Slice-Id trailer with every listed slice's acceptance-test files
    And the slice-commit-completeness exit gate is evaluated
    Then the exit gate accepts the batched commit

  @driving_port @error @contract-shape:pure-function
  Scenario: A commit carrying no Slice-Id trailer is still refused as malformed input
    Given a deliver repository for an interleaved multi-slice session
    And the operator has authored each slice's acceptance-test files and production code
    When the operator commits a batched commit carrying no Slice-Id trailer with every listed slice's acceptance-test files
    And the slice-commit-completeness exit gate is evaluated
    Then the exit gate rejects the batched commit
    And the exit-gate diagnostic reports malformed input

  @driving_port @error @contract-shape:pure-function
  Scenario: A batched commit listing multiple slices is refused when one listed slice is deficient
    Given a deliver repository for an interleaved multi-slice session
    And the operator has authored each slice's acceptance-test files and production code
    When the operator commits a batched commit carrying multiple Slice-Id trailers with one listed slice's acceptance-test files missing
    And the slice-commit-completeness exit gate is evaluated
    Then the exit gate rejects the batched commit
    And the exit-gate diagnostic names the deficient slice
