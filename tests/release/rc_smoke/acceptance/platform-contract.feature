# US-5 — the matrix entry point is `nwave-ai install --platform TOOL`. Pin the
# passthrough so a future refactor cannot silently break the gate, and document
# the flag in the CLI usage text.
#
# Layer 4 (real CLI usage text + passthrough): example-based, no PBT machinery
# (Mandate 9 / 11). Driven through the published console script's arg-handling.

@feature-rc-cross-os-multitool-validation @us-5
Feature: The install platform selector is a supported, documented contract

  As a release engineer
  I want `--platform` documented and its passthrough pinned by a test
  So that the smoke matrix entry point cannot silently break

  @driving_port @real-io @contract-shape:unbounded-preservation
  Scenario: The installer usage text documents the platform selector
    Given the published installer usage text
    When the release engineer reads the install command help
    Then the platform selector is documented

  @driving_port @real-io @contract-shape:bounded-change
  Scenario Outline: The chosen platform reaches the installer unchanged
    Given the release engineer chooses platform "<tool>"
    When the install command forwards its arguments
    Then the installer receives platform "<tool>" unchanged

    Examples:
      | tool        |
      | claude-code |
      | codex       |
      | opencode    |
