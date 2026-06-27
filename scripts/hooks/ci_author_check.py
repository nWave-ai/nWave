"""Authoritative CI commit-identity range check.

The unbypassable gate for the ``commit-author-identity-validation`` feature: a
pure-Python runner (matching the repo's zero-shell preference) invoked by the CI
"Fast checks" stage. Iterates ``git log <base>..<head>`` and validates every
commit's author + committer NAME *and* email through the shared validator core,
exiting non-zero (and listing every offending commit) if any commit in the range
carries a placeholder identity. This is the only gate that survives
``--no-verify`` and a ``core.hooksPath`` injection (research §3.1) — so it cannot
afford to skip the NAME field the pre-commit gate already checks (R3-F1): a
placeholder *name* (``Test`` / ``User``) with a valid email must be flagged too.

Robust parsing (R3-F1): the ``git log`` / ``git show`` format is NUL/control
separated — records split on NUL (``-z``), the five fields (sha, author name,
author email, committer name, committer email) split on the 0x1F unit separator,
which cannot appear inside a git ident. This keeps every field correctly placed
even when a name carries a TAB or newline (which a ``\\t``-delimited format would
let misalign the columns and hide a placeholder behind a clean-looking fragment).

The CI workflow step calls this with ``--base`` / ``--head`` and checks out the
repo with ``actions/checkout`` ``fetch-depth: 0`` so the range is visible.
Reuses the validator core (DRY). Design source:
``docs/analysis/commit-author-validation-research.md`` §3.1, §3.2.
"""

from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys


# C1: self-locate the repo root so the sibling-module import resolves regardless
# of cwd or install shape. In a clean CI checkout (no `uv sync` / PYTHONPATH) the
# `scripts` package is not on sys.path, so this bootstrap is what lets the gate
# run at all — without it the script crashes ModuleNotFoundError before
# validating anything. parents[2] of scripts/hooks/x.py is the repo root.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from scripts.hooks.validate_author_identity import (
    is_valid_author_email,
    validate_name_field,
)


# R3-F1 robust range format: records separated by NUL (``-z``); the five fields
# separated by the 0x1F ASCII unit separator, which cannot appear inside a git
# ident — so a TAB or newline in a name can never misalign the column split.
_UNIT_SEP = "\x1f"
_RECORD_SEP = "\x00"
_RANGE_FORMAT = "%H%x1f%an%x1f%ae%x1f%cn%x1f%ce"

# Each parsed record: (sha, author_name, author_email, committer_name,
# committer_email).
Record = tuple[str, str, str, str, str]


def commits_in_range(base: str, head: str) -> list[Record]:
    """Return ``(sha, author_name, author_email, committer_name, committer_email)``.

    One NUL-separated record per commit in ``base..head`` (R3-F1).
    """
    result = subprocess.run(
        ["git", "log", "-z", f"{base}..{head}", f"--format={_RANGE_FORMAT}"],
        capture_output=True,
        text=True,
        check=True,
    )
    return _parse_records(result.stdout)


def single_commit(head: str) -> list[Record]:
    """Return the one NUL-separated record for a single commit.

    W1: the degrade-to-HEAD path. When no ``base..head`` range exists (initial
    push, force-push, or a HEAD with no parent), the gate still validates the
    single pushed commit's author + committer (name AND email) rather than
    validating nothing.
    """
    result = subprocess.run(
        ["git", "show", "-s", "-z", f"--format={_RANGE_FORMAT}", head],
        capture_output=True,
        text=True,
        check=True,
    )
    return _parse_records(result.stdout)


def _parse_records(stdout: str) -> list[Record]:
    """Split NUL-separated records into clean 5-field tuples, dropping malformed.

    Defensive like ``_parse_rows``: a record that does not split into exactly
    five unit-separated fields is dropped rather than mis-unpacked downstream.
    """
    records: list[Record] = []
    for chunk in stdout.split(_RECORD_SEP):
        if not chunk:
            continue
        fields = chunk.split(_UNIT_SEP)
        if len(fields) == 5:
            records.append((fields[0], fields[1], fields[2], fields[3], fields[4]))
    return records


def _parse_rows(stdout: str) -> list[tuple[str, str, str]]:
    """Drop a malformed TAB-separated ``sha\\tae\\tce`` row safely (R3-F4 guard).

    Retained as the pinned defensive-drop contract for the legacy 3-field row
    shape (one that does not split into exactly three fields is dropped, never
    mis-unpacked). The live range format is now the NUL/unit-separated 5-field
    record parsed by ``_parse_records``.
    """
    rows = []
    for line in stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t", 2)
        if len(parts) == 3:
            rows.append((parts[0], parts[1], parts[2]))
    return rows


def main(argv: list[str] | None = None) -> int:
    """CI entry: validate every commit in ``--base..--head``."""
    parser = argparse.ArgumentParser(
        description="Validate commit author/committer identity over a range."
    )
    parser.add_argument(
        "--base",
        default=None,
        help="base ref/SHA (exclusive); omit or pass empty to validate only --head",
    )
    parser.add_argument("--head", required=True, help="head ref/SHA (inclusive)")
    args = parser.parse_args(argv)

    # W1: with no base (absent or empty string), degrade to validating the single
    # HEAD commit — never let "no range" mean "no validation". An empty
    # ``--base ""`` is treated as absent because ``git log "..HEAD"`` resolves to
    # an empty range and would otherwise validate ZERO commits.
    if not args.base:
        commits = single_commit(args.head)
    else:
        commits = commits_in_range(args.base, args.head)

    errors = []
    for sha, author_name, author_email, committer_name, committer_email in commits:
        for role, name in [
            ("author", author_name),
            ("committer", committer_name),
        ]:
            ok, reason = validate_name_field(name)
            if not ok:
                errors.append(f"{sha[:8]} {role} name rejected: {reason} ({name!r})")
        for role, email in [
            ("author", author_email),
            ("committer", committer_email),
        ]:
            ok, reason = is_valid_author_email(email)
            if not ok:
                errors.append(f"{sha[:8]} {role} email rejected: {reason} ({email!r})")

    if errors:
        print(
            "Author identity check FAILED — commits with invalid identity:",
            file=sys.stderr,
        )
        for err in errors:
            print(f"  {err}", file=sys.stderr)
        return 1
    print("All commit author/committer identities OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
