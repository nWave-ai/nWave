"""
Unit tests for PhaseName canonical dispatch helpers (ADR-025, 2026-05-07).

Verifies:
- PhaseName.RED is a defined enum member alongside legacy members.
- is_canonical() returns True only for v5 canonical members (RED, GREEN, COMMIT).
- to_canonical() collapses legacy members onto their canonical equivalent:
    PREPARE / RED_ACCEPTANCE / RED_UNIT -> RED
    GREEN_UNIT / GREEN_ACCEPTANCE / CHECK_ACCEPTANCE -> GREEN
    REVIEW / REFACTOR_* / POST_REFACTOR_REVIEW / FINAL_VALIDATE -> COMMIT
"""

import pytest

from des.domain.value_objects import PhaseName


class TestCanonicalMembers:
    """v5 canonical PhaseName members exist."""

    def test_red_is_defined(self):
        """PhaseName.RED is a valid enum member."""
        assert PhaseName.RED == "RED"

    def test_green_is_defined(self):
        """PhaseName.GREEN remains defined for v5 canon."""
        assert PhaseName.GREEN == "GREEN"

    def test_commit_is_defined(self):
        """PhaseName.COMMIT remains defined for v5 canon."""
        assert PhaseName.COMMIT == "COMMIT"


class TestLegacyMembersPreserved:
    """All v4 legacy PhaseName members survive for audit-log replay."""

    @pytest.mark.parametrize(
        "phase_name",
        [
            "PREPARE",
            "RED_ACCEPTANCE",
            "RED_UNIT",
            "REVIEW",
            "REFACTOR_CONTINUOUS",
            "REFACTOR_L1",
            "REFACTOR_L2",
            "REFACTOR_L3",
            "REFACTOR_L4",
            "GREEN_UNIT",
            "GREEN_ACCEPTANCE",
            "CHECK_ACCEPTANCE",
            "POST_REFACTOR_REVIEW",
            "FINAL_VALIDATE",
        ],
    )
    def test_legacy_member_present(self, phase_name):
        """Each legacy member resolves to its string value."""
        member = PhaseName(phase_name)
        assert member.value == phase_name


class TestIsCanonical:
    """is_canonical() distinguishes v5 from v4-and-older."""

    @pytest.mark.parametrize(
        "canonical", [PhaseName.RED, PhaseName.GREEN, PhaseName.COMMIT]
    )
    def test_canonical_members_return_true(self, canonical):
        """RED, GREEN, COMMIT are canonical."""
        assert canonical.is_canonical() is True

    @pytest.mark.parametrize(
        "legacy",
        [
            PhaseName.PREPARE,
            PhaseName.RED_ACCEPTANCE,
            PhaseName.RED_UNIT,
            PhaseName.REVIEW,
            PhaseName.REFACTOR_CONTINUOUS,
            PhaseName.REFACTOR_L1,
            PhaseName.REFACTOR_L4,
            PhaseName.GREEN_UNIT,
            PhaseName.FINAL_VALIDATE,
            PhaseName.POST_REFACTOR_REVIEW,
        ],
    )
    def test_legacy_members_return_false(self, legacy):
        """Every legacy member is non-canonical."""
        assert legacy.is_canonical() is False


class TestToCanonical:
    """to_canonical() collapses legacy phases onto v5 canon."""

    @pytest.mark.parametrize(
        "legacy_phase",
        [PhaseName.PREPARE, PhaseName.RED_ACCEPTANCE, PhaseName.RED_UNIT],
    )
    def test_red_family_collapses_to_red(self, legacy_phase):
        """PREPARE, RED_ACCEPTANCE, RED_UNIT collapse into v5 RED."""
        assert legacy_phase.to_canonical() == PhaseName.RED

    @pytest.mark.parametrize(
        "legacy_phase",
        [
            PhaseName.GREEN_UNIT,
            PhaseName.GREEN_ACCEPTANCE,
            PhaseName.CHECK_ACCEPTANCE,
        ],
    )
    def test_green_family_collapses_to_green(self, legacy_phase):
        """GREEN_UNIT / GREEN_ACCEPTANCE / CHECK_ACCEPTANCE map to v5 GREEN."""
        assert legacy_phase.to_canonical() == PhaseName.GREEN

    @pytest.mark.parametrize(
        "legacy_phase",
        [
            PhaseName.REVIEW,
            PhaseName.REFACTOR_CONTINUOUS,
            PhaseName.REFACTOR_L1,
            PhaseName.REFACTOR_L2,
            PhaseName.REFACTOR_L3,
            PhaseName.REFACTOR_L4,
            PhaseName.POST_REFACTOR_REVIEW,
            PhaseName.FINAL_VALIDATE,
        ],
    )
    def test_review_refactor_family_collapses_to_commit(self, legacy_phase):
        """REVIEW + REFACTOR_* + POST_REFACTOR_REVIEW + FINAL_VALIDATE map to v5 COMMIT."""
        assert legacy_phase.to_canonical() == PhaseName.COMMIT

    @pytest.mark.parametrize(
        "canonical", [PhaseName.RED, PhaseName.GREEN, PhaseName.COMMIT]
    )
    def test_canonical_members_map_to_themselves(self, canonical):
        """Already-canonical members are idempotent under to_canonical()."""
        assert canonical.to_canonical() == canonical
