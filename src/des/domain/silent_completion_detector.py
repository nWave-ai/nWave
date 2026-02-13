"""
SilentCompletionDetector: Domain service for detecting silent completion failures.

A silent completion occurs when:
1. Task execution finishes (completed_at is set)
2. All phases remain NOT_EXECUTED (no phase updates recorded)
3. Agent returns without updating any phase status

This detector identifies such scenarios and provides recovery guidance following
the WHY/HOW/ACTION pattern for junior developer education.

DOMAIN LANGUAGE:
- Silent Completion: Agent returned without updating any phase status
- Status Mismatch: Phase status contradicts its outcome description
- Missing Outcome: Phase marked EXECUTED without describing what was done
- Recovery Guidance: WHY/HOW/ACTION structured recovery instructions
"""

from typing import Any


class SilentCompletionDetector:
    """
    Detects and reports silent completion failures.

    A silent completion is when:
    - Task has completed_at timestamp set (agent finished)
    - All phases remain NOT_EXECUTED (no progress recorded)
    - Mismatch between task state and phase state

    Provides recovery suggestions following WHY/HOW/ACTION pattern.
    """

    def is_silent_completion(
        self,
        phase_execution_log: list[dict[str, Any]],
        task_state: dict[str, Any],
    ) -> bool:
        """
        Check if a task exhibits silent completion failure pattern.

        Silent completion occurs when:
        - Task has completed_at set (task finished)
        - All phases remain NOT_EXECUTED (no updates recorded)
        - Indicates agent ran but made no progress

        Args:
            phase_execution_log: List of phase execution records from step file
            task_state: Task state dict with status, completed_at, etc.

        Returns:
            True if silent completion detected, False otherwise

        Business Language:
        "When a task is finished but all phases are still NOT_EXECUTED,
        the agent completed silently without updating the step file."
        """
        # Check if task has completed_at set (task finished)
        completed_at = task_state.get("completed_at")
        if completed_at is None:
            return False

        # Check if all phases are NOT_EXECUTED (no phase updates were recorded)
        all_phases_untouched = all(
            phase.get("status") == "NOT_EXECUTED" for phase in phase_execution_log
        )

        return all_phases_untouched

    def detect_missing_outcomes(
        self,
        phase_execution_log: list[dict[str, Any]],
    ) -> list[str]:
        """
        Detect phases marked EXECUTED but missing outcome field.

        Args:
            phase_execution_log: List of phase execution records

        Returns:
            List of phase names with EXECUTED status but no outcome

        Business Language:
        "A phase marked EXECUTED should describe what work was completed.
        If outcome is missing, we don't have a record of what the phase did."
        """
        missing = []

        for phase in phase_execution_log:
            status = phase.get("status")
            outcome = phase.get("outcome")

            # EXECUTED status requires non-empty outcome
            if status == "EXECUTED" and not outcome:
                phase_name = phase.get("phase_name", "UNKNOWN")
                missing.append(phase_name)

        return missing

    def detect_status_mismatches(
        self,
        phase_execution_log: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Detect phases where status contradicts outcome description.

        Args:
            phase_execution_log: List of phase execution records

        Returns:
            List of dicts with phase_name, status, outcome, and mismatch details

        Business Language:
        "Phase status should match what the outcome describes.
        If status says EXECUTED but outcome describes a failure, something is wrong."
        """
        mismatches = []

        for phase in phase_execution_log:
            status = phase.get("status")
            outcome = phase.get("outcome", "")
            phase_name = phase.get("phase_name", "UNKNOWN")

            if not outcome or status == "NOT_EXECUTED":
                continue

            # Check for contradictions between status and outcome
            outcome_lower = outcome.lower()

            # Status says EXECUTED but outcome describes failure/error
            if status == "EXECUTED":
                failure_indicators = [
                    "failed",
                    "error",
                    "crashed",
                    "broken",
                    "did not pass",
                    "not working",
                ]
                if any(indicator in outcome_lower for indicator in failure_indicators):
                    mismatches.append(
                        {
                            "phase_name": phase_name,
                            "status": status,
                            "outcome": outcome,
                            "mismatch_type": "status_outcome_contradiction",
                        }
                    )

        return mismatches

    def generate_recovery_suggestions(
        self,
        phase_execution_log: list[dict[str, Any]],
        task_state: dict[str, Any],
        transcript_path: str = "/path/to/transcript.log",
    ) -> list[str]:
        """
        Generate recovery suggestions for silent completion failure.

        Args:
            phase_execution_log: List of phase execution records
            task_state: Task state dictionary
            transcript_path: Path to agent transcript (default: generic path)

        Returns:
            List of 3+ recovery suggestions with actionable guidance

        Business Language:
        "Recovery suggestions help developers understand what went wrong
        and provide specific steps to recover from the failure."
        """
        suggestions = []

        # Suggestion 1: Review transcript (WHY explanation)
        suggestions.append(
            f"WHY: Your agent completed but didn't update any phase status in the step file. "
            f"This typically means the agent either encountered an error early or finished before "
            f"reaching the OUTCOME_RECORDING section.\n\n"
            f"HOW: Check the agent transcript to see what the agent was doing when it stopped. "
            f"The transcript will show any errors or where execution halted.\n\n"
            f"ACTION: Review {transcript_path} for error messages or early exit indication."
        )

        # Suggestion 2: OUTCOME_RECORDING requirement (HOW explanation)
        suggestions.append(
            "WHY: The system doesn't know what phases were completed if the agent doesn't update them. "
            "This is critical for tracking progress and resuming from the right place.\n\n"
            "HOW: Your prompt must include an OUTCOME_RECORDING section with clear instructions "
            "to update the step file after each phase completes.\n\n"
            "ACTION: Verify your prompt template includes OUTCOME_RECORDING section with "
            "instructions to update phase_execution_log status and outcome fields."
        )

        # Suggestion 3: Manual update process (ACTION-focused)
        suggestions.append(
            f"WHY: Without phase updates, you have no record of what work was done and cannot see progress. "
            f"This blocks the execution system from continuing to the next phase.\n\n"
            f"HOW: You can manually update the phase status based on what you find in the transcript. "
            f"Match each completed phase to its actual outcome (EXECUTED, FAILED, SKIPPED, etc.).\n\n"
            f"ACTION: Based on {transcript_path}, manually set each completed phase's status and outcome "
            f"in the step file, then retry execution with `/nw:execute`."
        )

        return suggestions

    def get_recovery_guidance(
        self,
        phase_execution_log: list[dict[str, Any]],
        task_state: dict[str, Any],
        transcript_path: str = "/path/to/transcript.log",
    ) -> str:
        """
        Get formatted recovery guidance for silent completion.

        Combines multiple suggestions into coherent guidance.

        Args:
            phase_execution_log: List of phase execution records
            task_state: Task state dictionary
            transcript_path: Path to agent transcript

        Returns:
            Single formatted guidance string with WHY/HOW/ACTION structure
        """
        phase_count = len(phase_execution_log)

        guidance = (
            f"SILENT COMPLETION DETECTED: Agent finished but didn't update the step file "
            f"({phase_count} phases still NOT_EXECUTED).\n\n"
            f"WHY THIS HAPPENED:\n"
            f"Your agent completed execution but made no updates to the phase_execution_log. "
            f"This typically indicates either:\n"
            f"1. Agent encountered an early error and couldn't proceed to OUTCOME_RECORDING\n"
            f"2. Agent completed work but OUTCOME_RECORDING section was missing from your prompt\n"
            f"3. Agent crashed or timed out before reaching the status update phase\n\n"
            f"HOW TO FIX:\n"
            f"1. Review the agent transcript ({transcript_path}) to understand what happened\n"
            f"2. Check if your prompt includes OUTCOME_RECORDING section with clear update instructions\n"
            f"3. Manually update phase statuses based on transcript evidence\n"
            f"4. If transcript shows errors, fix them and retry execution\n\n"
            f"ACTION STEPS:\n"
            f"Step 1: `cat {transcript_path}` - Review agent execution history\n"
            f"Step 2: For each completed phase, update the step file with status and outcome\n"
            f"Step 3: Run `/nw:execute` again to continue from the first incomplete phase\n"
            f"Step 4: Add OUTCOME_RECORDING section to your prompt template to prevent recurrence"
        )

        return guidance
