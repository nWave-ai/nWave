"""Tests for assert_state_delta matcher — walking skeleton + core semantics.

@walking_skeleton
Scenario: Test author asserts a clean prepend transition and a violation is reported

    Given a PATH variable with value '/usr/bin'
    When assert_state_delta is called with PATH prepended with '/des/bin'
      and the new value is '/des/bin:/usr/bin'
    Then no AssertionError is raised

    And when assert_state_delta is called with a wrong new PATH value
    Then an AssertionError is raised whose message contains:
      - key='PATH'
      - the old value '/usr/bin'
      - the wrong new value '/wrong'
      - the predicate name 'prepended_with'

@slice-1 @us-1
Scenario: implicit-unchanged catches an undeclared change

    Given before={'PATH':'/u/bin','HOME':'/home/u'}
      and after={'PATH':'/des/bin:/u/bin','HOME':'/home/changed'}
      and universe={'PATH','HOME'}
      and expected={'PATH': prepended_with('/des/bin')}  (HOME not in expected)
    When assert_state_delta is called
    Then an AssertionError is raised
      and the message contains kind='undeclared_change' and key='HOME'
      and includes the old value '/home/u' and new value '/home/changed'

@slice-1 @us-1
Scenario: multi-violation collection (A7 — two simultaneous predicate failures)

    Given before={'PATH':'/u','HOME':'/h','X':'1'}
      and after={'PATH':'/wrong','HOME':'/h2','X':'1'}
      and universe={'PATH','HOME','X'}
      and expected={'PATH': prepended_with('/des'), 'HOME': unchanged()}
    When assert_state_delta is called
    Then an AssertionError is raised
      and the message reports exactly two violations: PATH (predicate_failed) AND
      HOME (predicate_failed via unchanged())
      and the message has exactly one header line plus two violation lines
"""

from __future__ import annotations

import pytest
from nwave_ai.state_delta import (
    Violation,
    assert_state_delta,
    prepended_with,
    unchanged,
)


# ---------------------------------------------------------------------------
# Walking skeleton (step 01-01)
# ---------------------------------------------------------------------------


def test_walking_skeleton_clean_prepend_and_violation() -> None:
    """Walking skeleton: happy-path returns None; violation raises with full context."""
    # --- Happy path: prepend is correct ---
    result = assert_state_delta(
        before={"PATH": "/usr/bin"},
        after={"PATH": "/des/bin:/usr/bin"},
        universe={"PATH"},
        expected={"PATH": prepended_with("/des/bin")},
    )
    assert result is None

    # --- Violation: new value does not satisfy the predicate ---
    with pytest.raises(AssertionError) as exc_info:
        assert_state_delta(
            before={"PATH": "/usr/bin"},
            after={"PATH": "/wrong"},
            universe={"PATH"},
            expected={"PATH": prepended_with("/des/bin")},
        )

    message = str(exc_info.value)
    assert "PATH" in message
    assert "/usr/bin" in message
    assert "/wrong" in message
    assert "prepended_with" in message


# ---------------------------------------------------------------------------
# @slice-1 @us-1 — Acceptance: implicit-unchanged enforcement (AC5)
# ---------------------------------------------------------------------------


def test_implicit_unchanged_catches_undeclared_change() -> None:
    """@slice-1 @us-1 — HOME changed but not declared in expected → undeclared_change."""
    before = {"PATH": "/u/bin", "HOME": "/home/u"}
    after = {"PATH": "/des/bin:/u/bin", "HOME": "/home/changed"}
    universe = {"PATH", "HOME"}
    expected = {"PATH": prepended_with("/des/bin")}  # HOME deliberately omitted

    with pytest.raises(AssertionError) as exc_info:
        assert_state_delta(
            before=before,
            after=after,
            universe=universe,
            expected=expected,
        )

    message = str(exc_info.value)
    assert "undeclared_change" in message
    assert "HOME" in message
    assert "/home/u" in message
    assert "/home/changed" in message


# ---------------------------------------------------------------------------
# Unit tests for core semantics (step 01-02, AC1-AC4)
# ---------------------------------------------------------------------------


def test_violation_dataclass_fields_accessible() -> None:
    """AC4 — Violation frozen dataclass exposes all 5 required fields."""
    v = Violation(
        kind="predicate_failed",
        key="MY_VAR",
        old="old_val",
        new="new_val",
        predicate_name="some_predicate",
    )
    assert v.kind == "predicate_failed"
    assert v.key == "MY_VAR"
    assert v.old == "old_val"
    assert v.new == "new_val"
    assert v.predicate_name == "some_predicate"


def test_multi_violation_collected_in_single_assertion_error() -> None:
    """AC1 — ALL violations collected; single AssertionError lists each one."""

    def always_false(old: object, new: object) -> bool:
        return False

    always_false.__name__ = "always_false"

    with pytest.raises(AssertionError) as exc_info:
        assert_state_delta(
            before={"A": "1", "B": "2"},
            after={"A": "bad_a", "B": "bad_b"},
            universe={"A", "B"},
            expected={"A": always_false, "B": always_false},
        )

    message = str(exc_info.value)
    # Both keys must appear in the single error — not just the first one
    assert "A" in message
    assert "B" in message


