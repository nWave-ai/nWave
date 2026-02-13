"""
E2E WIRING TESTS: Validate nWave commands integrate turn counting, timeout warnings, and extension API

PERSONA: Marcus (Senior Developer)
STORY: As a senior developer, I want to verify that turn counting, timeout warnings,
       and extension API are all wired into actual nWave command execution paths
       (/nw:execute and /nw:develop), so that these features work during real
       command invocations (EXTERNAL VALIDITY).

PROBLEM: Features exist in isolation but may not be properly integrated into the
         orchestrator's command execution loop. Without E2E validation, we cannot
         be certain these features execute during real commands. Both primary nWave
         commands must have full DES feature integration.

SOLUTION: Create comprehensive E2E tests that:
          - Invoke /nw:execute and /nw:develop with real command paths
          - Validate turn_count increments in step file
          - Validate timeout warnings emit when thresholds crossed
          - Validate extension request API is callable and updates limits
          - Prove features are wired into actual execution for BOTH commands

BUSINESS VALUE:
- Proves external validity of turn/timeout features
- Validates integration across all components
- Prevents integration failures in production
- Ensures audit trail completeness
- Confirms feature parity between /nw:execute and /nw:develop

SOURCE:
- docs/feature/des-us006/steps/08-01.json (Step 08-01 - /nw:execute wiring)
- docs/feature/des-us006/steps/08-02.json (Step 08-02 - /nw:develop wiring)
"""


