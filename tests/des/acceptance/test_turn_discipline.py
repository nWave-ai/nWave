"""
E2E Acceptance Tests: US-006 Turn Discipline Without max_turns

PERSONA: Marcus (Senior Developer)
STORY: As a senior developer, I want DES to include turn discipline instructions
       in every prompt so that agents self-regulate their execution time even
       though max_turns is unavailable.

PROBLEM: Task tool doesn't accept max_turns parameter (it's CLI-only). Without
         a turn limit, an agent could loop indefinitely trying to fix an
         unfixable issue. Marcus needs a mechanism to prevent runaway execution.

SOLUTION: TIMEOUT_INSTRUCTION section in every DES-validated prompt that includes:
          - Turn budget guidance (~50 turns)
          - Progress checkpoints (turn ~10, ~25, ~40, ~50)
          - Early exit protocol
          - Turn count logging at phase transitions

BUSINESS VALUE:
- Prevents runaway agent execution that could waste compute resources
- Enables graceful degradation when agents get stuck
- Provides visibility into agent progress through checkpoints
- Allows Marcus to review and provide guidance on partial completions

SOURCE:
- docs/feature/des/discuss/user-stories.md (US-006)
- docs/feature/des/discuss/acceptance-criteria.md (Scenarios 15-17)
- docs/design/deterministic-execution-system-design.md (Section 4.3)
"""


