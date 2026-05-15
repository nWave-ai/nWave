"""Unit tests for predicate factories: prepended_with, appended_with, unchanged, set_to,
containing, normalized_to, idempotent_after, legacy_healed.

DoD #5: each predicate has positive + negative + composition tests.
8 predicates x (positive + negative + composition + edge cases) = ~55 unit tests total.
"""

from __future__ import annotations

from typing import Any

from nwave_ai.state_delta import (
    Predicate,
    appended_with,
    containing,
    idempotent_after,
    legacy_healed,
    normalized_to,
    prepended_with,
    set_to,
    unchanged,
)


# ---------------------------------------------------------------------------
# prepended_with
# ---------------------------------------------------------------------------


class TestPrependedWith:
    def test_positive_default_separator(self) -> None:
        pred = prepended_with("/des/bin")
        assert pred("/usr/bin", "/des/bin:/usr/bin") is True

    def test_negative_wrong_new_value(self) -> None:
        pred = prepended_with("/des/bin")
        assert pred("/usr/bin", "/wrong") is False

    def test_negative_constant_true_guard(self) -> None:
        """Ensures the predicate is not a constant lambda: True."""
        pred = prepended_with("/des/bin")
        assert pred("/usr/bin", "/usr/bin") is False  # old == new, not prepended

    def test_custom_separator(self) -> None:
        pred = prepended_with("/opt", sep=";")
        assert pred("/usr/bin", "/opt;/usr/bin") is True
        assert pred("/usr/bin", "/opt:/usr/bin") is False  # wrong sep

    def test_callable_as_predicate_type(self) -> None:
        pred: Predicate = prepended_with("X")
        result: bool = pred("old", "X:old")
        assert result is True

    def test_composition_with_unchanged_via_lambda(self) -> None:
        """Either prepended OR unchanged should satisfy the composed predicate."""

        def composed(o: Any, n: Any) -> bool:
            return prepended_with("X")(o, n) or unchanged()(o, n)

        assert composed("/u/bin", "X:/u/bin") is True  # prepend branch
        assert composed("/u/bin", "/u/bin") is True  # unchanged branch
        assert composed("/u/bin", "/wrong") is False  # neither branch

    def test_closure_independence(self) -> None:
        """Two separate calls produce independent closures with no shared state."""
        pred_a = prepended_with("A")
        pred_b = prepended_with("B")
        assert pred_a("x", "A:x") is True
        assert pred_b("x", "B:x") is True
        assert pred_a("x", "B:x") is False  # pred_a is not affected by pred_b
        assert pred_b("x", "A:x") is False  # pred_b is not affected by pred_a


# ---------------------------------------------------------------------------
# appended_with  (NEW)
# ---------------------------------------------------------------------------


class TestAppendedWith:
    def test_positive_default_separator(self) -> None:
        pred = appended_with(".bak")
        assert pred("/etc/hosts", "/etc/hosts:.bak") is True

    def test_negative_wrong_new_value(self) -> None:
        pred = appended_with(".bak")
        assert pred("/etc/hosts", "/etc/hosts") is False

    def test_negative_constant_true_guard(self) -> None:
        """Ensures the predicate is not a constant lambda: True."""
        pred = appended_with(".bak")
        assert pred("/etc/hosts", "totally-different") is False

    def test_negative_prepended_not_appended(self) -> None:
        """Prefix-only placement should not match appended_with."""
        pred = appended_with(".bak")
        assert pred("/etc/hosts", ".bak:/etc/hosts") is False

    def test_custom_separator(self) -> None:
        pred = appended_with("suffix", sep="|")
        assert pred("base", "base|suffix") is True
        assert pred("base", "base:suffix") is False  # wrong sep

    def test_empty_old_value(self) -> None:
        pred = appended_with("end")
        assert pred("", ":end") is True  # "" + ":" + "end"

    def test_callable_as_predicate_type(self) -> None:
        pred: Predicate = appended_with("x")
        result: bool = pred("old", "old:x")
        assert result is True

    def test_composition_with_unchanged_via_lambda(self) -> None:
        """Either appended OR unchanged should satisfy the composed predicate."""

        def composed(o: Any, n: Any) -> bool:
            return appended_with("v2")(o, n) or unchanged()(o, n)

        assert composed("pkg", "pkg:v2") is True  # append branch
        assert composed("pkg", "pkg") is True  # unchanged branch
        assert composed("pkg", "other") is False  # neither branch

    def test_closure_independence(self) -> None:
        pred_a = appended_with("A")
        pred_b = appended_with("B")
        assert pred_a("x", "x:A") is True
        assert pred_b("x", "x:B") is True
        assert pred_a("x", "x:B") is False
        assert pred_b("x", "x:A") is False


