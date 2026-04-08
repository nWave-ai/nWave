Feature: Enforcement policy does not block non-step numeric patterns
  As an orchestrator launching non-DES agents
  I want prompts containing dates, line ranges, version ranges, and similar patterns to pass through
  So that only genuine step execution work triggers DES enforcement

  # Issue: nWave-ai/nWave#33
  # Root Cause: STEP_ID_PATTERN regex matches ANY NN-NN token, not just step IDs

  # --- FALSE POSITIVES: must NOT trigger enforcement (currently RED) ---

  @e2e @enforcement @false-positive
  Scenario: Date reference in prompt is not mistaken for a step identifier
    Given an agent prompt mentioning "Fix the issue from 03-29"
    And no DES markers are present
    When the enforcement hook evaluates the prompt
    Then the prompt is allowed through
    And no block reason is returned

  @e2e @enforcement @false-positive
  Scenario: Numeric build range in prompt is not mistaken for a step identifier
    Given an agent prompt mentioning "builds 10-12 failed in CI"
    And no DES markers are present
    When the enforcement hook evaluates the prompt
    Then the prompt is allowed through
    And no block reason is returned

  @e2e @enforcement @false-positive
  Scenario: Line range in prompt is not mistaken for a step identifier
    Given an agent prompt mentioning "see lines 50-80"
    And no DES markers are present
    When the enforcement hook evaluates the prompt
    Then the prompt is allowed through
    And no block reason is returned

  @e2e @enforcement @false-positive
  Scenario: Port range in prompt is not mistaken for a step identifier
    Given an agent prompt mentioning "ports 80-82 are exposed"
    And no DES markers are present
    When the enforcement hook evaluates the prompt
    Then the prompt is allowed through
    And no block reason is returned

  @e2e @enforcement @false-positive
  Scenario: Page reference in prompt is not mistaken for a step identifier
    Given an agent prompt mentioning "pages 10-15"
    And no DES markers are present
    When the enforcement hook evaluates the prompt
    Then the prompt is allowed through
    And no block reason is returned

  @e2e @enforcement @false-positive
  Scenario: Time reference in prompt is not mistaken for a step identifier
    Given an agent prompt mentioning "meeting at 09-30"
    And no DES markers are present
    When the enforcement hook evaluates the prompt
    Then the prompt is allowed through
    And no block reason is returned

  @e2e @enforcement @false-positive
  Scenario: Exempt marker overrides enforcement even with step-id-like pattern
    Given an agent prompt mentioning "Review step 04-02 for completeness"
    And the DES-ENFORCEMENT exempt marker is present
    When the enforcement hook evaluates the prompt
    Then the prompt is allowed through
    And no block reason is returned

  # --- TRUE POSITIVES: MUST trigger enforcement (currently GREEN) ---

  @e2e @enforcement @true-positive
  Scenario: Bare step keyword followed by numeric identifier triggers enforcement
    Given an agent prompt mentioning "Execute step 04-02"
    And no DES markers are present
    When the enforcement hook evaluates the prompt
    Then the prompt is blocked
    And the block reason contains "DES_MARKERS_MISSING"

  @e2e @enforcement @true-positive
  Scenario: DES-STEP-ID marker in prompt triggers enforcement
    Given an agent prompt containing a DES-STEP-ID marker with value "04-02"
    And no DES-VALIDATION marker is present
    When the enforcement hook evaluates the prompt
    Then the prompt is blocked
    And the block reason contains "DES_MARKERS_MISSING"

  @e2e @enforcement @true-positive
  Scenario: Step reference in natural language triggers enforcement
    Given an agent prompt mentioning "step 11-01 of the roadmap"
    And no DES markers are present
    When the enforcement hook evaluates the prompt
    Then the prompt is blocked
    And the block reason contains "DES_MARKERS_MISSING"

  @e2e @enforcement @true-positive
  Scenario: Step-id in HTML comment triggers enforcement
    Given an agent prompt mentioning "<!-- step 04-02 -->"
    And no DES markers are present
    When the enforcement hook evaluates the prompt
    Then the prompt is blocked
    And the block reason contains "DES_MARKERS_MISSING"

  @e2e @enforcement @true-positive
  Scenario: Step-id with trailing punctuation triggers enforcement
    Given an agent prompt mentioning "Execute step 04-02."
    And no DES markers are present
    When the enforcement hook evaluates the prompt
    Then the prompt is blocked
    And the block reason contains "DES_MARKERS_MISSING"

  @e2e @enforcement @true-positive
  Scenario: Step-id in quotes triggers enforcement
    Given an agent prompt mentioning '"step 04-02"'
    And no DES markers are present
    When the enforcement hook evaluates the prompt
    Then the prompt is blocked
    And the block reason contains "DES_MARKERS_MISSING"
