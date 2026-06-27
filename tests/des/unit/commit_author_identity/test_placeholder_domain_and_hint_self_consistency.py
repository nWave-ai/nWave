"""Placeholder-domain denylist + fix-hint self-consistency (layer 1, no I/O).

Why this module exists (the "why"): the pre-commit validator's OWN fix-hint
(``validate_author_identity.main()``) suggests ``you@yourdomain.com`` as the
value a contributor should configure. A contributor who pastes that verbatim —
instead of replacing it with their real address — commits under the placeholder
identity; if many do, everyone commits as the SAME person. So
``you@yourdomain.com`` (and the whole ``yourdomain.com`` domain, including
subdomains) must be REJECTED, which forces people to set a real identity. And a
validator must never RECOMMEND a value it would itself reject — otherwise the
hint is self-contradicting.

Two concerns, pinned here as failing tests that drive the crafter:

  * Denylist additions (EXPECTED-RED today) — the validator currently ACCEPTS
    ``you@yourdomain.com`` / ``someone@yourdomain.com`` / ``dev@sub.yourdomain.com``;
    it must reject them with a sensible reason (known placeholder / placeholder
    domain). The crafter adds ``yourdomain.com`` to the denylist.

  * Hint self-consistency — two guards on the ``Fix:`` line the operator sees:
      1. ``test_fix_hint_does_not_recommend_a_known_placeholder_address``
         (EXPECTED-RED today) — the hint must not hand out any address the suite
         already classifies as a placeholder. RED now because the hint suggests
         ``you@yourdomain.com`` and that address is in the reject-set; goes GREEN
         once the crafter rewrites the hint to a clearly-non-literal placeholder
         (e.g. ``<your-email>``).
      2. ``test_fix_hint_recommends_only_emails_the_validator_itself_accepts``
         (the regression ratchet) — couples the hint to ``is_valid_author_email``
         itself. GREEN today (the validator currently accepts its own
         suggestion); turns RED the instant the crafter adds the ``yourdomain.com``
         denylist WITHOUT rewriting the hint — which is exactly what forces the
         hint rewrite and prevents the contradiction from ever regressing.

Both hint guards are designed so a clearly-non-literal placeholder (no concrete
email, or an angle-bracket form like ``<your-email>``) PASSES, while a concrete
denylisted address FAILS.

Layer 1, example-based (Mandate 9 + 11): pure ``is_valid_author_email`` calls and
a monkeypatched ``main()`` whose ``git var`` resolution is stubbed — no git, no
subprocess, no network.
"""

from __future__ import annotations

import re

from tests.des.acceptance.commit_author_identity.steps.domain_types import (
    EMAIL_REPRESENTATIVE,
    REJECTED_EMAIL_CLASSES,
)


#: Matches a concrete, fully-qualified email (requires ``@`` and a dotted TLD).
#: A clearly-non-literal placeholder such as ``<your-email>`` or ``Your Name``
#: has no ``@``/dotted-domain shape and is therefore NOT extracted — so a hint
#: rewritten to an angle-bracket form recommends "no concrete email" and passes.
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")

#: A placeholder author/committer ident that forces ``main()`` down its rejection
#: branch (so the ``Fix:`` hint is printed). ``Test`` + ``test@example.com`` are
#: both already rejected by the validator core today.
_PLACEHOLDER_IDENT = "Test <test@example.com> 0 +0000"


def _captured_fix_hint_line(capsys, monkeypatch) -> str:
    """Drive the REAL ``main()`` to its rejection path and return its ``Fix:`` line.

    ``get_git_ident`` is stubbed so no ``git``/subprocess runs; ``main()`` then
    judges a placeholder identity, rejects it, and prints the operator-facing
    ``Fix:`` hint to stderr exactly as production would. We read the hint from
    that real output — never by re-spelling the literal here (SSOT: the hint is
    owned by the production module).

    Only the ``Fix:`` line is returned, NOT the whole rejection output: the
    rejection-detail lines echo the injected placeholder identity
    (``test@example.com``), and extracting emails from those would make the
    self-consistency guards fail for the WRONG reason. The contract is about what
    the hint RECOMMENDS, so we isolate the recommendation line.
    """
    import scripts.hooks.validate_author_identity as validator

    monkeypatch.setattr(validator, "get_git_ident", lambda _var: _PLACEHOLDER_IDENT)
    return_code = validator.main()
    assert return_code == 1, "expected main() to reject the placeholder identity"

    fix_lines = [
        line
        for line in capsys.readouterr().err.splitlines()
        if line.lstrip().startswith("Fix:")
    ]
    assert fix_lines, "main() did not emit a 'Fix:' hint line"
    return "\n".join(fix_lines)


