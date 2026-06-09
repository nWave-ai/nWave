Feature: A slice's G_COMMIT commit is certified against the whole slice contract
  As an nWave operator shipping an ATDD-pure slice
  I want the G_COMMIT exit gate to refuse a commit unless it contains the
    slice's acceptance-test files AND passed the canonical contract gate
  So that "shipped" is a mechanical consequence of the exit gate passing,
    never an agent's narrative claim

  # slice-14 of the atdd-pure-roadmap-free-rollout. The exit-side symmetric
  # counterpart of slice-03's carpaccio ENTRY gate. Closes the RCA-diagnosed
  # "verification narrower than the contract" defect class
  # (docs/analysis/rca-slice-shipped-broken-verification-narrower-than-contract-2026-05-20.md).
  #
  # Regression ATs: FAIL on master -- the two CLIs
  # (verify_slice_commit_completeness.py, run_contract_gate.py) do not exist
  # as working surfaces; their RED scaffolds raise AssertionError. They PASS
  # once slice-14 lands.
  #
  # The G_COMMIT exit gate is ONE DES gate object with TWO assertions:
  #   E1 -- slice-commit completeness: the committed file set contains the
  #         slice's @slice-NN .feature files (RCA Gate 1, Branch A).
  #   E2 -- terminating run == contract gate: a Gate-Scope: digest is present
  #         and matches a fresh run_contract_gate.py --collect-only digest
  #         (RCA Gate 2, Branch B).
  #   Verdict -- the gate PASSES iff E1 AND E2 both pass; on FAIL, DES blocks
  #         G_COMMIT phase completion so "shipped" is mechanically derivable
  #         (RCA Gate 3, Branch C).
  #
  # @coupled:slice-14-exit-gate -- group of 3 ATs. coupling_justification:
  # commit-completeness and contract-gate-scope are ONE indivisible
  # "is this committed slice the whole deliverable?" exit-gate contract --
  # one DES gate object on G_COMMIT. Greening a-b without c, or either limb
  # without the other, would ship a half-gate certifying one subset of the
  # contract while the RCA defect class is precisely "verifier subset of
  # contract". 3 ATs = N, within ceiling -- @coupled documents indivisibility,
  # no size escape needed.
  #
  # SUT exit-gate state model (C2): the gate evaluates a single G_COMMIT
  # commit and resolves to PASS or FAIL. Two binary input axes drive it:
  #   commit AT-file content  in {INCLUDED, MISSING}      -> E1
  #   Gate-Scope: digest      in {MATCHING, MISMATCH, ABSENT} -> E2
  # Of the six (content x digest) combinations the gate PASSES exactly one:
  # (INCLUDED, MATCHING). The three scenarios below pin one FAIL-on-E1, one
  # FAIL-on-E2, and the single PASS -- the materially-distinct decision-table
  # rows (C5).
  #
  # Driving port: the G_COMMIT DES exit gate, exercised through its two
  # production CLIs (verify_slice_commit_completeness, run_contract_gate),
  # invoked via their argv entry points against a real git repository.
  # Layer 3 (subprocess / FS / git acceptance) -> example-only, no PBT
  # (Mandate 9/11). verify_slice_commit_completeness has a pure-read git
  # contract: the state-observing step asserts via assert_state_delta that the
  # gate mutates no git state -- no new commit, no working-tree change
  # (Mandate 8).

  @coupled:slice-14-exit-gate @driving_port @error @contract-shape:pure-function
  Scenario: A G_COMMIT commit missing the slice's acceptance-test files is refused
    Given a deliver repository for feature "atdd-pure-demo"
    And the operator has authored the slice's acceptance-test files and production code
    When the operator commits a G_COMMIT commit that is missing the slice's acceptance-test files with a matching contract-gate digest
    And the G_COMMIT exit gate is evaluated
    Then the G_COMMIT exit gate fails
    And the exit-gate diagnostic names the missing acceptance-test files
    And the slice is not certified as shipped

  @coupled:slice-14-exit-gate @walking_skeleton @driving_port @contract-shape:pure-function
  Scenario Outline: A G_COMMIT commit without a verified contract-gate scope is refused
    Given a deliver repository for feature "atdd-pure-demo"
    And the operator has authored the slice's acceptance-test files and production code
    When the operator commits a G_COMMIT commit that includes the slice's acceptance-test files with a <digest_state> contract-gate digest
    And the G_COMMIT exit gate is evaluated
    Then the G_COMMIT exit gate fails
    And the exit-gate diagnostic names the unverified contract-gate scope
    And the slice is not certified as shipped

    Examples: the digest is stale, or the digest is missing entirely
      | digest_state |
      | mismatching  |
      | absent       |

  @coupled:slice-14-exit-gate @walking_skeleton @driving_port @contract-shape:pure-function
  Scenario: A complete G_COMMIT commit with a verified contract-gate scope is certified
    Given a deliver repository for feature "atdd-pure-demo"
    And the operator has authored the slice's acceptance-test files and production code
    When the operator commits a G_COMMIT commit that includes the slice's acceptance-test files with a matching contract-gate digest
    And the G_COMMIT exit gate is evaluated
    Then the G_COMMIT exit gate passes
    And the slice is certified as shipped
    And the exit gate leaves the repository unchanged
