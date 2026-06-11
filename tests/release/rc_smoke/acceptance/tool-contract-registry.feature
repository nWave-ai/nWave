# US-2 — the matrix is data, not branching (DESIGN D-2). Each supported tool is
# one ToolContract row carrying its install package, boot command, isolation env
# var, and required real-artifact globs. Adding a tool is adding a row.
#
# Layer 2 in-memory acceptance: the same SmokeRunner orchestration runs over
# each tool's contract; the per-tool difference is pure data.

@feature-rc-cross-os-multitool-validation @us-2
Feature: Each supported tool is smoked through its own contract

  As a release engineer
  I want every supported tool described by a single contract row
  So that adding or changing a tool is a data change, not a new code path

  @driving_port @in-memory @contract-shape:bounded-change
  Scenario Outline: A clean lane passes for each supported tool
    Given a published release candidate and an isolated install target
    And the supported tool "<tool>" installs, provisions, boots, and writes its artifacts
    When the release engineer runs the smoke lane for "<tool>"
    Then the lane passes

    Examples:
      | tool        |
      | claude-code |
      | codex       |
      | opencode    |

  @driving_port @in-memory @error @contract-shape:bounded-change
  Scenario Outline: A boot failure fails the lane for each supported tool
    Given a published release candidate and an isolated install target
    And the supported tool "<tool>" is installed and provisioned but fails to boot
    When the release engineer runs the smoke lane for "<tool>"
    Then the lane fails

    Examples:
      | tool        |
      | claude-code |
      | codex       |
      | opencode    |

  @driving_port @in-memory @error @contract-shape:unbounded-preservation
  Scenario Outline: Missing real artifacts fail the lane for each supported tool
    Given a published release candidate and an isolated install target
    And the supported tool "<tool>" boots but provisioned no real artifacts
    When the release engineer runs the smoke lane for "<tool>"
    Then the lane fails
    And the failure names the missing artifacts in a readable diagnostic

    Examples:
      | tool        |
      | claude-code |
      | codex       |
      | opencode    |

  @driving_port @in-memory @error @contract-shape:bounded-change
  Scenario: An unsupported tool has no contract and is rejected loudly
    Given the smoke harness contract registry
    When the release engineer requests a lane for an unsupported tool "copilot"
    Then the request is rejected with a readable unsupported-tool diagnostic