# ---------------------------------------------------------------------------
# unchanged
# ---------------------------------------------------------------------------


class TestUnchanged:
    def test_positive_equal_values(self) -> None:
        pred = unchanged()
        assert pred("/home/user", "/home/user") is True

    def test_negative_different_values(self) -> None:
        pred = unchanged()
        assert pred("/home/user", "/home/other") is False

    def test_negative_constant_true_guard(self) -> None:
        """Ensures the predicate is not a constant lambda: True."""
        pred = unchanged()
        assert pred("before", "after") is False

    def test_positive_non_string_types(self) -> None:
        pred = unchanged()
        assert pred(42, 42) is True
        assert pred(42, 43) is False

    def test_callable_as_predicate_type(self) -> None:
        pred: Predicate = unchanged()
        result: bool = pred("same", "same")
        assert result is True

    def test_composition_with_prepended_with_via_lambda(self) -> None:
        """Either unchanged OR prepended should satisfy the composed predicate."""

        def composed(o: Any, n: Any) -> bool:
            return unchanged()(o, n) or prepended_with("X")(o, n)

        assert composed("v", "v") is True  # unchanged branch
        assert composed("v", "X:v") is True  # prepend branch
        assert composed("v", "wrong") is False  # neither branch

    def test_closure_independence(self) -> None:
        pred_1 = unchanged()
        pred_2 = unchanged()
        # Both are equivalent but independent closures
        assert pred_1("a", "a") is True
        assert pred_2("b", "b") is True
        # Mutating __name__ on one should not affect the other (closures isolated)
        pred_1.__name__ = "renamed"
        assert pred_2.__name__ == "unchanged()"


# ---------------------------------------------------------------------------
# set_to  (NEW)
# ---------------------------------------------------------------------------


class TestSetTo:
    def test_positive_new_equals_target(self) -> None:
        pred = set_to("active")
        assert pred("inactive", "active") is True

    def test_negative_new_not_equal_target(self) -> None:
        pred = set_to("active")
        assert pred("inactive", "inactive") is False

    def test_negative_constant_true_guard(self) -> None:
        """Ensures the predicate is not a constant lambda: True."""
        pred = set_to("active")
        assert pred("inactive", "pending") is False

    def test_old_value_is_ignored(self) -> None:
        """Different old values should not change the verdict when new matches target."""
        pred = set_to("enabled")
        assert pred("disabled", "enabled") is True
        assert pred("pending", "enabled") is True
        assert pred("", "enabled") is True
        assert pred(None, "enabled") is True

    def test_old_none_new_matches(self) -> None:
        pred = set_to(42)
        assert pred(None, 42) is True
        assert pred(None, 43) is False

    def test_non_string_target(self) -> None:
        pred = set_to(True)
        assert pred(False, True) is True
        assert pred(False, False) is False

    def test_callable_as_predicate_type(self) -> None:
        pred: Predicate = set_to("done")
        result: bool = pred("todo", "done")
        assert result is True

    def test_composition_with_unchanged_via_lambda(self) -> None:
        """Either set_to a value OR unchanged should satisfy the composed predicate."""

        def composed(o: Any, n: Any) -> bool:
            return set_to("enabled")(o, n) or unchanged()(o, n)

        assert composed("disabled", "enabled") is True  # set_to branch
        assert composed("stable", "stable") is True  # unchanged branch
        assert composed("any", "other") is False  # neither branch

    def test_closure_independence(self) -> None:
        pred_x = set_to("X")
        pred_y = set_to("Y")
        assert pred_x("old", "X") is True
        assert pred_y("old", "Y") is True
        assert pred_x("old", "Y") is False
        assert pred_y("old", "X") is False


# ---------------------------------------------------------------------------
# Cross-predicate: closure independence across all 4 factories
# ---------------------------------------------------------------------------


class TestClosureIndependence:
    def test_all_four_factories_produce_independent_closures(self) -> None:
        """Separate factory calls produce separate closures with no shared state."""
        pred_prepend_a = prepended_with("A")
        pred_prepend_b = prepended_with("B")
        pred_append_a = appended_with("A")
        pred_append_b = appended_with("B")
        pred_unchanged_1 = unchanged()
        pred_unchanged_2 = unchanged()
        pred_set_x = set_to("X")
        pred_set_y = set_to("Y")

        # Each predicate independently matches only its own criterion
        assert pred_prepend_a("x", "A:x") is True
        assert pred_prepend_b("x", "A:x") is False

        assert pred_append_a("x", "x:A") is True
        assert pred_append_b("x", "x:A") is False

        assert pred_unchanged_1("v", "v") is True
        assert pred_unchanged_2("v", "v") is True  # both work; closures separate

        assert pred_set_x("old", "X") is True
        assert pred_set_y("old", "X") is False


