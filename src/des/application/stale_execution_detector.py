"""
StaleExecutionDetector Application Service

LAYER: Application Layer (Hexagonal Architecture)

BUSINESS PURPOSE:
Scans the steps directory for IN_PROGRESS phases that exceed a configurable
staleness threshold, returning a StaleDetectionResult.

CONFIGURATION:
- Default threshold: 30 minutes
- Environment variable: DES_STALE_THRESHOLD_MINUTES

DEPENDENCIES:
- Domain: StaleExecution (value object)
- Domain: StaleDetectionResult (entity)
- Infrastructure: File system (pure file scanning, no DB/HTTP)

USAGE:
    detector = StaleExecutionDetector(project_root=Path("/path/to/project"))
    result = detector.scan_for_stale_executions()

    if result.is_blocked:
        print(result.alert_message)
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from des.domain.stale_detection_result import StaleDetectionResult
from des.domain.stale_execution import StaleExecution


class StaleExecutionDetector:
    """
    Application service for detecting stale executions in steps directory.

    Scans all .json files in steps/ directory, identifies IN_PROGRESS phases,
    and flags those exceeding the staleness threshold.

    Attributes:
        project_root: Path to project root directory
        threshold_minutes: Staleness threshold in minutes (default 30)
        uses_external_services: False (pure file scanning, no DB/HTTP)
        is_session_scoped: True (no daemon, terminates with session)
    """

    def __init__(self, project_root: Path):
        """
        Initialize StaleExecutionDetector with project root.

        Args:
            project_root: Path to project root directory

        Configuration:
            Reads DES_STALE_THRESHOLD_MINUTES environment variable.
            Defaults to 30 minutes if not set or invalid.
            Validates that threshold is a positive integer.
        """
        self.project_root = Path(project_root)

        # Read and validate threshold from environment variable
        env_value = os.environ.get("DES_STALE_THRESHOLD_MINUTES", "30")
        try:
            threshold = int(env_value)
            # Validate positive threshold
            if threshold <= 0:
                threshold = 30
        except ValueError:
            # Fall back to default on parsing error
            threshold = 30

        self.threshold_minutes = threshold

        # Metadata properties documenting zero external dependencies
        self.uses_external_services = False  # Pure file scanning (no DB/HTTP)
        self.is_session_scoped = True  # No daemon, terminates with session

    def scan_for_stale_executions(self) -> StaleDetectionResult:
        """
        Scan steps directory for stale IN_PROGRESS phases.

        Returns:
            StaleDetectionResult with list of detected stale executions

        Business Logic:
            1. Find all .json files in steps/ directory
            2. For each file, load JSON and check for IN_PROGRESS phases
            3. Calculate age of each IN_PROGRESS phase
            4. Flag phases exceeding threshold as stale
            5. Return StaleDetectionResult with aggregated results

        Error Handling:
            - Missing steps directory: returns empty result
            - Corrupted JSON files: skips file, continues scan
            - Missing fields: skips phase, continues scan
        """
        stale_executions = []
        warnings = []

        steps_dir = self.project_root / "steps"

        # Handle missing steps directory gracefully
        if not steps_dir.exists():
            return StaleDetectionResult(stale_executions=[], warnings=[])

        # Scan all .json files in steps directory
        for step_file in steps_dir.glob("*.json"):
            try:
                stale_execution = self._check_step_file_for_staleness(step_file)
                if stale_execution:
                    stale_executions.append(stale_execution)
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                # Collect warning for corrupted or malformed file
                relative_path = f"steps/{step_file.name}"
                warnings.append({"file_path": relative_path, "error": str(e)})
                continue

        return StaleDetectionResult(
            stale_executions=stale_executions, warnings=warnings
        )

    def _check_step_file_for_staleness(self, step_file: Path) -> StaleExecution | None:
        """
        Check a single step file for stale IN_PROGRESS phases.

        Args:
            step_file: Path to step file to check

        Returns:
            StaleExecution if stale phase found, None otherwise

        Raises:
            json.JSONDecodeError: If file contains invalid JSON
            KeyError: If required fields are missing
            ValueError: If timestamp parsing fails
        """
        step_data = json.loads(step_file.read_text())

        # Only check IN_PROGRESS steps
        if step_data.get("state", {}).get("status") != "IN_PROGRESS":
            return None

        # Check for tdd_cycle field
        tdd_cycle = step_data.get("tdd_cycle")
        if not tdd_cycle:
            return None

        # Find IN_PROGRESS phase in phase_execution_log
        phase_execution_log = tdd_cycle.get("phase_execution_log", [])

        for phase in phase_execution_log:
            if phase.get("status") == "IN_PROGRESS":
                started_at = phase.get("started_at")
                if not started_at:
                    # Skip phases missing started_at timestamp
                    continue

                age_minutes = self._calculate_age_minutes(started_at)

                if age_minutes > self.threshold_minutes:
                    # Stale phase found - return StaleExecution
                    relative_path = f"steps/{step_file.name}"
                    return StaleExecution(
                        step_file=relative_path,
                        phase_name=phase.get("phase_name", "UNKNOWN"),
                        age_minutes=age_minutes,
                        started_at=started_at,
                    )

        return None

    def _calculate_age_minutes(self, started_at: str) -> int:
        """
        Calculate age in minutes from ISO 8601 timestamp to now.

        Args:
            started_at: ISO 8601 timestamp string

        Returns:
            Age in minutes (integer)

        Raises:
            ValueError: If timestamp cannot be parsed
        """
        # Parse ISO 8601 timestamp
        started_datetime = datetime.fromisoformat(started_at.replace("Z", "+00:00"))

        # Ensure naive datetimes are treated as UTC
        if started_datetime.tzinfo is None:
            started_datetime = started_datetime.replace(tzinfo=timezone.utc)

        # Calculate age
        now = datetime.now(timezone.utc)
        age_delta = now - started_datetime

        return int(age_delta.total_seconds() / 60)
