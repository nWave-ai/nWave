Feature: des-verify-integrity respects the project's workflow mode
  As an nWave operator finalising a feature
  I want des-verify-integrity to verify the AT-completion ledger for ATDD-pure features
  So that a roadmap-free feature gets a correct integrity verdict
  And classic features keep their existing 0/1/2 exit-code contract unchanged

  # ADR-028 D4.2 / slice-02 of the atdd-pure-roadmap-free-rollout.
  # Regression ATs: FAIL on master (des-verify-integrity has no mode-awareness
  # -- it exits 2 the instant roadmap.json is absent, before any mode check),
  # PASS once slice-02 lands.
  #
  # D4.2 has FOUR contract limbs, one scenario group each:
  #   1. atdd_pure + complete ledger (roadmap absent or leftover) -> verified
  #   2. atdd_pure + absent ledger   -> structured diagnostic, exit 1, no crash
  #   3. atdd_pure + --roadmap-only  -> the flag is a no-op, same verified verdict
  #   4. classic / unset             -> the existing 0/1/2 contract, zero regression
  #
  # SUT workflow-mode state model (C2):
  #   workflow mode is resolved from {project_dir}/.nwave/config.yaml key
  #   `workflow.mode` -- the SAME path slice-01's des-init-log uses.
  #   States: {atdd_pure} -> validate the AT-completion ledger ;
  #           {classic, unset, no-config-file} -> the existing roadmap.json +
  #           execution-log.json cross-reference, byte-for-byte unchanged.
  #
  # Driving port: the des-verify-integrity CLI, invoked via its argv entry
  # point. Layer 3 (subprocess/FS acceptance) -> example-only, no PBT
  # (Mandate 9/11). The verifier has a pure-read contract: the one
  # state-observing step asserts via assert_state_delta that NO project file
  # is mutated (Mandate 8).

  @walking_skeleton @driving_port @contract-shape:bounded-change
  Scenario Outline: An ATDD-pure feature with a complete ledger is verified regardless of any leftover roadmap
    Given a deliver project directory for feature "atdd-pure-demo"
    And the project workflow mode is "atdd_pure"
    And the AT-completion ledger is present with every slice shipped
    And a leftover roadmap is "<leftover_roadmap>" in the project directory
    When the operator runs des-verify-integrity for that feature
    Then des-verify-integrity reports the feature verified
    And the leftover roadmap is treated as "<roadmap_treatment>"

    Examples:
      | leftover_roadmap | roadmap_treatment            |
      | absent           | not required and not created |
      | present          | reported as a warning        |

  @driving_port @contract-shape:bounded-change
  Scenario: An ATDD-pure feature with no AT-completion ledger gets a structured diagnostic, not a crash
    Given a deliver project directory for feature "atdd-pure-demo"
    And the project workflow mode is "atdd_pure"
    And the AT-completion ledger is absent
    When the operator runs des-verify-integrity for that feature
    Then des-verify-integrity reports an integrity violation
    And the diagnostic message names the missing AT-completion ledger
    And des-verify-integrity does not crash

  @driving_port @contract-shape:bounded-change
  Scenario: An ATDD-pure feature verified with --roadmap-only treats the flag as a no-op
    Given a deliver project directory for feature "atdd-pure-demo"
    And the project workflow mode is "atdd_pure"
    And the AT-completion ledger is present with every slice shipped
    When the operator runs des-verify-integrity with --roadmap-only for that feature
    Then des-verify-integrity reports the feature verified
    And des-verify-integrity does not fail for a missing roadmap

  @driving_port @contract-shape:bounded-change
  Scenario Outline: A classic feature keeps the existing integrity verdict, with zero regression
    Given a deliver project directory for feature "classic-demo"
    And the project workflow mode is "<workflow_mode>"
    And a classic deliver project with "<trace_completeness>"
    When the operator runs des-verify-integrity for that feature
    Then des-verify-integrity reports "<expected_verdict>"

    Examples: classic mode -- the existing 0/1 contract
      | workflow_mode | trace_completeness | expected_verdict       |
      | classic       | complete traces    | the feature verified   |
      | classic       | incomplete traces  | an integrity violation |

    Examples: unset mode is treated as classic -- no-regression default
      | workflow_mode | trace_completeness | expected_verdict     |
      | unset         | complete traces    | the feature verified |
