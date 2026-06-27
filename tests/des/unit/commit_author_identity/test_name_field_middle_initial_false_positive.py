"""Regression: ``validate_name_field`` must not reject real multi-word names.

The R3-F1 name-aware range check (``validate_name_field`` in
``scripts/hooks/validate_author_identity.py``) wraps the whole-field placeholder
rule with a per-token guard so a placeholder smuggled behind a control character
(``"Test\\tFaker"``) is still recognised. Today that guard tokenizes on ALL
whitespace::

    for token in name.split():          # splits on spaces, tabs, newlines …

so a SPACE-separated token that merely *equals* a denylisted placeholder
(``t`` / ``test`` / ``user``) wrongly trips the gate. Real human names are
rejected as a result:

  * ``John T Smith``   — middle initial ``T``  → token ``T``    → ``t`` denied
  * ``Bao T Nguyen``   — middle initial ``T``  → token ``T``    → ``t`` denied
  * ``Mary T O'Brien`` — middle initial ``T``  → token ``T``    → ``t`` denied
  * ``Pat User``       — surname ``User``       → token ``User`` → ``user`` denied
  * ``Test Ng``        — given name ``Test``    → token ``Test`` → ``test`` denied
  * ``Liu Test Wei``   — middle name ``Test``   → token ``Test`` → ``test`` denied

A space-separated token equal to ``t`` / ``test`` / ``user`` is NOT a
placeholder — only the WHOLE field (an exact ``Test`` / ``T`` / ``User``) or a
token hidden behind a TAB / newline is. The crafter narrows the tokenization to
CONTROL characters (tab / newline) only; these tests pin both halves of the
contract:

  * EXPECTED-RED  — the six real names above must be ACCEPTED (rejected today).
  * EXPECTED-PASS — a TAB-hidden leading placeholder (``"Test\\tFaker"``) and a
    NEWLINE-hidden placeholder must STAY rejected, and a bare whole-field
    placeholder must STAY rejected. These must not change when the fix lands.

Layer 1 (pure function, no git / no I/O), example-based — Mandate 9 + 11.
"""

from __future__ import annotations

import pytest

from scripts.hooks.validate_author_identity import validate_name_field


# ── EXPECTED-RED: real multi-word names whose SPACE-separated tokens collide
#    with the placeholder denylist must be ACCEPTED. These FAIL today (the gate
#    rejects them) and turn GREEN once tokenization is narrowed to control chars.

_REAL_NAMES_WITH_COLLIDING_TOKENS = [
    "John T Smith",
    "Bao T Nguyen",
    "Pat User",
    "Test Ng",
    "Liu Test Wei",
    "Mary T O'Brien",
]


@pytest.mark.parametrize("name", _REAL_NAMES_WITH_COLLIDING_TOKENS)
def test_real_name_with_placeholder_colliding_token_is_accepted(name: str) -> None:
    """A real name is accepted even when a SPACE-separated token equals a placeholder.

    ``"John T Smith"`` is a legitimate contributor with a middle initial — the
    space-separated ``T`` is NOT the placeholder name ``T`` (which is the WHOLE
    field). EXPECTED-RED until the per-token loop stops splitting on spaces.
    """
    ok, reason = validate_name_field(name)
    assert ok is True, f"{name!r} wrongly rejected: {reason}"
    assert reason == "ok"


# ── EXPECTED-PASS: the tab/newline-hidden placeholder guard must NOT weaken ──
# Git preserves a literal TAB inside a stored commit name, so a placeholder can
# hide behind one. Narrowing tokenization to control chars keeps catching it.


def test_tab_hidden_leading_placeholder_is_still_rejected() -> None:
    """``"Test\\tFaker"`` — a leading placeholder behind a TAB — stays REJECTED.

    The whole field ``"Test\\tFaker"`` is not an exact placeholder, but it BEGINS
    with the known placeholder ``Test`` hidden behind a tab. A control-char split
    still isolates the ``Test`` token, so the field is refused. This assertion is
    the existing tab-attack guard and must not change.
    """
    ok, reason = validate_name_field("Test\tFaker")
    assert ok is False
    assert "placeholder name" in reason


def test_newline_hidden_leading_placeholder_is_still_rejected() -> None:
    """A NEWLINE-hidden leading placeholder stays REJECTED at the faithful layer.

    Git strips a literal newline from a STORED commit name, so this vector is
    faithful only at the pure-function layer (here), where the newline survives.
    ``"User\\nGearoid O'Treasaigh"`` hides the placeholder ``User`` behind a
    newline; a control-char split still isolates it and refuses the field.
    """
    ok, reason = validate_name_field("User\nGearoid O'Treasaigh")
    assert ok is False
    assert "placeholder name" in reason


# ── EXPECTED-PASS: a bare whole-field placeholder must STAY rejected ─────────
# The boundary the fix must preserve: narrowing the token loop must not let an
# exact whole-field placeholder (the thing the gate exists to catch) slip past.


@pytest.mark.parametrize("name", ["Test", "T", "User", "TEST", "USER", "test", "  "])
def test_whole_field_placeholder_is_still_rejected(name: str) -> None:
    """An exact placeholder / empty-ish whole field stays REJECTED.

    ``Test`` / ``T`` / ``User`` (any case) and a whitespace-only field are
    placeholders/empties the whole-field rule already catches; the tokenization
    narrowing must leave this judgement intact.
    """
    ok, _reason = validate_name_field(name)
    assert ok is False
