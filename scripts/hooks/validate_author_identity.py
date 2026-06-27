"""pre-commit hook: validate git author and committer identity.

Shared validator core + pre-commit entry for the
``commit-author-identity-validation`` feature. Rejects known placeholder emails
(``test@example.com``, ``t@t.com``, etc.), placeholder domains, machine-guessed
local hostnames, and malformed identities before they enter shared history —
while allowing legitimate anonymous ``*@users.noreply.github.com`` addresses.

Public surface (reused by ``validate_push_identity`` and ``ci_author_check``):
  * ``is_valid_author_email(email) -> tuple[bool, str]``  — (is_valid, reason)
  * ``is_valid_author_name(name) -> tuple[bool, str]``    — (is_valid, reason)
  * ``main() -> int``  — pre-commit entry: reads ``git var GIT_AUTHOR_IDENT`` +
    ``GIT_COMMITTER_IDENT``, validates both independently, returns non-zero on
    rejection.

Design source: ``docs/analysis/commit-author-validation-research.md`` §2.3
(denylist / allowlist / well-formedness) and §2.4 (pre-commit entry).
"""

from __future__ import annotations

import re
import subprocess
import sys


# Known placeholder domains and test fixture addresses (research §2.3).
DENYLIST_DOMAINS = frozenset(
    {
        "example.com",  # RFC 2606 reserved; no real person uses this
        "example.org",
        "example.net",
        "test.com",  # common test domain
        "localhost",  # machine-local; cannot be real
        "invalid",  # RFC 2606 reserved TLD
        # `yourdomain.com` is the placeholder the fix-hint used to suggest. Reject
        # the whole domain (every local part, every subdomain, via the endswith
        # logic) so a contributor who pastes the hint verbatim is forced to set a
        # real identity — otherwise everyone commits as the same placeholder.
        "yourdomain.com",
    }
)

# Literal denylist for known fixture/harness identities.
DENYLIST_LITERAL = frozenset(
    {
        "test@example.com",
        "t@t.com",
        "you@yourdomain.com",  # the placeholder the fix-hint used to suggest
        "",  # empty email
    }
)

# Denylist patterns (regex applied to the full email string).
DENYLIST_PATTERNS = [
    re.compile(r"^$"),  # empty
    re.compile(r"\s"),  # contains whitespace
    re.compile(r"@localhost$"),  # hostname-guessed local
    re.compile(r"@.*\.local$", re.IGNORECASE),  # macOS/mDNS hostnames
    re.compile(r"^user@\S+"),  # git's guessed "user@hostname"
]

# Allowlist — GitHub no-reply addresses are legitimate anonymous identities.
# R3-F3: the local part forbids whitespace (``[^@\s]+``). A real GitHub no-reply
# handle can never contain a space, and the allowlist runs BEFORE the ``\s``
# well-formedness guard — so a no-reply-SHAPED address with a space in the local
# part (``a b@users.noreply.github.com``) must NOT be allowlisted; it falls
# through to the whitespace rejection like any other malformed address.
ALLOWLIST_PATTERNS = [
    re.compile(r"^\d+\+[^@\s]+@users\.noreply\.github\.com$"),  # GitHub noreply (id)
    re.compile(r"^[^@\s]+@users\.noreply\.github\.com$"),  # GitHub noreply (non-id)
]

# Known fixture/placeholder names (research §2.3 DENYLIST_NAMES). Compared
# case-insensitively (M4): a shouting placeholder (`TEST`, `USER`) is still a
# placeholder, so the lowered name is matched against this lowered set.
DENYLIST_NAMES = frozenset({"test", "t", "user"})


def is_valid_author_email(email: str) -> tuple[bool, str]:
    """Return ``(is_valid, reason)`` for an author/committer email.

    Check order: allowlist -> literal denylist -> domain denylist -> pattern
    denylist -> well-formedness (research §2.3).
    """
    for pattern in ALLOWLIST_PATTERNS:
        if pattern.match(email):
            return True, "allowlisted"

    if email in DENYLIST_LITERAL:
        return False, f"known placeholder: {email!r}"

    if "@" in email:
        # M3: strip a single trailing dot — `example.com.` is the fully-qualified
        # form of the same reserved placeholder domain `example.com` and must be
        # rejected, not let slip past the denylist by the trailing dot.
        domain = email.split("@", 1)[1].lower().rstrip(".")
        for bad_domain in DENYLIST_DOMAINS:
            if domain == bad_domain or domain.endswith("." + bad_domain):
                return False, f"placeholder domain: {domain!r}"
    else:
        return False, "no @ symbol"

    for pattern in DENYLIST_PATTERNS:
        if pattern.search(email):
            return False, f"matches denylist pattern: {pattern.pattern!r}"

    if not re.match(r"^[^@ ]+@[^@ ]+\.[^@ ]+$", email):
        return False, f"malformed email: {email!r}"

    return True, "ok"


