# Feature: Commit author/committer identity validation — validator core
# Design source: docs/feature/commit-author-identity-validation/plan.md (DESIGN)
#                docs/analysis/commit-author-validation-research.md §2.3
# Layer: 1/2 (pure validator core, in-memory acceptance — direct driving-port call)
# Tier: A (production composition root; no Tier B — config-shaped, no chained journey)

Feature: The project recognises placeholder and misconfigured commit identities
  As a maintainer protecting shared history
  I want the identity validator to recognise which author and committer
    identities are placeholders, misconfigurations, or legitimate
  So that the same judgement is reused by every enforcement layer

  # ── Walking skeleton ────────────────────────────────────────────────
  # Observable user value end-to-end through the validator driving port:
  # a placeholder is named as such, with a reason the operator can read.

  @walking_skeleton @driving_port @contract-shape:pure-function @core
  Scenario: A well-known placeholder address is recognised as not a real person
    Given the maintainer is reviewing commit identities
    When the validator judges an email of class "PLACEHOLDER_TEST_EXAMPLE"
    Then the email is rejected
    And the rejection names a reason the maintainer can act on

  # ── Rejected email classes (research §2.3 denylist + malformed) ─────
  # Finite, enumerable equivalence classes → Scenario Outline (parametrize),
  # NOT property-based, per the falsifier-gate.

  @driving_port @contract-shape:pure-function @core @error
  Scenario Outline: A placeholder, guessed, or malformed address is rejected
    Given the maintainer is reviewing commit identities
    When the validator judges an email of class "<email_class>"
    Then the email is rejected

    Examples: literal placeholders
      | email_class                |
      | PLACEHOLDER_TEST_EXAMPLE   |
      | PLACEHOLDER_T_AT_T         |

    Examples: placeholder domains
      | email_class                |
      | EXAMPLE_COM                |
      | EXAMPLE_ORG                |
      | EXAMPLE_NET                |
      | TEST_COM                   |
      | SUBDOMAIN_OF_EXAMPLE       |

    Examples: the validator's own suggested placeholder domain (self-contradiction guard)
      | email_class                |
      | PLACEHOLDER_YOURDOMAIN     |
      | YOURDOMAIN_ANY_LOCAL       |
      | SUBDOMAIN_OF_YOURDOMAIN    |

    Examples: machine-guessed and local hostnames
      | email_class                |
      | AT_LOCALHOST               |
      | DOT_LOCAL_HOST             |
      | GUESSED_USER_AT_HOST       |

    Examples: malformed and degenerate
      | email_class                |
      | EMPTY                      |
      | WHITESPACE_INSIDE          |
      | NO_AT_SYMBOL               |

    Examples: fully-qualified placeholder domain (trailing dot — M3)
      | email_class                |
      | TRAILING_DOT_FQDN          |

    Examples: no-reply shape with whitespace in the local part (R3-F3)
      | email_class                |
      | NOREPLY_WHITESPACE_LOCAL   |

  # ── Accepted email classes (allowlist + a real address) ─────────────

  @driving_port @contract-shape:pure-function @core
  Scenario Outline: A GitHub anonymous address or a real address is accepted
    Given the maintainer is reviewing commit identities
    When the validator judges an email of class "<email_class>"
    Then the email is accepted

    Examples:
      | email_class       |
      | NOREPLY_NUMERIC   |
      | NOREPLY_PLAIN     |
      | REAL_ADDRESS      |

  # ── Allowlist precedence — a no-reply address whose local part collides
  #    with a denylist rule is STILL accepted (allowlist runs first, F4) ──
  # `user@users.noreply.github.com` matches the `^user@` guessed-host pattern
  # and `user` is a denylist NAME — only the allowlist running first saves it.

  @driving_port @contract-shape:pure-function @core
  Scenario: A no-reply address whose local part collides with a denylist rule is accepted
    Given the maintainer is reviewing commit identities
    When the validator judges an email of class "NOREPLY_COLLISION"
    Then the email is accepted

  # ── Universal invariant — allowlist always wins (PBT, unbounded) ────
  # The allowlist is an open-ended pattern (any local part, any numeric
  # prefix). "For all noreply-shaped addresses, accept" is an unbounded
  # universal invariant → property-based, not example-based.

  @property @driving_port @contract-shape:pure-function @core
  Scenario: Every GitHub no-reply address is accepted regardless of its local part
    Given the maintainer is reviewing commit identities
    When the validator judges any GitHub no-reply address
    Then the email is always accepted

  # ── Universal invariant — placeholder is rejected for every name (PBT)
  # The denylist literals are rejected no matter what name accompanies
  # them — the email judgement does not depend on the name field.

  @property @driving_port @contract-shape:pure-function @core @error
  Scenario: A placeholder address is rejected whatever name accompanies it
    Given the maintainer is reviewing commit identities
    When the validator judges a placeholder address paired with any name
    Then the email is always rejected

  # ── Rejected name classes (research §2.3 DENYLIST_NAMES) ────────────

  @driving_port @contract-shape:pure-function @core @error
  Scenario Outline: An empty or fixture placeholder name is rejected
    Given the maintainer is reviewing commit identities
    When the validator judges a name of class "<name_class>"
    Then the name is rejected

    Examples:
      | name_class          |
      | EMPTY               |
      | WHITESPACE_ONLY     |
      | NAME_TEST_CAPITAL   |
      | NAME_T              |
      | NAME_TEST_LOWER     |
      | NAME_USER           |

    Examples: same placeholders shouted in uppercase (case-insensitive — M4)
      | name_class          |
      | NAME_TEST_UPPER     |
      | NAME_USER_UPPER     |

  # ── Accepted name class ─────────────────────────────────────────────

  @driving_port @contract-shape:pure-function @core
  Scenario: A real human name is accepted
    Given the maintainer is reviewing commit identities
    When the validator judges a name of class "REAL_NAME"
    Then the name is accepted
