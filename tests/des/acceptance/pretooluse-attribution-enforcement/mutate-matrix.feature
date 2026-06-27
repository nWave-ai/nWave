Feature: Every message-creating git commit lands the dual co-author trailer
  As a maintainer of an nWave project
  I want commits the agent runs in every common shape — standalone and chained —
  to carry the dual trailer
  So that attribution is not lost just because the agent staged-and-committed in
  one line

  Agents commit through and chains constantly. The rewrite must find the
  message-creating git commit wherever it sits in a flat chain, inject the dual
  trailer into that commit only, and leave the rest of the chain byte-identical.

  # ---------------------------------------------------------------------------
  # The mutate matrix — pure rewrite core (Layer 3 composition, in-memory)
  # ---------------------------------------------------------------------------

  @driving_port @in-memory @contract-shape:pure-function
  Scenario Outline: The dual trailer is injected for a message-creating commit
    Given the rewrite core receives <command_shape>
    When the rewrite core plans the attribution
    Then the dual trailer is injected
    And the planned message credits Claude and nWave exactly once

    Examples: standalone and git-flag variants
      | command_shape                                          |
      | a standalone git commit with a message                 |
      | a git commit skipping verification with a message      |

    Examples: flat compound chains
      | command_shape                                          |
      | a staged-then-commit chain                             |
      | a change-directory-then-commit chain                   |
      | an environment-prefixed git commit with a message      |
      | a git commit with a best-effort fallback               |
      | a status-then-commit chain                             |

    Examples: POSIX combined and attached short flags
      | command_shape                                                      |
      | a stage-all-and-message git commit with combined short flags       |
      | a sign-off-and-message git commit with combined short flags        |
      | a git commit with an attached short message value                  |
      | a git commit with combined short flags and an attached value       |
      | a combined-short-flag git commit whose message looks like a flag   |

  @in-memory @contract-shape:pure-function
  Scenario: The rewrite touches only the commit segment of a chain
    Given the rewrite core receives a staged-then-commit chain
    When the rewrite core plans the attribution
    Then the dual trailer is injected
    And removing the injected trailer restores the original command exactly

  @property @in-memory @contract-shape:pure-function
  Scenario: Re-applying the rewrite never doubles the trailer
    Given the rewrite core receives a standalone git commit with a message
    When the rewrite core plans the attribution
    And the rewrite core plans the attribution of the already-rewritten command
    Then the command runs unchanged
    And the planned message credits Claude and nWave exactly once
