"""
Unit tests for schema rollback handler.

Tests validate:
1. Failure count detection (FAIL outcomes)
2. Rollback trigger conditions (v2.0 + 2+ failures)
3. Phase log expansion (8 phases → 14 phases)
4. Schema version conversion (2.0 → 1.0)
5. Rollback metadata tracking
6. Edge cases (missing phases, unknown statuses, etc.)
"""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from des.application.schema_rollback_handler import (
    PHASES_V1_FULL,
    PHASES_V2_OPTIMIZED,
    SchemaRollbackHandler,
)


class TestFailureCountDetection:
    """Tests for failure count detection in step files."""

    def test_count_failures_with_no_failures(self):
        """
        GIVEN step with no FAIL outcomes
        WHEN count_failures() called
        THEN returns 0
        """
        step_data = {
            "tdd_cycle": {
                "phase_execution_log": [
                    {"phase_name": "PREPARE", "outcome": "PASS"},
                    {"phase_name": "RED_ACCEPTANCE", "outcome": None},
                    {"phase_name": "RED_UNIT", "outcome": "PASS"},
                ]
            }
        }

        count = SchemaRollbackHandler.count_failures(step_data)

        assert count == 0

    def test_count_failures_with_two_failures(self):
        """
        GIVEN step with 2 FAIL outcomes
        WHEN count_failures() called
        THEN returns 2
        """
        step_data = {
            "tdd_cycle": {
                "phase_execution_log": [
                    {"phase_name": "RED_ACCEPTANCE", "outcome": "FAIL"},
                    {"phase_name": "RED_UNIT", "outcome": "PASS"},
                    {"phase_name": "GREEN", "outcome": "FAIL"},
                ]
            }
        }

        count = SchemaRollbackHandler.count_failures(step_data)

        assert count == 2

    def test_count_failures_with_missing_phase_log(self):
        """
        GIVEN step with missing phase_execution_log
        WHEN count_failures() called
        THEN returns 0
        """
        step_data = {"tdd_cycle": {}}

        count = SchemaRollbackHandler.count_failures(step_data)

        assert count == 0


class TestRollbackTriggerConditions:
    """Tests for rollback trigger logic."""

    def test_should_rollback_v1_0_never_rolls_back(self):
        """
        GIVEN v1.0 schema step with 2+ failures
        WHEN should_rollback() called
        THEN returns False (v1.0 stays v1.0)
        """
        step_data = {
            "schema_version": "1.0",
            "tdd_cycle": {
                "phase_execution_log": [
                    {"phase_name": "PREPARE", "outcome": "FAIL"},
                    {"phase_name": "RED_ACCEPTANCE", "outcome": "FAIL"},
                    {"phase_name": "RED_UNIT", "outcome": "PASS"},
                ]
            },
        }

        should_rollback = SchemaRollbackHandler.should_rollback(step_data)

        assert should_rollback is False

    def test_should_rollback_v2_0_with_one_failure(self):
        """
        GIVEN v2.0 schema step with 1 failure (below threshold)
        WHEN should_rollback() called
        THEN returns False
        """
        step_data = {
            "schema_version": "2.0",
            "tdd_cycle": {
                "phase_execution_log": [
                    {"phase_name": "PREPARE", "outcome": "FAIL"},
                    {"phase_name": "RED_ACCEPTANCE", "outcome": "PASS"},
                ]
            },
        }

        should_rollback = SchemaRollbackHandler.should_rollback(step_data)

        assert should_rollback is False

    def test_should_rollback_v2_0_with_two_failures(self):
        """
        GIVEN v2.0 schema step with 2 failures (at threshold)
        WHEN should_rollback() called
        THEN returns True
        """
        step_data = {
            "schema_version": "2.0",
            "tdd_cycle": {
                "phase_execution_log": [
                    {"phase_name": "PREPARE", "outcome": "FAIL"},
                    {"phase_name": "RED_ACCEPTANCE", "outcome": "FAIL"},
                    {"phase_name": "RED_UNIT", "outcome": "PASS"},
                ]
            },
        }

        should_rollback = SchemaRollbackHandler.should_rollback(step_data)

        assert should_rollback is True

    def test_should_rollback_v2_0_with_three_failures(self):
        """
        GIVEN v2.0 schema step with 3 failures (above threshold)
        WHEN should_rollback() called
        THEN returns True
        """
        step_data = {
            "schema_version": "2.0",
            "tdd_cycle": {
                "phase_execution_log": [
                    {"phase_name": "PREPARE", "outcome": "FAIL"},
                    {"phase_name": "RED_ACCEPTANCE", "outcome": "FAIL"},
                    {"phase_name": "RED_UNIT", "outcome": "FAIL"},
                ]
            },
        }

        should_rollback = SchemaRollbackHandler.should_rollback(step_data)

        assert should_rollback is True


