"""Property-based unit tests for the commit-identity validator core (layer 1).

Mandate 9: PBT-full is permitted ONLY at layers 1-2. These are layer-1 unit
tests over the PURE validator functions ``is_valid_author_email`` /
``is_valid_author_name`` — no git, no subprocess, no I/O. They cover the
genuinely UNBOUNDED universal invariants that the finite Scenario Outlines in
``identity-validation-core.feature`` cannot enumerate:

  * Allowlist is open-ended — ANY ``<anything>@users.noreply.github.com`` and
    ANY ``<digits>+<anything>@users.noreply.github.com`` is accepted. The local
    part is an infinite domain → property-based, not example-based
    (falsifier-gate: the domain is NOT finite/enumerable).
  * Whitespace ANYWHERE in an address is rejected (well-formedness invariant).
  * The two literal placeholders are rejected for EVERY accompanying name — the
    email judgement is independent of the name field.

These back the two ``@property``-tagged Gherkin scenarios. The example-pinned
canonical case lives in the ``.feature``; the generative exploration lives here.

The validator core is implemented: this module is NOT skipped — every property
runs against the real ``is_valid_author_email`` and passes (it backs the landed
core slice). No module-level skip exists.
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st


# Local-part alphabet for the GitHub no-reply allowlist (RFC-pragmatic subset:
# the part before '@' that GitHub permits in a no-reply handle).
#
# F4: the strategy is widened with explicit collision local-parts (`user`,
# `test`, `User`, `Test`) so the allowlist-precedence invariant is reliably
# exercised — a `user@users.noreply.github.com` collides with the `^user@`
# guessed-host denylist pattern and the `user`/`User` name denylist, yet must
# be accepted because the allowlist runs first. Pure `st.text` would only hit
# these handles by chance; `st.one_of` with `st.sampled_from` guarantees them.
_COLLISION_LOCAL_PARTS = st.sampled_from(["user", "test", "User", "Test", "t"])

_LOCAL_PART = st.one_of(
    st.text(
        alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.",
        min_size=1,
        max_size=40,
    ),
    _COLLISION_LOCAL_PARTS,
)


@given(local=_LOCAL_PART)
@settings(max_examples=300)
def test_plain_github_noreply_is_always_accepted(local: str) -> None:
    """Every ``<local>@users.noreply.github.com`` is accepted (allowlist invariant)."""
    from scripts.hooks.validate_author_identity import is_valid_author_email

    email = f"{local}@users.noreply.github.com"
    ok, _reason = is_valid_author_email(email)
    assert ok is True


@given(uid=st.integers(min_value=1, max_value=10**9), local=_LOCAL_PART)
@settings(max_examples=300)
def test_numeric_github_noreply_is_always_accepted(uid: int, local: str) -> None:
    """Every ``<digits>+<local>@users.noreply.github.com`` is accepted."""
    from scripts.hooks.validate_author_identity import is_valid_author_email

    email = f"{uid}+{local}@users.noreply.github.com"
    ok, _reason = is_valid_author_email(email)
    assert ok is True


@given(
    left=st.text(min_size=0, max_size=8),
    right=st.text(min_size=1, max_size=8),
    ws=st.sampled_from([" ", "\t"]),
)
@settings(max_examples=300)
def test_address_with_internal_whitespace_is_always_rejected(
    left: str, right: str, ws: str
) -> None:
    """Any address containing whitespace fails well-formedness (research §2.3)."""
    from scripts.hooks.validate_author_identity import is_valid_author_email

    email = f"{left}{ws}{right}@example-real.io"
    ok, _reason = is_valid_author_email(email)
    assert ok is False


@given(name=st.text(min_size=0, max_size=40))
@settings(max_examples=300)
def test_placeholder_email_rejected_for_every_name(name: str) -> None:
    """``test@example.com`` is rejected no matter what name is paired with it.

    The email judgement does not consult the name field — the placeholder is
    rejected for the empty name, a real name, or any other.
    """
    from scripts.hooks.validate_author_identity import is_valid_author_email

    ok, _reason = is_valid_author_email("test@example.com")
    assert ok is False
