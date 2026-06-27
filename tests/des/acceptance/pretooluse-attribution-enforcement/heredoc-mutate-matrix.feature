Feature: A heredoc or command-substitution commit lands the dual trailer
  As a maintainer of an nWave project
  I want the commit the agent composes as a heredoc inside a command substitution
  to carry the dual trailer, in every common shape the agent emits
  So that attribution is deterministic and model-independent — not silently
  delegated to whatever the model happened to write inside the message

  Claude Code composes every non-trivial commit as
  `git commit -m "$(cat <<'EOF' … EOF)"` — and frequently as
  `git add . && git commit -m "$(cat <<'EOF' … EOF)"`. The rewrite core declined
  both, so the deterministic trailer silently degraded to model-composed
  attribution. This feature restores determinism on those dominant shapes: the
  rewrite delimits the true top level (a command-substitution depth counter paired
  with a heredoc-body-skip), then appends a second `-m` carrying the dual trailer
  OUTSIDE the substitution. The heredoc body is never parsed.

  # ---------------------------------------------------------------------------
  # The heredoc mutate matrix — pure rewrite core (Layer 3 composition, in-memory)
  # ---------------------------------------------------------------------------

  @driving_port @in-memory @contract-shape:pure-function
  Scenario Outline: A heredoc or command-substitution commit is attributed
    Given the rewrite core receives <command_shape>
    When the rewrite core plans the attribution
    Then the dual trailer is injected
    And the planned message credits Claude and nWave exactly once
    And the original command is preserved as a prefix of the rewrite
    And the trailer is the last argument of the rewritten commit
    And the rewritten command is syntactically valid bash

    Examples: standalone — the dominant Claude Code shape
      | command_shape                                                  |
      | a standalone git commit whose message is a heredoc             |
      | a standalone git commit whose message is a command substitution |

    Examples: operator-before-chained — the other common Claude Code shape
      | command_shape                                                       |
      | a staged-then-commit chain whose message is a heredoc               |
      | a change-directory-then-commit chain whose message is a heredoc     |
      | an environment-prefixed git commit whose message is a heredoc       |

  # ---------------------------------------------------------------------------
  # The body-parenthesis correctness pin — the BLOCKING-bug regressions.
  # A bare `)` in the heredoc body must NOT mis-close the substitution. The
  # three placement assertions (prefix preserved, trailer is the last argument,
  # valid bash) prove a CORRECT mutate — not merely a non-crash. A rewrite that
  # mis-split the command would still be non-empty and could even parse, but it
  # would FAIL the prefix and last-argument assertions.
  # ---------------------------------------------------------------------------

  @driving_port @in-memory @contract-shape:bounded-change
  Scenario: A standalone heredoc whose body has a parenthesis is attributed correctly
    Given the rewrite core receives a standalone heredoc git commit whose body contains a parenthesis
    When the rewrite core plans the attribution
    Then the dual trailer is injected
    And the original command is preserved as a prefix of the rewrite
    And the trailer is the last argument of the rewritten commit
    And the rewritten command is syntactically valid bash
    And the planned message credits Claude and nWave exactly once

  @driving_port @in-memory @contract-shape:bounded-change
  Scenario: A staged-then-commit heredoc whose body has a parenthesis is attributed correctly
    Given the rewrite core receives a staged-then-commit heredoc chain whose body contains a parenthesis
    When the rewrite core plans the attribution
    Then the dual trailer is injected
    And the original command is preserved as a prefix of the rewrite
    And the trailer is the last argument of the rewritten commit
    And the rewritten command is syntactically valid bash
    And the planned message credits Claude and nWave exactly once

  # ---------------------------------------------------------------------------
  # Chained-narrative idempotency (Pillar 2) — re-applying the rewrite to its own
  # heredoc output never doubles the trailer.
  # ---------------------------------------------------------------------------

  @property @in-memory @contract-shape:pure-function
  Scenario: Re-applying the rewrite to a heredoc commit never doubles the trailer
    Given the rewrite core receives a standalone git commit whose message is a heredoc
    When the rewrite core plans the attribution
    And the rewrite core plans the attribution of the already-rewritten command
    Then the command runs unchanged
    And the planned message credits Claude and nWave exactly once
