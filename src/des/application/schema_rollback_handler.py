"""
Schema Rollback Handler for DES Framework.

Implements automatic migration from v2.0 (8-phase) to v1.0 (14-phase) schema
when a step fails twice, ensuring backward compatibility during transition period.

Design:
- Detects failure count in step file
- Triggers rollback when failure count >= 2
- Converts phase_execution_log from 8 to 14 phases
- Preserves execution history and metadata
- Updates schema_version from "2.0" to "1.0"

This ensures safe migration with automatic rollback to proven v1.0 schema.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)

# V1.0 Schema: 14-phase TDD cycle
PHASES_V1_FULL = [
    "PREPARE",
    "RED_ACCEPTANCE",
    "RED_UNIT",
    "GREEN_UNIT",
    "CHECK_ACCEPTANCE",
    "GREEN_ACCEPTANCE",
    "REVIEW",
    "REFACTOR_L1",
    "REFACTOR_L2",
    "REFACTOR_L3",
    "REFACTOR_L4",
    "POST_REFACTOR_REVIEW",
    "FINAL_VALIDATE",
    "COMMIT",
]

# V2.0 Schema: 8-phase optimized TDD cycle
PHASES_V2_OPTIMIZED = [
    "PREPARE",
    "RED_ACCEPTANCE",
    "RED_UNIT",
    "GREEN",
    "REVIEW",
    "REFACTOR_CONTINUOUS",
    "REFACTOR_L4",
    "COMMIT",
]

# V3.0 Schema: 7-phase TDD cycle (removed REFACTOR_L4 to orchestrator)
PHASES_V3_CONSOLIDATED = [
    "PREPARE",
    "RED_ACCEPTANCE",
    "RED_UNIT",
    "GREEN",
    "REVIEW",
    "REFACTOR_CONTINUOUS",
    "COMMIT",
]

# V4.0 Schema: 5-phase streamlined TDD cycle
# REVIEW moved to deliver-level Phase 4 (Adversarial Review via /nw:review)
# REFACTOR_CONTINUOUS moved to deliver-level Phase 3 (Complete Refactoring L1-L4)
PHASES_V4_STREAMLINED = [
    "PREPARE",
    "RED_ACCEPTANCE",
    "RED_UNIT",
    "GREEN",
    "COMMIT",
]

# Mapping from v3.0 phases to v4.0 (contraction: REVIEW and REFACTOR_CONTINUOUS dropped)
PHASE_CONTRACTION_V3_TO_V4 = {
    "PREPARE": "PREPARE",
    "RED_ACCEPTANCE": "RED_ACCEPTANCE",
    "RED_UNIT": "RED_UNIT",
    "GREEN": "GREEN",
    "REVIEW": None,  # Dropped — moved to deliver-level Phase 4
    "REFACTOR_CONTINUOUS": None,  # Dropped — moved to deliver-level Phase 3
    "COMMIT": "COMMIT",
}

# Mapping from v2.0 phases back to v1.0 phases for rollback
PHASE_EXPANSION_MAP = {
    "PREPARE": ["PREPARE"],
    "RED_ACCEPTANCE": ["RED_ACCEPTANCE"],
    "RED_UNIT": ["RED_UNIT"],
    "GREEN": ["GREEN_UNIT", "CHECK_ACCEPTANCE", "GREEN_ACCEPTANCE"],
    "REVIEW": ["REVIEW"],
    "REFACTOR_CONTINUOUS": ["REFACTOR_L1", "REFACTOR_L2", "REFACTOR_L3"],
    "REFACTOR_L4": ["REFACTOR_L4"],
    "COMMIT": ["POST_REFACTOR_REVIEW", "FINAL_VALIDATE", "COMMIT"],
}

# Rollback threshold: number of failures before triggering rollback
ROLLBACK_THRESHOLD = 2


class SchemaRollbackHandler:
    """Handles schema migration and rollback between v1.0 and v2.0."""

    @staticmethod
    def count_failures(step_data: dict[str, Any]) -> int:
        """
        Count the number of FAILED phases in step file.

        Returns:
            Count of phases with outcome == "FAIL"
        """
        phase_log = step_data.get("tdd_cycle", {}).get("phase_execution_log", [])
        failed_count = sum(1 for phase in phase_log if phase.get("outcome") == "FAIL")
        return failed_count

    @staticmethod
    def should_rollback(step_data: dict[str, Any]) -> bool:
        """
        Determine if step should be rolled back to v1.0 schema.

        Triggers rollback when:
        - Schema is v2.0 AND
        - Failure count >= ROLLBACK_THRESHOLD

        Returns:
            True if rollback should be triggered
        """
        schema_version = step_data.get("schema_version", "1.0")
        failure_count = SchemaRollbackHandler.count_failures(step_data)

        if schema_version == "2.0" and failure_count >= ROLLBACK_THRESHOLD:
            logger.warning(
                f"Step has {failure_count} failures with v2.0 schema (threshold: {ROLLBACK_THRESHOLD}). "
                f"Triggering rollback to v1.0."
            )
            return True

        return False

    @staticmethod
    def expand_phase_log(v2_phases: list) -> list:
        """
        Expand v2.0 phase_execution_log (8 phases) to v1.0 format (14 phases).

        Handles:
        - PREPARE → PREPARE
        - RED_ACCEPTANCE → RED_ACCEPTANCE
        - RED_UNIT → RED_UNIT
        - GREEN → GREEN_UNIT, CHECK_ACCEPTANCE, GREEN_ACCEPTANCE
        - REVIEW → REVIEW
        - REFACTOR_CONTINUOUS → REFACTOR_L1, REFACTOR_L2, REFACTOR_L3
        - REFACTOR_L4 → REFACTOR_L4
        - COMMIT → POST_REFACTOR_REVIEW, FINAL_VALIDATE, COMMIT

        Returns:
            Expanded phase_execution_log with 14 phases
        """
        v1_phases = []

        for v2_phase in v2_phases:
            phase_name = v2_phase.get("phase_name", "UNKNOWN")
            status = v2_phase.get("status", "NOT_EXECUTED")
            outcome = v2_phase.get("outcome")

            # Get expanded phase names from mapping
            expanded_names = PHASE_EXPANSION_MAP.get(phase_name, [phase_name])

            # Create phase entry for each expanded phase
            for expanded_phase_name in expanded_names:
                phase_entry = {
                    "phase_name": expanded_phase_name,
                    "status": status,  # Carry over status
                    "started_at": v2_phase.get("started_at"),
                    "ended_at": v2_phase.get("ended_at"),
                    "outcome": outcome,  # Carry over outcome
                    "notes": f"Migrated from v2.0 {phase_name}",
                    "blocked_by": v2_phase.get("blocked_by"),
                }
                v1_phases.append(phase_entry)

        return v1_phases

    @staticmethod
    def rollback_to_v1(step_data: dict[str, Any]) -> dict[str, Any]:
        """
        Rollback step file from v2.0 to v1.0 schema.

        Converts:
        - phase_execution_log from 8 to 14 phases
        - schema_version from "2.0" to "1.0"
        - Adds rollback metadata

        Args:
            step_data: Step file data in v2.0 schema

        Returns:
            Step file data converted to v1.0 schema
        """
        # Get v2.0 phase log
        v2_phase_log = step_data.get("tdd_cycle", {}).get("phase_execution_log", [])

        # Expand to v1.0 format (14 phases)
        v1_phase_log = SchemaRollbackHandler.expand_phase_log(v2_phase_log)

        # Update step data with v1.0 schema
        step_data["schema_version"] = "1.0"
        step_data["tdd_cycle"]["phase_execution_log"] = v1_phase_log

        # Add rollback metadata
        step_data["rollback_info"] = {
            "triggered_at": datetime.now().isoformat(),
            "reason": f"Failure count >= {ROLLBACK_THRESHOLD} with v2.0 schema",
            "original_schema": "2.0",
            "migrated_to": "1.0",
            "phase_count": len(v1_phase_log),
        }

        logger.info(
            f"Successfully rolled back step from v2.0 to v1.0 schema. "
            f"Phase count: {len(v2_phase_log)} → {len(v1_phase_log)}"
        )

        return step_data

    @staticmethod
    def handle_step_failure(step_file_path: Path) -> tuple[bool, str]:
        """
        Handle step failure by checking rollback conditions.

        If rollback is triggered:
        1. Loads step file
        2. Checks failure count
        3. Converts v2.0 → v1.0 if needed
        4. Saves updated step file
        5. Returns True to indicate rollback occurred

        Args:
            step_file_path: Path to step JSON file

        Returns:
            Tuple of (rollback_occurred, message)
        """
        try:
            # Load step file
            with open(step_file_path, encoding="utf-8") as f:
                step_data = json.load(f)

            # Check if rollback should trigger
            if not SchemaRollbackHandler.should_rollback(step_data):
                return False, "No rollback needed"

            # Perform rollback
            rolled_back_data = SchemaRollbackHandler.rollback_to_v1(step_data)

            # Save updated step file
            with open(step_file_path, "w", encoding="utf-8") as f:
                json.dump(rolled_back_data, f, indent=2)

            message = (
                f"Step rolled back to v1.0 schema due to {SchemaRollbackHandler.count_failures(step_data)} "
                f"failures with v2.0. Step file updated: {step_file_path}"
            )
            logger.warning(message)
            return True, message

        except json.JSONDecodeError as e:
            return False, f"Cannot parse step file: {e}"
        except FileNotFoundError:
            return False, f"Step file not found: {step_file_path}"
        except Exception as e:
            return False, f"Error handling step failure: {e}"