# ── EXPECTED-RED: placeholder-domain denylist additions ──────────────────────
# The validator currently ACCEPTS all three (verified: returns (True, 'ok')).
# After the crafter adds `yourdomain.com` to the denylist they must be rejected
# with a sensible reason — "placeholder" covers both "known placeholder: …" (if
# added to the literal denylist) and "placeholder domain: …" (if added to the
# domain denylist), so the assertion does not over-constrain the fix mechanism.


def test_literal_suggested_placeholder_address_is_rejected() -> None:
    """``you@yourdomain.com`` — the literal the fix-hint suggests — is rejected."""
    from scripts.hooks.validate_author_identity import is_valid_author_email

    ok, reason = is_valid_author_email("you@yourdomain.com")
    assert ok is False
    assert "placeholder" in reason.lower()


def test_any_local_part_at_placeholder_domain_is_rejected() -> None:
    """Any local part at ``yourdomain.com`` is rejected (domain denylist)."""
    from scripts.hooks.validate_author_identity import is_valid_author_email

    ok, reason = is_valid_author_email("someone@yourdomain.com")
    assert ok is False
    assert "placeholder" in reason.lower()


def test_subdomain_of_placeholder_domain_is_rejected() -> None:
    """A subdomain of ``yourdomain.com`` is rejected (domain ``endswith`` logic)."""
    from scripts.hooks.validate_author_identity import is_valid_author_email

    ok, reason = is_valid_author_email("dev@sub.yourdomain.com")
    assert ok is False
    assert "placeholder" in reason.lower()


# ── EXPECTED-RED (today): the fix-hint must not recommend a known placeholder ─


def test_fix_hint_does_not_recommend_a_known_placeholder_address(
    capsys, monkeypatch
) -> None:
    """The operator-facing ``Fix:`` hint must not hand out a placeholder address.

    RED today: the hint suggests ``you@yourdomain.com``, which the suite's
    reject-set already contains — a contributor who pastes the hint verbatim
    commits under a shared placeholder identity. Goes GREEN once the crafter
    rewrites the hint to a clearly-non-literal placeholder (e.g. ``<your-email>``)
    that the email regex does not extract.
    """
    hint = _captured_fix_hint_line(capsys, monkeypatch)
    suggested = set(_EMAIL_RE.findall(hint))

    placeholder_addresses = {
        EMAIL_REPRESENTATIVE[cls]
        for cls in REJECTED_EMAIL_CLASSES
        if "@" in EMAIL_REPRESENTATIVE[cls]
    }
    offending = sorted(suggested & placeholder_addresses)

    assert not offending, (
        f"the fix-hint recommends placeholder address(es) {offending} that the "
        f"project rejects; rewrite the hint to a clearly-non-literal placeholder "
        f"like <your-email> so it cannot be pasted verbatim into a real identity"
    )


# ── Regression ratchet: never recommend a value the validator itself rejects ──


def test_fix_hint_recommends_only_emails_the_validator_itself_accepts(
    capsys, monkeypatch
) -> None:
    """A validator must not RECOMMEND a value it would itself REJECT.

    Couples the ``Fix:`` hint to ``is_valid_author_email``. GREEN today (the
    validator currently accepts its own suggestion ``you@yourdomain.com``); turns
    RED the instant the crafter adds the ``yourdomain.com`` denylist without
    rewriting the hint — the ratchet that forces the hint rewrite and stops the
    self-contradiction from regressing. A hint with no concrete email (e.g. the
    angle-bracket ``<your-email>`` form) extracts nothing and passes.
    """
    from scripts.hooks.validate_author_identity import is_valid_author_email

    hint = _captured_fix_hint_line(capsys, monkeypatch)
    suggested = _EMAIL_RE.findall(hint)

    for email in suggested:
        ok, reason = is_valid_author_email(email)
        assert ok is True, (
            f"the fix-hint recommends {email!r} which the validator itself "
            f"rejects ({reason}); rewrite the hint to a non-literal placeholder "
            f"(e.g. <your-email>) so the advice it gives is one it would accept"
        )


# ── EXPECTED-PASS: no over-rejection (regression guard) ──────────────────────
# Adding the `yourdomain.com` denylist must not start rejecting genuine
# addresses. A real deliverable domain and a GitHub no-reply both stay accepted.


def test_genuine_real_domain_email_is_still_accepted() -> None:
    """A real, deliverable address at a non-placeholder domain stays accepted."""
    from scripts.hooks.validate_author_identity import is_valid_author_email

    ok, _reason = is_valid_author_email("gearoid@some-real-domain.ie")
    assert ok is True


def test_github_noreply_is_still_accepted() -> None:
    """A GitHub no-reply address (legitimate anonymous identity) stays accepted."""
    from scripts.hooks.validate_author_identity import is_valid_author_email

    ok, _reason = is_valid_author_email("12345+gearoid@users.noreply.github.com")
    assert ok is True
