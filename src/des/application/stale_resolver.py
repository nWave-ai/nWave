"""
StaleResolver Application Service

LAYER: Application Layer (Hexagonal Architecture)

BUSINESS PURPOSE:
Marks stale step executions as ABANDONED, updating the step file with:
- State status set to ABANDONED
- Failure reason describing what happened
- Recovery suggestions for next steps
- Abandoned timestamp for audit trail
- Phase status updated to ABANDONED for the stuck phase

CONFIGURATION:
- None required (stateless service)

DEPENDENCIES:
- Infrastructure: File system (JSON file reading/writing)

USAGE:
    resolver = StaleResolver(project_root=Path("/path/to/project"))
    resolver.mark_abandoned(
        step_file="steps/01-01.json",
        reason="Agent crashed during RED_ACCEPTANCE phase"
    )
"""

import json
from datetime import datetime, timezone
from pathlib import Path


class StaleResolver:
    """
    Application service for resolving stale step executions.

    Marks steps as ABANDONED when they cannot be recovered, updating the
    step file with failure reason, recovery suggestions, and timestamps.

    Attributes:
        project_root: Path to project root directory
    """

    def __init__(self, project_root: Path):
        """
        Initialize StaleResolver with project root.

        Args:
            project_root: Path to project root directory (string or Path)
        """
        self.project_root = Path(project_root)

    def mark_abandoned(self, step_file: str, reason: str) -> None:
        """
        Mark a stale step as ABANDONED with recovery suggestions.

        Updates the step file with:
        - state.status = "ABANDONED"
        - state.failure_reason = reason
        - state.recovery_suggestions = list of actionable steps
        - state.abandoned_at = ISO timestamp
        - Updates IN_PROGRESS phase status to ABANDONED

        Args:
            step_file: Relative path to step file (e.g., "steps/01-01.json")
            reason: Description of why the step was abandoned

        Raises:
            FileNotFoundError: If step file doesn't exist
            json.JSONDecodeError: If step file contains invalid JSON
        """
        step_path = self.project_root / step_file

        # Load step data
        if not step_path.exists():
            raise FileNotFoundError(f"Step file not found: {step_path}")

        step_data = json.loads(step_path.read_text())

        # Update state
        step_data["state"]["status"] = "ABANDONED"
        step_data["state"]["failure_reason"] = reason
        step_data["state"]["recovery_suggestions"] = (
            self._generate_recovery_suggestions(reason)
        )
        step_data["state"]["abandoned_at"] = datetime.now(timezone.utc).isoformat()

        # Update IN_PROGRESS phase to ABANDONED
        if "tdd_cycle" in step_data and "phase_execution_log" in step_data["tdd_cycle"]:
            for phase in step_data["tdd_cycle"]["phase_execution_log"]:
                if phase.get("status") == "IN_PROGRESS":
                    phase["status"] = "ABANDONED"

        # Save updated step data
        step_path.write_text(json.dumps(step_data, indent=2))

    def _generate_recovery_suggestions(self, reason: str) -> list[str]:
        """
        Generate actionable recovery suggestions based on failure reason.

        Args:
            reason: Failure reason description

        Returns:
            List of recovery suggestions
        """
        suggestions = [
            "Review conversation transcript to understand what went wrong",
            "Reset the failed phase and retry with manual intervention",
            "Check for any partial changes that need to be rolled back",
            "Verify all dependencies and prerequisites are met before retrying",
        ]

        # Add context-specific suggestions based on reason
        if "crash" in reason.lower() or "timeout" in reason.lower():
            suggestions.insert(
                1, "Check system resources and connectivity before retry"
            )

        if "test" in reason.lower():
            suggestions.insert(1, "Review test failures and fix underlying issues")

        return suggestions
