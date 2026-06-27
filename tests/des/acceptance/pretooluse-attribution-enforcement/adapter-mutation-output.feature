Feature: The attribution hook emits a well-formed rewrite instruction
  As Claude Code dispatching the PreToolUse hook
  I want the attribution hook to return a complete, allow-paired rewrite
  So that the rewritten git commit runs with every original field preserved and
  no permission prompt

  When the hook decides to rewrite a commit, it must return an allow decision
  paired with the full original command input — the rewritten command plus every
  other field the agent supplied. A partial or unpaired instruction would drop
  fields or trigger a permission prompt.

  # ---------------------------------------------------------------------------
  # Adapter mutation contract — real hook adapter (Layer 4 wiring_e2e)
  # ---------------------------------------------------------------------------

  @real-io @contract-shape:bounded-change
  Scenario: The rewrite instruction pairs allow with the full original input
    Given Claude is about to run a standalone git commit with a message
    When the attribution hook processes the commit
    Then the hook rewrites the command to carry the dual trailer
    And the rewrite is granted without a permission prompt
    And every field the agent supplied is preserved in the rewrite

  @real-io @contract-shape:bounded-change
  Scenario: A passed-through command produces no rewrite instruction
    Given Claude is about to run a Bash command that is not a git commit
    When the attribution hook processes the commit
    Then the agent's command runs unchanged
    And the hook produces no output
