@coupled:slice-07-at-authoring
Feature: DISTILL records a tamper-evident AT-review verdict for a reviewed slice

  An Acceptance-Test Designer running DISTILL on an atdd_pure feature authors a
  slice's acceptance tests, then dispatches the acceptance-designer reviewer.
  When the reviewer approves the slice's AT set, DISTILL records that approval
  as a tamper-evident verdict in the feature's AT-completion ledger -- the
  single audit record that lets the DELIVER entry gate later confirm the slice
  was reviewed before any crafter is dispatched.

  The scenarios below form one coupled AT group (@coupled:slice-07-at-authoring):
  authoring a slice's AT set and recording the AT-review verdict are one
  indivisible "produce a handoff-ready, gate-clearable slice spec" contract --
  an approved AT set with no recorded verdict cannot clear the DELIVER entry
  gate and so cannot reach implementation. coupling_justification recorded in
  the slice plan.

  # ADR-029 D5 (mandatory mechanical AT-review gate -- producer half).
  # Driving port: the at-review-verdict producer CLI invoked by DISTILL.
  # Layer 3 (subprocess/FS acceptance) -- example-only, no PBT (Mandate 9/11).
  # Contract: the producer SIGNS exactly the seven fields schema_version,
  # slice_id, verdict, reviewer_agent_id, at_ids, at_content_hash, timestamp;
  # event and hmac_sha256 are excluded from the signed input.

  Background:
    Given an atdd_pure feature with an empty AT-completion ledger

  @slice-07 @driving_port @walking_skeleton @contract-shape:bounded-change
  Scenario: An approved slice gets a signed verdict appended to the ledger
    Given an acceptance-designer reviewer approved the entering slice's AT set
    When the designer records the AT-review verdict for the entering slice
    Then the ledger gains one signed AT-review verdict for the entering slice
    And the recorded verdict verifies against the reviewer signing key
    And no earlier ledger record is altered

  @slice-07 @driving_port @contract-shape:bounded-change
  Scenario: The verdict signature covers the slice identity and the reviewed AT set
    Given an acceptance-designer reviewer approved the entering slice's AT set
    When the designer records the AT-review verdict for the entering slice
    Then the signed verdict covers the slice identity and the reviewed AT set
    And the signing input excludes the routing tag and the signature itself

  @slice-07 @driving_port @error @property @contract-shape:bounded-change
  Scenario Outline: A verdict altered after recording no longer verifies
    Given a slice with a recorded approved AT-review verdict in the ledger
    When the recorded verdict has its "<altered field>" altered
    Then recomputing the signature over the altered verdict fails to verify

    # Each row alters one signed field; the recomputed HMAC must diverge from
    # the stored signature -- the closed-world guarantee that the three fields
    # the DELIVER entry gate trusts (slice_id, at_ids, at_content_hash) cannot
    # be tampered with after the reviewer signed them.
    Examples: signed fields that void the signature when altered
      | altered field    |
      | slice identity   |
      | reviewed AT set  |
      | reviewed content |
      | schema version   |
      | reviewer verdict |

  @slice-07 @driving_port @error @contract-shape:bounded-change
  Scenario: A rejected slice review records no verdict
    Given an acceptance-designer reviewer asked the entering slice for revision
    When the designer completes the AT-review for the entering slice
    Then the ledger gains no AT-review verdict for the entering slice

  @slice-07 @driving_port @property @contract-shape:bounded-change
  Scenario Outline: The signed verdict covers a reviewed AT set of any size
    Given the entering slice has <reviewed test count> reviewed acceptance tests
    And an acceptance-designer reviewer approved the entering slice's AT set
    When the designer records the AT-review verdict for the entering slice
    Then the signed verdict lists <reviewed test count> reviewed test identifiers
    And the signed content fingerprint matches the reviewed acceptance tests

    # Cardinality of the reviewed AT set (zero/one/many). A slice with the
    # ADR-028 minimum of one scenario and a slice with many scenarios must
    # both produce a verdict whose at_content_hash reflects exactly those
    # bodies -- the closed-world guarantee that an in-place body rewrite of a
    # scenario keeping its id (the Hole-fix case) cannot reach the crafter
    # unreviewed. Layer 3: enumerated rows, not a Hypothesis @given (Mandate
    # 9/11). The default two-scenario size is already covered above.
    Examples: reviewed AT set sizes
      | reviewed test count |
      | 1                   |
      | 7                   |

  @slice-07 @driving_port @contract-shape:bounded-change
  Scenario: A re-reviewed slice appends a fresh verdict the gate will trust
    Given an acceptance-designer reviewer approved the entering slice's AT set
    When the designer records the AT-review verdict for the entering slice
    And the designer records the AT-review verdict a second time for the slice
    Then the ledger holds two signed AT-review verdicts for the entering slice
    And no earlier ledger record is altered
    And the second recorded verdict is the one a later gate would trust
