Feature: An unsafe or non-message commit runs unchanged
  As a maintainer of an nWave project
  I want the attribution hook to decline any command it cannot rewrite safely
  So that a missed trailer is the worst outcome — never a corrupted commit and
  never a changed commit message

  A missed trailer is recoverable; a corrupted multi-command commit is not. So
  on any doubt — an embedded command substitution, an unbalanced quote, two
  commits in one chain — and on any commit whose message is not on the command
  line — the rewrite declines and the original command runs unchanged.

  # ---------------------------------------------------------------------------
  # The passthrough matrix — pure rewrite core (Layer 3 composition, in-memory)
  # ---------------------------------------------------------------------------

  @driving_port @in-memory @contract-shape:pure-function
  Scenario Outline: An unsafe or ambiguous command runs unchanged
    Given the rewrite core receives <command_shape>
    When the rewrite core plans the attribution
    Then the command runs unchanged
    And a declining reason is recorded

    Examples: ambiguous or unsafe shell shapes (fail-safe)
      | command_shape                                              |
      | a git commit whose message embeds a command substitution   |
      | a git commit with an unbalanced quote                      |
      | a chain with two separate git commits                      |

    Examples: non-message-creating commits (scope punt)
      | command_shape                                              |
      | a git commit reusing an existing message                   |
      | a git commit amending without editing the message          |
      | a git commit reading its message from a file               |
      | a bare git commit that opens the editor                    |

    Examples: not a commit at all
      | command_shape                                              |
      | a Bash command that is not a git commit                    |

    Examples: short-flag commits with no command-line message (scope punt)
      | command_shape                                                       |
      | a combined-short-flag git commit reading its message from a file    |
      | a combined-short-flag git commit with no message value              |

  @in-memory @contract-shape:pure-function
  Scenario: An already-attributed command is left untouched
    Given the rewrite core receives a git commit already carrying the nWave co-author
    When the rewrite core plans the attribution
    Then the command runs unchanged
    And a declining reason is recorded
