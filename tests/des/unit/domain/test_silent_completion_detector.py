"""
Unit tests for SilentCompletionDetector domain service.

Tests the detection of silent completion scenarios where:
1. Phase execution completes without updating step file state
2. All phases remain NOT_EXECUTED despite task completion
3. Mismatches exist between status and outcome fields
4. Recovery guidance is generated for recovery

STEP: des-us005/02-02 - Detect silent completion failures
ACCEPTANCE CRITERIA:
- AC-005.1: Detects when all phases remain NOT_EXECUTED despite completion
- AC-005.1: Distinguishes from normal unstarted state
- AC-005.1: Generates 3+ recovery suggestions
- AC-005.1: Includes transcript path in suggestions
- AC-005.1: Explains OUTCOME_RECORDING requirement
"""

from des.domain.silent_completion_detector import SilentCompletionDetector


class TestDetectAllPhasesNotExecuted:
    """Test detection of all phases remaining NOT_EXECUTED."""

    def test_detect_all_phases_not_executed_with_completion_set(self):
        """
        GIVEN phase_execution_log with all phases in NOT_EXECUTED status
        AND task state shows completed_at is set (task finished)
        WHEN is_silent_completion is called
        THEN returns True (silent completion detected)

        Business Language:
        "When all phases remain NOT_EXECUTED but the task has finished,
        the agent completed silently without updating any phase status."
        """
        # Arrange
        detector = SilentCompletionDetector()

        phase_log = [
            {"phase_name": "PREPARE", "status": "NOT_EXECUTED"},
            {"phase_name": "RED_ACCEPTANCE", "status": "NOT_EXECUTED"},
            {"phase_name": "RED_UNIT", "status": "NOT_EXECUTED"},
            {"phase_name": "GREEN", "status": "NOT_EXECUTED"},
            {"phase_name": "REVIEW", "status": "NOT_EXECUTED"},
            {"phase_name": "REFACTOR_CONTINUOUS", "status": "NOT_EXECUTED"},
            {"phase_name": "REFACTOR_L4", "status": "NOT_EXECUTED"},
            {"phase_name": "COMMIT", "status": "NOT_EXECUTED"},
        ]

        task_state = {
            "status": "IN_PROGRESS",
            "started_at": "2026-01-28T10:00:00Z",
            "completed_at": "2026-01-28T10:15:00Z",  # Task finished but no phases completed
        }

        # Act
        is_silent = detector.is_silent_completion(phase_log, task_state)

        # Assert
        assert is_silent is True, (
            "Should detect all phases NOT_EXECUTED as silent completion"
        )


class TestDistinguishSilentCompletionFromNormalUnstarted:
    """Test distinguishing silent completion from normal unstarted state."""

    def test_distinguish_silent_completion_from_normal_unstarted(self):
        """
        GIVEN phase_execution_log with all phases in NOT_EXECUTED status
        WHEN checking different task states
        THEN silent completion is detected only when task has completed_at set
        AND normal unstarted state is when task is PENDING or NOT_STARTED

        Business Language:
        "Silent completion is different from a normal unstarted task.
        A normal task hasn't started yet. A silent completion has finished
        but left no trace of work in the phase log."
        """
        # Arrange
        detector = SilentCompletionDetector()

        phase_log = [
            {"phase_name": "PREPARE", "status": "NOT_EXECUTED"},
            {"phase_name": "RED_ACCEPTANCE", "status": "NOT_EXECUTED"},
        ]

        # Act & Assert: Normal unstarted state (not silent completion)
        task_state_unstarted = {
            "status": "PENDING",
            "started_at": None,
            "completed_at": None,
        }
        is_silent = detector.is_silent_completion(phase_log, task_state_unstarted)
        assert is_silent is False, (
            "Normal unstarted task should NOT be detected as silent completion"
        )

        # Act & Assert: Silent completion state (task ran but no updates)
        task_state_completed = {
            "status": "IN_PROGRESS",
            "started_at": "2026-01-28T10:00:00Z",
            "completed_at": "2026-01-28T10:15:00Z",
        }
        is_silent = detector.is_silent_completion(phase_log, task_state_completed)
        assert is_silent is True, (
            "Task with completed_at but all phases NOT_EXECUTED should be silent completion"
        )


class TestGenerate3OrMoreSilentCompletionSuggestions:
    """Test generation of 3+ recovery suggestions for silent completion."""

    def test_generate_3_or_more_silent_completion_suggestions(self):
        """
        GIVEN silent completion detected (all phases NOT_EXECUTED, task completed)
        WHEN generate_recovery_suggestions is called
        THEN returns list with 3 or more actionable suggestions

        Business Language:
        "Recovery suggestions help developers understand what went wrong and how to fix it.
        We provide multiple perspectives to help them learn from the failure."
        """
        # Arrange
        detector = SilentCompletionDetector()

        phase_log = [
            {"phase_name": "PREPARE", "status": "NOT_EXECUTED"},
            {"phase_name": "RED_ACCEPTANCE", "status": "NOT_EXECUTED"},
            {"phase_name": "RED_UNIT", "status": "NOT_EXECUTED"},
        ]

        task_state = {
            "status": "IN_PROGRESS",
            "completed_at": "2026-01-28T10:15:00Z",
        }

        # Act
        suggestions = detector.generate_recovery_suggestions(phase_log, task_state)

        # Assert
        assert suggestions is not None, "Should generate suggestions"
        assert isinstance(suggestions, list), "Suggestions should be list"
        assert len(suggestions) >= 3, (
            f"Should have 3+ suggestions, got {len(suggestions)}: {suggestions}"
        )


