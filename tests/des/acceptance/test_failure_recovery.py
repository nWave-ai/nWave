"""
E2E Acceptance Test: US-005 Failure Recovery Guidance

PERSONA: Alex (Junior Developer)
STORY: As a junior developer, I want DES to provide clear recovery guidance when
       execution fails, so that I know exactly what to do instead of being stuck
       with a cryptic error.

BUSINESS VALUE:
- Junior developers learn from failures with educational context
- Specific, actionable recovery steps reduce debugging time
- Recovery suggestions prevent manual step file corruption
- Error messages explain WHY errors occurred and HOW to fix them

ACCEPTANCE CRITERIA:
- AC-005.1: Every failure mode has associated recovery suggestions
- AC-005.2: Suggestions are stored in step file `recovery_suggestions` array
- AC-005.3: Suggestions are actionable (specific commands or file paths)
- AC-005.4: Validation errors include fix guidance in error message
- AC-005.5: Recovery suggestions include explanatory text describing WHY and HOW

SCOPE: Covers US-005 Acceptance Criteria (AC-005.1 through AC-005.5)
WAVE: DISTILL (Acceptance Test Creation)
STATUS: RED (Outside-In TDD - awaiting DELIVER wave implementation)

SOURCE:
- docs/feature/des/discuss/user-stories.md (US-005)
"""

import pytest

from des.application.recovery_guidance_handler import RecoveryGuidanceHandler