class TestPhaseLogExpansion:
    """Tests for expanding v2.0 phase log to v1.0 format."""

    def test_expand_prepare_phase(self):
        """
        GIVEN v2.0 PREPARE phase
        WHEN expand_phase_log() called
        THEN PREPARE maps to single PREPARE in v1.0
        """
        v2_phases = [
            {
                "phase_name": "PREPARE",
                "status": "EXECUTED",
                "outcome": "PASS",
                "started_at": "2025-01-13T10:00:00",
                "ended_at": "2025-01-13T10:05:00",
                "blocked_by": None,
            }
        ]

        expanded = SchemaRollbackHandler.expand_phase_log(v2_phases)

        assert len(expanded) == 1
        assert expanded[0]["phase_name"] == "PREPARE"
        assert expanded[0]["outcome"] == "PASS"

    def test_expand_green_phase(self):
        """
        GIVEN v2.0 GREEN phase (merged from 3 phases)
        WHEN expand_phase_log() called
        THEN GREEN expands to GREEN_UNIT, CHECK_ACCEPTANCE, GREEN_ACCEPTANCE
        """
        v2_phases = [
            {
                "phase_name": "GREEN",
                "status": "EXECUTED",
                "outcome": "PASS",
                "started_at": "2025-01-13T10:30:00",
                "ended_at": "2025-01-13T10:40:00",
                "blocked_by": None,
            }
        ]

        expanded = SchemaRollbackHandler.expand_phase_log(v2_phases)

        assert len(expanded) == 3
        phase_names = [p["phase_name"] for p in expanded]
        assert phase_names == ["GREEN_UNIT", "CHECK_ACCEPTANCE", "GREEN_ACCEPTANCE"]
        # All should carry over status and outcome
        for phase in expanded:
            assert phase["status"] == "EXECUTED"
            assert phase["outcome"] == "PASS"

    def test_expand_refactor_continuous_phase(self):
        """
        GIVEN v2.0 REFACTOR_CONTINUOUS phase (merged from 3 levels)
        WHEN expand_phase_log() called
        THEN REFACTOR_CONTINUOUS expands to REFACTOR_L1, L2, L3
        """
        v2_phases = [
            {
                "phase_name": "REFACTOR_CONTINUOUS",
                "status": "EXECUTED",
                "outcome": "PASS",
                "started_at": None,
                "ended_at": None,
                "blocked_by": None,
            }
        ]

        expanded = SchemaRollbackHandler.expand_phase_log(v2_phases)

        assert len(expanded) == 3
        phase_names = [p["phase_name"] for p in expanded]
        assert phase_names == ["REFACTOR_L1", "REFACTOR_L2", "REFACTOR_L3"]

    def test_expand_commit_phase(self):
        """
        GIVEN v2.0 COMMIT phase (merged from 3 phases)
        WHEN expand_phase_log() called
        THEN COMMIT expands to POST_REFACTOR_REVIEW, FINAL_VALIDATE, COMMIT
        """
        v2_phases = [
            {
                "phase_name": "COMMIT",
                "status": "EXECUTED",
                "outcome": "PASS",
                "started_at": None,
                "ended_at": None,
                "blocked_by": None,
            }
        ]

        expanded = SchemaRollbackHandler.expand_phase_log(v2_phases)

        assert len(expanded) == 3
        phase_names = [p["phase_name"] for p in expanded]
        assert phase_names == ["POST_REFACTOR_REVIEW", "FINAL_VALIDATE", "COMMIT"]

    def test_expand_all_8_phases(self):
        """
        GIVEN all 8 v2.0 phases
        WHEN expand_phase_log() called
        THEN result has exactly 14 v1.0 phases in correct order
        """
        v2_phases = [
            {
                "phase_name": phase,
                "status": "EXECUTED",
                "outcome": "PASS",
                "started_at": None,
                "ended_at": None,
                "blocked_by": None,
            }
            for phase in PHASES_V2_OPTIMIZED
        ]

        expanded = SchemaRollbackHandler.expand_phase_log(v2_phases)

        assert len(expanded) == 14
        phase_names = [p["phase_name"] for p in expanded]
        assert phase_names == PHASES_V1_FULL

    def test_expand_preserves_outcome_for_skipped(self):
        """
        GIVEN v2.0 phase with SKIPPED status
        WHEN expand_phase_log() called
        THEN expanded phases preserve SKIPPED status and blocked_by reason
        """
        v2_phases = [
            {
                "phase_name": "REFACTOR_L4",
                "status": "SKIPPED",
                "outcome": None,
                "started_at": None,
                "ended_at": None,
                "blocked_by": "NOT_APPLICABLE: Trivial change",
            }
        ]

        expanded = SchemaRollbackHandler.expand_phase_log(v2_phases)

        assert len(expanded) == 1
        assert expanded[0]["status"] == "SKIPPED"
        assert expanded[0]["blocked_by"] == "NOT_APPLICABLE: Trivial change"


