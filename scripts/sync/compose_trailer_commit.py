"""Compose the empty-trailer commit message for a public-PR mirror sync.

Emits on stdout a complete commit message body, ready for
`git commit --allow-empty -F -`, with the contractually-fixed trailer
block parsed by `.github/workflows/close-public-pr.yml` and the
release-shipped step in `.github/workflows/release-prod.yml`.

CLI contract: docs/feature/public-pr-sync/devops/wave-decisions.md §3.

    python scripts/sync/compose_trailer_commit.py \\
        --pr-number <N> \\
        --public-head-sha <40-hex-sha> \\
        --contributor-name "<display-name>" \\
        --contributor-email "<email>"

Exit codes:
    0 = success; commit message body on stdout, stderr silent
    2 = usage error (bad args, invalid formats); error sentence on stderr
"""

from __future__ import annotations

import argparse
import re
import sys
from typing import NoReturn


EMAIL_RE = re.compile(r"^[^<>\s@]+@[^<>\s@]+\.[^<>\s@]+$")
SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")


class UsageError(Exception):
    """Raised when input validation fails. Mapped to exit code 2."""


def _die(message: str) -> NoReturn:
    """Print an error sentence to stderr and exit with code 2."""
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(2)


def _validate_pr_number(raw: str) -> int:
    """A positive integer. Rejects 0, negatives, floats, and non-numeric input."""
    try:
        n = int(raw)
    except ValueError as exc:
        raise UsageError(
            f"--pr-number must be a positive integer, got {raw!r}"
        ) from exc
    if n <= 0:
        raise UsageError(f"--pr-number must be positive, got {n}")
    return n


def _validate_sha(raw: str) -> str:
    """Exactly 40 hex characters. Case-insensitive (git accepts either)."""
    if not SHA_RE.fullmatch(raw):
        raise UsageError(
            f"--public-head-sha must be exactly 40 hex characters, got {raw!r}"
        )
    return raw


def _validate_name(raw: str) -> str:
    """Non-empty after whitespace trim; must not contain `<` or `>`."""
    trimmed = raw.strip()
    if not trimmed:
        raise UsageError("--contributor-name must not be empty")
    if "<" in trimmed or ">" in trimmed:
        raise UsageError("--contributor-name must not contain '<' or '>'")
    return trimmed


def _validate_email(raw: str) -> str:
    """Matches the pinned regex: no trailer-corrupting chars, exactly one @, dot on RHS."""
    if not EMAIL_RE.fullmatch(raw):
        raise UsageError(f"--contributor-email is not a valid email: {raw!r}")
    return raw


def _compose(pr_number: int, head_sha: str, name: str, email: str) -> str:
    """Build the exact byte sequence of the commit message."""
    subject = f"chore(sync): mirror of nWave-ai/nWave#{pr_number}"
    trailers = (
        f"Public-PR: nWave-ai/nWave#{pr_number}\n"
        f"Public-Head: {head_sha}\n"
        f"Co-authored-by: {name} <{email}>\n"
    )
    return f"{subject}\n\n{trailers}"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compose the empty-trailer commit message for a public-PR mirror sync."
        ),
        add_help=True,
    )
    parser.add_argument(
        "--pr-number", required=True, help="Public PR number (positive integer)"
    )
    parser.add_argument(
        "--public-head-sha", required=True, help="40-hex commit SHA on public"
    )
    parser.add_argument(
        "--contributor-name",
        required=True,
        help="Contributor display name (no '<' or '>')",
    )
    parser.add_argument(
        "--contributor-email",
        required=True,
        help="Contributor email (matches ^[^<>\\s@]+@[^<>\\s@]+\\.[^<>\\s@]+$)",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    """Parse args, validate, emit commit message on stdout, or exit 2 on error."""
    parser = _build_parser()

    # argparse exits with code 2 on missing required args by default — matches our contract.
    # But it prints to stderr with its own format, which satisfies "error sentence on stderr".
    args = parser.parse_args(argv)

    try:
        pr_number = _validate_pr_number(args.pr_number)
        head_sha = _validate_sha(args.public_head_sha)
        name = _validate_name(args.contributor_name)
        email = _validate_email(args.contributor_email)
    except UsageError as exc:
        _die(str(exc))

    sys.stdout.write(_compose(pr_number, head_sha, name, email))


if __name__ == "__main__":
    main()
