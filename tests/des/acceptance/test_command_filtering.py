"""
E2E Acceptance Test: US-001 Command-Origin Task Filtering

PERSONA: Marcus (Senior Developer)
STORY: As a senior developer, I want only /nw:execute and /nw:develop commands
       to trigger DES validation so that I don't get validation overhead on
       research/review tasks.

ACCEPTANCE CRITERIA: AC-001.1
  GIVEN I invoke /nw:execute with a step file
  WHEN the orchestrator prepares the Task prompt
  THEN the prompt MUST include <!-- DES-VALIDATION: required --> marker
  AND the prompt MUST include <!-- DES-STEP-FILE: [path] --> marker

BUSINESS VALUE:
- Marcus can explore freely without validation overhead
- Command-driven workflows get full validation protection
- Clear separation between exploration and production work

SOURCE:
- docs/feature/des/discuss/user-stories.md (US-001)
- docs/feature/des/discuss/acceptance-criteria.md (Scenario 1)
- docs/feature/des/design/architecture-design.md (Section 4.1)
"""


class TestCommandOriginFiltering:
    """
    E2E acceptance tests for command-origin filtering.

    Validates that DES correctly identifies and tags command-originated
    Task invocations while allowing ad-hoc exploration to bypass validation.
    """

    def test_execute_command_includes_des_validation_marker(
        self, in_memory_filesystem, des_orchestrator
    ):
        """
        GIVEN /nw:execute command invoked with step file path
        WHEN orchestrator renders Task prompt for sub-agent
        THEN prompt contains DES-VALIDATION marker

        Business Context:
        Marcus runs `/nw:execute @software-crafter steps/01-01.json` to implement
        a feature. The orchestrator must tag this as requiring DES validation
        so that Gate 1 validates all 14 TDD phases are in the prompt.

        Expected Markers:
        - <!-- DES-VALIDATION: required -->
        - <!-- DES-STEP-FILE: steps/01-01.json -->
        - <!-- DES-ORIGIN: command:/nw:execute -->
        """
        from pathlib import Path

        # GIVEN: /nw:execute command invoked with step file (no real filesystem access)
        command = "/nw:execute"
        agent = "@software-crafter"
        step_file = "steps/01-01.json"
        project_root = Path("/project")

        # WHEN: Orchestrator renders Task prompt
        # NOTE: No step file seeding needed - render_prompt doesn't read file
        prompt = des_orchestrator.render_prompt(
            command=command,
            agent=agent,
            step_file=step_file,
            project_root=project_root,
        )

        # THEN: Prompt contains DES validation markers
        assert "<!-- DES-VALIDATION: required -->" in prompt, (
            "DES validation marker missing - Gate 1 validation will not trigger"
        )

        assert f"<!-- DES-STEP-FILE: {step_file} -->" in prompt, (
            "Step file marker missing - SubagentStop hook cannot locate step file"
        )

        assert "<!-- DES-ORIGIN: command:/nw:execute -->" in prompt, (
            "Origin marker missing - audit trail cannot track command source"
        )

    def test_ad_hoc_task_bypasses_des_validation(self, des_orchestrator):
        """
        GIVEN Marcus uses Task tool for ad-hoc exploration
        WHEN prompt is generated without DES command context
        THEN prompt does NOT contain DES-VALIDATION marker

        Business Context:
        Marcus wants quick research: Task(prompt="Find all uses of UserRepository").
        This should execute immediately without DES validation overhead.
        No step file, no TDD phases, no validation gates.

        Expected Result:
        - NO <!-- DES-VALIDATION: required --> marker
        - NO <!-- DES-STEP-FILE: ... --> marker
        - Task executes immediately
        """
        # GIVEN: Ad-hoc Task invocation (not from nWave command)
        prompt_text = "Find all uses of UserRepository in the codebase"

        # WHEN: Orchestrator prepares ad-hoc prompt (no filesystem access)
        prompt = des_orchestrator.prepare_ad_hoc_prompt(
            prompt=prompt_text, project_root=None
        )

        # THEN: No DES markers present
        assert "<!-- DES-VALIDATION: required -->" not in prompt, (
            "Ad-hoc tasks should not trigger DES validation"
        )

        assert "<!-- DES-STEP-FILE:" not in prompt, (
            "Ad-hoc tasks have no step file association"
        )

        assert "<!-- DES-ORIGIN:" not in prompt, (
            "Ad-hoc tasks have no command origin tracking"
        )

    def test_research_command_skips_full_validation(self, des_orchestrator):
        """
        GIVEN Marcus invokes /nw:research for exploration
        WHEN orchestrator prepares Task prompt
        THEN prompt does NOT include full DES validation requirements

        Business Context:
        Marcus runs `/nw:research "authentication patterns"` to explore approaches.
        Research commands are exploratory, not production work.
        Should not enforce TDD phases or quality gates.

        Expected Result:
        - NO DES-VALIDATION marker (or marked as "none")
        - Task executes without 14-phase validation
        - Lightweight execution for fast exploration
        """
        # GIVEN: /nw:research command invoked
        command = "/nw:research"
        research_topic = "authentication patterns"

        # WHEN: Orchestrator renders research prompt (no filesystem access)
        prompt = des_orchestrator.render_prompt(
            command=command, topic=research_topic, project_root=None
        )

        # THEN: NO DES validation markers (validation_level = "none")
        # Architecture decision (v1.6.0, line 417): Research commands bypass ALL validation
        # Research commands grouped with ad-hoc tasks - no markers, no overhead
        assert "<!-- DES-VALIDATION:" not in prompt, (
            "Research commands must have NO DES-VALIDATION marker (validation_level='none')"
        )

        # No step file required for research
        assert "<!-- DES-STEP-FILE:" not in prompt, (
            "Research commands do not use step files"
        )

    def test_develop_command_includes_des_validation_marker(
        self, in_memory_filesystem, des_orchestrator
    ):
        """
        GIVEN /nw:develop command invoked with step file
        WHEN orchestrator renders Task prompt
        THEN prompt contains DES validation markers (same as execute)

        Business Context:
        Marcus runs `/nw:develop "implement UserRepository.save()"`.
        Develop command is production work requiring full TDD enforcement.
        Should have same validation requirements as /nw:execute.

        Expected Markers:
        - <!-- DES-VALIDATION: required -->
        - <!-- DES-STEP-FILE: steps/01-01.json -->
        - <!-- DES-ORIGIN: command:/nw:develop -->
        """
        from pathlib import Path

        # GIVEN: /nw:develop command invoked with step file (no real filesystem access)
        command = "/nw:develop"
        agent = "@software-crafter"
        step_file = "steps/01-01.json"
        project_root = Path("/project")

        # WHEN: Orchestrator renders develop prompt
        # NOTE: No step file seeding needed - render_prompt doesn't read file
        prompt = des_orchestrator.render_prompt(
            command=command,
            agent=agent,
            step_file=step_file,
            project_root=project_root,
        )

        # THEN: Full DES validation required (same as execute)
        assert "<!-- DES-VALIDATION: required -->" in prompt, (
            "Develop command requires full DES validation"
        )

        assert f"<!-- DES-STEP-FILE: {step_file} -->" in prompt, (
            "Develop command must reference step file for state tracking"
        )

        assert "<!-- DES-ORIGIN: command:/nw:develop -->" in prompt, (
            "Origin must be tracked for audit trail"
        )
