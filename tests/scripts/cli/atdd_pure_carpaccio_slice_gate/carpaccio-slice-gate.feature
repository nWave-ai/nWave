@coupled:slice-03-gate
Feature: Carpaccio slice gate clears or blocks a slice at the DELIVER entry gate

  An operator (or orchestrator) submitting a slice for implementation on an
  atdd_pure feature is checked at the DELIVER entry gate before any crafter is
  dispatched. The gate enforces one indivisible "is this slice cleared to enter
  implementation?" contract with two halves: the carpaccio decomposition check
  (the slice is a thin enough vertical) and the AT-review check (the slice's
  acceptance tests were reviewed and approved). A slice enters implementation
  only when BOTH halves clear.

  The scenarios below form one coupled AT group (@coupled:slice-03-gate): the
  carpaccio decomposition check (assertions 1-4) and the AT-review check
  (assertion 5) ship in the same gate, share slice identification, and a slice
  must pass both -- greening the decomposition checks without the AT-review
  check would ship a gate that lets unreviewed acceptance tests reach the
  crafter. coupling_justification recorded in the slice plan.

  # ADR-028 D2-bis (carpaccio assertions 1-4) + ADR-029 D5 (assertion 5).
  # Driving port: the carpaccio-slice-gate CLI invoked as a DES entry_gate.
  # Layer 3 (subprocess/FS acceptance) -- example-only, no PBT (Mandate 9/11).

  Background:
    Given a repository for an atdd_pure feature

  @slice-03 @driving_port @walking_skeleton @contract-shape:pure-function
  Scenario: A thin, reviewed slice is cleared to enter implementation
    Given the feature carries a valid in-size slice plan
    And the entering slice has a recorded approved AT-review verdict
    When the operator runs the carpaccio slice gate for the entering slice
    Then the slice is cleared to enter implementation
    And the gate writes no file in the repository

  @slice-03 @driving_port @error @contract-shape:pure-function
  Scenario Outline: A slice that violates the carpaccio decomposition is blocked
    Given the feature carries <slice plan>
    And the entering slice has a recorded approved AT-review verdict
    When the operator runs the carpaccio slice gate for the entering slice
    Then the slice is <verdict>
    And the gate writes no file in the repository

    # ADR-028 D2-bis assertions 1-4: slice-size ceiling, incremental total
    # coverage, walking-skeleton-first ordering, value-annotation. A coverage
    # or ordering violation is exit 44 (D2-bis L224-226), same as an oversized
    # slice -- no separate verdict value. The missing-section row is exit 1.
    Examples: carpaccio decomposition failures
      | slice plan                                          | verdict                                |
      | an un-annotated over-size slice                     | blocked with an oversized slice error  |
      | an untagged authored scenario                       | blocked with an oversized slice error  |
      | a slice ordered before the walking-skeleton slice   | blocked with an oversized slice error  |
      | no slice plan section                               | blocked with a missing slice plan      |

  @slice-03 @driving_port @error @contract-shape:pure-function
  Scenario Outline: A malformed input is blocked with a diagnostic naming its cause
    Given the feature carries <slice plan>
    And the entering slice has a recorded approved AT-review verdict
    When the operator runs the carpaccio slice gate for the entering slice
    Then the slice is blocked with a malformed input error
    And the malformed-input diagnostic identifies "<cause>"
    And the gate writes no file in the repository

    # Both rows reach exit 2, but the operator's fix differs -- repair the
    # slice-plan table vs repair a .feature slice tag. The gate's JSON
    # diagnostic MUST name which input is at fault (parallel to how the
    # AT-review outline asserts the rejection `reason`).
    Examples: distinct malformed-input causes
      | slice plan                                          | cause                |
      | a malformed slice-plan table                        | the slice-plan table |
      | an orphan slice tag with no plan row                | a .feature slice tag |

  @slice-03 @driving_port @contract-shape:pure-function
  Scenario: An indivisible coupled over-size slice is cleared with its justification
    Given the feature carries a coupled over-size slice with a recorded justification
    And the entering slice has a recorded approved AT-review verdict
    When the operator runs the carpaccio slice gate for the entering slice
    Then the slice is cleared to enter implementation
    And the gate records that the coupled slice was accepted
    And the gate writes no file in the repository

  @slice-03 @driving_port @error @property @contract-shape:pure-function
  Scenario Outline: An unreviewed slice is refused before any crafter is dispatched
    Given the feature carries a valid in-size slice plan
    And the carpaccio decomposition check would otherwise pass
    But the AT-review state is "<at-review condition>"
    When the operator runs the carpaccio slice gate for the entering slice
    Then the slice is blocked with an AT-review rejection
    And the rejection names the reason "<reason>"
    And the gate writes no file in the repository

    Examples: the closed AT-review rejection reason set
      | at-review condition                                          | reason           |
      | the reviewer signing key is unavailable                      | key-absent       |
      | no AT-review verdict was recorded for the slice              | absent           |
      | the AT-review verdict is not an approval                     | not-approved     |
      | the AT-review verdict signature does not verify              | hmac-mismatch    |
      | the reviewed scenario set no longer matches the slice        | stale-at-set     |
      | a reviewed scenario body was rewritten after approval        | stale-at-content |