def is_valid_author_name(name: str) -> tuple[bool, str]:
    """Return ``(is_valid, reason)`` for an author/committer name."""
    if not name or not name.strip():
        return False, "empty name"
    if name.strip().lower() in DENYLIST_NAMES:
        return False, f"known placeholder name: {name!r}"
    return True, "ok"


def validate_name_field(name: str) -> tuple[bool, str]:
    """Robustly validate a stored-commit NAME field — ``(is_valid, reason)``.

    The shared core entry the range runners (``validate_push_identity`` and
    ``ci_author_check``) use for author/committer NAMES, so the tab-robustness
    rule lives in ONE place (DRY, like the email denylist). It wraps
    ``is_valid_author_name`` with one extra guard: a control character (a TAB git
    preserves inside a stored commit name) can hide a placeholder token behind an
    otherwise clean-looking field — ``"Test\\tFaker"`` whole-fields as a real
    name, yet it BEGINS with the known placeholder ``Test``. The whole field is
    judged first (empty / whitespace-only / exact placeholder / case variants);
    then each whitespace-delimited token is judged, so a placeholder smuggled
    behind a tab is still recognised and named on the offending field.
    """
    ok, reason = is_valid_author_name(name)
    if not ok:
        return ok, reason
    # Split on CONTROL whitespace only (tab / newline / carriage-return /
    # form-feed / vertical-tab) — NOT spaces. A space separates the parts of a
    # legitimate multi-word name (``John T Smith``), so a space-delimited token
    # that merely equals a placeholder is not an attack. Only a control
    # character — itself anomalous in a stored commit name — can hide a
    # placeholder behind an otherwise clean field (``"Test\tFaker"``).
    for token in re.split(r"[\t\n\r\f\v]", name):
        if not token:
            continue
        token_ok, token_reason = is_valid_author_name(token)
        if not token_ok:
            return token_ok, token_reason
    return True, "ok"


def get_git_ident(var_name: str) -> str:
    """Return the full git identity string for an ident logical variable.

    ``var_name`` is ``GIT_AUTHOR_IDENT`` or ``GIT_COMMITTER_IDENT``. The result
    is ``"Name <email> unix-timestamp +timezone"`` — resolved the same way git
    resolves identity for the commit it is about to write (research §2.2).
    """
    result = subprocess.run(
        ["git", "var", var_name],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def extract_email(ident: str) -> str:
    """Parse the email from a ``Name <email> timestamp timezone`` ident string."""
    match = re.search(r"<([^>]*)>", ident)
    return match.group(1) if match else ""


def extract_name(ident: str) -> str:
    """Parse the name from a ``Name <email> timestamp timezone`` ident string."""
    match = re.match(r"^(.*?)\s*<", ident)
    return match.group(1).strip() if match else ""


def main() -> int:
    """pre-commit entry: validate the resolved author + committer identity.

    Reads ``git var GIT_AUTHOR_IDENT`` and ``GIT_COMMITTER_IDENT``, validates the
    name and email of each role independently, and returns non-zero with a clear
    explanation on stderr if any field is rejected — including the degraded case
    where git can resolve no identity at all (research §2.4).
    """
    errors = []
    for var, role in [
        ("GIT_AUTHOR_IDENT", "author"),
        ("GIT_COMMITTER_IDENT", "committer"),
    ]:
        try:
            ident = get_git_ident(var)
        except subprocess.CalledProcessError:
            errors.append(f"{role}: could not resolve identity (is user.email set?)")
            continue

        name = extract_name(ident)
        email = extract_email(ident)

        name_ok, name_reason = is_valid_author_name(name)
        email_ok, email_reason = is_valid_author_email(email)

        if not name_ok:
            errors.append(f"{role} name rejected: {name_reason}")
        if not email_ok:
            errors.append(f"{role} email rejected: {email_reason}")

    if errors:
        print("COMMIT REJECTED — invalid author/committer identity:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        print(
            "\nFix: set YOUR real identity — "
            "git config user.email '<your-email>' && "
            "git config user.name '<your-name>' "
            "(or a GitHub no-reply address, unique per person).",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
