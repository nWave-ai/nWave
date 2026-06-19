# US-1 / US-3 — the smoke harness orchestrates one lane and reports a verdict
# that BLOCKS promotion on any failure. The defect this feature fixes: a failing
# step must NEVER report a pass (the codex false-PASS + "red annotations / green
# pipeline" regression class, SPIKE findings).
#
# Layer 2 in-memory acceptance: the harness (driving port) is driven through
# in-memory fakes for the install / boot / filesystem driven ports. The REAL
# cross-OS install runs ONLY in the validate-rc-multitool CI gate.

@feature-rc-cross-os-multitool-validation @us-1 @us-3
Feature: The RC smoke harness reports a trustworthy pass or fail per tool lane

  As a release engineer promoting a release candidate
  I want each tool lane to pass only when install, provisioning, boot, and real
  artifacts all succeed
  So that a platform regression blocks promotion instead of reaching users

  @walking_skeleton @driving_port @in-memory @contract-shape:bounded-change
  Scenario: A clean lane installs, provisions, boots, and confirms artifacts
    Given a published release candidate and an isolated install target
    And the tool installs, provisions, boots, and writes its nWave artifacts
    When the release engineer runs the smoke lane
    Then the lane passes
    And the harness reports success to the release pipeline

  @driving_port @in-memory @error @contract-shape:bounded-change
  Scenario: A lane whose install aborts is reported as a failure
    Given a published release candidate and an isolated install target
    And installing the published package aborts
    When the release engineer runs the smoke lane
    Then the lane fails
    And the harness reports failure to the release pipeline
    And the failure names the install step in a readable diagnostic

  @driving_port @in-memory @error @contract-shape:bounded-change
  Scenario: A lane whose tool fails to boot is reported as a failure
    Given a published release candidate and an isolated install target
    And the tool is installed and provisioned but fails to boot
    When the release engineer runs the smoke lane
    Then the lane fails
    And the harness reports failure to the release pipeline

  @driving_port @in-memory @error @contract-shape:unbounded-preservation
  Scenario: A lane that provisions no real artifacts is reported as a failure
    Given a published release candidate and an isolated install target
    And the tool boots but provisioned no real nWave artifacts
    When the release engineer runs the smoke lane
    Then the lane fails
    And the failure names the missing artifacts in a readable diagnostic

  @driving_port @in-memory @error @contract-shape:bounded-change
  Scenario: A bare directory without real artifacts does not count as provisioned
    Given a published release candidate and an isolated install target
    And the tool boots and only a bare config directory exists
    When the release engineer runs the smoke lane
    Then the lane fails

  @driving_port @in-memory @contract-shape:bounded-change
  Scenario: Running the same clean lane twice yields the same pass verdict
    Given a published release candidate and an isolated install target
    And the tool installs, provisions, boots, and writes its nWave artifacts
    When the release engineer runs the smoke lane twice
    Then both runs pass with the same verdict

  @driving_port @in-memory @contract-shape:unbounded-preservation
  Scenario: The harness always provisions into the isolated target, never the real tree
    Given a published release candidate and an isolated install target
    And the tool installs, provisions, boots, and writes its nWave artifacts
    When the release engineer runs the smoke lane
    Then the lane passes
    And every install and artifact check used the isolated target only