# ---------------------------------------------------------------------------
# containing  (NEW — predicates 5-6)
# ---------------------------------------------------------------------------


class TestContaining:
    def test_containing_substring_in_new(self) -> None:
        pred = containing("/usr/bin")
        assert pred("", "/des/bin:/usr/bin") is True

    def test_containing_substring_absent_returns_false(self) -> None:
        pred = containing("/usr/bin")
        assert pred("", "/des/bin:/opt/bin") is False

    def test_containing_constant_true_guard(self) -> None:
        """Predicate must not be a constant lambda: True."""
        pred = containing("needle")
        assert pred("anything", "no-match-here") is False

    def test_containing_ignores_old_value(self) -> None:
        """Same new value with different old values must produce the same verdict."""
        pred = containing("/usr/bin")
        assert pred("/old/path/a", "/des/bin:/usr/bin") is True
        assert pred("/old/path/b", "/des/bin:/usr/bin") is True
        assert pred("/old/path/a", "/des/bin:/other") is False
        assert pred("/old/path/b", "/des/bin:/other") is False

    def test_containing_composes_with_prepended_with(self) -> None:
        """Both conditions must hold simultaneously."""

        def composed(o: Any, n: Any) -> bool:
            return prepended_with("/des/bin")(o, n) and containing("/usr/bin")(o, n)

        # Both true: new is prepended and contains the substring
        assert composed("/usr/bin", "/des/bin:/usr/bin") is True
        # Only containing is true (new contains substring but is not correctly prepended)
        assert composed("/usr/bin", "/other:/usr/bin") is False
        # Only prepended is true (new is correctly prepended but substring absent)
        assert composed("/opt/bin", "/des/bin:/opt/bin") is False


# ---------------------------------------------------------------------------
# normalized_to  (NEW — predicates 5-6)
# ---------------------------------------------------------------------------


class TestNormalizedTo:
    def test_normalized_to_equal_after_normalization_returns_true(self) -> None:
        """$HOME expansion normalizer: old is expanded, new has $HOME literal."""

        def home_expander(value: str) -> str:
            return value.replace("$HOME", "/home/u")

        pred = normalized_to(home_expander)
        # old is already expanded; new uses $HOME literal — both normalize to same value
        assert pred("/home/u/.local/bin", "$HOME/.local/bin") is True

    def test_normalized_to_normalizer_outputs_differ_returns_false(self) -> None:
        def home_expander(value: str) -> str:
            return value.replace("$HOME", "/home/u")

        pred = normalized_to(home_expander)
        assert pred("/home/u/.local/bin", "$HOME/.other/bin") is False

    def test_normalized_to_identity_normalizer_behaves_like_unchanged(self) -> None:
        """normalized_to(lambda x: x) must agree with unchanged() on every pair."""
        identity_pred = normalized_to(lambda x: x)
        unchanged_pred = unchanged()

        pairs = [
            ("same", "same"),
            ("before", "after"),
            ("", ""),
            ("/a/b", "/a/c"),
            (42, 42),
        ]
        for old, new in pairs:
            assert identity_pred(old, new) == unchanged_pred(old, new), (
                f"Mismatch on pair ({old!r}, {new!r})"
            )

    def test_normalized_to_constant_true_guard(self) -> None:
        """Predicate must not be a constant lambda: True."""
        pred = normalized_to(str.upper)
        assert pred("hello", "WORLD") is False  # "HELLO" != "WORLD"

    def test_normalized_to_positive_str_upper(self) -> None:
        pred = normalized_to(str.upper)
        assert pred("hello", "HELLO") is True


# ---------------------------------------------------------------------------
# Cross-predicate: closure independence across all 6 factories
# ---------------------------------------------------------------------------


class TestPredicates56ClosureIndependence:
    def test_factory_closure_independence(self) -> None:
        """Separate factory calls for containing and normalized_to produce independent closures."""
        pred_a = containing("abc")
        pred_b = containing("xyz")
        assert pred_a("", "abc") is True
        assert pred_b("", "abc") is False
        assert pred_a("", "xyz") is False
        assert pred_b("", "xyz") is True

        pred_upper = normalized_to(str.upper)
        pred_lower = normalized_to(str.lower)
        # "HELLO" upper-normalized == "HELLO" upper-normalized → True
        assert pred_upper("hello", "HELLO") is True
        # "HELLO" lower-normalized ("hello") != "HELLO" lower-normalized ("hello") → True
        assert pred_lower("HELLO", "hello") is True
        # "hello" upper ("HELLO") != "world" upper ("WORLD") → False
        assert pred_upper("hello", "world") is False


# ---------------------------------------------------------------------------
# idempotent_after  (NEW — predicate 7)
# ---------------------------------------------------------------------------