class TestTurnDisciplineInclusion:
    """
    E2E acceptance tests for TIMEOUT_INSTRUCTION section inclusion.

    Validates that DES-validated prompts contain turn discipline instructions
    to enable agent self-regulation without programmatic turn limits.
    """

    # PREPARE phase: Remove @pytest.mark.skip to enable test
    def test_scenario_001_des_validated_prompt_includes_timeout_instruction_section(
        self, tmp_project_root, minimal_step_file, des_orchestrator
    ):
        """
        AC-006.1: All DES-validated prompts include TIMEOUT_INSTRUCTION section.

        GIVEN /nw:execute command invoked with step file
        WHEN orchestrator renders the full Task prompt
        THEN prompt contains TIMEOUT_INSTRUCTION section header

        Business Context:
        Marcus runs `/nw:execute @software-crafter steps/01-01.json`.
        The prompt must include turn discipline so the agent knows to
        self-regulate and exit gracefully if stuck.

        Without this section, agents could loop indefinitely trying to fix
        an unfixable test, wasting compute and blocking Marcus's workflow.
        """
        # GIVEN: /nw:execute command with step file
        command = "/nw:execute"
        agent = "@software-crafter"
        step_file_path = str(minimal_step_file.relative_to(tmp_project_root))

        # WHEN: Orchestrator renders full Task prompt
        # NOTE: This will fail until DELIVER wave implements full prompt rendering
        prompt = des_orchestrator.render_full_prompt(
            command=command,
            agent=agent,
            step_file=step_file_path,
            project_root=tmp_project_root,
        )

        # THEN: Prompt contains TIMEOUT_INSTRUCTION section
        assert "TIMEOUT_INSTRUCTION" in prompt, (
            "TIMEOUT_INSTRUCTION section missing - agents cannot self-regulate without turn discipline"
        )

        # Verify section is properly formatted with header marker
        assert (
            "## TIMEOUT_INSTRUCTION" in prompt or "# TIMEOUT_INSTRUCTION" in prompt
        ), "TIMEOUT_INSTRUCTION must be a proper section header (## or #)"

    def test_scenario_002_timeout_instruction_specifies_turn_budget(
        self, tmp_project_root, minimal_step_file, des_orchestrator
    ):
        """
        AC-006.2: Turn budget (approximately 50) is specified in instructions.

        GIVEN /nw:execute command invoked with step file
        WHEN orchestrator renders the full Task prompt
        THEN TIMEOUT_INSTRUCTION section specifies ~50 turn budget

        Business Context:
        The 50-turn budget is based on empirical observation of typical step
        completion times. Most steps complete in 30-45 turns. The 50-turn
        limit provides buffer while preventing infinite loops.

        Example instruction:
        "Aim to complete this task within approximately 50 turns."
        """
        # GIVEN: /nw:execute command with step file
        command = "/nw:execute"
        step_file_path = str(minimal_step_file.relative_to(tmp_project_root))

        # WHEN: Orchestrator renders full Task prompt
        prompt = des_orchestrator.render_full_prompt(
            command=command,
            agent="@software-crafter",
            step_file=step_file_path,
            project_root=tmp_project_root,
        )

        # THEN: Turn budget of ~50 is specified
        # Accept variations: "50 turns", "approximately 50", "~50"
        turn_budget_patterns = ["50 turn", "approximately 50", "~50", "around 50"]
        budget_found = any(
            pattern in prompt.lower() for pattern in turn_budget_patterns
        )

        assert budget_found, (
            "Turn budget (~50) not specified in TIMEOUT_INSTRUCTION. "
            "Agents need explicit budget to know when to exit gracefully."
        )

    def test_scenario_003_timeout_instruction_defines_progress_checkpoints(
        self, tmp_project_root, minimal_step_file, des_orchestrator
    ):
        """
        AC-006.3: Progress checkpoints are defined (turn ~10, ~25, ~40, ~50).

        GIVEN /nw:execute command invoked with step file
        WHEN orchestrator renders the full Task prompt
        THEN TIMEOUT_INSTRUCTION section defines progress checkpoints

        Business Context:
        Checkpoints help agents (and Marcus reviewing transcripts) understand
        if execution is on track:
        - Turn ~10: PREPARE and RED phases should be complete
        - Turn ~25: GREEN phases should be complete
        - Turn ~40: REFACTOR phases should be complete
        - Turn ~50: COMMIT phase starting (finishing on time)

        If an agent is at turn 40 but still in RED phase, it knows something
        is wrong and should consider early exit.
        """
        # GIVEN: /nw:execute command with step file
        command = "/nw:execute"
        step_file_path = str(minimal_step_file.relative_to(tmp_project_root))

        # WHEN: Orchestrator renders full Task prompt
        prompt = des_orchestrator.render_full_prompt(
            command=command,
            agent="@software-crafter",
            step_file=step_file_path,
            project_root=tmp_project_root,
        )

        # THEN: Progress checkpoints are defined
        # Must mention at least the key checkpoint turns
        checkpoint_indicators = [
            # Must mention turn numbers with phase expectations
            "turn 10" in prompt.lower() or "~10" in prompt,
            "turn 25" in prompt.lower() or "~25" in prompt,
            "turn 40" in prompt.lower() or "~40" in prompt,
        ]

        assert any(checkpoint_indicators), (
            "Progress checkpoints not defined in TIMEOUT_INSTRUCTION. "
            "Expected checkpoints at turn ~10, ~25, ~40 to help agents track progress."
        )

        # Verify checkpoints are associated with phases
        phase_checkpoint_terms = ["prepare", "red", "green", "refactor", "commit"]
        phase_found = any(term in prompt.lower() for term in phase_checkpoint_terms)

        assert phase_found, (
            "Checkpoints must be associated with TDD phases "
            "(e.g., 'Turn ~10: PREPARE and RED phases complete')"
        )

    def test_scenario_004_timeout_instruction_documents_early_exit_protocol(
        self, tmp_project_root, minimal_step_file, des_orchestrator
    ):
        """
        AC-006.4: Early exit protocol is documented in prompt.

        GIVEN /nw:execute command invoked with step file
        WHEN orchestrator renders the full Task prompt
        THEN TIMEOUT_INSTRUCTION section documents early exit protocol

        Business Context:
        When an agent realizes it cannot complete within the turn budget,
        it needs clear instructions on how to exit gracefully:
        1. Save current progress to step file
        2. Set current phase to IN_PROGRESS with notes
        3. Return with status "PARTIAL_COMPLETION"
        4. Explain what's blocking completion

        This allows Marcus to review and provide guidance rather than
        having the agent spin indefinitely.
        """
        # GIVEN: /nw:execute command with step file
        command = "/nw:execute"
        step_file_path = str(minimal_step_file.relative_to(tmp_project_root))

        # WHEN: Orchestrator renders full Task prompt
        prompt = des_orchestrator.render_full_prompt(
            command=command,
            agent="@software-crafter",
            step_file=step_file_path,
            project_root=tmp_project_root,
        )

        # THEN: Early exit protocol is documented
        early_exit_indicators = [
            "early exit" in prompt.lower(),
            "cannot complete" in prompt.lower(),
            "save progress" in prompt.lower(),
            "partial" in prompt.lower(),
            "stuck" in prompt.lower(),
            "return" in prompt.lower() and "budget" in prompt.lower(),
        ]

        assert any(early_exit_indicators), (
            "Early exit protocol not documented in TIMEOUT_INSTRUCTION. "
            "Agents need explicit guidance on how to exit gracefully when stuck."
        )

        # Verify protocol mentions saving state
        state_save_terms = ["save", "progress", "in_progress", "notes", "update"]
        state_guidance = any(term in prompt.lower() for term in state_save_terms)

        assert state_guidance, (
            "Early exit protocol must include state-saving guidance "
            "(save progress, update step file, set phase to IN_PROGRESS)"
        )

    def test_scenario_005_timeout_instruction_requires_turn_count_logging(
        self, tmp_project_root, minimal_step_file, des_orchestrator
    ):
        """
        AC-006.5: Prompt instructs agent to log turn count at each phase transition.

        GIVEN /nw:execute command invoked with step file
        WHEN orchestrator renders the full Task prompt
        THEN TIMEOUT_INSTRUCTION instructs agent to log turn count at phase transitions

        Business Context:
        Turn count logging serves two purposes:
        1. Agent self-awareness: Tracking progress against budget
        2. Audit trail: Marcus can review transcript to see execution pacing

        Example log format:
        "[Turn 15] Starting GREEN_UNIT phase"
        "[Turn 32] Completed REFACTOR_L2 phase"

        This helps identify if certain phases are consuming too many turns.
        """
        # GIVEN: /nw:execute command with step file
        command = "/nw:execute"
        step_file_path = str(minimal_step_file.relative_to(tmp_project_root))

        # WHEN: Orchestrator renders full Task prompt
        prompt = des_orchestrator.render_full_prompt(
            command=command,
            agent="@software-crafter",
            step_file=step_file_path,
            project_root=tmp_project_root,
        )

        # THEN: Turn count logging instruction is present
        logging_indicators = [
            "log" in prompt.lower() and "turn" in prompt.lower(),
            "record" in prompt.lower() and "turn" in prompt.lower(),
            "track" in prompt.lower() and "turn" in prompt.lower(),
            "[turn" in prompt.lower(),  # Example format
        ]

        assert any(logging_indicators), (
            "Turn count logging not required in TIMEOUT_INSTRUCTION. "
            "Agents must log turn count at phase transitions for visibility."
        )

        # Verify logging is associated with phase transitions
        transition_terms = ["phase", "transition", "start", "complete", "begin", "end"]
        transition_guidance = any(term in prompt.lower() for term in transition_terms)

        assert transition_guidance, (
            "Turn logging must be associated with phase transitions "
            "(e.g., 'Log turn count when starting/completing each phase')"
        )