class TestSchemaVersionConversion:
    """Tests for full schema rollback conversion."""

    def test_rollback_to_v1_updates_schema_version(self):
        """
        GIVEN v2.0 step data
        WHEN rollback_to_v1() called
        THEN schema_version updated from "2.0" to "1.0"
        """
        step_data = {
            "schema_version": "2.0",
            "tdd_cycle": {
                "phase_execution_log": [
                    {
                        "phase_name": "PREPARE",
                        "status": "EXECUTED",
                        "outcome": "PASS",
                        "started_at": None,
                        "ended_at": None,
                        "blocked_by": None,
                    },
                    {
                        "phase_name": "RED_ACCEPTANCE",
                        "status": "EXECUTED",
                        "outcome": "PASS",
                        "started_at": None,
                        "ended_at": None,
                        "blocked_by": None,
                    },
                ]
            },
        }

        rolled_back = SchemaRollbackHandler.rollback_to_v1(step_data)

        assert rolled_back["schema_version"] == "1.0"

    def test_rollback_to_v1_expands_phases(self):
        """
        GIVEN v2.0 step with 8 phases
        WHEN rollback_to_v1() called
        THEN phase_execution_log expanded to 14 phases
        """
        v2_phases = [
            {
                "phase_name": phase,
                "status": "EXECUTED",
                "outcome": "PASS",
                "started_at": None,
                "ended_at": None,
                "blocked_by": None,
            }
            for phase in PHASES_V2_OPTIMIZED
        ]

        step_data = {
            "schema_version": "2.0",
            "tdd_cycle": {"phase_execution_log": v2_phases},
        }

        rolled_back = SchemaRollbackHandler.rollback_to_v1(step_data)

        assert len(rolled_back["tdd_cycle"]["phase_execution_log"]) == 14

    def test_rollback_to_v1_adds_metadata(self):
        """
        GIVEN v2.0 step
        WHEN rollback_to_v1() called
        THEN rollback_info metadata added with timestamp and reason
        """
        step_data = {
            "schema_version": "2.0",
            "tdd_cycle": {
                "phase_execution_log": [
                    {
                        "phase_name": "PREPARE",
                        "status": "EXECUTED",
                        "outcome": "PASS",
                        "started_at": None,
                        "ended_at": None,
                        "blocked_by": None,
                    }
                ]
            },
        }

        rolled_back = SchemaRollbackHandler.rollback_to_v1(step_data)

        assert "rollback_info" in rolled_back
        assert rolled_back["rollback_info"]["original_schema"] == "2.0"
        assert rolled_back["rollback_info"]["migrated_to"] == "1.0"
        assert "triggered_at" in rolled_back["rollback_info"]
        assert "reason" in rolled_back["rollback_info"]


