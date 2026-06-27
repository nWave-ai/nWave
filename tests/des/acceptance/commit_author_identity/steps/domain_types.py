"""Typed domain vocabulary for the commit-author-identity-validation suite.

SSOT-via-Types-Services-DSL mandate (criterion 1, canonical:
``nw-test-design-mandates``): every domain noun used in the Gherkin of this
feature is expressed here exactly once as a typed concept. Step bodies and the
composition-root services consume these types — never raw string literals
re-spelled per step. A single ``parsers.parse`` decorator over an enum member
NAME then covers the whole literal space (DSL emergence, Mandate-12).

Design source: ``docs/feature/commit-author-identity-validation/plan.md`` (DESIGN
section) + ``docs/analysis/commit-author-validation-research.md`` §2.3 (the
canonical denylist / allowlist / well-formedness behaviour table), §2.4
(pre-commit), §2.5 (pre-push), §3.2 (CI runner).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import NewType


# ---------------------------------------------------------------------------
# Scalar value-objects (NewType — the validator core speaks these, never raw str)
# ---------------------------------------------------------------------------

AuthorEmail = NewType("AuthorEmail", str)
AuthorName = NewType("AuthorName", str)
CommitSha = NewType("CommitSha", str)


# ---------------------------------------------------------------------------
# Identity role — author and committer are validated INDEPENDENTLY (research
# §2.2: ``git commit --author`` / ``git cherry-pick`` produce diverging pairs).
# ---------------------------------------------------------------------------


class IdentityRole(Enum):
    """The two identity slots git records on every commit object."""

    AUTHOR = "author"
    COMMITTER = "committer"


# ---------------------------------------------------------------------------
# Validation verdict — the pure-function driving surface returns this shape:
# ``is_valid_author_email(email) -> (bool, reason)``. ``Verdict`` names the
# boolean half; ``reason`` is free text the validator emits for the operator.
# ---------------------------------------------------------------------------


class Verdict(Enum):
    """Outcome of validating one identity field."""

    ACCEPTED = "accepted"
    REJECTED = "rejected"


@dataclass(frozen=True)
class FieldRuling:
    """The full ``(verdict, reason)`` result for one validated field.

    Mirrors the production tuple ``(bool, str)`` but typed: ``verdict`` is the
    boolean half (Verdict.ACCEPTED iff the tuple's bool is True) and ``reason``
    is the validator's human-readable explanation (e.g. ``"known placeholder"``,
    ``"allowlisted"``, ``"malformed email"``).
    """

    verdict: Verdict
    reason: str


# ---------------------------------------------------------------------------
# Email equivalence classes (C1 partitioning) — research §2.3 behaviour table.
# Each member NAME is what the Gherkin quotes; the parser converter maps the
# NAME back to the member, and the composition root maps the member to its
# representative literal. One typed decorator covers the whole class space.
# ---------------------------------------------------------------------------


class EmailClass(Enum):
    """Equivalence classes of author/committer email, per research §2.3.

    REJECT classes (placeholder / malformed / guessed) and ACCEPT classes
    (allowlisted noreply / real address) partition the input domain. The
    representative literal for each class lives in ``EMAIL_REPRESENTATIVE``.
    """

    # --- REJECT: literal placeholders (denylist literal) ---
    PLACEHOLDER_TEST_EXAMPLE = "placeholder-test-example"  # test@example.com
    PLACEHOLDER_T_AT_T = "placeholder-t-at-t"  # t@t.com

    # --- REJECT: placeholder domains (denylist domain + subdomain) ---
    EXAMPLE_COM = "example-com"  # alice@example.com
    EXAMPLE_ORG = "example-org"  # bob@example.org
    EXAMPLE_NET = "example-net"  # carol@example.net
    TEST_COM = "test-com"  # dev@test.com
    SUBDOMAIN_OF_EXAMPLE = "subdomain-of-example"  # ci@build.example.com

    # --- REJECT: the validator's OWN suggested placeholder domain ---
    # The pre-commit fix-hint (`validate_author_identity.main()`) suggests
    # `you@yourdomain.com` as the value to configure. A contributor who pastes
    # the hint verbatim — instead of replacing it — commits under this shared
    # placeholder identity; if many do, everyone commits as the SAME person. So
    # the whole `yourdomain.com` domain (every local part, every subdomain) must
    # be rejected, forcing people to set a real identity. The literal suggested
    # address is its own representative so the self-consistency guard can pin it.
    PLACEHOLDER_YOURDOMAIN = "placeholder-yourdomain"  # you@yourdomain.com (the hint)
    YOURDOMAIN_ANY_LOCAL = "yourdomain-any-local"  # someone@yourdomain.com
    SUBDOMAIN_OF_YOURDOMAIN = "subdomain-of-yourdomain"  # dev@sub.yourdomain.com

    # --- REJECT: machine-guessed / local hostnames (denylist pattern) ---
    AT_LOCALHOST = "at-localhost"  # root@localhost
    DOT_LOCAL_HOST = "dot-local-host"  # gearoid@Gearoids-MacBook-Pro.local
    # F5: a DOTTED domain so ONLY the `^user@\S+` guessed-host rule can reject
    # it — a non-dotted host (`user@buildbox`) would also trip the malformed
    # well-formedness fallback, masking which rule actually fires. The dotted
    # form isolates the `^user@` rule (adversarial review F5).
    GUESSED_USER_AT_HOST = "guessed-user-at-host"  # user@buildbox.corp.io

    # --- REJECT: malformed / degenerate well-formedness failures ---
    EMPTY = "empty"  # ""
    WHITESPACE_INSIDE = "whitespace-inside"  # "a b@x.io"
    NO_AT_SYMBOL = "no-at-symbol"  # "not-an-email"
    # M3: a placeholder domain with a TRAILING DOT (fully-qualified form). The
    # domain `example.com.` is the same reserved placeholder as `example.com`
    # and must be rejected — the trailing dot must not let it slip past the
    # domain denylist (adversarial review M3).
    TRAILING_DOT_FQDN = "trailing-dot-fqdn"  # foo@example.com.
    # R3-F3: a no-reply-SHAPED address whose LOCAL PART contains a SPACE. The
    # allowlist pattern `^[^@]+@users\.noreply\.github\.com$` runs BEFORE the
    # `\s` well-formedness guard, and `[^@]+` admits whitespace — so today this
    # malformed address is wrongly allowlisted. A real no-reply local part can
    # never contain a space, so this MUST be rejected (adversarial review R3-F3).
    NOREPLY_WHITESPACE_LOCAL = "noreply-whitespace-local"  # "a b@users.noreply…"

    # --- ACCEPT: GitHub noreply allowlist (research §2.3 ALLOWLIST_PATTERNS) ---
    NOREPLY_NUMERIC = "noreply-numeric"  # 12345+name@users.noreply.github.com
    NOREPLY_PLAIN = "noreply-plain"  # name@users.noreply.github.com
    # F4: a no-reply address whose LOCAL PART (`user`) collides with the
    # `^user@` guessed-host denylist pattern AND with the `User`/`user` name
    # denylist. Only the allowlist running FIRST saves it — so this rep is the
    # one that proves allowlist precedence over the denylist (adversarial
    # review F4).
    NOREPLY_COLLISION = "noreply-collision"  # user@users.noreply.github.com

    # --- ACCEPT: a real, deliverable address ---
    REAL_ADDRESS = "real-address"  # gearoid@somerealdomain.ie


#: Representative literal per email equivalence class. The composition root
#: maps the typed class to this concrete value before driving the validator —
#: keeping the literal spelled exactly ONCE in the whole suite (SSOT).
EMAIL_REPRESENTATIVE: dict[EmailClass, str] = {
    EmailClass.PLACEHOLDER_TEST_EXAMPLE: "test@example.com",
    EmailClass.PLACEHOLDER_T_AT_T: "t@t.com",
    EmailClass.EXAMPLE_COM: "alice@example.com",
    EmailClass.EXAMPLE_ORG: "bob@example.org",
    EmailClass.EXAMPLE_NET: "carol@example.net",
    EmailClass.TEST_COM: "dev@test.com",
    EmailClass.SUBDOMAIN_OF_EXAMPLE: "ci@build.example.com",
    EmailClass.PLACEHOLDER_YOURDOMAIN: "you@yourdomain.com",
    EmailClass.YOURDOMAIN_ANY_LOCAL: "someone@yourdomain.com",
    EmailClass.SUBDOMAIN_OF_YOURDOMAIN: "dev@sub.yourdomain.com",
    EmailClass.AT_LOCALHOST: "root@localhost",
    EmailClass.DOT_LOCAL_HOST: "gearoid@Gearoids-MacBook-Pro.local",
    EmailClass.GUESSED_USER_AT_HOST: "user@buildbox.corp.io",
    EmailClass.EMPTY: "",
    EmailClass.WHITESPACE_INSIDE: "a b@example-real.io",
    EmailClass.NO_AT_SYMBOL: "not-an-email",
    EmailClass.TRAILING_DOT_FQDN: "foo@example.com.",
    EmailClass.NOREPLY_NUMERIC: "12345+gearoid@users.noreply.github.com",
    EmailClass.NOREPLY_PLAIN: "gearoid@users.noreply.github.com",
    EmailClass.NOREPLY_COLLISION: "user@users.noreply.github.com",
    EmailClass.NOREPLY_WHITESPACE_LOCAL: "a b@users.noreply.github.com",
    EmailClass.REAL_ADDRESS: "gearoid@somerealdomain.ie",
}

#: The classes the validator MUST reject (research §2.3 denylist + malformed).
REJECTED_EMAIL_CLASSES: frozenset[EmailClass] = frozenset(
    {
        EmailClass.PLACEHOLDER_TEST_EXAMPLE,
        EmailClass.PLACEHOLDER_T_AT_T,
        EmailClass.EXAMPLE_COM,
        EmailClass.EXAMPLE_ORG,
        EmailClass.EXAMPLE_NET,
        EmailClass.TEST_COM,
        EmailClass.SUBDOMAIN_OF_EXAMPLE,
        EmailClass.PLACEHOLDER_YOURDOMAIN,
        EmailClass.YOURDOMAIN_ANY_LOCAL,
        EmailClass.SUBDOMAIN_OF_YOURDOMAIN,
        EmailClass.AT_LOCALHOST,
        EmailClass.DOT_LOCAL_HOST,
        EmailClass.GUESSED_USER_AT_HOST,
        EmailClass.EMPTY,
        EmailClass.WHITESPACE_INSIDE,
        EmailClass.NO_AT_SYMBOL,
        EmailClass.TRAILING_DOT_FQDN,
        EmailClass.NOREPLY_WHITESPACE_LOCAL,
    }
)

#: The classes the validator MUST accept (allowlist + real address).
ACCEPTED_EMAIL_CLASSES: frozenset[EmailClass] = frozenset(
    {
        EmailClass.NOREPLY_NUMERIC,
        EmailClass.NOREPLY_PLAIN,
        EmailClass.NOREPLY_COLLISION,
        EmailClass.REAL_ADDRESS,
    }
)


# ---------------------------------------------------------------------------
# Name equivalence classes (C1) — research §2.3 DENYLIST_NAMES + real name.
# ---------------------------------------------------------------------------


class NameClass(Enum):
    """Equivalence classes of author/committer name, per research §2.3."""

    # --- REJECT: empty / whitespace-only ---
    EMPTY = "empty"  # ""
    WHITESPACE_ONLY = "whitespace-only"  # "   "

    # --- REJECT: known fixture placeholder names ---
    NAME_TEST_CAPITAL = "name-test-capital"  # "Test"
    NAME_T = "name-t"  # "T"
    NAME_TEST_LOWER = "name-test-lower"  # "test"
    NAME_USER = "name-user"  # "User"
    # M4: the SAME fixture placeholders in UPPERCASE. A case-sensitive denylist
    # lets `TEST` and `USER` (and `T`) through; the denylist must be
    # case-insensitive so a shouting placeholder is still recognised
    # (adversarial review M4).
    NAME_TEST_UPPER = "name-test-upper"  # "TEST"
    NAME_USER_UPPER = "name-user-upper"  # "USER"

    # --- ACCEPT: a real human name ---
    REAL_NAME = "real-name"  # "Gearoid O'Treasaigh"


#: Representative literal per name equivalence class (SSOT — spelled once).
NAME_REPRESENTATIVE: dict[NameClass, str] = {
    NameClass.EMPTY: "",
    NameClass.WHITESPACE_ONLY: "   ",
    NameClass.NAME_TEST_CAPITAL: "Test",
    NameClass.NAME_T: "T",
    NameClass.NAME_TEST_LOWER: "test",
    NameClass.NAME_USER: "User",
    NameClass.NAME_TEST_UPPER: "TEST",
    NameClass.NAME_USER_UPPER: "USER",
    NameClass.REAL_NAME: "Gearoid O'Treasaigh",
}

#: Name classes the validator MUST reject (research §2.3 DENYLIST_NAMES).
REJECTED_NAME_CLASSES: frozenset[NameClass] = frozenset(
    {
        NameClass.EMPTY,
        NameClass.WHITESPACE_ONLY,
        NameClass.NAME_TEST_CAPITAL,
        NameClass.NAME_T,
        NameClass.NAME_TEST_LOWER,
        NameClass.NAME_USER,
        NameClass.NAME_TEST_UPPER,
        NameClass.NAME_USER_UPPER,
    }
)

#: Name classes the validator MUST accept.
ACCEPTED_NAME_CLASSES: frozenset[NameClass] = frozenset({NameClass.REAL_NAME})


# ---------------------------------------------------------------------------
# Enforcement-layer gate outcome — the hook / CI driving surfaces return an
# exit code; this names the observable the operator perceives.
# ---------------------------------------------------------------------------


class GateOutcome(Enum):
    """What the operator observes from an enforcement-layer run.

    ``ADMITTED``  — the gate exits 0; the commit / push / range is allowed.
    ``REJECTED``  — the gate exits non-zero; shared history is protected.
    """

    ADMITTED = "admitted"
    REJECTED = "rejected"


# ---------------------------------------------------------------------------
# Push-range shape — the pre-push driving surface distinguishes an existing
# upstream range from a brand-new branch (zero-SHA, research §2.5).
# ---------------------------------------------------------------------------


class PushRangeShape(Enum):
    """Shape of the ref update a pre-push run is asked to validate."""

    EXISTING_UPSTREAM = "existing-upstream"  # remote_sha..local_sha
    NEW_BRANCH_ZERO_SHA = "new-branch-zero-sha"  # 000..0 remote → --not --remotes


# ---------------------------------------------------------------------------
# Bypass posture — whether the offending commit reached the range via the
# normal path or by skipping the local gate (research §2.7 ``--no-verify``).
# ---------------------------------------------------------------------------


class CommitBypass(Enum):
    """How a commit entered the range the push-level / CI gate must inspect."""

    NORMAL = "normal"  # made through the ordinary commit path
    NO_VERIFY = "no-verify"  # local hooks skipped via --no-verify