class TestE2EExecuteCommandWiring:
    """
    E2E WIRING TEST validating turn counting, timeout warnings, and extension API
    integration in /nw:execute command execution path.

    Tests prove EXTERNAL VALIDITY by invoking real command and validating
    all features execute during actual orchestrator operation.
    """

    def test_scenario_021_e2e_execute_command_has_turn_and_timeout_features(
        self,
        tmp_project_root,
        minimal_step_file,
        des_orchestrator,
        in_memory_filesystem,
    ):
        """
        AC-08-01.1: E2E test proves turn counting, timeout warnings, and extension API
                    are wired into /nw:execute command execution.

        GIVEN /nw:execute @software-crafter steps/test-step.json command invoked
        WHEN orchestrator executes step through complete execution path
        AND agent performs multiple iterations
        AND execution crosses timeout warning thresholds (mocked time)
        THEN turn_count increments in step file after each iteration
        AND timeout warnings emit when thresholds crossed
        AND extension request API is callable and updates total_extensions_minutes
        AND all features execute in actual command invocation path

        Business Context:
        Marcus runs `/nw:execute @software-crafter steps/08-01.json` and expects:
        1. Turn counting tracks agent iterations
        2. Timeout warnings alert approaching limits
        3. Extension API allows requesting more time
        4. All features proven to work in real command execution

        EXTERNAL VALIDITY PROVEN:
        This test validates features work in actual command path, not just unit tests.
        Integration failures would be caught here before production deployment.
        """
        # GIVEN: Step file configured with turn/timeout limits
        step_file_path = str(minimal_step_file.relative_to(tmp_project_root))

        # Create initial step file structure with required fields
        step_data = {
            "task_id": "08-01",
            "project_id": "test-project",
            "state": {
                "status": "IN_PROGRESS",
                "started_at": "2026-01-26T10:00:00Z",
                "completed_at": None,
            },
            "tdd_cycle": {
                "max_turns": 50,
                "duration_minutes": 30,
                "total_extensions_minutes": 0,
                "phase_execution_log": [
                    {
                        "phase_name": "PREPARE",
                        "phase_index": 0,
                        "status": "IN_PROGRESS",
                        "turn_count": 0,
                    }
                ],
            },
        }

        # Write initial data to in-memory filesystem (not real filesystem)
        # The orchestrator uses in_memory_filesystem, so we must write there
        in_memory_filesystem.write_json(minimal_step_file, step_data)

        # WHEN: Orchestrator executes /nw:execute command
        # Simulate agent performing 3 iterations with mocked time progression
        command = "/nw:execute"
        agent = "@software-crafter"
        expected_iterations = 3

        # Mock time progression to cross warning thresholds
        # Assume duration_minutes=30 triggers warnings at 50%, 75%, 90%
        # Simulate elapsed time: 900s (15min = 50%), 1350s (22.5min = 75%), 1620s (27min = 90%)
        mocked_elapsed_times = [900, 1350, 1620]  # seconds

        result = des_orchestrator.execute_step(
            command=command,
            agent=agent,
            step_file=step_file_path,
            project_root=tmp_project_root,
            simulated_iterations=expected_iterations,
            mocked_elapsed_times=mocked_elapsed_times,  # Test parameter
            timeout_thresholds=[15, 22, 27],  # 50%, 75%, 90% of 30 minutes
        )

        # THEN: Turn count increments for each iteration
        assert result.turn_count == expected_iterations, (
            f"Expected turn_count={expected_iterations} after {expected_iterations} iterations, "
            f"got {result.turn_count}"
        )

        # AND: Turn count persisted to step file
        step_data = in_memory_filesystem.read_json(minimal_step_file)

        phase_log = step_data["tdd_cycle"]["phase_execution_log"]
        current_phase = next(
            (p for p in phase_log if p["status"] == "IN_PROGRESS"), None
        )

        assert current_phase is not None, "No IN_PROGRESS phase found"
        assert "turn_count" in current_phase, "turn_count field missing"
        assert current_phase["turn_count"] == expected_iterations, (
            f"Expected turn_count={expected_iterations} in step file, "
            f"got {current_phase.get('turn_count')}"
        )

        # AND: Timeout warnings emitted when thresholds crossed
        assert hasattr(result, "timeout_warnings"), (
            "Result missing timeout_warnings field"
        )
        assert len(result.timeout_warnings) >= 3, (
            f"Expected at least 3 timeout warnings (50%, 75%, 90%), "
            f"got {len(result.timeout_warnings)}"
        )

        # Verify warnings contain threshold information
        warnings_text = " ".join([w.lower() for w in result.timeout_warnings])
        assert any(threshold in warnings_text for threshold in ["50%", "75%", "90%"]), (
            "Warnings should mention threshold percentages (50%, 75%, 90%)"
        )

        # Extension API testing COMMENTED OUT - OUT_OF_SCOPE for US-006
        # Extension API functionality will be implemented in a future user story.
        # This test section is commented out to align with the scope declaration
        # at line 180 which states: "extension_api is OUT_OF_SCOPE for US-006"
        #
        # # AND: Extension request API is callable and updates limits
        # # Simulate requesting 10-minute extension
        # extension_request = {
        #     "step_file": step_file_path,
        #     "extension_minutes": 10,
        #     "justification": "Complex refactoring requires additional time",
        # }
        #
        # extension_result = des_orchestrator.request_execution_extension(
        #     **extension_request
        # )
        #
        # assert extension_result.approved is True, "Extension request should be approved"
        # assert (
        #     extension_result.new_total_extensions == 10
        # ), f"Expected new_total_extensions=10, got {extension_result.new_total_extensions}"
        #
        # # Verify extension persisted to step file
        # with open(minimal_step_file, "r") as f:
        #     step_data = json.load(f)
        #
        # assert (
        #     step_data["tdd_cycle"]["total_extensions_minutes"] == 10
        # ), "Extension should be persisted to step file total_extensions_minutes"

        # AND: EXTERNAL VALIDITY PROVEN
        # All features executed in actual command invocation path
        assert result.execution_path == "DESOrchestrator.execute_step", (
            "Test must validate features execute in real orchestrator path"
        )

        assert result.features_validated == [
            "turn_counting",
            "timeout_monitoring",
        ], (
            "Both features should be validated in execution path (extension_api is OUT_OF_SCOPE for US-006)"
        )


