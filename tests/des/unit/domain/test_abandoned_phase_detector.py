"""
Unit Tests: AbandonedPhaseDetector

Tests for the AbandonedPhaseDetector domain service that identifies phases
left in IN_PROGRESS state (abandoned) and provides recovery mechanisms.

COVERAGE TARGET: 100% of AbandonedPhaseDetector functionality
"""

from datetime import datetime, timedelta, timezone

import pytest


class TestAbandonedPhaseDetector:
    """Unit tests for AbandonedPhaseDetector domain service."""

    # =========================================================================
    # Test 1: test_abandoned_phase_detector_exists
    # Verify the AbandonedPhaseDetector class can be instantiated
    # =========================================================================

    def test_abandoned_phase_detector_exists(self):
        """
        GIVEN AbandonedPhaseDetector domain service
        WHEN instantiated with no parameters
        THEN detector instance is created successfully

        Business Value: Foundation test - ensures detector exists and is callable
        """
        from des.domain.abandoned_phase_detector import AbandonedPhaseDetector

        detector = AbandonedPhaseDetector()
        assert detector is not None
        assert isinstance(detector, AbandonedPhaseDetector)

    # =========================================================================
    # Test 2: test_detects_not_executed_after_timeout
    # Verify detector identifies phases stuck in NOT_EXECUTED after timeout
    # =========================================================================

    def test_detects_not_executed_after_timeout(self):
        """
        GIVEN phase with status NOT_EXECUTED and started_at timestamp
        WHEN phase has remained NOT_EXECUTED beyond timeout threshold (default: 30 min)
        THEN detector returns True indicating phase is abandoned

        Business Value: Detects stalled phases that never started execution
        Timeout Threshold: 30 minutes (configurable)
        """
        from des.domain.abandoned_phase_detector import AbandonedPhaseDetector

        detector = AbandonedPhaseDetector()

        # Create phase that was started 35 minutes ago but never executed
        base_time = datetime.now(timezone.utc)
        started_at = (base_time - timedelta(minutes=35)).isoformat()

        phase_record = {
            "phase_name": "GREEN_UNIT",
            "status": "NOT_EXECUTED",
            "started_at": started_at,
            "ended_at": None,
            "turn_count": 0,  # No turns - nothing happened
        }

        # Detect abandoned phase
        is_abandoned = detector.is_abandoned(
            phase=phase_record,
            timeout_minutes=30,
            current_time=base_time,
        )

        assert is_abandoned is True, "Phase NOT_EXECUTED for 35 min should be abandoned"

    # =========================================================================
    # Test 3: test_detects_turn_count_stalled
    # Verify detector identifies phases with stalled turn count
    # =========================================================================

    def test_detects_turn_count_stalled(self):
        """
        GIVEN phase with turn_count that hasn't changed over extended time
        WHEN turn_count remains at initial value (0 or stale value) past threshold
        THEN detector identifies phase as abandoned due to stalled progress

        Business Value: Detects phases that started but made no progress
        Stalled Threshold: No turn count change for 20 minutes
        """
        from des.domain.abandoned_phase_detector import AbandonedPhaseDetector

        detector = AbandonedPhaseDetector()

        # Create phase that started 25 minutes ago but never progressed (turn_count=0)
        base_time = datetime.now(timezone.utc)
        started_at = (base_time - timedelta(minutes=25)).isoformat()

        phase_record = {
            "phase_name": "RED_UNIT",
            "status": "IN_PROGRESS",
            "started_at": started_at,
            "ended_at": None,
            "turn_count": 0,  # No progress made
        }

        # Detect abandoned phase with stalled progress
        is_abandoned = detector.is_abandoned_by_stalled_turn_count(
            phase=phase_record,
            stalled_threshold_minutes=20,
            current_time=base_time,
        )

        assert is_abandoned is True, (
            "Phase IN_PROGRESS for 25 min with no turn change should be abandoned"
        )

    # =========================================================================
    # Test 4: test_provides_recovery_message_for_abandoned
    # Verify detector generates recovery message for abandoned phases
    # =========================================================================

    def test_provides_recovery_message_for_abandoned(self):
        """
        GIVEN abandoned phase detected
        WHEN recovery message is generated
        THEN message includes:
             1. Phase name and position
             2. WHY abandoned (timeout or stalled)
             3. HOW to fix (reset status)
             4. ACTION (specific command)

        Business Value: Clear recovery guidance for junior developers
        """
        from des.domain.abandoned_phase_detector import AbandonedPhaseDetector

        detector = AbandonedPhaseDetector()

        phase_record = {
            "phase_name": "GREEN_UNIT",
            "status": "IN_PROGRESS",
            "started_at": (
                datetime.now(timezone.utc) - timedelta(minutes=35)
            ).isoformat(),
            "ended_at": None,
            "turn_count": 0,
        }

        # Generate recovery message
        message = detector.generate_recovery_message(
            phase=phase_record,
            reason="timeout",
            step_file_path="steps/02-01.json",
        )

        # Verify message contains required elements
        assert message is not None, "Should generate recovery message"
        assert isinstance(message, str), "Message should be string"
        assert "GREEN_UNIT" in message, "Should mention phase name"
        assert len(message) > 50, "Should have substantial guidance"

        # Verify guidance structure
        assert any(
            keyword in message.lower()
            for keyword in ["why", "how", "action", "reset", "not_executed"]
        ), "Should have guidance structure"

    # =========================================================================
    # Test 5: test_handles_missing_started_at_gracefully
    # Verify detector handles edge case: missing started_at timestamp
    # =========================================================================

    def test_handles_missing_started_at_gracefully(self):
        """
        GIVEN phase with status IN_PROGRESS but missing started_at timestamp
        WHEN detector checks for abandoned status
        THEN detector handles gracefully without crashing, returns reasonable result

        Business Value: Robust handling of malformed phase records
        Edge Case: Corrupted phase data
        """
        from des.domain.abandoned_phase_detector import AbandonedPhaseDetector

        detector = AbandonedPhaseDetector()

        # Phase with missing started_at
        phase_record = {
            "phase_name": "REVIEW",
            "status": "IN_PROGRESS",
            "started_at": None,  # Missing timestamp
            "ended_at": None,
            "turn_count": 0,
        }

        # Should handle gracefully without exception
        try:
            result = detector.is_abandoned(
                phase=phase_record,
                timeout_minutes=30,
                current_time=datetime.now(timezone.utc),
            )
            # With no started_at, cannot determine if abandoned, so default to safe value
            assert result is False or result is True, "Should return boolean"
        except Exception as e:
            pytest.fail(f"Should handle missing started_at gracefully: {e}")

    # =========================================================================
    # Test 6: test_distinguishes_abandoned_vs_pending
    # Verify detector correctly distinguishes abandoned from pending phases
    # =========================================================================

    def test_distinguishes_abandoned_vs_pending(self):
        """
        GIVEN two phases: one abandoned (>30 min), one pending (<5 min)
        WHEN detector checks both
        THEN abandoned phase returns True, pending phase returns False

        Business Value: Prevents false positives - don't report in-progress work as abandoned
        """
        from des.domain.abandoned_phase_detector import AbandonedPhaseDetector

        detector = AbandonedPhaseDetector()
        base_time = datetime.now(timezone.utc)

        # Abandoned phase: started 35 minutes ago
        abandoned_phase = {
            "phase_name": "GREEN_UNIT",
            "status": "IN_PROGRESS",
            "started_at": (base_time - timedelta(minutes=35)).isoformat(),
            "ended_at": None,
            "turn_count": 0,
        }

        # Pending phase: started 2 minutes ago (still working)
        pending_phase = {
            "phase_name": "RED_UNIT",
            "status": "IN_PROGRESS",
            "started_at": (base_time - timedelta(minutes=2)).isoformat(),
            "ended_at": None,
            "turn_count": 3,  # Making progress
        }

        is_abandoned = detector.is_abandoned(
            phase=abandoned_phase,
            timeout_minutes=30,
            current_time=base_time,
        )

        is_pending = detector.is_abandoned(
            phase=pending_phase,
            timeout_minutes=30,
            current_time=base_time,
        )

        assert is_abandoned is True, "Phase at 35 min should be abandoned"
        assert is_pending is False, "Phase at 2 min should still be pending"