DES_BIN = "DES_BIN"


class TestIdempotentAfter:
    def test_positive_prefix_is_first_segment(self) -> None:
        """new already starts with prefix as first colon-separated segment."""
        pred = idempotent_after(DES_BIN)
        assert pred("anything", "DES_BIN:/usr/bin") is True

    def test_negative_prefix_not_first_segment(self) -> None:
        """new has a different first segment → predicate fails."""
        pred = idempotent_after(DES_BIN)
        assert pred("anything", "/usr/bin:/opt/bin") is False

    def test_negative_constant_true_guard(self) -> None:
        """Predicate must not be a constant lambda: True."""
        pred = idempotent_after(DES_BIN)
        assert pred("anything", "OTHER:/usr/bin") is False

    def test_custom_separator(self) -> None:
        pred = idempotent_after("pre", sep=";")
        assert pred("x", "pre;rest") is True
        assert pred("x", "rest;pre") is False

    def test_name_is_set(self) -> None:
        pred = idempotent_after(DES_BIN)
        assert "idempotent_after" in pred.__name__

    def test_closure_independence(self) -> None:
        pred_a = idempotent_after("A")
        pred_b = idempotent_after("B")
        assert pred_a("x", "A:rest") is True
        assert pred_b("x", "A:rest") is False
        assert pred_a("x", "B:rest") is False
        assert pred_b("x", "B:rest") is True


# ---------------------------------------------------------------------------
# legacy_healed  (NEW — predicate 8, D-11 paper-trace)
# ---------------------------------------------------------------------------

_LEGACY_FORM = "DES_BIN:SYSTEM_PATH_FALLBACK"


def _is_legacy(s: str) -> bool:
    return s == _LEGACY_FORM


def _is_healed(s: str) -> bool:
    return s != _LEGACY_FORM and s.startswith("DES_BIN:")


class TestLegacyHealed:
    def test_legacy_healed_case_1_legacy_to_healed_passes(self) -> None:
        """D-11 Case 1: detector(old)=True AND healed_check(new)=True → True."""
        pred = legacy_healed(_is_legacy, _is_healed)
        old = _LEGACY_FORM
        new = "DES_BIN:/usr/bin"
        assert pred(old, new) is True

    def test_legacy_healed_case_2_heal_failed_returns_false(self) -> None:
        """D-11 Case 2: detector(old)=True AND healed_check(new)=False → False."""
        pred = legacy_healed(_is_legacy, _is_healed)
        old = _LEGACY_FORM
        new = _LEGACY_FORM  # heal did not happen
        assert pred(old, new) is False

    def test_legacy_healed_case_3_non_legacy_short_circuits_to_false(self) -> None:
        """D-11 Case 3: detector(old)=False → False (short-circuit)."""
        pred = legacy_healed(_is_legacy, _is_healed)
        old = "/usr/bin"  # regular shape, not legacy form
        new = "DES_BIN:/usr/bin"
        assert pred(old, new) is False

    def test_legacy_healed_case_4_composition_with_prepended_with_via_lambda(
        self,
    ) -> None:
        """D-11 Case 4: user-side lambda dispatches to legacy_healed or prepended_with."""
        healed_pred = legacy_healed(_is_legacy, _is_healed)
        prepend_pred = prepended_with(DES_BIN)

        def composed(o: Any, n: Any) -> bool:
            return healed_pred(o, n) if _is_legacy(o) else prepend_pred(o, n)

        # Legacy input branch → routes to legacy_healed
        assert composed(_LEGACY_FORM, "DES_BIN:/usr/bin") is True  # healed
        assert composed(_LEGACY_FORM, _LEGACY_FORM) is False  # not healed

        # Non-legacy input branch → routes to prepended_with
        assert composed("/usr/bin", "DES_BIN:/usr/bin") is True  # prepend matched
        assert composed("/usr/bin", "/wrong") is False  # prepend not matched

    def test_legacy_healed_constant_true_guard(self) -> None:
        """Predicate must not be a constant lambda: True."""
        pred = legacy_healed(_is_legacy, _is_healed)
        # old is legacy but new is not healed
        assert pred(_LEGACY_FORM, "some_other_value") is False

    def test_legacy_healed_factory_closure_independence(self) -> None:
        """Two separate calls to legacy_healed produce independent closures."""

        def always_true(_: Any) -> bool:
            return True

        def always_false(_: Any) -> bool:
            return False

        pred_pass = legacy_healed(always_true, always_true)
        pred_fail = legacy_healed(always_true, always_false)

        assert pred_pass("x", "y") is True
        assert pred_fail("x", "y") is False
        # Verify pred_pass is unaffected by pred_fail's closure
        assert pred_pass("a", "b") is True