class TestTurnDisciplineNonValidationCommands:
    """
    Tests verifying that non-validation commands do NOT receive TIMEOUT_INSTRUCTION.

    Ad-hoc and research commands bypass DES validation entirely, so they
    should not have turn discipline overhead.
    """

    def test_scenario_006_ad_hoc_task_has_no_timeout_instruction(
        self, tmp_project_root, des_orchestrator
    ):
        """
        GIVEN Marcus uses Task tool for ad-hoc exploration
        WHEN prompt is generated without DES command context
        THEN prompt does NOT contain TIMEOUT_INSTRUCTION section

        Business Context:
        Ad-hoc exploration tasks like "Find all uses of UserRepository"
        should execute immediately without turn discipline overhead.
        These are quick research tasks, not production TDD workflows.
        """
        # GIVEN: Ad-hoc Task invocation
        prompt_text = "Find all uses of UserRepository in the codebase"

        # WHEN: Orchestrator prepares ad-hoc prompt
        prompt = des_orchestrator.prepare_ad_hoc_prompt(
            prompt=prompt_text, project_root=tmp_project_root
        )

        # THEN: No TIMEOUT_INSTRUCTION section
        assert "TIMEOUT_INSTRUCTION" not in prompt, (
            "Ad-hoc tasks should not have TIMEOUT_INSTRUCTION - no turn discipline needed"
        )

    def test_scenario_007_research_command_has_no_timeout_instruction(
        self, tmp_project_root, des_orchestrator
    ):
        """
        GIVEN Marcus invokes /nw:research for exploration
        WHEN orchestrator prepares Task prompt
        THEN prompt does NOT contain TIMEOUT_INSTRUCTION section

        Business Context:
        Research commands are exploratory, not production work.
        They should not have turn discipline overhead since
        they bypass DES validation entirely.
        """
        # GIVEN: /nw:research command
        command = "/nw:research"
        research_topic = "authentication patterns"

        # WHEN: Orchestrator renders research prompt
        prompt = des_orchestrator.render_prompt(
            command=command, topic=research_topic, project_root=tmp_project_root
        )

        # THEN: No TIMEOUT_INSTRUCTION section
        assert "TIMEOUT_INSTRUCTION" not in prompt, (
            "Research commands should not have TIMEOUT_INSTRUCTION - exploratory only"
        )