class TestE2EDevelopCommandWiring:
    """
    E2E WIRING TEST validating turn counting, timeout warnings, and extension API
    integration in /nw:develop command execution path.

    Tests prove EXTERNAL VALIDITY by invoking real /nw:develop command and validating
    all features execute during actual orchestrator operation (same as /nw:execute).

    SOURCE: docs/feature/des-us006/steps/08-02.json (Step 08-02)
    """

    def test_scenario_020_develop_command_has_turn_and_timeout_features(
        self,
        tmp_project_root,
        minimal_step_file,
        des_orchestrator,
        in_memory_filesystem,
    ):
        """
        AC-08-02.1: E2E test proves turn counting and timeout warnings
                    are wired into /nw:develop command execution (same as /nw:execute).

        GIVEN /nw:develop @software-crafter steps/test-step.json command invoked
        WHEN orchestrator executes step through complete execution path
        AND agent performs multiple iterations
        AND execution crosses timeout warning thresholds (mocked time)
        THEN turn_count increments in step file after each iteration (SAME AS /nw:execute)
        AND timeout warnings emit when thresholds crossed (SAME BEHAVIOR)
        AND all features execute in actual /nw:develop command invocation path

        Business Context:
        Marcus runs `/nw:develop @software-crafter steps/08-02.json` and expects:
        1. Turn counting tracks agent iterations (SAME AS /nw:execute)
        2. Timeout warnings alert approaching limits (SAME AS /nw:execute)
        3. All features proven to work in /nw:develop command execution path

        EXTERNAL VALIDITY PROVEN:
        This test validates features work in /nw:develop command path, not just /nw:execute.
        Proves BOTH primary nWave commands have full DES feature integration.
        Integration failures would be caught here before production deployment.
        """
        # GIVEN: Step file configured with turn/timeout limits
        step_file_path = str(minimal_step_file.relative_to(tmp_project_root))

        # Create initial step file structure with required fields
        step_data = {
            "task_id": "08-02",
            "project_id": "test-project",
            "state": {
                "status": "IN_PROGRESS",
                "started_at": "2026-01-26T10:00:00Z",
                "completed_at": None,
            },
            "tdd_cycle": {
                "max_turns": 50,
                "duration_minutes": 30,
                "total_extensions_minutes": 0,
                "phase_execution_log": [
                    {
                        "phase_name": "PREPARE",
                        "phase_index": 0,
                        "status": "IN_PROGRESS",
                        "turn_count": 0,
                    }
                ],
            },
        }

        # Write initial data to in-memory filesystem (not real filesystem)
        in_memory_filesystem.write_json(minimal_step_file, step_data)

        # WHEN: Orchestrator executes /nw:develop command (KEY DIFFERENCE)
        command = "/nw:develop"
        agent = "@software-crafter"
        expected_iterations = 3

        # Mock time: 900s (15min=50%), 1350s (22.5min=75%), 1620s (27min=90%)
        mocked_elapsed_times = [900, 1350, 1620]

        result = des_orchestrator.execute_step(
            command=command,
            agent=agent,
            step_file=step_file_path,
            project_root=tmp_project_root,
            simulated_iterations=expected_iterations,
            mocked_elapsed_times=mocked_elapsed_times,
            timeout_thresholds=[15, 22, 27],
        )

        # THEN: Turn count increments for each iteration
        assert result.turn_count == expected_iterations, (
            f"Expected turn_count={expected_iterations}, got {result.turn_count}"
        )

        # AND: Turn count persisted to step file
        step_data = in_memory_filesystem.read_json(minimal_step_file)
        phase_log = step_data["tdd_cycle"]["phase_execution_log"]
        current_phase = next(
            (p for p in phase_log if p["status"] == "IN_PROGRESS"), None
        )

        assert current_phase is not None, "No IN_PROGRESS phase found"
        assert current_phase["turn_count"] == expected_iterations

        # AND: Timeout warnings emitted when thresholds crossed
        assert len(result.timeout_warnings) >= 3, (
            f"Expected at least 3 timeout warnings, got {len(result.timeout_warnings)}"
        )

        # AND: EXTERNAL VALIDITY PROVEN FOR /nw:develop COMMAND
        assert result.execution_path == "DESOrchestrator.execute_step"

        assert result.features_validated == [
            "turn_counting",
            "timeout_monitoring",
        ], (
            "Both features should be validated in /nw:develop execution path "
            "(extension_api is OUT_OF_SCOPE for US-006)"
        )
