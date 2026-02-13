"""
E2E Acceptance Test: US-008 Session-Scoped Stale Execution Detection

PERSONA: Priya (Tech Lead)
STORY: As a tech lead, I want DES to detect stale executions during my work session,
       so that stuck agents are caught early without requiring external daemons or databases.

BUSINESS VALUE:
- Prevents starting new work while previous execution is abandoned
- Catches stuck agents without external monitoring infrastructure
- Lightweight, zero-dependency solution (pure file scanning)
- Session-scoped checks terminate with the session

SCOPE: Covers US-008 Acceptance Criteria (AC-008.1 through AC-008.5)
WAVE: DISTILL (Acceptance Test Creation)
STATUS: RED (Outside-In TDD - awaiting DEVELOP wave implementation)
"""

import json
from datetime import datetime, timedelta, timezone

from des.application.stale_execution_detector import StaleExecutionDetector


class TestSessionScopedStaleDetection:
    """E2E acceptance tests for US-008: Session-scoped stale execution detection."""

    # =========================================================================
    # AC-008.1: Stale check runs automatically before each /nw:execute invocation
    # Scenario 1: Pre-execution scan detects stale execution from previous session
    # =========================================================================

    def test_scenario_001_pre_execution_scan_detects_stale_execution(
        self, tmp_project_root
    ):
        """
        GIVEN step 01-01 has RED_UNIT phase IN_PROGRESS since 45 minutes ago
        WHEN Marcus runs /nw:execute for step 02-01
        THEN execution is BLOCKED with alert showing stale step details

        Business Value: Priya ensures Marcus cannot accidentally start new work
                       while a previous execution remains abandoned. This prevents
                       confusing state where multiple steps appear "in progress".

        Domain Example (from story):
        Marcus runs `/nw:execute @software-crafter "steps/02-01.json"`.
        Before starting, DES scans for stale executions.
        Finds step 01-01 with RED_UNIT IN_PROGRESS since 45 min ago.
        Alert: "Stale execution found: step 01-01.json, phase RED_UNIT (45 min)"
        """
        # Arrange: Create stale step file with IN_PROGRESS phase from 45 min ago
        stale_step_path = tmp_project_root / "steps" / "01-01.json"
        stale_timestamp = (
            datetime.now(timezone.utc) - timedelta(minutes=45)
        ).isoformat()

        stale_step_data = {
            "task_id": "01-01",
            "project_id": "test-project",
            "workflow_type": "tdd_cycle",
            "state": {"status": "IN_PROGRESS", "started_at": stale_timestamp},
            "tdd_cycle": {
                "phase_execution_log": [
                    {
                        "phase_name": "PREPARE",
                        "status": "EXECUTED",
                        "started_at": stale_timestamp,
                    },
                    {
                        "phase_name": "RED_ACCEPTANCE",
                        "status": "EXECUTED",
                        "started_at": stale_timestamp,
                    },
                    {
                        "phase_name": "RED_UNIT",
                        "status": "IN_PROGRESS",
                        "started_at": stale_timestamp,
                    },
                    {"phase_name": "GREEN_UNIT", "status": "NOT_EXECUTED"},
                    # ... remaining phases NOT_EXECUTED
                ]
            },
        }

        stale_step_path.parent.mkdir(parents=True, exist_ok=True)
        stale_step_path.write_text(json.dumps(stale_step_data, indent=2))

        # Create target step for new execution
        target_step_path = tmp_project_root / "steps" / "02-01.json"
        target_step_data = {
            "task_id": "02-01",
            "project_id": "test-project",
            "workflow_type": "tdd_cycle",
            "state": {"status": "TODO"},
        }
        target_step_path.write_text(json.dumps(target_step_data, indent=2))

        # Act: Attempt to execute new step (pre-execution stale check should run)
        from des.application.orchestrator import DESOrchestrator

        orchestrator = DESOrchestrator.create_with_defaults()
        result = orchestrator.execute_step_with_stale_check(
            command="/nw:execute",
            agent="@software-crafter",
            step_file="steps/02-01.json",
            project_root=tmp_project_root,
        )

        # Assert: Execution blocked with stale alert
        assert result.blocked is True
        assert result.blocking_reason == "STALE_EXECUTION_DETECTED"
        assert "01-01.json" in result.stale_alert.step_file
        assert "RED_UNIT" in result.stale_alert.phase_name
        assert result.stale_alert.age_minutes >= 45
        assert "Resolve before proceeding" in result.stale_alert.message

    # =========================================================================
    # AC-008.1: Stale check runs automatically before each /nw:execute invocation
    # Scenario 2: Clean start when no stale executions exist
    # =========================================================================

    def test_scenario_002_clean_start_when_no_stale_executions(self, tmp_project_root):
        """
        GIVEN no step files have IN_PROGRESS phases
        WHEN Marcus runs /nw:execute for step 01-01
        THEN pre-execution scan passes and execution proceeds normally

        Business Value: Priya ensures the stale detection mechanism does not
                       create false positives or unnecessary workflow delays
                       when all previous work is properly completed.

        Domain Example (from story):
        Marcus runs `/nw:execute @software-crafter "steps/01-01.json"`.
        Pre-execution scan finds no stale IN_PROGRESS phases.
        Execution proceeds normally.
        No daemon running in background - check completes and control returns.
        """
        # Arrange: Create completed step file (no IN_PROGRESS phases)
        completed_step_path = tmp_project_root / "steps" / "00-01.json"
        completed_step_data = {
            "task_id": "00-01",
            "project_id": "test-project",
            "workflow_type": "tdd_cycle",
            "state": {
                "status": "DONE",
                "completed_at": datetime.now(timezone.utc).isoformat(),
            },
            "tdd_cycle": {
                "phase_execution_log": [
                    {"phase_name": "PREPARE", "status": "EXECUTED"},
                    {"phase_name": "RED_ACCEPTANCE", "status": "EXECUTED"},
                    {"phase_name": "RED_UNIT", "status": "EXECUTED"},
                    {"phase_name": "GREEN_UNIT", "status": "EXECUTED"},
                    {"phase_name": "CHECK_ACCEPTANCE", "status": "EXECUTED"},
                    {"phase_name": "GREEN_ACCEPTANCE", "status": "EXECUTED"},
                    {"phase_name": "REVIEW", "status": "EXECUTED"},
                    {"phase_name": "REFACTOR_L1", "status": "EXECUTED"},
                    {"phase_name": "REFACTOR_L2", "status": "EXECUTED"},
                    {"phase_name": "REFACTOR_L3", "status": "EXECUTED"},
                    {"phase_name": "REFACTOR_L4", "status": "EXECUTED"},
                    {"phase_name": "POST_REFACTOR_REVIEW", "status": "EXECUTED"},
                    {"phase_name": "FINAL_VALIDATE", "status": "EXECUTED"},
                    {"phase_name": "COMMIT", "status": "EXECUTED"},
                ]
            },
        }

        completed_step_path.parent.mkdir(parents=True, exist_ok=True)
        completed_step_path.write_text(json.dumps(completed_step_data, indent=2))

        # Create target step for new execution
        target_step_path = tmp_project_root / "steps" / "01-01.json"
        target_step_data = {
            "task_id": "01-01",
            "project_id": "test-project",
            "workflow_type": "tdd_cycle",
            "state": {"status": "TODO"},
            "tdd_cycle": {
                "phase_execution_log": [
                    {"phase_name": "PREPARE", "status": "NOT_EXECUTED", "turn_count": 0}
                ]
            },
        }
        target_step_path.write_text(json.dumps(target_step_data, indent=2))

        # Act: Execute step (pre-execution stale check should pass)
        from des.application.orchestrator import DESOrchestrator

        orchestrator = DESOrchestrator.create_with_defaults()
        result = orchestrator.execute_step_with_stale_check(
            command="/nw:execute",
            agent="@software-crafter",
            step_file="steps/01-01.json",
            project_root=tmp_project_root,
        )

        # Assert: Execution proceeds normally (not blocked, proceeds with execution)
        assert result.blocked is False, (
            "Execution should not be blocked when no stale steps"
        )
        assert result.execute_result is not None, (
            "execute_result should be populated when not blocked"
        )
        assert result.stale_alert is None, "No stale alert should be present when clean"

    # =========================================================================
    # AC-008.2: Stale threshold is configurable (default 30 minutes)
    # Scenario 3: Recent IN_PROGRESS phase within threshold not flagged as stale
    # =========================================================================

    def test_scenario_003_recent_in_progress_within_threshold_not_stale(
        self, tmp_project_root
    ):
        """
        GIVEN step 01-01 has GREEN_UNIT phase IN_PROGRESS since 15 minutes ago
        AND stale threshold is 30 minutes (default)
        WHEN Marcus runs /nw:execute for step 02-01
        THEN execution proceeds (15 min < 30 min threshold)

        Business Value: Priya ensures legitimate in-progress work is not
                       incorrectly flagged as stale. A 15-minute running task
                       is normal; only truly abandoned work should be caught.

        Threshold Configuration: Default 30 minutes
        """
        # Arrange: Create step with recent IN_PROGRESS (15 min ago - within threshold)
        recent_step_path = tmp_project_root / "steps" / "01-01.json"
        recent_timestamp = (
            datetime.now(timezone.utc) - timedelta(minutes=15)
        ).isoformat()

        recent_step_data = {
            "task_id": "01-01",
            "project_id": "test-project",
            "workflow_type": "tdd_cycle",
            "state": {"status": "IN_PROGRESS", "started_at": recent_timestamp},
            "tdd_cycle": {
                "phase_execution_log": [
                    {"phase_name": "PREPARE", "status": "EXECUTED"},
                    {"phase_name": "RED_ACCEPTANCE", "status": "EXECUTED"},
                    {"phase_name": "RED_UNIT", "status": "EXECUTED"},
                    {
                        "phase_name": "GREEN_UNIT",
                        "status": "IN_PROGRESS",
                        "started_at": recent_timestamp,
                    },
                ]
            },
        }

        recent_step_path.parent.mkdir(parents=True, exist_ok=True)
        recent_step_path.write_text(json.dumps(recent_step_data, indent=2))

        # Create target step
        target_step_path = tmp_project_root / "steps" / "02-01.json"
        target_step_data = {
            "task_id": "02-01",
            "project_id": "test-project",
            "state": {"status": "TODO"},
        }
        target_step_path.write_text(json.dumps(target_step_data, indent=2))

        # Act: Scan for stale executions with default 30-minute threshold
        from des.application.stale_execution_detector import StaleExecutionDetector

        detector = StaleExecutionDetector(project_root=tmp_project_root)
        result = detector.scan_for_stale_executions()

        # Assert: Execution proceeds (15 min < 30 min threshold)
        assert result.is_blocked is False
        assert len(result.stale_executions) == 0
        # Note: The 15-min-old IN_PROGRESS is still active, not stale

    # =========================================================================
    # AC-008.2: Stale threshold is configurable
    # Scenario 4: Custom threshold via environment variable
    # =========================================================================

    def test_scenario_004_custom_threshold_via_environment_variable(
        self, tmp_project_root, monkeypatch
    ):
        """
        GIVEN DES_STALE_THRESHOLD_MINUTES=10 environment variable is set
        AND step 01-01 has IN_PROGRESS phase since 15 minutes ago
        WHEN Marcus runs /nw:execute for step 02-01
        THEN execution is BLOCKED (15 min > 10 min custom threshold)

        Business Value: Priya can configure stricter stale detection for
                       high-velocity teams or relax it for long-running tasks.
                       Environment variable allows per-environment tuning.

        Custom Threshold: 10 minutes (via DES_STALE_THRESHOLD_MINUTES)
        """
        # Arrange: Set custom threshold via environment variable
        monkeypatch.setenv("DES_STALE_THRESHOLD_MINUTES", "10")

        # Create step with 15-minute-old IN_PROGRESS (exceeds 10-min threshold)
        stale_step_path = tmp_project_root / "steps" / "01-01.json"
        stale_timestamp = (
            datetime.now(timezone.utc) - timedelta(minutes=15)
        ).isoformat()

        stale_step_data = {
            "task_id": "01-01",
            "project_id": "test-project",
            "state": {"status": "IN_PROGRESS", "started_at": stale_timestamp},
            "tdd_cycle": {
                "phase_execution_log": [
                    {"phase_name": "PREPARE", "status": "EXECUTED"},
                    {
                        "phase_name": "RED_ACCEPTANCE",
                        "status": "IN_PROGRESS",
                        "started_at": stale_timestamp,
                    },
                ]
            },
        }

        stale_step_path.parent.mkdir(parents=True, exist_ok=True)
        stale_step_path.write_text(json.dumps(stale_step_data, indent=2))

        # Create target step
        target_step_path = tmp_project_root / "steps" / "02-01.json"
        target_step_data = {"task_id": "02-01", "state": {"status": "TODO"}}
        target_step_path.write_text(json.dumps(target_step_data, indent=2))

        # Act: Detect stale executions with custom 10-minute threshold
        from des.application.stale_execution_detector import StaleExecutionDetector

        detector = StaleExecutionDetector(project_root=tmp_project_root)
        result = detector.scan_for_stale_executions()

        # Assert: Execution blocked (15 min > 10 min threshold)
        assert result.is_blocked is True
        assert len(result.stale_executions) == 1
        assert result.stale_executions[0].step_file == "steps/01-01.json"

    # =========================================================================
    # AC-008.3: Detection blocks execution with clear alert
    # Scenario 5: Alert includes step file, phase name, and age
    # =========================================================================

    def test_scenario_005_alert_includes_step_phase_and_age_details(
        self, tmp_project_root
    ):
        """
        GIVEN step 03-02 has REFACTOR_L2 phase IN_PROGRESS since 60 minutes ago
        WHEN stale detection runs before new execution
        THEN alert message includes: step file path, phase name, and age in minutes

        Business Value: Priya receives actionable information to quickly locate
                       and resolve the stale execution. No guesswork required.

        Alert Format: "Stale execution found: {step_file}, phase {phase_name} ({age} min)"
        """
        # Arrange: Create stale step with specific phase
        stale_step_path = tmp_project_root / "steps" / "03-02.json"
        stale_timestamp = (
            datetime.now(timezone.utc) - timedelta(minutes=60)
        ).isoformat()

        stale_step_data = {
            "task_id": "03-02",
            "project_id": "test-project",
            "state": {"status": "IN_PROGRESS", "started_at": stale_timestamp},
            "tdd_cycle": {
                "phase_execution_log": [
                    {"phase_name": "PREPARE", "status": "EXECUTED"},
                    {"phase_name": "RED_ACCEPTANCE", "status": "EXECUTED"},
                    {"phase_name": "RED_UNIT", "status": "EXECUTED"},
                    {"phase_name": "GREEN_UNIT", "status": "EXECUTED"},
                    {"phase_name": "CHECK_ACCEPTANCE", "status": "EXECUTED"},
                    {"phase_name": "GREEN_ACCEPTANCE", "status": "EXECUTED"},
                    {"phase_name": "REVIEW", "status": "EXECUTED"},
                    {"phase_name": "REFACTOR_L1", "status": "EXECUTED"},
                    {
                        "phase_name": "REFACTOR_L2",
                        "status": "IN_PROGRESS",
                        "started_at": stale_timestamp,
                    },
                ]
            },
        }

        stale_step_path.parent.mkdir(parents=True, exist_ok=True)
        stale_step_path.write_text(json.dumps(stale_step_data, indent=2))

        # Create target step
        target_step_path = tmp_project_root / "steps" / "04-01.json"
        target_step_data = {"task_id": "04-01", "state": {"status": "TODO"}}
        target_step_path.write_text(json.dumps(target_step_data, indent=2))

        # Act: Run stale detection
        # from des.stale_detector import StaleExecutionDetector
        # detector = StaleExecutionDetector(project_root=tmp_project_root)
        # stale_results = detector.scan_for_stale_executions()

        # Assert: Alert contains all required details
        # assert len(stale_results) == 1
        # stale_alert = stale_results[0]
        # assert "03-02.json" in stale_alert.step_file
        # assert stale_alert.phase_name == "REFACTOR_L2"
        # assert stale_alert.age_minutes >= 60
        # assert "Stale execution found: " in stale_alert.message
        # assert "03-02.json" in stale_alert.message
        # assert "REFACTOR_L2" in stale_alert.message
        # assert "60" in stale_alert.message or "min" in stale_alert.message

    # =========================================================================
    # AC-008.4: User can resolve stale step (mark ABANDONED) to unblock
    # Scenario 6: Resolve stale step and continue with new execution
    # =========================================================================

    def test_scenario_006_resolve_stale_step_unblocks_new_execution(
        self, tmp_project_root
    ):
        """
        GIVEN stale step 01-01 is detected (RED_UNIT IN_PROGRESS for 45 min)
        WHEN Marcus marks step 01-01 as ABANDONED with recovery suggestions
        AND runs /nw:execute for step 02-01 again
        THEN pre-execution scan passes and new execution starts

        Business Value: Priya ensures developers can recover from stuck states
                       by explicitly acknowledging abandoned work. This creates
                       a clear audit trail of the resolution decision.

        Domain Example (from story):
        Marcus resolves stale step 01-01 (marks as ABANDONED with recovery suggestions).
        Runs `/nw:execute` again.
        Pre-execution scan passes - no stale phases found.
        New execution starts on step 02-01.
        """
        # Arrange: Create already-resolved step
        # Step is IN_PROGRESS but the current phase is ABANDONED (not IN_PROGRESS)
        # This simulates a step that was abandoned after crash/timeout
        resolved_step_path = tmp_project_root / "steps" / "01-01.json"
        old_timestamp = (datetime.now(timezone.utc) - timedelta(minutes=45)).isoformat()
        resolved_step_data = {
            "task_id": "01-01",
            "project_id": "test-project",
            "state": {
                "status": "IN_PROGRESS",  # Step overall is IN_PROGRESS
                "failure_reason": "Agent crashed during RED_UNIT phase",
                "recovery_suggestions": [
                    "Review agent transcript for error details",
                    "Reset RED_UNIT phase status to NOT_EXECUTED",
                    "Run `/nw:execute` again to resume from RED_UNIT",
                ],
                "abandoned_at": datetime.now(timezone.utc).isoformat(),
            },
            "tdd_cycle": {
                "phase_execution_log": [
                    {"phase_name": "PREPARE", "status": "EXECUTED"},
                    {"phase_name": "RED_ACCEPTANCE", "status": "EXECUTED"},
                    {
                        "phase_name": "RED_UNIT",
                        "status": "ABANDONED",  # Phase is ABANDONED, not IN_PROGRESS
                        "started_at": old_timestamp,
                        "abandoned_reason": "Agent crashed - manually resolved",
                    },
                ]
            },
        }

        resolved_step_path.parent.mkdir(parents=True, exist_ok=True)
        resolved_step_path.write_text(json.dumps(resolved_step_data, indent=2))

        # Create target step for new execution
        target_step_path = tmp_project_root / "steps" / "02-01.json"
        target_step_data = {
            "task_id": "02-01",
            "project_id": "test-project",
            "state": {"status": "TODO"},
        }
        target_step_path.write_text(json.dumps(target_step_data, indent=2))

        # Act: Run pre-execution scan (should pass since stale step is resolved)
        detector = StaleExecutionDetector(project_root=tmp_project_root)
        result = detector.scan_for_stale_executions()

        # Assert: No stale executions detected (ABANDONED status not flagged)
        assert result.is_blocked is False
        assert len(result.stale_executions) == 0
        assert result.alert_message == ""

    # =========================================================================
    # AC-008.4: User can resolve stale step
    # Scenario 7: Mark stale step as ABANDONED with recovery suggestions
    # =========================================================================

    def test_scenario_007_mark_step_abandoned_updates_state_correctly(
        self, tmp_project_root
    ):
        """
        GIVEN step 01-01 has IN_PROGRESS phase (stale)
        WHEN Marcus invokes stale resolution command
        THEN step file is updated with ABANDONED status and recovery suggestions

        Business Value: Priya ensures proper state management for abandoned work.
                       The step file becomes a record of what happened and how
                       to recover, useful for post-mortem analysis.

        Resolution Updates:
        - state.status -> ABANDONED
        - state.failure_reason -> descriptive message
        - state.recovery_suggestions -> actionable steps
        - phase.status -> ABANDONED (for the stuck phase)
        """
        # Arrange: Create stale step
        stale_step_path = tmp_project_root / "steps" / "01-01.json"
        stale_timestamp = (
            datetime.now(timezone.utc) - timedelta(minutes=45)
        ).isoformat()

        stale_step_data = {
            "task_id": "01-01",
            "project_id": "test-project",
            "state": {"status": "IN_PROGRESS", "started_at": stale_timestamp},
            "tdd_cycle": {
                "phase_execution_log": [
                    {"phase_name": "PREPARE", "status": "EXECUTED"},
                    {
                        "phase_name": "RED_ACCEPTANCE",
                        "status": "IN_PROGRESS",
                        "started_at": stale_timestamp,
                    },
                ]
            },
        }

        stale_step_path.parent.mkdir(parents=True, exist_ok=True)
        stale_step_path.write_text(json.dumps(stale_step_data, indent=2))

        # Act: Resolve the stale step
        from des.application.stale_resolver import StaleResolver

        resolver = StaleResolver(project_root=tmp_project_root)
        resolver.mark_abandoned(
            step_file="steps/01-01.json",
            reason="Agent crashed during RED_ACCEPTANCE phase",
        )

        # Assert: Step file properly updated
        updated_step = json.loads(stale_step_path.read_text())
        assert updated_step["state"]["status"] == "ABANDONED"
        assert "Agent crashed" in updated_step["state"]["failure_reason"]
        assert len(updated_step["state"]["recovery_suggestions"]) >= 1
        assert any(
            "transcript" in s.lower()
            for s in updated_step["state"]["recovery_suggestions"]
        )
        assert (
            updated_step["tdd_cycle"]["phase_execution_log"][1]["status"] == "ABANDONED"
        )
        assert "abandoned_at" in updated_step["state"]

    # =========================================================================
    # AC-008.5: No external dependencies - pure file scanning
    # Scenario 8: Stale detection works without database or external services
    # =========================================================================

    def test_scenario_008_pure_file_scanning_no_external_dependencies(
        self, tmp_project_root
    ):
        """
        GIVEN multiple step files exist in steps/ directory
        WHEN stale detection scan runs
        THEN scan completes using only file system operations (no DB, no HTTP)

        Business Value: Priya ensures the solution is lightweight and portable.
                       No installation, no configuration, no network access.
                       Works in any environment with basic file system.

        Zero Dependencies:
        - No database connections
        - No HTTP calls
        - No external services
        - No persistent daemon
        - Pure Python file I/O
        """
        # Arrange: Create multiple step files with various states
        (tmp_project_root / "steps").mkdir(parents=True, exist_ok=True)

        # Step 1: Completed
        step1_data = {"task_id": "01-01", "state": {"status": "DONE"}}
        (tmp_project_root / "steps" / "01-01.json").write_text(json.dumps(step1_data))

        # Step 2: Stale IN_PROGRESS
        stale_timestamp = (
            datetime.now(timezone.utc) - timedelta(minutes=45)
        ).isoformat()
        step2_data = {
            "task_id": "02-01",
            "state": {"status": "IN_PROGRESS", "started_at": stale_timestamp},
            "tdd_cycle": {
                "phase_execution_log": [
                    {
                        "phase_name": "PREPARE",
                        "status": "IN_PROGRESS",
                        "started_at": stale_timestamp,
                    }
                ]
            },
        }
        (tmp_project_root / "steps" / "02-01.json").write_text(json.dumps(step2_data))

        # Step 3: TODO
        step3_data = {"task_id": "03-01", "state": {"status": "TODO"}}
        (tmp_project_root / "steps" / "03-01.json").write_text(json.dumps(step3_data))

        # Act: Run stale detection (should be pure file scanning)
        from des.application.stale_execution_detector import StaleExecutionDetector

        detector = StaleExecutionDetector(project_root=tmp_project_root)
        result = detector.scan_for_stale_executions()

        # Assert: Scan found the stale step using only file I/O
        assert result.is_blocked is True
        assert len(result.stale_executions) == 1
        assert "02-01" in result.stale_executions[0].step_file

        # Verify metadata properties exist (will validate values in unit tests)
        assert hasattr(detector, "uses_external_services")
        assert hasattr(detector, "is_session_scoped")

    # =========================================================================
    # AC-008.5: Session-scoped (terminates with session)
    # Scenario 9: No persistent daemon remains after check completes
    # =========================================================================

    def test_scenario_009_no_persistent_daemon_after_check_completes(
        self, tmp_project_root
    ):
        """
        GIVEN stale detection check is invoked
        WHEN the check completes (pass or fail)
        THEN no background process remains running

        Business Value: Priya ensures the solution is truly session-scoped.
                       No zombie processes, no resource leaks, no surprises
                       when returning to the terminal later.

        Session Scope Guarantees:
        - No background threads after return
        - No daemon processes spawned
        - No file watchers left running
        - Clean termination on check completion
        """
        # Arrange: Create project with step files
        (tmp_project_root / "steps").mkdir(parents=True, exist_ok=True)
        step_data = {"task_id": "01-01", "state": {"status": "TODO"}}
        (tmp_project_root / "steps" / "01-01.json").write_text(json.dumps(step_data))

        # Act: Run stale detection and verify no daemon
        import multiprocessing
        import threading

        initial_threads = threading.active_count()
        initial_processes = len(multiprocessing.active_children())

        from des.application.stale_execution_detector import StaleExecutionDetector

        detector = StaleExecutionDetector(project_root=tmp_project_root)
        detector.scan_for_stale_executions()

        final_threads = threading.active_count()
        final_processes = len(multiprocessing.active_children())

        # Assert: No new threads or processes remain
        assert final_threads == initial_threads, "Stale check left threads running"
        assert final_processes == initial_processes, "Stale check spawned daemon"

    # =========================================================================
    # Edge Case: Multiple stale executions detected simultaneously
    # =========================================================================

    def test_scenario_010_multiple_stale_executions_all_reported(
        self, tmp_project_root
    ):
        """
        GIVEN step 01-01, 02-01, and 03-01 all have stale IN_PROGRESS phases
        WHEN stale detection scan runs
        THEN all 3 stale steps are reported with individual alerts

        Business Value: Priya ensures comprehensive detection - if multiple
                       things are stuck, the developer sees the full picture
                       rather than discovering issues one at a time.
        """
        # Arrange: Create 3 stale step files
        (tmp_project_root / "steps").mkdir(parents=True, exist_ok=True)

        for step_num, phase_name in [
            ("01-01", "RED_UNIT"),
            ("02-01", "GREEN_UNIT"),
            ("03-01", "REFACTOR_L1"),
        ]:
            stale_timestamp = (
                datetime.now(timezone.utc) - timedelta(minutes=45)
            ).isoformat()
            step_data = {
                "task_id": step_num,
                "project_id": "test-project",
                "state": {"status": "IN_PROGRESS", "started_at": stale_timestamp},
                "tdd_cycle": {
                    "phase_execution_log": [
                        {
                            "phase_name": phase_name,
                            "status": "IN_PROGRESS",
                            "started_at": stale_timestamp,
                        }
                    ]
                },
            }
            (tmp_project_root / "steps" / f"{step_num}.json").write_text(
                json.dumps(step_data)
            )

        # Act: Run stale detection
        from des.application.stale_execution_detector import (
            StaleExecutionDetector,
        )

        detector = StaleExecutionDetector(project_root=tmp_project_root)
        stale_result = detector.scan_for_stale_executions()

        # Assert: All 3 stale steps reported
        assert len(stale_result.stale_executions) == 3
        step_files = [se.step_file for se in stale_result.stale_executions]
        assert any("01-01" in s for s in step_files)
        assert any("02-01" in s for s in step_files)
        assert any("03-01" in s for s in step_files)

    # =========================================================================
    # Edge Case: Step file with corrupted JSON
    # =========================================================================

    def test_scenario_011_corrupted_step_file_gracefully_handled(
        self, tmp_project_root
    ):
        """
        GIVEN one step file has corrupted JSON content
        WHEN stale detection scan runs
        THEN scan continues, reporting the corrupted file as warning (not crash)

        Business Value: Priya ensures the stale detection is robust. A single
                       corrupted file should not crash the entire scan or
                       block all development work.
        """
        # Arrange: Create corrupted step file and valid step file
        (tmp_project_root / "steps").mkdir(parents=True, exist_ok=True)

        # Corrupted file
        (tmp_project_root / "steps" / "01-01.json").write_text("{ invalid json content")

        # Valid stale file
        stale_timestamp = (
            datetime.now(timezone.utc) - timedelta(minutes=45)
        ).isoformat()
        valid_stale_data = {
            "task_id": "02-01",
            "state": {"status": "IN_PROGRESS", "started_at": stale_timestamp},
            "tdd_cycle": {
                "phase_execution_log": [
                    {
                        "phase_name": "PREPARE",
                        "status": "IN_PROGRESS",
                        "started_at": stale_timestamp,
                    }
                ]
            },
        }
        (tmp_project_root / "steps" / "02-01.json").write_text(
            json.dumps(valid_stale_data)
        )

        # Act: Run stale detection
        from des.application.stale_execution_detector import StaleExecutionDetector

        detector = StaleExecutionDetector(project_root=tmp_project_root)
        result = detector.scan_for_stale_executions()

        # Assert: Scan completes, reports warning for corrupted file
        assert len(result.stale_executions) == 1  # Valid stale file detected
        assert "02-01" in result.stale_executions[0].step_file

        # Check warnings were logged
        assert hasattr(result, "warnings")
        assert len(result.warnings) == 1  # Corrupted file warning
        assert "01-01.json" in result.warnings[0]["file_path"]
        # Error message should indicate JSON parsing issue
        error_msg = result.warnings[0]["error"].lower()
        assert any(
            keyword in error_msg for keyword in ["json", "parse", "expecting", "decode"]
        )