class TestTurnDisciplineValidation:
    """
    Tests for TIMEOUT_INSTRUCTION validation during pre-invocation checks.

    Per US-002, TIMEOUT_INSTRUCTION is one of 9 mandatory sections.
    These tests verify validation correctly handles its presence/absence.
    """

    def test_scenario_008_missing_timeout_instruction_blocks_invocation(
        self, tmp_project_root, minimal_step_file
    ):
        """
        GIVEN orchestrator generates prompt missing TIMEOUT_INSTRUCTION
        WHEN pre-invocation validation runs
        THEN validation FAILS with specific error message
        AND Task invocation is BLOCKED

        Business Context:
        Without turn discipline, agents could run indefinitely.
        Pre-invocation validation must catch missing TIMEOUT_INSTRUCTION
        before Task tool is invoked.

        Expected Error:
        "MISSING: Mandatory section 'TIMEOUT_INSTRUCTION' not found"
        """
        from des.application.prompt_validator import PromptValidator

        # GIVEN: Prompt missing TIMEOUT_INSTRUCTION
        incomplete_prompt = """
        <!-- DES-VALIDATION: required -->
        <!-- DES-STEP-FILE: steps/01-01.json -->

        ## DES_METADATA
        step_id: 01-01

        ## AGENT_IDENTITY
        You are software-crafter

        ## TASK_CONTEXT
        Implement feature X

        ## TDD_PHASES
        PREPARE, RED_ACCEPTANCE, RED_UNIT, GREEN_UNIT, CHECK_ACCEPTANCE,
        GREEN_ACCEPTANCE, REVIEW, REFACTOR_L1, REFACTOR_L2, REFACTOR_L3,
        REFACTOR_L4, POST_REFACTOR_REVIEW, FINAL_VALIDATE, COMMIT

        ## QUALITY_GATES
        G1-G6 definitions here

        ## OUTCOME_RECORDING
        Record outcomes in step file

        ## BOUNDARY_RULES
        ALLOWED: step file modifications
        FORBIDDEN: other file modifications

        <!-- NOTE: TIMEOUT_INSTRUCTION intentionally omitted -->
        """

        # WHEN: Pre-invocation validation runs
        validator = PromptValidator()
        result = validator.validate(incomplete_prompt)

        # THEN: Validation fails with specific error
        assert not result.is_valid, (
            "Validation should FAIL when TIMEOUT_INSTRUCTION is missing"
        )

        assert any("TIMEOUT_INSTRUCTION" in error for error in result.errors), (
            "Error message must identify TIMEOUT_INSTRUCTION as the missing section"
        )

        assert any("MISSING" in error.upper() for error in result.errors), (
            "Error should indicate the section is MISSING, not incomplete"
        )


