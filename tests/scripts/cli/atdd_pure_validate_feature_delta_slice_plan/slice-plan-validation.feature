@slice-06
Feature: The slice-plan validator clears or rejects a Product Owner's slice plan

  A Product Owner running DISCUSS on an atdd_pure feature authors the carpaccio
  Slice Plan -- the `## Wave: DISCUSS / [REF] Slice Plan` section of the
  feature-delta, a five-column table (Slice, Value statement, Status,
  Annotation, Justification). Before that feature-delta flows downstream, the
  Product Owner runs the slice-plan check to confirm the section is present and
  structurally well formed, so a missing or malformed slice plan is caught at
  authoring time instead of at the DELIVER entry gate.

  The slice-plan check is the structural half of slice-plan validation: it
  asserts the section exists and the table carries the five required columns.
  The content half -- slice sizes, coverage, ordering -- belongs to the
  carpaccio slice gate (slice-03), a separate concern.

  # ADR-028 D2 / D2-bis (slice-plan section structure) + ADR-029 D3 (the
  # Product Owner authors the slice plan; DoR item "slice plan passes the
  # structural check"). Driving port: the validate-feature-delta CLI invoked
  # with --require-slice-plan.
  # Layer 3 (subprocess/FS acceptance) -- example-only, no PBT (Mandate 9/11).

  Background:
    Given a feature-delta authored for an atdd_pure feature

  @slice-06 @driving_port @walking_skeleton @contract-shape:pure-function
  Scenario: A well-formed slice plan clears the structural check
    Given the feature-delta carries a well-formed slice plan
    When the Product Owner runs the slice-plan check on the feature-delta
    Then the slice plan is accepted
    And the check leaves the feature-delta unchanged

  @slice-06 @driving_port @error @contract-shape:pure-function
  Scenario Outline: A feature-delta whose slice plan is unsound is rejected
    Given the feature-delta carries <slice plan>
    When the Product Owner runs the slice-plan check on the feature-delta
    Then the slice plan is <verdict>
    And the check leaves the feature-delta unchanged

    # ADR-028 D2 (L137) is explicit: the slice-plan table has "Five columns,
    # fixed order" -- Slice, Value statement, Status, Annotation, Justification.
    # D2-bis (L199) enumerates malformed conditions as "wrong column count,
    # missing required columns, duplicate slice_id, non-slice-NN identifier";
    # it does not separately name the reordered case, but D2's "fixed order"
    # is the binding contract -- a column re-order violates it, so a reordered
    # table is malformed (resolution recorded in the DISTILL [REF] note).
    # The rejection diagnostic names the cause so the Product Owner knows what
    # to repair. C1 (empty/zero-row table), C3 (zero / one / many slice rows),
    # C6 (malformed input -> explicit rejection, never silent acceptance).
    Examples: structurally unsound slice plans
      | slice plan                                          | verdict                                |
      | no slice-plan section                               | rejected for a missing slice plan      |
      | a slice plan with only four columns                 | rejected for a malformed slice plan    |
      | a slice plan with a header but zero slice rows       | rejected for a malformed slice plan    |
      | a slice plan whose table has the columns reordered  | rejected for a malformed slice plan    |

  @slice-06 @driving_port @contract-shape:pure-function
  Scenario: A slice plan listing many slices clears the structural check
    Given the feature-delta carries a slice plan with many slice rows
    When the Product Owner runs the slice-plan check on the feature-delta
    Then the slice plan is accepted
    And the check leaves the feature-delta unchanged

  @slice-06 @driving_port @contract-shape:pure-function
  Scenario: A feature-delta with no slice plan still passes the plain heading check
    Given the feature-delta carries no slice-plan section
    When the Product Owner runs the plain heading check on the feature-delta
    Then the slice plan is accepted

  @slice-06 @driving_port @error @contract-shape:pure-function
  Scenario: A malformed wave heading is rejected even when the slice plan is well formed
    Given the feature-delta carries a malformed wave heading and a well-formed slice plan
    When the Product Owner runs the slice-plan check on the feature-delta
    Then the slice plan is rejected for a malformed wave heading
    And the check leaves the feature-delta unchanged