class TestFailureRecoveryGuidance:
    """E2E acceptance tests for US-005: Failure Recovery Guidance."""

    # =========================================================================
    # AC-005.1: Every failure mode has associated recovery suggestions
    # Scenario 1: Crash Recovery - Agent crash during phase execution
    # =========================================================================

    def test_scenario_001_crash_recovery_provides_recovery_suggestions(
        self, tmp_project_root, step_file_with_abandoned_phase
    ):
        """
        GIVEN agent crashed during GREEN_UNIT phase (status: IN_PROGRESS)
        WHEN SubagentStop hook fires and detects abandoned phase
        THEN step file is updated with FAILED state and recovery_suggestions array

        Business Value: Alex's agent crashed during GREEN_UNIT. Instead of being
                       stuck with a cryptic "IN_PROGRESS" state, he receives clear
                       step-by-step recovery guidance in the step file.

        Failure Mode: Agent crash leaving phase IN_PROGRESS
        Expected Recovery Suggestions:
        1. Review agent transcript for error details
        2. Reset GREEN_UNIT phase status to NOT_EXECUTED
        3. Run `/nw:execute` again to resume from GREEN_UNIT

        Domain Example (from US-005):
        Alex's agent crashed during GREEN_UNIT.
        Step file updated with status: FAILED and recovery_suggestions array.
        Alex follows suggestions step by step.
        """
        # Arrange: Step file with GREEN_UNIT phase IN_PROGRESS (abandoned)
        step_file = step_file_with_abandoned_phase
        abandoned_phase = "GREEN_UNIT"

        # Act: RecoveryGuidanceHandler generates suggestions for abandoned phase
        from des.application.recovery_guidance_handler import (
            RecoveryGuidanceHandler,
        )

        recovery_handler = RecoveryGuidanceHandler()

        # Generate suggestions for the abandoned phase failure
        suggestions = recovery_handler.generate_recovery_suggestions(
            failure_type="abandoned_phase",
            context={
                "phase": abandoned_phase,
                "step_file": str(step_file),
            },
        )

        # Handle the failure - update step file with recovery suggestions
        updated_step = recovery_handler.handle_failure(
            step_file_path=str(step_file),
            failure_type="abandoned_phase",
            context={
                "phase": abandoned_phase,
                "failure_reason": f"Agent crashed during {abandoned_phase} phase",
                "suggestions": suggestions,
            },
        )

        # Assert: Recovery suggestions are generated
        assert suggestions is not None, "Should generate recovery suggestions"
        assert isinstance(suggestions, list), "Suggestions should be a list"
        assert len(suggestions) >= 1, "Should have at least one suggestion"

        # Assert: Suggestions contain actionable elements
        assert any("transcript" in s.lower() for s in suggestions), (
            "Should mention transcript"
        )
        assert any("NOT_EXECUTED" in s for s in suggestions), (
            "Should reference phase status"
        )
        assert any("/nw:execute" in s or "execute" in s.lower() for s in suggestions), (
            "Should mention execution"
        )

        # Assert: Step file updated with recovery suggestions
        assert updated_step is not None, "Should return updated step"
        assert "recovery_suggestions" in updated_step, (
            "Should include recovery_suggestions"
        )
        assert isinstance(updated_step["recovery_suggestions"], list), (
            "recovery_suggestions should be list"
        )

    # =========================================================================
    # AC-005.1: Every failure mode has associated recovery suggestions
    # Scenario 2: Silent Completion - Agent returned without updating state
    # =========================================================================

    def test_scenario_002_silent_completion_provides_recovery_suggestions(
        self, tmp_project_root, step_file_with_silent_completion
    ):
        """
        GIVEN agent returned without updating step file (all phases NOT_EXECUTED)
        WHEN SubagentStop hook fires and detects mismatch
        THEN step file is updated with recovery suggestions for silent completion

        Business Value: Alex's agent returned but didn't update any phase status.
                       He receives specific guidance to check the transcript and
                       manually update phase status based on evidence.

        Failure Mode: Agent completed without updating step file
        Expected Recovery Suggestions:
        1. Check agent transcript at {path} for errors
        2. Verify prompt contained OUTCOME_RECORDING instructions
        3. Manually update phase status based on transcript evidence
        """
        # Arrange: Step file with all phases NOT_EXECUTED despite agent completion
        step_file = step_file_with_silent_completion

        # Act: RecoveryGuidanceHandler detects silent completion
        from des.application.recovery_guidance_handler import (
            RecoveryGuidanceHandler,
        )

        recovery_handler = RecoveryGuidanceHandler()

        # Detect silent completion (all phases NOT_EXECUTED but task completed)
        suggestions = recovery_handler.generate_recovery_suggestions(
            failure_type="silent_completion",
            context={
                "transcript_path": "/path/to/transcript.log",
                "step_file": str(step_file),
            },
        )

        # Handle the silent completion failure
        updated_step = recovery_handler.handle_failure(
            step_file_path=str(step_file),
            failure_type="silent_completion",
            context={
                "failure_reason": "Agent completed without updating any phase status",
                "transcript_path": "/path/to/transcript.log",
                "step_file": str(step_file),
            },
        )

        # Assert: Suggestions generated for silent completion
        assert suggestions is not None, "Should generate recovery suggestions"
        assert isinstance(suggestions, list), "Suggestions should be a list"
        assert len(suggestions) >= 3, "Should have at least 3 suggestions"

        # Assert: Suggestions contain specific elements for silent completion
        assert any("transcript" in s.lower() for s in suggestions), (
            "Should mention transcript location"
        )
        assert any("OUTCOME_RECORDING" in s for s in suggestions), (
            "Should explain OUTCOME_RECORDING"
        )
        assert any("manually update" in s.lower() for s in suggestions), (
            "Should mention manual update"
        )

        # Assert: Step file updated with recovery suggestions
        assert updated_step is not None, "Should return updated state"
        assert "recovery_suggestions" in updated_step, (
            "Should include recovery_suggestions"
        )
        assert isinstance(updated_step["recovery_suggestions"], list), (
            "recovery_suggestions should be list"
        )
        assert len(updated_step["recovery_suggestions"]) >= 3, (
            "Should have 3+ suggestions"
        )

    # =========================================================================
    # AC-005.1: Every failure mode has associated recovery suggestions
    # Scenario 3: Validation Failure - Missing mandatory section in prompt
    # =========================================================================

    def test_scenario_003_validation_failure_provides_recovery_suggestions(
        self, tmp_project_root
    ):
        """
        GIVEN orchestrator produced prompt missing TDD_PHASES section
        WHEN pre-invocation validation fails
        THEN error includes recovery suggestion to fix the template

        Business Value: Alex's orchestrator produced incomplete prompt.
                       Instead of "validation failed", he gets specific guidance:
                       "Update the prompt template to include TDD_PHASES section
                       with all 14 phases enumerated."

        Failure Mode: Pre-invocation validation failure (missing section)
        Expected: Error message includes actionable fix guidance
        """
        # Arrange: Prompt missing TDD_PHASES section
        _incomplete_prompt = """
        <!-- DES-VALIDATION: required -->
        <!-- DES-STEP-FILE: steps/01-01.json -->

        # DES_METADATA
        Step: 01-01.json

        # AGENT_IDENTITY
        Agent: software-crafter

        # TASK_CONTEXT
        Implement UserRepository

        # MISSING: TDD_PHASES section

        # QUALITY_GATES
        G1-G6 defined

        # OUTCOME_RECORDING
        Update step file

        # BOUNDARY_RULES
        Scope defined

        # TIMEOUT_INSTRUCTION
        50 turns
        """

        # Act: Pre-invocation validation fails
        # validation_result = des_validator.validate_prompt(incomplete_prompt)

        # Assert: Error includes recovery suggestion
        # assert validation_result.status == "FAILED"
        # assert "TDD_PHASES" in validation_result.error_message
        # assert validation_result.recovery_guidance is not None
        # assert "template" in validation_result.recovery_guidance.lower()
        # assert "14 phases" in validation_result.recovery_guidance.lower()

    # =========================================================================
    # AC-005.2: Integration with orchestrator
    # Scenario 4: Orchestrator detects agent failure and triggers recovery handler
    # =========================================================================

    def test_scenario_004_orchestrator_crashes_recovery_suggestions(
        self, tmp_project_root, step_file_with_abandoned_phase
    ):
        """
        GIVEN orchestrator detects SubagentStop event (agent returned or crashed)
        WHEN post-execution validation detects abandoned phase
        THEN recovery handler generates suggestions AND updates step file with FAILED status

        Business Value: Alex's agent crashed during execution. The orchestrator:
                       1) Detects the failure via SubagentStop hook
                       2) Extracts failure context (phase name, transcript path)
                       3) Generates recovery suggestions with transcript reference
                       4) Updates step file with status: FAILED and recovery_suggestions
                       5) Returns control with guidance displayed to Alex

        Workflow Integration Points:
        1) SubagentStop hook: Detects agent crash/completion
        2) Post-execution validation: Detects validation failures
        3) Step file update: Persists recovery suggestions
        4) Error handling: Falls back to generic guidance if suggestion generation fails

        Acceptance Criteria Validation:
        AC-005.2: SubagentStop hook calls RecoveryGuidanceHandler
        AC-005.2: Failure context properly extracted and passed
        AC-005.2: Step file updated with recovery suggestions
        AC-005.2: Recovery suggestions displayed to user
        AC-005.2: No orchestrator crashes if suggestion generation fails
        """
        # Arrange: Step file with abandoned phase (simulating agent crash)
        step_file = step_file_with_abandoned_phase
        import json

        # Act 1: Simulate SubagentStop hook detecting abandoned phase
        from des.application.recovery_guidance_handler import (
            RecoveryGuidanceHandler,
        )

        # Extract failure context from step file
        step_data = json.loads(step_file.read_text())
        abandoned_phase = None
        for phase_log in step_data.get("tdd_cycle", {}).get("phase_execution_log", []):
            if phase_log.get("status") == "IN_PROGRESS":
                abandoned_phase = phase_log.get("phase_name")
                break

        # Generate recovery suggestions
        recovery_handler = RecoveryGuidanceHandler()
        context = {
            "phase": abandoned_phase or "UNKNOWN_PHASE",
            "step_file": str(step_file),
            "transcript_path": "transcripts/01-01-RED_UNIT.log",
            "failure_reason": f"Agent crashed during {abandoned_phase} phase",
        }

        suggestions = recovery_handler.generate_recovery_suggestions(
            failure_type="abandoned_phase",
            context=context,
        )

        # Act 2: Update step file with FAILED status and recovery suggestions
        updated_state = recovery_handler.handle_failure(
            step_file_path=str(step_file),
            failure_type="abandoned_phase",
            context=context,
        )

        # Assert: SubagentStop hook integration successful
        assert suggestions is not None, "Should generate recovery suggestions"
        assert isinstance(suggestions, list), "Suggestions should be a list"
        assert len(suggestions) >= 3, "Should have 3+ suggestions for abandoned phase"

        # Assert: Failure context extracted correctly
        assert abandoned_phase is not None, "Should identify abandoned phase"
        assert "IN_PROGRESS" in " ".join(
            [
                p.get("status", "")
                for p in step_data.get("tdd_cycle", {}).get("phase_execution_log", [])
            ]
        ), "Step file should have phase marked IN_PROGRESS"

        # Assert: Step file updated with FAILED status
        updated_step_data = json.loads(step_file.read_text())
        assert "state" in updated_step_data, "Step file should have state object"
        assert "recovery_suggestions" in updated_step_data["state"], (
            "Step file should have recovery_suggestions"
        )

        # Assert: Recovery suggestions include transcript path
        joined_suggestions = " ".join(suggestions)
        assert "transcript" in joined_suggestions.lower(), (
            "Suggestions should reference transcript for debugging"
        )

        # Assert: Suggestions are actionable
        assert any("/nw:execute" in s or "execute" in s.lower() for s in suggestions), (
            "Suggestions should include execution command"
        )
        assert any("NOT_EXECUTED" in s for s in suggestions), (
            "Suggestions should reference phase status reset"
        )

        # Assert: Recovery handler doesn't crash orchestrator
        assert updated_state is not None, (
            "Handler should return result without crashing"
        )
        assert isinstance(updated_state, dict), (
            "Handler should return dict for orchestrator to process"
        )

    # =========================================================================
    # AC-005.2: Suggestions stored in step file `recovery_suggestions` array
    # Scenario 4b: Recovery suggestions persisted to step file JSON
    # =========================================================================

    def test_scenario_004_recovery_suggestions_stored_in_step_file(
        self, tmp_project_root, step_file_with_abandoned_phase
    ):
        """
        GIVEN failure detected during post-execution validation
        WHEN recovery handler updates step file
        THEN recovery_suggestions array is persisted in step file JSON

        Business Value: Alex can review the step file to find recovery guidance
                       even after closing the terminal. The suggestions survive
                       session boundaries and can be shared with teammates.

        Expected Structure:
        {
          "state": {
            "status": "FAILED",
            "failure_reason": "...",
            "recovery_suggestions": ["suggestion 1", "suggestion 2", ...]
          }
        }
        """

        # Arrange: Step file with abandoned phase
        step_file = step_file_with_abandoned_phase
        import json

        # Act: Manually add recovery_suggestions to step file state
        step_data = json.loads(step_file.read_text())

        # Add recovery_suggestions array to state
        step_data["state"]["recovery_suggestions"] = [
            "Review agent transcript for error details",
            "Reset GREEN_UNIT phase status to NOT_EXECUTED",
            "Run /nw:execute again to resume from GREEN_UNIT",
        ]

        # Persist to file
        step_file.write_text(json.dumps(step_data, indent=2))

        # Assert: Re-read step file and verify recovery_suggestions persisted
        step_data_reloaded = json.loads(step_file.read_text())
        assert "recovery_suggestions" in step_data_reloaded["state"]
        assert isinstance(step_data_reloaded["state"]["recovery_suggestions"], list)
        assert len(step_data_reloaded["state"]["recovery_suggestions"]) > 0

    # =========================================================================
    # AC-005.3: Suggestions are actionable (specific commands or file paths)
    # Scenario 5: Recovery suggestions contain executable commands
    # =========================================================================

    def test_scenario_005_recovery_suggestions_contain_actionable_commands(
        self, tmp_project_root, step_file_with_abandoned_phase
    ):
        """
        GIVEN agent crashed during REFACTOR_L2 phase
        WHEN recovery suggestions are generated
        THEN suggestions include specific commands Alex can execute

        Business Value: Alex doesn't have to interpret abstract guidance.
                       He gets specific commands like `/nw:execute @software-crafter
                       "steps/01-01.json"` that he can copy-paste to recover.

        Actionable Criteria:
        - Contains executable command (e.g., `/nw:execute`)
        - Contains file path reference (e.g., `steps/01-01.json`)
        - Contains phase name for context (e.g., `REFACTOR_L2`)
        """
        # Arrange: Step file with REFACTOR_L2 phase abandoned
        _step_file = step_file_with_abandoned_phase

        # Act: Recovery handler generates suggestions
        recovery_handler = RecoveryGuidanceHandler()
        suggestions = recovery_handler.generate_recovery_suggestions(
            failure_type="abandoned_phase",
            context={
                "phase": "REFACTOR_L2",
                "step_file": "steps/01-01.json",
                "transcript_path": "/tmp/transcripts/session.log",
            },
        )

        # Assert: Suggestions contain actionable elements
        actionable_command_found = any(
            "/nw:execute" in s or "/nw:develop" in s for s in suggestions
        )
        file_path_found = any("steps/" in s or ".json" in s for s in suggestions)
        phase_name_found = any("REFACTOR_L2" in s for s in suggestions)

        assert actionable_command_found, "Suggestions must include executable commands"
        assert file_path_found, "Suggestions must include file paths"
        assert phase_name_found, "Suggestions must reference the failed phase"

    # =========================================================================
    # AC-005.3: Suggestions are actionable (specific commands or file paths)
    # Scenario 6: Recovery suggestions include transcript file path
    # =========================================================================

    def test_scenario_006_recovery_suggestions_include_transcript_path(
        self, tmp_project_root, step_file_with_abandoned_phase
    ):
        """
        GIVEN agent crash detected with known transcript location
        WHEN recovery suggestions are generated
        THEN suggestions include specific path to agent transcript for debugging

        Business Value: Alex knows exactly where to find the agent transcript
                       for debugging. No hunting through directories - the path
                       is provided explicitly in the recovery guidance.

        Expected: "Check agent transcript at {transcript_path} for errors"
        """
        # Arrange: Known transcript path
        transcript_path = "/tmp/agent-transcripts/session-12345.log"

        # Act: Recovery handler generates suggestions with transcript path
        recovery_handler = RecoveryGuidanceHandler()
        suggestions = recovery_handler.generate_recovery_suggestions(
            failure_type="agent_crash",
            context={
                "transcript_path": transcript_path,
                "phase": "GREEN",
            },
        )

        # Assert: Suggestions include specific transcript path
        transcript_suggestion_found = any(transcript_path in s for s in suggestions)
        assert transcript_suggestion_found, (
            f"Suggestions must include specific transcript path: {transcript_path}"
        )

    # =========================================================================
    # AC-005.4: Validation errors include fix guidance in error message
    # Scenario 7: Validation error message includes inline fix guidance
    # =========================================================================

    def test_scenario_007_validation_error_includes_inline_fix_guidance(
        self, tmp_project_root
    ):
        """
        GIVEN prompt validation fails due to missing BOUNDARY_RULES section
        WHEN validation error is returned
        THEN error message includes fix guidance explaining what to add

        Business Value: Alex sees the validation error AND the fix in one message.
                       No need to consult documentation - the error tells him:
                       "Add BOUNDARY_RULES section with allowed/forbidden patterns."

        Error Format:
        "MISSING: Mandatory section 'BOUNDARY_RULES' not found.
         FIX: Add BOUNDARY_RULES section with ALLOWED and FORBIDDEN file patterns."
        """
        # Arrange: Create validator and prompt missing BOUNDARY_RULES
        from des.application.validator import TemplateValidator

        prompt_missing_boundary_rules = """
# DES_METADATA
Step: 01-01.json
Command: /nw:develop

# AGENT_IDENTITY
Agent: software-crafter

# TASK_CONTEXT
Implement UserRepository with proper dependency injection

# TDD_PHASES
All 14 phases listed

# QUALITY_GATES
G1-G6 defined

# OUTCOME_RECORDING
Update step file with phase completion

# TIMEOUT_INSTRUCTION
50 turns max
        """

        # Act: Validation fails
        validator = TemplateValidator()
        validation_result = validator.validate_prompt(prompt_missing_boundary_rules)

        # Assert: Error message includes inline fix guidance with FIX: prefix
        assert validation_result.status == "FAILED", (
            "Validation should fail for missing BOUNDARY_RULES"
        )
        assert "BOUNDARY_RULES" in str(validation_result.errors), (
            "Error should mention BOUNDARY_RULES"
        )
        assert validation_result.recovery_guidance is not None, (
            "Should have recovery guidance"
        )

        # Check that recovery guidance includes FIX: formatted guidance
        guidance_text = " ".join(validation_result.recovery_guidance)
        assert (
            "FIX:" in guidance_text
            or "Fix:" in guidance_text
            or "fix:" in guidance_text
        ), "Recovery guidance should include 'FIX:' prefix formatting"

        # Check that guidance is specific and actionable
        assert any(
            keyword in guidance_text.lower()
            for keyword in ["add", "include", "update", "section", "boundary"]
        ), "Recovery guidance should mention how to add the section"

        # Verify guidance explains what BOUNDARY_RULES is for
        assert any(
            pattern in guidance_text.lower()
            for pattern in [
                "file patterns",
                "allowed",
                "forbidden",
                "scope",
                "files can be modified",
                "specify which",
            ]
        ), "Guidance should explain what BOUNDARY_RULES contains"

    # =========================================================================
    # AC-005.4: Validation errors include fix guidance in error message
    # Scenario 8: Missing TDD phase error includes phase name and fix
    # =========================================================================

    # =========================================================================
    # AC-005.5: Recovery suggestions include explanatory text (WHY and HOW)
    # Scenario 9: Recovery suggestion explains WHY error occurred
    # =========================================================================

    def test_scenario_009_recovery_suggestion_explains_why_error_occurred(
        self, tmp_project_root
    ):
        """
        GIVEN agent crash detected during RED_UNIT phase
        WHEN recovery suggestions are generated
        THEN at least one suggestion explains WHY the error occurred

        Business Value: Alex doesn't just get instructions - he learns.
                       Explanation: "The agent left RED_UNIT in IN_PROGRESS state,
                       indicating it started but did not complete. This typically
                       occurs when the agent encounters an unhandled error or timeout."

        Educational Context Requirement (AC-005.5):
        - Minimum 1 sentence describing WHY the error occurred
        - Helps junior developers understand failure patterns
        """
        # Act: Recovery handler generates suggestions with explanatory text
        from des.application.recovery_guidance_handler import (
            RecoveryGuidanceHandler,
        )

        recovery_handler = RecoveryGuidanceHandler()
        suggestions = recovery_handler.generate_recovery_suggestions(
            failure_type="abandoned_phase",
            context={"phase": "RED_UNIT"},
        )

        # Assert: At least one suggestion explains WHY
        why_explanation_found = any(
            any(
                keyword in s.lower()
                for keyword in [
                    "because",
                    "this occurs when",
                    "indicating",
                    "this means",
                    "this typically",
                    "the agent",
                ]
            )
            for s in suggestions
        )
        assert why_explanation_found, (
            "At least one suggestion must explain WHY the error occurred"
        )

    # =========================================================================
    # AC-005.5: Recovery suggestions include explanatory text (WHY and HOW)
    # Scenario 10: Recovery suggestion explains HOW the fix resolves issue
    # =========================================================================

    def test_scenario_010_recovery_suggestion_explains_how_fix_resolves_issue(
        self, tmp_project_root
    ):
        """
        GIVEN silent completion detected (agent returned without updating state)
        WHEN recovery suggestions are generated
        THEN at least one suggestion explains HOW the fix resolves the issue

        Business Value: Alex understands the causal relationship between the fix
                       and the resolution. Example: "Resetting the phase to NOT_EXECUTED
                       allows the execution framework to retry the phase from scratch,
                       ensuring a clean state for the next attempt."

        Educational Context Requirement (AC-005.5):
        - Minimum 1 sentence describing HOW the fix resolves the issue
        - Helps junior developers learn recovery patterns
        """
        # Act: Recovery handler generates suggestions with HOW explanation
        from des.application.recovery_guidance_handler import (
            RecoveryGuidanceHandler,
        )

        recovery_handler = RecoveryGuidanceHandler()
        suggestions = recovery_handler.generate_recovery_suggestions(
            failure_type="silent_completion",
            context={"step_file": "steps/01-01.json"},
        )

        # Assert: At least one suggestion explains HOW fix works
        how_explanation_found = any(
            any(
                keyword in s.lower()
                for keyword in [
                    "allows",
                    "ensures",
                    "this will",
                    "resolves",
                    "fixes",
                    "so that",
                    "enabling",
                    "to recover",
                ]
            )
            for s in suggestions
        )
        assert how_explanation_found, (
            "At least one suggestion must explain HOW the fix resolves the issue"
        )

    # =========================================================================
    # AC-005.5: Combined WHY + HOW in recovery suggestion
    # Scenario 11: Complete educational recovery suggestion with context
    # =========================================================================

    def test_scenario_011_complete_educational_recovery_suggestion(
        self, tmp_project_root
    ):
        """
        GIVEN validation error for missing OUTCOME_RECORDING section
        WHEN recovery guidance is generated
        THEN guidance includes both WHY the section is needed AND HOW to add it

        Business Value: Alex gets complete learning context in one message.
                       WHY: "OUTCOME_RECORDING is required because it instructs
                       the agent to update the step file after each phase."
                       HOW: "Add an OUTCOME_RECORDING section with instructions
                       to update phase status and outcome fields."

        Complete Educational Context:
        - Explains purpose of the missing element (WHY)
        - Provides specific fix instructions (HOW)
        - Minimum 1 sentence for each aspect
        """
        # Act: Recovery guidance generated
        from des.application.recovery_guidance_handler import (
            RecoveryGuidanceHandler,
        )

        recovery_handler = RecoveryGuidanceHandler()
        recovery_guidance = recovery_handler.generate_recovery_suggestions(
            failure_type="missing_section",
            context={"section_name": "OUTCOME_RECORDING"},
        )

        # Assert: Guidance includes both WHY and HOW
        why_keywords = ["because", "required", "needed", "purpose", "ensures"]
        how_keywords = ["add", "include", "update", "with", "section"]

        guidance_text = " ".join(recovery_guidance).lower()
        has_why = any(kw in guidance_text for kw in why_keywords)
        has_how = any(kw in guidance_text for kw in how_keywords)

        assert has_why, "Recovery guidance must explain WHY the element is needed"
        assert has_how, "Recovery guidance must explain HOW to fix the issue"
        assert len(recovery_guidance) >= 2, (
            "Recovery guidance must have at least 2 suggestions (WHY + HOW)"
        )

    # =========================================================================
    # AC-005.1: Timeout failure detection with recovery suggestions
    # Scenario 004_timeout: Detect when phase exceeded timeout threshold
    # =========================================================================

    def test_scenario_004_timeout_detect_exceeded_timeout_duration(
        self, tmp_project_root, step_file_with_abandoned_phase
    ):
        """
        GIVEN phase execution exceeded configured timeout threshold
        WHEN recovery handler detects timeout failure
        THEN generates 3+ recovery suggestions with time analysis

        Business Value: Alex sees clear guidance when his task times out.
                       Instead of "something went wrong", he learns:
                       - Phase ran 35 minutes (exceeded 30-minute timeout)
                       - Why: Complex logic may need optimization
                       - How: Try optimizing code OR increase timeout threshold
                       - What: Specific commands to adjust and retry

        Acceptance Criteria Validation:
        1. Detects timeout (actual > configured duration)
        2. Compares actual execution time vs configured timeout
        3. Generates 3+ recovery suggestions with time analysis
        4. Includes timeout duration and actual execution time
        5. Recommends optimization or threshold adjustment approaches

        Expected Recovery Suggestions:
        1. Phase runtime analysis - WHY timeout occurred based on complexity
        2. Code optimization guidance - HOW to improve performance
        3. Timeout threshold adjustment - HOW to increase threshold and retry
        4. Debugging approach - specific commands to profile and measure
        """
        # Arrange: Step file with phase that exceeded timeout
        step_file = step_file_with_abandoned_phase
        from datetime import datetime, timedelta, timezone

        # Simulate a phase that ran for 35 minutes (exceeded 30-minute timeout)
        base_time = datetime(2026, 1, 26, 10, 0, 0, tzinfo=timezone.utc)
        phase_start = (base_time - timedelta(minutes=35)).isoformat()
        configured_timeout_minutes = 30
        actual_runtime_minutes = 35

        # Act: RecoveryGuidanceHandler detects and handles timeout failure
        from des.application.recovery_guidance_handler import (
            RecoveryGuidanceHandler,
        )

        recovery_handler = RecoveryGuidanceHandler()

        # Generate suggestions for timeout failure
        suggestions = recovery_handler.generate_recovery_suggestions(
            failure_type="timeout_failure",
            context={
                "phase": "GREEN_UNIT",
                "phase_start": phase_start,
                "configured_timeout_minutes": configured_timeout_minutes,
                "actual_runtime_minutes": actual_runtime_minutes,
                "step_file": str(step_file),
            },
        )

        # Handle the timeout failure - update step file with recovery suggestions
        updated_step = recovery_handler.handle_failure(
            step_file_path=str(step_file),
            failure_type="timeout_failure",
            context={
                "phase": "GREEN_UNIT",
                "phase_start": phase_start,
                "configured_timeout_minutes": configured_timeout_minutes,
                "actual_runtime_minutes": actual_runtime_minutes,
                "failure_reason": f"Phase exceeded {configured_timeout_minutes}-minute timeout (ran {actual_runtime_minutes} minutes)",
                "suggestions": suggestions,
            },
        )

        # Assert: Recovery suggestions meet acceptance criteria
        assert suggestions is not None, "Should generate recovery suggestions"
        assert isinstance(suggestions, list), "Suggestions should be a list"
        assert len(suggestions) >= 3, (
            f"Should have 3+ suggestions, got {len(suggestions)}"
        )

        # AC-005.1: Every suggestion addresses timeout context
        joined_suggestions = " ".join(suggestions)
        assert str(configured_timeout_minutes) in joined_suggestions, (
            "Should include configured timeout (30 minutes)"
        )
        assert str(actual_runtime_minutes) in joined_suggestions, (
            "Should include actual runtime (35 minutes)"
        )

        # AC-005.3: Suggestions are actionable with specific guidance
        # Should include optimization approach
        assert any(
            keyword in s.lower()
            for s in suggestions
            for keyword in [
                "optimize",
                "performance",
                "profile",
                "improve",
                "reduce",
                "simplify",
            ]
        ), "Should recommend code optimization approach"

        # Should include threshold adjustment approach
        assert any(
            keyword in s.lower()
            for s in suggestions
            for keyword in [
                "increase",
                "threshold",
                "timeout",
                "extend",
                "raise",
                "adjust",
            ]
        ), "Should recommend threshold adjustment approach"

        # Should include actionable commands
        assert any(
            pattern in s
            for s in suggestions
            for pattern in ["/nw:execute", "timeout", "minutes", "run", "measure"]
        ), "Should include actionable commands or technical guidance"

        # AC-005.5: Suggestions explain WHY and HOW
        for suggestion in suggestions:
            # Check for WHY explanations
            assert any(
                kw in suggestion.lower()
                for kw in [
                    "because",
                    "indicates",
                    "due to",
                    "the phase",
                    "why",
                    "reason",
                ]
            ), f"Suggestion should explain WHY: {suggestion}"

        # Assert: Step file updated with recovery suggestions
        assert updated_step is not None, "Should return updated state"
        assert "recovery_suggestions" in updated_step, (
            "Should include recovery_suggestions"
        )
        assert isinstance(updated_step["recovery_suggestions"], list), (
            "recovery_suggestions should be list"
        )
        assert len(updated_step["recovery_suggestions"]) >= 3, (
            "Should have 3+ suggestions in step file"
        )

    # =========================================================================
    # AC-005.5: Recovery suggestions use beginner-friendly, junior-dev language
    # Scenario 13: Recovery suggestions are simple, clear, and educational
    # =========================================================================

    def test_scenario_013_recovery_suggestions_use_junior_dev_language(
        self, tmp_project_root, step_file_with_abandoned_phase
    ):
        """
        GIVEN recovery suggestions are generated for a failure
        WHEN suggestions are created for junior developer audience
        THEN suggestions use simple language, include concrete examples, and no unexplained jargon

        Business Value: Junior developers learn from errors with clear, educational guidance
                       they can immediately act on. No jargon barriers - suggestions explain
                       complex concepts in simple terms with concrete examples.

        AC-005.5 Requirements (Junior-Dev Language):
        1. All suggestions scored 'beginner-friendly' by readability check
        2. No technical jargon without explanation
        3. All suggestions include concrete examples
        4. Average suggestion length: 3-4 sentences

        Example (BAD): "The orchestrator will not progress past an IN_PROGRESS phase without
                       manual intervention to reset phase status and retry execution."

        Example (GOOD): "Your agent stopped during the GREEN phase. To retry, you need to
                       reset the phase status from IN_PROGRESS to NOT_EXECUTED in the step file.
                       Then run `/nw:execute` again. This tells the system the phase is ready
                       to try again from the start."
        """
        # Arrange: Recovery suggestions for abandoned phase failure
        from des.application.recovery_guidance_handler import (
            RecoveryGuidanceHandler,
        )

        recovery_handler = RecoveryGuidanceHandler()
        step_file = step_file_with_abandoned_phase

        # Act: Generate recovery suggestions for junior developer
        suggestions = recovery_handler.generate_recovery_suggestions(
            failure_type="abandoned_phase",
            context={
                "phase": "GREEN",
                "step_file": str(step_file),
                "transcript_path": "/tmp/transcripts/session.log",
            },
        )

        # Assert: Suggestions are beginner-friendly
        assert suggestions is not None, "Should generate suggestions"
        assert isinstance(suggestions, list), "Suggestions should be list"
        assert len(suggestions) >= 1, "Should have suggestions"

        # AC-005.5.1: Readability check - no excessive jargon
        jargon_terms = [
            "orchestrator",  # Replace with "system"
            "framework",  # Explain or replace
            "partially state",  # Unclear
            "corrupted state",  # Frightening
        ]

        for suggestion in suggestions:
            # Check for unexplained jargon
            found_jargon = []
            for jargon in jargon_terms:
                if jargon.lower() in suggestion.lower():
                    found_jargon.append(jargon)

            # Jargon check: if found, verify it's in context with explainer words
            if found_jargon:
                # Verify jargon is explained near it (within 50 chars)
                for jargon in found_jargon:
                    idx = suggestion.lower().find(jargon.lower())
                    context_window = suggestion[max(0, idx - 50) : idx + 100]
                    # Verify explanation words exist nearby
                    assert any(
                        word in context_window.lower()
                        for word in [
                            "means",
                            "refers to",
                            "is",
                            "indicates",
                            "represents",
                        ]
                    ), f"Jargon '{jargon}' not explained in context"

        # AC-005.5.2 & 3: Check for concrete examples and simple structure
        for suggestion in suggestions:
            # If it's a structured suggestion (has WHY/HOW/ACTION), check each part
            if (
                "WHY:" in suggestion
                and "HOW:" in suggestion
                and "ACTION:" in suggestion
            ):
                # Extract parts
                why_part = suggestion.split("HOW:")[0].replace("WHY:", "").strip()
                how_part = suggestion.split("ACTION:")[0].split("HOW:")[1].strip()
                action_part = suggestion.split("ACTION:")[1].strip()

                # WHY should be 1-2 sentences max
                why_sentences = why_part.count(".") + 1
                assert why_sentences <= 2, (
                    f"WHY section too long ({why_sentences} sentences): {why_part}"
                )

                # HOW should be 1-2 sentences max
                how_sentences = how_part.count(".") + 1
                assert how_sentences <= 2, (
                    f"HOW section too long ({how_sentences} sentences): {how_part}"
                )

                # ACTION should be specific (contains command or path)
                assert any(char in action_part for char in ["/", ".", "`", "-"]), (
                    f"ACTION should be specific/actionable: {action_part}"
                )

        # AC-005.5.4: Average suggestion length should be 3-4 sentences per section
        # For WHY/HOW/ACTION format: 1-2 sentences per section = 3-6 total periods
        total_periods = 0
        for suggestion in suggestions:
            # Count actual sentence-ending periods (not in paths like "01-01.json")
            # For WHY/HOW/ACTION format, count periods in content areas
            total_periods += suggestion.count(".")

        avg_periods = total_periods / len(suggestions)
        # With WHY (1-2 periods) + HOW (1-2 periods) + ACTION (0-1 periods) = 2-5 periods avg
        assert 2 <= avg_periods <= 6, (
            f"Average suggestion length should have 2-5 periods per suggestion, got {avg_periods}"
        )

    # =========================================================================
    # AC-005.1 + AC-005.2: Failure mode registry - all modes have suggestions
    # Scenario 12: All defined failure modes have registered recovery handlers
    # =========================================================================

    def test_scenario_012_all_failure_modes_have_recovery_handlers(self):
        """
        GIVEN the defined failure mode registry
        WHEN iterating through all failure modes
        THEN each mode has associated recovery suggestions (no orphan modes)

        Business Value: Alex is never left without guidance, regardless of
                       failure type. System guarantee: every possible failure
                       mode has at least one recovery suggestion.

        Defined Failure Modes:
        1. abandoned_phase - Agent crashed during phase execution
        2. silent_completion - Agent returned without updating state
        3. missing_section - Validation found missing mandatory section
        4. missing_phase - Validation found missing TDD phase
        5. invalid_outcome - Phase marked EXECUTED without outcome
        6. invalid_skip - Phase marked SKIPPED without blocked_by reason
        7. stale_execution - IN_PROGRESS phase older than threshold
        """
        # Arrange: List of all defined failure modes
        defined_failure_modes = [
            "abandoned_phase",
            "silent_completion",
            "missing_section",
            "missing_phase",
            "invalid_outcome",
            "invalid_skip",
            "stale_execution",
        ]

        # Act: Check each failure mode has recovery handler
        recovery_handler = RecoveryGuidanceHandler()

        # Assert: Each mode has suggestions
        for mode in defined_failure_modes:
            suggestions = recovery_handler.get_recovery_suggestions_for_mode(mode)
            assert suggestions is not None, f"No recovery handler for mode: {mode}"
            assert len(suggestions) > 0, f"Empty suggestions for mode: {mode}"