class TestTurnDisciplineContent:
    """
    Tests verifying the content and format of TIMEOUT_INSTRUCTION section.

    These tests ensure the section contains all required elements in
    a format that agents can parse and follow.
    """

    def test_scenario_009_timeout_instruction_has_complete_structure(
        self, tmp_project_root, minimal_step_file, des_orchestrator
    ):
        """
        GIVEN /nw:execute command with step file
        WHEN orchestrator renders full prompt
        THEN TIMEOUT_INSTRUCTION contains all required elements:
             - Turn budget (~50)
             - Progress checkpoints
             - Early exit protocol
             - Turn logging instruction

        Business Context:
        This is a comprehensive test verifying the complete structure
        of TIMEOUT_INSTRUCTION. All elements must be present for
        effective agent self-regulation.
        """
        # GIVEN: /nw:execute command
        command = "/nw:execute"
        step_file_path = str(minimal_step_file.relative_to(tmp_project_root))

        # WHEN: Orchestrator renders full prompt
        prompt = des_orchestrator.render_full_prompt(
            command=command,
            agent="@software-crafter",
            step_file=step_file_path,
            project_root=tmp_project_root,
        )

        # THEN: All required elements present
        # Extract TIMEOUT_INSTRUCTION section for detailed analysis
        assert "TIMEOUT_INSTRUCTION" in prompt, "Section header missing"

        # Element 1: Turn budget
        budget_present = "50" in prompt and "turn" in prompt.lower()
        assert budget_present, "Turn budget (~50) missing"

        # Element 2: Checkpoints (at least one checkpoint reference)
        checkpoint_present = any(
            marker in prompt
            for marker in ["~10", "~25", "~40", "turn 10", "turn 25", "turn 40"]
        )
        assert checkpoint_present, "Progress checkpoints missing"

        # Element 3: Early exit protocol
        early_exit_present = (
            "cannot complete" in prompt.lower()
            or "early exit" in prompt.lower()
            or "save progress" in prompt.lower()
            or "stuck" in prompt.lower()
        )
        assert early_exit_present, "Early exit protocol missing"

        # Element 4: Turn logging
        logging_present = "log" in prompt.lower() and (
            "turn" in prompt.lower() or "phase" in prompt.lower()
        )
        assert logging_present, "Turn logging instruction missing"

    def test_scenario_010_develop_command_also_includes_timeout_instruction(
        self, tmp_project_root, minimal_step_file, des_orchestrator
    ):
        """
        GIVEN /nw:develop command with step file
        WHEN orchestrator renders full prompt
        THEN prompt includes TIMEOUT_INSTRUCTION (same as execute)

        Business Context:
        Both /nw:execute and /nw:develop are production workflows
        requiring full DES validation. The TIMEOUT_INSTRUCTION must
        be present for both command types.
        """
        # GIVEN: /nw:develop command
        command = "/nw:develop"
        step_file_path = str(minimal_step_file.relative_to(tmp_project_root))

        # WHEN: Orchestrator renders full prompt
        prompt = des_orchestrator.render_full_prompt(
            command=command,
            agent="@software-crafter",
            step_file=step_file_path,
            project_root=tmp_project_root,
        )

        # THEN: TIMEOUT_INSTRUCTION present
        assert "TIMEOUT_INSTRUCTION" in prompt, (
            "/nw:develop command must include TIMEOUT_INSTRUCTION like /nw:execute"
        )

        # Verify it has the same structure as execute command
        assert "50" in prompt, "Turn budget must be specified for develop command"

    def test_scenario_013_timeout_warnings_emit_at_thresholds(
        self,
        tmp_project_root,
        minimal_step_file,
        des_orchestrator,
        in_memory_filesystem,
    ):
        """
        GIVEN execute_step() with timeout_thresholds=[20, 30, 36] and 40-minute budget
        WHEN execution crosses thresholds at 50%, 75%, 90% elapsed
        THEN warnings_emitted contains threshold warnings with remaining time

        Business Context:
        Agents need proactive warnings at configurable thresholds (50%, 75%, 90%)
        to self-regulate execution and complete work before timeout.
        """
        # GIVEN: Step file with phase in IN_PROGRESS state
        step_file_path = str(minimal_step_file.relative_to(tmp_project_root))

        step_data = {
            "task_id": "06-01",
            "project_id": "test-project",
            "state": {"status": "IN_PROGRESS"},
            "tdd_cycle": {
                "phase_execution_log": [
                    {
                        "phase_name": "GREEN",
                        "status": "IN_PROGRESS",
                        "started_at": "2026-01-26T09:35:00Z",
                    }
                ],
            },
        }

        in_memory_filesystem.write_json(minimal_step_file, step_data)

        # WHEN: Execute step with mocked elapsed times crossing thresholds
        # Mocked elapsed times simulate 5 iterations: 15, 21, 26, 31, 37 minutes
        result = des_orchestrator.execute_step(
            command="/nw:execute",
            agent="@software-crafter",
            step_file=step_file_path,
            project_root=tmp_project_root,
            simulated_iterations=5,
            timeout_thresholds=[20, 30, 36],
            mocked_elapsed_times=[900, 1260, 1560, 1860, 2220],
        )

        # THEN: Warnings emitted for crossed thresholds
        assert len(result.warnings_emitted) > 0, (
            "Should emit warnings for crossed thresholds"
        )

        # Verify threshold warning was emitted (at least one)
        threshold_warning = next(
            (
                w
                for w in result.warnings_emitted
                if "threshold" in w.lower() or "timeout" in w.lower()
            ),
            None,
        )
        assert threshold_warning is not None, (
            "Should emit warning for crossed threshold"
        )

    def test_scenario_014_agent_receives_timeout_warnings_in_prompt(
        self,
        tmp_project_root,
        minimal_step_file,
        des_orchestrator,
        in_memory_filesystem,
    ):
        """
        GIVEN phase execution has crossed 75% threshold
        WHEN agent receives next turn prompt
        THEN prompt includes timeout warning with threshold info

        Business Context:
        Warnings must be visible in agent prompt context so agents can
        adjust strategy (complete current work, skip optional steps, etc.)
        """
        # GIVEN: Step file with phase in IN_PROGRESS state
        step_file_path = str(minimal_step_file.relative_to(tmp_project_root))

        step_data = {
            "task_id": "06-01",
            "project_id": "test-project",
            "state": {"status": "IN_PROGRESS"},
            "tdd_cycle": {
                "phase_execution_log": [
                    {
                        "phase_name": "GREEN",
                        "status": "IN_PROGRESS",
                        "started_at": "2026-01-26T09:28:00Z",
                    }
                ],
            },
        }

        in_memory_filesystem.write_json(minimal_step_file, step_data)

        # WHEN: Execute step with mocked elapsed times crossing 75% threshold (30 min)
        # Mocked: 3 iterations at 28, 31, 37 minutes elapsed
        result = des_orchestrator.execute_step(
            command="/nw:execute",
            agent="@software-crafter",
            step_file=step_file_path,
            project_root=tmp_project_root,
            simulated_iterations=3,
            timeout_thresholds=[20, 30, 36],
            mocked_elapsed_times=[1680, 1860, 2220],
        )

        # THEN: Warning format includes threshold and remaining time
        assert len(result.warnings_emitted) > 0, "Should emit timeout warnings"

        # Find 30-minute threshold warning
        warning_30 = next(
            (w for w in result.warnings_emitted if "30" in w),
            None,
        )
        assert warning_30 is not None, "Should emit warning for 30-minute threshold"

        # Verify warning contains useful information
        warning_lower = warning_30.lower()
        assert "30" in warning_30, "Warning should include threshold value (30 min)"
        assert "minute" in warning_lower or "min" in warning_lower, (
            "Warning should include time unit"
        )