class TestSilentCompletionSuggestionsIncludeTranscriptPath:
    """Test that recovery suggestions include transcript path."""

    def test_silent_completion_suggestions_include_transcript_path(self):
        """
        GIVEN silent completion detected
        WHEN generate_recovery_suggestions is called with transcript_path context
        THEN suggestions include specific path to transcript for debugging

        Business Language:
        "The transcript shows what the agent was doing. Recovery suggestions
        tell developers exactly where to find the transcript to debug the issue."

        AC-005.3: Suggestions are actionable (specific commands or file paths)
        """
        # Arrange
        detector = SilentCompletionDetector()

        phase_log = [
            {"phase_name": "PREPARE", "status": "NOT_EXECUTED"},
        ]

        task_state = {
            "status": "IN_PROGRESS",
            "completed_at": "2026-01-28T10:15:00Z",
        }

        transcript_path = "/tmp/agent-transcripts/session-12345.log"

        # Act
        suggestions = detector.generate_recovery_suggestions(
            phase_log,
            task_state,
            transcript_path=transcript_path,
        )

        # Assert
        assert any(transcript_path in s for s in suggestions), (
            f"Suggestions should include transcript path: {transcript_path}"
        )


class TestSilentCompletionExplainsOutcomeRecordingRequirement:
    """Test that recovery suggestions explain OUTCOME_RECORDING requirement."""

    def test_silent_completion_explains_outcome_recording_requirement(self):
        """
        GIVEN silent completion detected
        WHEN generate_recovery_suggestions is called
        THEN at least one suggestion explains OUTCOME_RECORDING requirement

        Business Language:
        "OUTCOME_RECORDING is how the agent tells the system what it completed.
        If OUTCOME_RECORDING is missing from the prompt, the agent has no way
        to update the step file. Recovery guidance explains this requirement."

        AC-005.5: Recovery suggestions include explanatory text (WHY and HOW)
        """
        # Arrange
        detector = SilentCompletionDetector()

        phase_log = [
            {"phase_name": "PREPARE", "status": "NOT_EXECUTED"},
        ]

        task_state = {
            "status": "IN_PROGRESS",
            "completed_at": "2026-01-28T10:15:00Z",
        }

        # Act
        suggestions = detector.generate_recovery_suggestions(phase_log, task_state)

        # Assert
        assert any("OUTCOME_RECORDING" in s for s in suggestions), (
            "Suggestions should explain OUTCOME_RECORDING requirement"
        )


class TestDetectMissingOutcomeField:
    """Test detection of phases marked EXECUTED without outcome field."""

    def test_detects_missing_outcome_field(self):
        """
        GIVEN phase marked EXECUTED but outcome field is None
        WHEN detect_missing_outcomes is called
        THEN returns list including that phase

        Business Language:
        "A phase marked EXECUTED should say what it accomplished.
        If outcome is missing, we don't know what work was actually completed."

        AC-005.1: Identifies phases that report EXECUTED but have no outcome
        """
        # Arrange
        detector = SilentCompletionDetector()

        phase_log = [
            {
                "phase_name": "PREPARE",
                "status": "EXECUTED",
                "outcome": "Environment set up",
            },
            {
                "phase_name": "RED_ACCEPTANCE",
                "status": "EXECUTED",
                "outcome": None,
            },  # Missing outcome
            {"phase_name": "RED_UNIT", "status": "NOT_EXECUTED", "outcome": None},
        ]

        # Act
        missing_outcome_phases = detector.detect_missing_outcomes(phase_log)

        # Assert
        assert "RED_ACCEPTANCE" in missing_outcome_phases, (
            "Should detect RED_ACCEPTANCE as missing outcome"
        )
        assert "PREPARE" not in missing_outcome_phases, (
            "Should not include PREPARE (has outcome)"
        )
        assert "RED_UNIT" not in missing_outcome_phases, (
            "Should not include RED_UNIT (status is NOT_EXECUTED)"
        )


class TestDetectStatusOutcomeMismatch:
    """Test detection of status/outcome field mismatches."""

    def test_detects_status_mismatch(self):
        """
        GIVEN phase with status/outcome mismatch (e.g., status=FAIL but outcome=PASS)
        WHEN detect_status_mismatches is called
        THEN returns list including that phase with mismatch details

        Business Language:
        "Phase status (EXECUTED, FAILED, SKIPPED) should match what outcome describes.
        If they mismatch, it's unclear whether the phase actually succeeded or failed."

        AC-005.1: Detects status/outcome mismatches
        """
        # Arrange
        detector = SilentCompletionDetector()

        phase_log = [
            {
                "phase_name": "RED_ACCEPTANCE",
                "status": "EXECUTED",
                "outcome": "Test suite failed",  # Mismatch: says EXECUTED but outcome describes FAILED
            },
            {
                "phase_name": "GREEN",
                "status": "EXECUTED",
                "outcome": "All tests passing",  # Match: status and outcome align
            },
        ]

        # Act
        mismatches = detector.detect_status_mismatches(phase_log)

        # Assert
        assert len(mismatches) >= 1, (
            f"Should detect at least 1 mismatch, found {mismatches}"
        )
        assert any(m["phase_name"] == "RED_ACCEPTANCE" for m in mismatches), (
            "Should include RED_ACCEPTANCE mismatch"
        )


