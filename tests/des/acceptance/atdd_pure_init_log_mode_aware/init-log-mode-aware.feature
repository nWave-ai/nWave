Feature: des-init-log respects the project's workflow mode
  As an nWave operator delivering a feature
  I want des-init-log to refuse creating an execution log for ATDD-pure features
  So that the roadmap-free, execution-log-free spine (ADR-028) is honoured
  And classic features keep their execution log exactly as before

  # ADR-028 D4.1 / slice 1 of 6. Regression ATs: FAIL on master
  # (des-init-log has no mode-awareness), PASS once slice 1 lands.
  #
  # SUT workflow-mode state model (C2):
  #   workflow mode is resolved from .nwave/config.yaml key `workflow.mode`.
  #   States: {atdd_pure} -> refuse ; {classic, unset, no-config-file} -> create.
  #   The only legal transition slice 1 introduces is the atdd_pure -> refuse
  #   early exit. No other state machine.
  #
  # Driving port: the des-init-log CLI, invoked via its argv entry point.
  # Layer 3 (subprocess/FS acceptance) -> example-only, no PBT (Mandate 9/11).

  @walking_skeleton @driving_port @contract-shape:unbounded-preservation
  Scenario: An ATDD-pure feature has its execution-log creation refused
    Given a deliver project directory for feature "atdd-pure-demo"
    And the project workflow mode is "atdd_pure"
    When the operator runs des-init-log for that feature
    Then des-init-log refuses with a non-zero exit code
    And the refusal message explains ATDD-pure is execution-log-free
    And no execution log is created in the project directory

  @driving_port @contract-shape:bounded-change
  Scenario Outline: des-init-log creates the execution log when the feature is not ATDD-pure
    Given a deliver project directory for feature "classic-demo"
    And the project workflow mode is "<workflow_mode>"
    When the operator runs des-init-log for that feature
    Then des-init-log succeeds with a zero exit code
    And an execution log is created for feature "classic-demo"

    Examples:
      | workflow_mode |
      | classic       |
      | unset         |
