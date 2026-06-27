Feature: A Claude-driven git commit carries the dual co-author trailer
  As a maintainer of an nWave project
  I want every commit Claude runs to credit both Claude and nWave
  So that contribution history is accurate without relying on the model
  remembering to compose the trailer

  The PreToolUse hook rewrites the git commit command before git runs, injecting
  the dual Co-Authored-By trailer deterministically. The walking skeleton proves
  the end-to-end seam through the real hook adapter: a standalone commit goes in,
  a rewritten command carrying the dual trailer comes out.

  # ---------------------------------------------------------------------------
  # Walking skeleton — real hook adapter, end-to-end (Layer 4 wiring_e2e)
  # ---------------------------------------------------------------------------

  @walking_skeleton @driving_port @real-io @contract-shape:bounded-change
  Scenario: A standalone commit Claude runs is rewritten to credit Claude and nWave
    Given Claude is about to run a standalone git commit with a message
    When the attribution hook processes the commit
    Then the hook rewrites the command to carry the dual trailer
    And the rewritten command credits Claude and nWave exactly once

  @real-io @contract-shape:bounded-change
  Scenario: The hook leaves a non-commit Bash command untouched
    Given Claude is about to run a Bash command that is not a git commit
    When the attribution hook processes the commit
    Then the agent's command runs unchanged
    And the hook produces no output