class TestProvidesRecoveryGuidance:
    """Test that detector provides recovery guidance for silent completion."""

    def test_provides_recovery_guidance(self):
        """
        GIVEN silent completion detected
        WHEN get_recovery_guidance is called
        THEN returns structured guidance with WHY/HOW/ACTION format

        Business Language:
        "Recovery guidance helps junior developers understand:
        - WHY the error occurred (educational context)
        - HOW the fix resolves the issue (mechanism)
        - ACTION they should take (specific commands/steps)"

        AC-005.5: Recovery suggestions include explanatory text
        """
        # Arrange
        detector = SilentCompletionDetector()

        phase_log = [
            {"phase_name": "PREPARE", "status": "NOT_EXECUTED"},
        ]

        task_state = {
            "status": "IN_PROGRESS",
            "completed_at": "2026-01-28T10:15:00Z",
        }

        # Act
        guidance = detector.get_recovery_guidance(phase_log, task_state)

        # Assert
        assert guidance is not None, "Should return recovery guidance"
        assert "WHY" in guidance, "Guidance should include WHY explanation"
        assert "HOW" in guidance, "Guidance should include HOW explanation"
        assert "ACTION" in guidance, "Guidance should include ACTION"


class TestHandlesPartialPhaseLog:
    """Test that detector handles partial/incomplete phase logs."""

    def test_handles_partial_phase_log(self):
        """
        GIVEN phase_execution_log with fewer than expected phases
        WHEN is_silent_completion is called
        THEN correctly identifies as silent completion if all present phases are NOT_EXECUTED

        Business Language:
        "Some steps might have been split into smaller phases. The detector should
        work regardless of how many phases are in the log."
        """
        # Arrange
        detector = SilentCompletionDetector()

        # Partial phase log (fewer phases than normal)
        phase_log = [
            {"phase_name": "PREPARE", "status": "NOT_EXECUTED"},
            {"phase_name": "RED_ACCEPTANCE", "status": "NOT_EXECUTED"},
        ]

        task_state = {
            "status": "IN_PROGRESS",
            "completed_at": "2026-01-28T10:15:00Z",
        }

        # Act
        is_silent = detector.is_silent_completion(phase_log, task_state)

        # Assert
        assert is_silent is True, (
            "Should detect silent completion with partial phase log"
        )


class TestDistinguishRealVsFalsePositives:
    """Test distinguishing real silent completions from false positives."""

    def test_distinguishes_real_vs_false_positives(self):
        """
        GIVEN various phase log and task state combinations
        WHEN is_silent_completion is called
        THEN correctly identifies real silent completions vs false positives

        Business Language:
        "We need to be careful not to flag normal tasks as failures.
        A real silent completion is when the agent finished work but didn't update anything.
        A false positive would be a task that's still running or hasn't started yet."

        AC-005.1: Distinguishes from normal unstarted state
        """
        # Arrange
        detector = SilentCompletionDetector()

        # Test case 1: Real silent completion (task finished, no updates)
        phase_log_silent = [
            {"phase_name": "PREPARE", "status": "NOT_EXECUTED"},
        ]
        task_state_silent = {
            "status": "IN_PROGRESS",
            "started_at": "2026-01-28T10:00:00Z",
            "completed_at": "2026-01-28T10:15:00Z",
        }

        # Test case 2: False positive - task in progress (still running)
        task_state_running = {
            "status": "IN_PROGRESS",
            "started_at": "2026-01-28T10:00:00Z",
            "completed_at": None,
        }

        # Test case 3: False positive - at least one phase executed
        phase_log_partial_progress = [
            {"phase_name": "PREPARE", "status": "EXECUTED"},
            {"phase_name": "RED_ACCEPTANCE", "status": "NOT_EXECUTED"},
        ]
        task_state_with_progress = {
            "status": "IN_PROGRESS",
            "started_at": "2026-01-28T10:00:00Z",
            "completed_at": "2026-01-28T10:15:00Z",
        }

        # Act & Assert
        assert (
            detector.is_silent_completion(phase_log_silent, task_state_silent) is True
        ), "Should detect real silent completion"

        assert (
            detector.is_silent_completion(phase_log_silent, task_state_running) is False
        ), "Should NOT flag running task as silent completion (false positive)"

        assert (
            detector.is_silent_completion(
                phase_log_partial_progress, task_state_with_progress
            )
            is False
        ), (
            "Should NOT flag task with at least one EXECUTED phase as silent completion (false positive)"
        )