class TestHandleStepFailure:
    """Tests for end-to-end step failure handling."""

    def test_handle_step_failure_no_rollback_needed(self):
        """
        GIVEN step file with 1 failure on v2.0
        WHEN handle_step_failure() called
        THEN returns (False, message) - no rollback triggered
        """
        with TemporaryDirectory() as tmpdir:
            step_file = Path(tmpdir) / "step.json"
            step_data = {
                "schema_version": "2.0",
                "tdd_cycle": {
                    "phase_execution_log": [
                        {
                            "phase_name": "PREPARE",
                            "outcome": "FAIL",
                            "status": "EXECUTED",
                            "started_at": None,
                            "ended_at": None,
                            "blocked_by": None,
                        },
                        {
                            "phase_name": "RED_ACCEPTANCE",
                            "outcome": "PASS",
                            "status": "EXECUTED",
                            "started_at": None,
                            "ended_at": None,
                            "blocked_by": None,
                        },
                    ]
                },
            }

            with open(step_file, "w") as f:
                json.dump(step_data, f)

            rollback_occurred, message = SchemaRollbackHandler.handle_step_failure(
                step_file
            )

            assert rollback_occurred is False
            assert "No rollback needed" in message

    def test_handle_step_failure_triggers_rollback(self):
        """
        GIVEN step file with 2 failures on v2.0 (all 8 v2.0 phases)
        WHEN handle_step_failure() called
        THEN returns (True, message) and step file updated to v1.0
        """
        with TemporaryDirectory() as tmpdir:
            step_file = Path(tmpdir) / "step.json"
            # Create v2.0 step with all 8 phases (2 of them failing)
            step_data = {
                "schema_version": "2.0",
                "tdd_cycle": {
                    "phase_execution_log": [
                        {
                            "phase_name": "PREPARE",
                            "outcome": "FAIL",
                            "status": "EXECUTED",
                            "started_at": None,
                            "ended_at": None,
                            "blocked_by": None,
                        },
                        {
                            "phase_name": "RED_ACCEPTANCE",
                            "outcome": "FAIL",
                            "status": "EXECUTED",
                            "started_at": None,
                            "ended_at": None,
                            "blocked_by": None,
                        },
                        {
                            "phase_name": "RED_UNIT",
                            "outcome": "PASS",
                            "status": "EXECUTED",
                            "started_at": None,
                            "ended_at": None,
                            "blocked_by": None,
                        },
                        {
                            "phase_name": "GREEN",
                            "outcome": "PASS",
                            "status": "EXECUTED",
                            "started_at": None,
                            "ended_at": None,
                            "blocked_by": None,
                        },
                        {
                            "phase_name": "REVIEW",
                            "outcome": "PASS",
                            "status": "EXECUTED",
                            "started_at": None,
                            "ended_at": None,
                            "blocked_by": None,
                        },
                        {
                            "phase_name": "REFACTOR_CONTINUOUS",
                            "outcome": "PASS",
                            "status": "EXECUTED",
                            "started_at": None,
                            "ended_at": None,
                            "blocked_by": None,
                        },
                        {
                            "phase_name": "REFACTOR_L4",
                            "outcome": None,
                            "status": "SKIPPED",
                            "started_at": None,
                            "ended_at": None,
                            "blocked_by": "NOT_APPLICABLE: Trivial change",
                        },
                        {
                            "phase_name": "COMMIT",
                            "outcome": None,
                            "status": "NOT_EXECUTED",
                            "started_at": None,
                            "ended_at": None,
                            "blocked_by": None,
                        },
                    ]
                },
            }

            with open(step_file, "w") as f:
                json.dump(step_data, f)

            rollback_occurred, message = SchemaRollbackHandler.handle_step_failure(
                step_file
            )

            assert rollback_occurred is True
            assert "rolled back to v1.0" in message

            # Verify step file was updated
            with open(step_file) as f:
                updated_data = json.load(f)

            assert updated_data["schema_version"] == "1.0"
            assert len(updated_data["tdd_cycle"]["phase_execution_log"]) == 14

    def test_handle_step_failure_file_not_found(self):
        """
        GIVEN non-existent step file path
        WHEN handle_step_failure() called
        THEN returns (False, error message)
        """
        non_existent = Path("/tmp/non-existent-step-file.json")

        rollback_occurred, message = SchemaRollbackHandler.handle_step_failure(
            non_existent
        )

        assert rollback_occurred is False
        assert "not found" in message.lower()


