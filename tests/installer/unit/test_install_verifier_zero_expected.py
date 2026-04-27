"""Tests for install_nwave verifier — zero-expected predicate contract.

v3.12.1 install regression — Bugs #2 + #5 of 4. The verifier in
install_nwave._verify_deployment had inline expressions:

    script_ok = script_matched == script_expected and script_expected > 0
    tmpl_ok   = tmpl_matched   == tmpl_expected   and tmpl_expected   > 0

The `> 0` clauses turn the legitimate state "no work needed"
(matched == 0 AND expected == 0) into a hard fail. Cascade:
all_synced = False -> install validation fails.

Correct semantics: matched == expected IS the synced contract.
Emptiness is not failure; it is "nothing to do, nothing missing".

These tests lock the predicate contract via a small pure helper
`_component_synced(matched, expected) -> bool`. The helper is the
driving port for the predicate; calling it directly is port-to-port
at domain scope.
"""

import pytest

from scripts.install.install_nwave import _component_synced


class TestComponentSyncedPredicate:
    """The verifier's component-synced predicate must be pure equality.

    Contract: a component is synced iff matched == expected.
    Emptiness (0 == 0) is success, not failure.
    """

    def test_zero_expected_zero_matched_is_synced(self):
        """Given source has 0 files and target has 0 files,
        when the predicate evaluates,
        then the component is considered synced.

        This is THE bug being fixed: the previous `> 0` clause made
        this case False, breaking installations whose source layout
        legitimately yields zero files for a component.
        """
        assert _component_synced(matched=0, expected=0) is True

    def test_one_expected_one_matched_is_synced(self):
        """Sanity: the happy path 1 == 1 still passes.

        Regression guard against accidentally breaking the equality
        contract when removing the `> 0` clause.
        """
        assert _component_synced(matched=1, expected=1) is True

    def test_two_expected_two_matched_is_synced(self):
        """Sanity: the happy path 2 == 2 still passes (typical case
        for utility scripts where two files are expected)."""
        assert _component_synced(matched=2, expected=2) is True

    def test_two_expected_one_matched_is_not_synced(self):
        """Real mismatch: source has 2 files, target has only 1.
        The predicate must report not-synced.
        """
        assert _component_synced(matched=1, expected=2) is False

    def test_zero_expected_one_matched_is_not_synced(self):
        """Defensive: target has a file the source did not declare.
        The predicate must still report not-synced (matched != expected).
        """
        assert _component_synced(matched=1, expected=0) is False

    @pytest.mark.parametrize(
        "matched,expected,is_synced",
        [
            (0, 0, True),
            (1, 1, True),
            (5, 5, True),
            (0, 1, False),
            (1, 0, False),
            (1, 2, False),
            (2, 1, False),
        ],
    )
    def test_predicate_is_pure_equality(
        self, matched: int, expected: int, is_synced: bool
    ) -> None:
        """Property: _component_synced(m, e) is True iff m == e.

        The predicate is total equality on natural numbers. No edge
        case (including zero) deviates from this contract.
        """
        assert _component_synced(matched=matched, expected=expected) is is_synced
