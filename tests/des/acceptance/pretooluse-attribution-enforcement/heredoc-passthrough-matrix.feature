Feature: A heredoc commit the rewrite cannot prove safe runs unchanged
  As a maintainer of an nWave project
  I want the attribution hook to decline any heredoc or substitution shape it
  cannot delimit with certainty
  So that the never-corrupt contract holds: a missed trailer is recoverable, a
  trailer appended after a chained command is a corrupted commit

  Coverage of heredoc commits stops exactly where corruption risk begins. An
  operator AFTER the substitution would need the trailer to land past a later
  command — deferred until the heredoc-extent scanner can locate it safely. A
  message read from a file, a backtick substitution, and any heredoc the scanner
  cannot bound (unterminated, stacked, here-string, tab-indented, unbalanced) all
  decline. The original command runs unchanged, with a recorded reason.

  # ---------------------------------------------------------------------------
  # The heredoc passthrough matrix — pure rewrite core (Layer 3, in-memory)
  # ---------------------------------------------------------------------------

  @driving_port @in-memory @contract-shape:unbounded-preservation
  Scenario Outline: A heredoc shape outside the safe boundary runs unchanged
    Given the rewrite core receives <command_shape>
    When the rewrite core plans the attribution
    Then the command runs unchanged
    And a declining reason is recorded

    Examples: operator-after-substitution — deferred scope boundary (DDD-5)
      | command_shape                                       |
      | a heredoc git commit followed by another command    |

    Examples: message off the command line (DDD-6)
      | command_shape                                       |
      | a git commit reading a heredoc message from a file  |

    Examples: substitution the depth counter declines (DDD-1)
      | command_shape                                       |
      | a git commit whose message embeds a backtick substitution |

    Examples: heredoc shapes the scanner cannot bound (DDD-2 decline)
      | command_shape                                       |
      | a git commit with an unterminated heredoc           |
      | a git commit with an unbalanced command substitution |
      | a git commit with two stacked heredocs              |
      | a git commit whose message is a here-string         |
      | a git commit with a tab-indented heredoc            |