class TestRollbackIntegration:
    """Integration tests for complete rollback flow."""

    def test_complete_v2_to_v1_migration_preserves_data(self):
        """
        GIVEN full v2.0 step file with mixed outcomes
        WHEN complete rollback performed
        THEN data integrity preserved across all phases
        """
        original_v2_step = {
            "task_id": "TEST-01-01",
            "schema_version": "2.0",
            "tdd_cycle": {
                "acceptance_test": {"scenario_name": "test_scenario"},
                "phase_execution_log": [
                    {
                        "phase_name": "PREPARE",
                        "status": "EXECUTED",
                        "outcome": "PASS",
                        "started_at": "2025-01-13T10:00:00",
                        "ended_at": "2025-01-13T10:05:00",
                        "blocked_by": None,
                        "notes": "Setup complete",
                    },
                    {
                        "phase_name": "RED_ACCEPTANCE",
                        "status": "EXECUTED",
                        "outcome": "FAIL",
                        "started_at": "2025-01-13T10:05:00",
                        "ended_at": "2025-01-13T10:10:00",
                        "blocked_by": None,
                        "notes": "Test failed as expected",
                    },
                    {
                        "phase_name": "RED_UNIT",
                        "status": "EXECUTED",
                        "outcome": "FAIL",
                        "started_at": "2025-01-13T10:10:00",
                        "ended_at": "2025-01-13T10:15:00",
                        "blocked_by": None,
                        "notes": "Unit test failed",
                    },
                    {
                        "phase_name": "GREEN",
                        "status": "SKIPPED",
                        "outcome": None,
                        "started_at": None,
                        "ended_at": None,
                        "blocked_by": "BLOCKED_BY_DEPENDENCY: Waiting for dependency",
                        "notes": None,
                    },
                    {
                        "phase_name": "REVIEW",
                        "status": "NOT_EXECUTED",
                        "outcome": None,
                        "started_at": None,
                        "ended_at": None,
                        "blocked_by": None,
                        "notes": None,
                    },
                    {
                        "phase_name": "REFACTOR_CONTINUOUS",
                        "status": "NOT_EXECUTED",
                        "outcome": None,
                        "started_at": None,
                        "ended_at": None,
                        "blocked_by": None,
                        "notes": None,
                    },
                    {
                        "phase_name": "REFACTOR_L4",
                        "status": "NOT_EXECUTED",
                        "outcome": None,
                        "started_at": None,
                        "ended_at": None,
                        "blocked_by": None,
                        "notes": None,
                    },
                    {
                        "phase_name": "COMMIT",
                        "status": "NOT_EXECUTED",
                        "outcome": None,
                        "started_at": None,
                        "ended_at": None,
                        "blocked_by": None,
                        "notes": None,
                    },
                ],
            },
        }

        rolled_back = SchemaRollbackHandler.rollback_to_v1(original_v2_step)

        # Verify schema changed
        assert rolled_back["schema_version"] == "1.0"

        # Verify phase count
        assert len(rolled_back["tdd_cycle"]["phase_execution_log"]) == 14

        # Verify first few phases (PREPARE stays the same)
        assert (
            rolled_back["tdd_cycle"]["phase_execution_log"][0]["phase_name"]
            == "PREPARE"
        )
        assert rolled_back["tdd_cycle"]["phase_execution_log"][0]["outcome"] == "PASS"

        # Verify GREEN expansion (3 phases)
        green_indices = [
            i
            for i, p in enumerate(rolled_back["tdd_cycle"]["phase_execution_log"])
            if p["phase_name"] in ["GREEN_UNIT", "CHECK_ACCEPTANCE", "GREEN_ACCEPTANCE"]
        ]
        assert len(green_indices) == 3
        # All expanded GREEN phases should have SKIPPED status
        for idx in green_indices:
            assert (
                rolled_back["tdd_cycle"]["phase_execution_log"][idx]["status"]
                == "SKIPPED"
            )
            assert (
                "BLOCKED_BY_DEPENDENCY"
                in rolled_back["tdd_cycle"]["phase_execution_log"][idx]["blocked_by"]
            )

        # Verify task_id preserved
        assert rolled_back["task_id"] == "TEST-01-01"

        # Verify acceptance_test preserved
        assert (
            rolled_back["tdd_cycle"]["acceptance_test"]["scenario_name"]
            == "test_scenario"
        )