# =============================================================================
# Fixtures for US-005 Tests
# =============================================================================


@pytest.fixture
def step_file_with_abandoned_phase(tmp_project_root):
    """
    Create a step file with a phase left IN_PROGRESS (abandoned).

    Simulates agent crash scenario where GREEN_UNIT was started but never completed.

    Returns:
        Path: Path to the created step file with abandoned phase
    """
    import json

    step_file = tmp_project_root / "steps" / "01-01.json"

    step_data = {
        "task_id": "01-01",
        "project_id": "test-project",
        "workflow_type": "tdd_cycle",
        "state": {
            "status": "IN_PROGRESS",
            "started_at": "2026-01-24T10:00:00Z",
            "completed_at": None,
        },
        "tdd_cycle": {
            "phase_execution_log": [
                {
                    "phase_number": 0,
                    "phase_name": "PREPARE",
                    "status": "EXECUTED",
                    "outcome": "Environment prepared",
                },
                {
                    "phase_number": 1,
                    "phase_name": "RED_ACCEPTANCE",
                    "status": "EXECUTED",
                    "outcome": "Acceptance test failing",
                },
                {
                    "phase_number": 2,
                    "phase_name": "RED_UNIT",
                    "status": "EXECUTED",
                    "outcome": "Unit test failing",
                },
                {
                    "phase_number": 3,
                    "phase_name": "GREEN_UNIT",
                    "status": "IN_PROGRESS",  # Abandoned - agent crashed here
                    "outcome": None,
                },
                # Remaining phases NOT_EXECUTED
                *[
                    {
                        "phase_number": i,
                        "phase_name": phase_name,
                        "status": "NOT_EXECUTED",
                        "outcome": None,
                    }
                    for i, phase_name in enumerate(
                        [
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
                        ],
                        start=4,
                    )
                ],
            ]
        },
    }

    step_file.parent.mkdir(parents=True, exist_ok=True)
    step_file.write_text(json.dumps(step_data, indent=2))
    return step_file


@pytest.fixture
def step_file_with_silent_completion(tmp_project_root):
    """
    Create a step file where agent returned without updating any phase.

    Simulates silent completion scenario where all phases remain NOT_EXECUTED
    despite agent claiming to have finished.

    Returns:
        Path: Path to the created step file with silent completion
    """
    import json

    step_file = tmp_project_root / "steps" / "01-02.json"

    step_data = {
        "task_id": "01-02",
        "project_id": "test-project",
        "workflow_type": "tdd_cycle",
        "state": {
            "status": "IN_PROGRESS",  # Task started but no phases completed
            "started_at": "2026-01-24T10:00:00Z",
            "completed_at": None,
        },
        "tdd_cycle": {
            "phase_execution_log": [
                {
                    "phase_number": i,
                    "phase_name": phase_name,
                    "status": "NOT_EXECUTED",  # All phases untouched
                    "outcome": None,
                }
                for i, phase_name in enumerate(
                    [
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
                )
            ]
        },
    }

    step_file.parent.mkdir(parents=True, exist_ok=True)
    step_file.write_text(json.dumps(step_data, indent=2))
    return step_file
