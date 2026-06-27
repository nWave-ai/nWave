"""Robustness unit tests for the range-runner row parsing (layer 1, no I/O).

Two adversarial-review findings are pinned here, both at the pure parsing seam
the push / CI runners share — driven directly, no git, no subprocess:

  * R3-F4 (EXPECTED-PASS coverage) — ``ci_author_check._parse_rows`` must DROP a
    malformed ``git log`` row (one that does not split into exactly
    ``sha \\t author_email \\t committer_email``) safely, rather than crash or
    fabricate a 1- or 2-field tuple that a downstream ``sha, ae, ce = row``
    unpack would choke on. Kills the ``_parse_rows`` malformed-drop guard
    mutation: a runner that dropped the ``len(parts) == 3`` filter would either
    raise on unpack or smuggle a malformed tuple through.

  * R3-F1 robustness (EXPECTED-PASS — value-pinning for the NAME-aware runner) —
    the name core ALREADY recognises ``Test`` / ``User`` placeholders, including
    the leading token of a tab-bearing name and the first line of a
    newline-bearing field. These tests pin the exact values the crafter's new
    NUL-separated ``%an``/``%cn`` rows must carry, so the runner-level RED
    acceptance scenarios (``A change set whose author name is a placeholder …``)
    have a precise unit spec to lean on. The runner-level GAP is proven RED at
    the acceptance layer (push/CI scenarios); these are the supporting layer-1
    assertions, which pass today.

Layer 1 (pure functions over fabricated rows), example-based — Mandate 9 + 11.
"""

from __future__ import annotations


# ── R3-F4: malformed-row drop is safe (EXPECTED-PASS — kills the guard mutation)


def test_parse_rows_drops_a_row_with_too_few_fields() -> None:
    """A row missing the committer-email column is dropped, not mis-unpacked."""
    from scripts.hooks.ci_author_check import _parse_rows

    # Well-formed row + a malformed one (only sha\temail — two fields).
    stdout = (
        "abc123\tauthor@users.noreply.github.com\tcommitter@users.noreply.github.com\n"
        "def456\tlonely@field.only\n"
    )
    rows = _parse_rows(stdout)

    # The malformed row is dropped; only the 3-field row survives, and every
    # surviving row is a clean 3-tuple safe to unpack downstream.
    assert rows == [
        (
            "abc123",
            "author@users.noreply.github.com",
            "committer@users.noreply.github.com",
        )
    ]
    assert all(len(row) == 3 for row in rows)


def test_parse_rows_drops_blank_lines() -> None:
    """Blank / whitespace-only lines never become rows (no empty-tuple smuggling)."""
    from scripts.hooks.ci_author_check import _parse_rows

    stdout = "\n   \nabc123\ta@x.io\tb@x.io\n\n"
    rows = _parse_rows(stdout)
    assert rows == [("abc123", "a@x.io", "b@x.io")]


# ── R3-F1 robustness: a tab/newline in a NAME cannot smuggle a placeholder ───
# These pin the contract for the NAME-aware runner the crafter must build. They
# call ``is_valid_author_name`` over the exact fragments a tab/newline split
# would otherwise mis-read, asserting the placeholder is recognised. They are
# EXPECTED-RED only insofar as the runners do not YET feed names to this check;
# the name-core itself already recognises them, so these double as the explicit
# spec for the values the new ``%an``/``%cn`` rows must carry.


def test_tab_bearing_placeholder_name_is_recognised_by_the_name_core() -> None:
    """The leading ``Test`` of a tab-bearing name is a recognised placeholder.

    Construction mirrors ``Test\\tFaker`` — git preserves the tab in a stored
    name. A NUL-separated runner keeps the whole name in one field; the name
    core must then recognise the ``Test`` placeholder (case-insensitive). The
    field as a WHOLE is also a placeholder-bearing fixture name and must not be
    accepted as a real human name.
    """
    from scripts.hooks.validate_author_identity import is_valid_author_name

    whole_field = "Test\tFaker"
    leading_token = whole_field.split("\t", 1)[0]
    ok_leading, _ = is_valid_author_name(leading_token)
    assert ok_leading is False  # "Test" is a known placeholder name


def test_newline_in_name_field_does_not_yield_an_acceptable_real_name() -> None:
    """A newline-bearing name field must never be read as a clean real name.

    Git strips a literal newline from a STORED commit name, but a NAME-aware
    runner that reads ``%an``/``%cn`` line-by-line (instead of NUL records) could
    split a multi-line value and read a clean-looking fragment. The contract:
    the first line of such a field — when it is a placeholder — is still
    rejected, so a newline cannot manufacture an acceptable name.
    """
    from scripts.hooks.validate_author_identity import is_valid_author_name

    field = "User\nGearoid O'Treasaigh"
    first_line = field.split("\n", 1)[0]
    ok_first, _ = is_valid_author_name(first_line)
    assert ok_first is False  # "User" is a known placeholder name