def test_predicate_failed_violation_kind_and_name() -> None:
    """AC3 — predicate returning False → kind='predicate_failed', predicate_name set."""
    with pytest.raises(AssertionError) as exc_info:
        assert_state_delta(
            before={"PATH": "/u/bin"},
            after={"PATH": "/wrong"},
            universe={"PATH"},
            expected={"PATH": prepended_with("/des/bin")},
        )

    message = str(exc_info.value)
    assert "predicate_failed" in message
    assert "prepended_with" in message


def test_undeclared_change_violation_kind() -> None:
    """AC2 — key in universe, not in expected, before!=after → kind='undeclared_change'."""
    with pytest.raises(AssertionError) as exc_info:
        assert_state_delta(
            before={"X": "original"},
            after={"X": "mutated"},
            universe={"X"},
            expected={},  # X not declared
        )

    message = str(exc_info.value)
    assert "undeclared_change" in message
    assert "X" in message
    assert "original" in message
    assert "mutated" in message


# ---------------------------------------------------------------------------
# @slice-1 @us-1 — Acceptance: multi-violation collection (step 01-03, A7)
# ---------------------------------------------------------------------------


def test_multi_violation_collection_with_unchanged_predicate() -> None:
    """@slice-1 @us-1 — PATH and HOME both fail; single AssertionError reports both."""
    before = {"PATH": "/u", "HOME": "/h", "X": "1"}
    after = {"PATH": "/wrong", "HOME": "/h2", "X": "1"}
    universe = {"PATH", "HOME", "X"}
    expected = {"PATH": prepended_with("/des"), "HOME": unchanged()}

    with pytest.raises(AssertionError) as exc_info:
        assert_state_delta(
            before=before,
            after=after,
            universe=universe,
            expected=expected,
        )

    message = str(exc_info.value)

    # Both violated keys must appear
    assert "PATH" in message
    assert "HOME" in message

    # Both must be predicate_failed (X is clean — no undeclared_change)
    assert message.count("predicate_failed") == 2

    # unchanged() predicate name must appear for HOME violation
    assert "unchanged()" in message

    # prepended_with predicate name must appear for PATH violation
    assert "prepended_with" in message

    # Message structure: 1 header line + 2 violation lines = 3 lines total
    lines = message.strip().splitlines()
    assert len(lines) == 3, (
        f"Expected 3 lines (1 header + 2 violations), got {len(lines)}: {message!r}"
    )


# ---------------------------------------------------------------------------
# Unit tests for unchanged() predicate (step 01-03)
# ---------------------------------------------------------------------------


def test_unchanged_predicate_returns_true_on_equal() -> None:
    """unchanged() returns True when old == new."""
    pred = unchanged()
    assert pred("/h", "/h") is True
    assert pred("same", "same") is True
    assert pred(None, None) is True


def test_unchanged_predicate_returns_false_on_different() -> None:
    """unchanged() returns False when old != new."""
    pred = unchanged()
    assert pred("/h", "/h2") is False
    assert pred("a", "b") is False
    assert pred(None, "something") is False


# ---------------------------------------------------------------------------
# Unit tests for strict mode (step 01-03, A6)
# ---------------------------------------------------------------------------


def test_strict_mode_raises_on_extra_key_in_after() -> None:
    """A6 — strict=True: key in after but outside universe raises strict_universe_mismatch."""
    with pytest.raises(AssertionError) as exc_info:
        assert_state_delta(
            before={"PATH": "/u"},
            after={"PATH": "/u", "EXTRA": "surprise"},
            universe={"PATH"},
            expected={},
            strict=True,
        )

    message = str(exc_info.value)
    assert "strict_universe_mismatch" in message
    assert "EXTRA" in message


def test_strict_universe_mismatch_violation_kind() -> None:
    """A6 — Violation kind is strict_universe_mismatch for extra-key in strict mode."""
    with pytest.raises(AssertionError) as exc_info:
        assert_state_delta(
            before={"PATH": "/u", "GHOST": "x"},
            after={"PATH": "/u"},
            universe={"PATH"},
            expected={},
            strict=True,
        )

    message = str(exc_info.value)
    assert "strict_universe_mismatch" in message
    assert "GHOST" in message


def test_lax_mode_default_ignores_extra_keys() -> None:
    """A6 — Default lax mode: extra keys in before/after outside universe are silently ignored."""
    # Should raise NO exception even though EXTRA is in before/after but not in universe
    result = assert_state_delta(
        before={"PATH": "/u", "EXTRA": "ignored"},
        after={"PATH": "/u", "EXTRA": "also_ignored"},
        universe={"PATH"},
        expected={},
    )
    assert result is None
