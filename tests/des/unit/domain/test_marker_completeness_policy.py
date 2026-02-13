"""Unit tests for Marker Completeness Policy.

Tests that DES markers are complete when DES-VALIDATION is present:
- Non-DES tasks always valid
- DES task with both IDs valid
- DES task missing project_id invalid
- DES task missing step_id invalid
- DES task missing both IDs invalid
- Orchestrator mode: step_id optional
"""

import pytest

from des.domain.des_marker_parser import DesMarkers
from des.domain.marker_completeness_policy import (
    MarkerCompletenessPolicy,
)


class TestMarkerCompletenessPolicy:
    """Unit tests for MarkerCompletenessPolicy."""

    @pytest.fixture
    def policy(self):
        return MarkerCompletenessPolicy()

    def test_non_des_task_always_valid(self, policy):
        """Non-DES task (is_des_task=False) should always be valid."""
        markers = DesMarkers(is_des_task=False, is_orchestrator_mode=False)
        result = policy.validate(markers)
        assert result.is_valid is True

    def test_des_task_with_both_ids_valid(self, policy):
        """DES task with both project_id and step_id should be valid."""
        markers = DesMarkers(
            is_des_task=True,
            is_orchestrator_mode=False,
            project_id="auth-upgrade",
            step_id="01-01",
        )
        result = policy.validate(markers)
        assert result.is_valid is True

    def test_des_task_missing_project_id(self, policy):
        """DES task without project_id should be invalid."""
        markers = DesMarkers(
            is_des_task=True,
            is_orchestrator_mode=False,
            project_id=None,
            step_id="01-01",
        )
        result = policy.validate(markers)
        assert result.is_valid is False
        assert "DES-PROJECT-ID" in (result.reason or "")

    def test_des_task_missing_step_id(self, policy):
        """DES task without step_id should be invalid."""
        markers = DesMarkers(
            is_des_task=True,
            is_orchestrator_mode=False,
            project_id="auth-upgrade",
            step_id=None,
        )
        result = policy.validate(markers)
        assert result.is_valid is False
        assert "DES-STEP-ID" in (result.reason or "")

    def test_des_task_missing_both_ids(self, policy):
        """DES task with both IDs missing should list both in reason."""
        markers = DesMarkers(
            is_des_task=True,
            is_orchestrator_mode=False,
            project_id=None,
            step_id=None,
        )
        result = policy.validate(markers)
        assert result.is_valid is False
        assert "DES-PROJECT-ID" in (result.reason or "")
        assert "DES-STEP-ID" in (result.reason or "")

    def test_orchestrator_mode_step_id_optional(self, policy):
        """Orchestrator mode with project_id but no step_id should be valid."""
        markers = DesMarkers(
            is_des_task=True,
            is_orchestrator_mode=True,
            project_id="auth-upgrade",
            step_id=None,
        )
        result = policy.validate(markers)
        assert result.is_valid is True
