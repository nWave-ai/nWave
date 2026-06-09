"""Tests for scripts/sync/compose_trailer_commit.py.

Composes the empty-trailer commit message appended to every pr-mirror/<N>
sync. The exact byte sequence on stdout is contractually fixed — both
close-public-pr.yml and release-prod.yml's sync-public step grep the
`Public-PR:` trailer, so any drift breaks the integration.

CLI contract:
    docs/feature/public-pr-sync/devops/wave-decisions.md §3

Tests invoke the script via subprocess by file path (how the consumer
workflow sync-public-pr.yml invokes it), to validate the real CLI contract.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "sync"
    / "compose_trailer_commit.py"
)

VALID_SHA = "a" * 40
VALID_NAME = "Alice Example"
VALID_EMAIL = "alice@example.com"
VALID_PR = "42"


def _run(args: list[str]) -> subprocess.CompletedProcess[bytes]:
    """Invoke the script via subprocess and capture raw bytes for byte-level asserts."""
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), *args],
        capture_output=True,
    )


def _ok_args(
    *,
    pr_number: str = VALID_PR,
    head_sha: str = VALID_SHA,
    name: str = VALID_NAME,
    email: str = VALID_EMAIL,
) -> list[str]:
    return [
        "--pr-number",
        pr_number,
        "--public-head-sha",
        head_sha,
        "--contributor-name",
        name,
        "--contributor-email",
        email,
    ]


# ---------------------------------------------------------------------------
# Happy path — exact byte sequence on stdout
# ---------------------------------------------------------------------------


class TestHappyPath:
    """Exact commit template output."""

    def test_emits_exact_byte_sequence(self):
        result = _run(
            _ok_args(
                pr_number="7",
                head_sha="0123456789abcdef0123456789abcdef01234567",
                name="Alice Example",
                email="alice@example.co.uk",
            )
        )

        assert result.returncode == 0
        assert result.stderr == b""
        expected = (
            b"chore(sync): mirror of nWave-ai/nWave#7\n"
            b"\n"
            b"Public-PR: nWave-ai/nWave#7\n"
            b"Public-Head: 0123456789abcdef0123456789abcdef01234567\n"
            b"Co-authored-by: Alice Example <alice@example.co.uk>\n"
        )
        assert result.stdout == expected

    def test_trailer_order_is_fixed(self):
        """Public-PR must precede Public-Head must precede Co-authored-by."""
        result = _run(_ok_args())

        assert result.returncode == 0
        text = result.stdout.decode()
        pr_idx = text.index("Public-PR:")
        head_idx = text.index("Public-Head:")
        coauthor_idx = text.index("Co-authored-by:")
        assert pr_idx < head_idx < coauthor_idx

    def test_subject_and_trailer_block_separated_by_single_blank_line(self):
        result = _run(_ok_args())

        assert result.returncode == 0
        lines = result.stdout.decode().split("\n")
        # subject, blank, Public-PR, Public-Head, Co-authored-by, trailing empty
        assert lines[0].startswith("chore(sync):")
        assert lines[1] == ""
        assert lines[2].startswith("Public-PR:")


# ---------------------------------------------------------------------------
# Validation rejections (exit 2, silent stdout, stderr has error sentence)
# ---------------------------------------------------------------------------


class TestContributorNameRejections:
    """--contributor-name must be non-empty and must not contain < or >."""

    @pytest.mark.parametrize(
        "bad_name",
        [
            "",
            "   ",
            "Bob <evil>",
            "has<angle",
            "has>angle",
        ],
    )
    def test_rejects_invalid_name(self, bad_name):
        result = _run(_ok_args(name=bad_name))

        assert result.returncode == 2
        assert result.stdout == b""
        assert result.stderr.strip() != b""


class TestContributorEmailRejections:
    """--contributor-email must match the pinned regex."""

    @pytest.mark.parametrize(
        "bad_email",
        [
            "plain-text",
            "no@dot",
            "two@@at.com",
            "has space@host.com",
            "<alice@example.com>",
            "alice@example.com>",
        ],
    )
    def test_rejects_malformed_email(self, bad_email):
        result = _run(_ok_args(email=bad_email))

        assert result.returncode == 2
        assert result.stdout == b""
        assert result.stderr.strip() != b""

    @pytest.mark.parametrize(
        "good_email",
        [
            "alice@example.co.uk",
            "bob@users.noreply.github.com",
            "carol@my-host.org",
        ],
    )
    def test_accepts_realistic_emails(self, good_email):
        result = _run(_ok_args(email=good_email))

        assert result.returncode == 0
        assert good_email.encode() in result.stdout


class TestPrNumberRejections:
    """--pr-number must be a positive integer."""

    @pytest.mark.parametrize("bad", ["0", "-1", "-42", "abc", "1.5", ""])
    def test_rejects_non_positive_or_non_integer(self, bad):
        result = _run(_ok_args(pr_number=bad))

        assert result.returncode == 2
        assert result.stdout == b""
        assert result.stderr.strip() != b""


class TestHeadShaRejections:
    """--public-head-sha must be exactly 40 hex characters."""

    @pytest.mark.parametrize(
        "bad_sha",
        [
            "",
            "a" * 39,  # too short
            "a" * 41,  # too long
            "g" * 40,  # non-hex char
            "A" * 40 + "X",  # mixed / too long
            "xyz" + "a" * 37,  # non-hex prefix
        ],
    )
    def test_rejects_invalid_sha(self, bad_sha):
        result = _run(_ok_args(head_sha=bad_sha))

        assert result.returncode == 2
        assert result.stdout == b""
        assert result.stderr.strip() != b""

    def test_accepts_uppercase_hex_sha(self):
        """SHAs are case-insensitive in git; uppercase must be accepted."""
        result = _run(_ok_args(head_sha="A" * 40))

        assert result.returncode == 0


# ---------------------------------------------------------------------------
# Exit code invariants & channel discipline
# ---------------------------------------------------------------------------


class TestExitCodeInvariants:
    """Only exit codes 0 or 2 — never 1, never 3+."""

    def test_missing_required_flag_exits_2(self):
        """Missing any required flag is a usage error (exit 2), not argparse's default 2 — we assert it's 2."""
        result = _run(["--pr-number", "1"])  # missing the other three

        assert result.returncode == 2
        assert result.stdout == b""

    def test_success_silent_on_stderr(self):
        result = _run(_ok_args())

        assert result.returncode == 0
        assert result.stderr == b""
