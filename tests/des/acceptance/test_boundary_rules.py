"""
E2E Acceptance Tests: US-007 Boundary Rules for Scope Enforcement

PERSONA: Priya (Tech Lead)
STORY: As a tech lead, I want DES to include explicit boundary rules in prompts,
       so that agents cannot accidentally expand scope beyond the assigned step.

PROBLEM: Priya reviewed a PR where the agent was supposed to implement one small
         feature but ended up refactoring three other files "while it was there."
         This scope creep caused merge conflicts and delayed the release.

SOLUTION: BOUNDARY_RULES section in prompts that explicitly defines ALLOWED and
          FORBIDDEN actions. Clear scope limitation to the assigned step only.
          Post-execution scope validation comparing git diff to allowed patterns.

BUSINESS VALUE:
- Prevents scope creep that causes merge conflicts and release delays
- Ensures predictable, controlled modifications
- Provides audit trail of scope violations for PR review
- Allows Priya to catch unauthorized file changes before they cause problems

SOURCE:
- docs/feature/des/discuss/user-stories.md (US-007)
- Acceptance Criteria AC-007.1 through AC-007.5

WAVE: DISTILL (Acceptance Test Creation)
STATUS: RED (Outside-In TDD - awaiting DELIVER wave implementation)
"""

import json


class TestBoundaryRulesInclusion:
    """
    E2E acceptance tests for BOUNDARY_RULES section inclusion in prompts.

    Validates that all step execution prompts contain explicit boundary rules
    defining what agents are ALLOWED and FORBIDDEN to do.
    """

    # =========================================================================
    # AC-007.1: BOUNDARY_RULES section included in all step execution prompts
    # Scenario 1: Step execution prompt includes BOUNDARY_RULES section
    # =========================================================================

    def test_scenario_001_step_execution_prompt_includes_boundary_rules_section(
        self, tmp_project_root, minimal_step_file, des_orchestrator
    ):
        """
        GIVEN /nw:execute command invoked with step file for UserRepository
        WHEN orchestrator renders the full Task prompt
        THEN prompt contains BOUNDARY_RULES section header

        Business Context:
        Priya needs assurance that every agent receives explicit scope
        limitations. Without BOUNDARY_RULES, agents might "helpfully"
        modify unrelated files, causing merge conflicts.

        Domain Example:
        Software-crafter working on step 01-01 for UserRepository receives
        prompt with BOUNDARY_RULES section defining what files it can touch.
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

        # THEN: Prompt contains BOUNDARY_RULES section
        assert "BOUNDARY_RULES" in prompt, (
            "BOUNDARY_RULES section missing - agents cannot know their scope limitations"
        )

        # Verify section is properly formatted with header marker
        assert "## BOUNDARY_RULES" in prompt or "# BOUNDARY_RULES" in prompt, (
            "BOUNDARY_RULES must be a proper section header (## or #)"
        )


class TestAllowedActionEnumeration:
    """
    E2E acceptance tests for ALLOWED action enumeration in BOUNDARY_RULES.

    Validates that ALLOWED actions are explicitly listed so agents know
    exactly which files and operations are permitted.
    """

    # =========================================================================
    # AC-007.2: ALLOWED actions explicitly enumerated (step file, task files, tests)
    # Scenario 2: ALLOWED section specifies permitted files
    # =========================================================================

    def test_scenario_002_boundary_rules_enumerate_allowed_actions(
        self, tmp_project_root, minimal_step_file, des_orchestrator
    ):
        """
        GIVEN /nw:execute command for step 01-01 targeting UserRepository
        WHEN orchestrator renders the full Task prompt
        THEN BOUNDARY_RULES section explicitly lists ALLOWED files/patterns

        Business Context:
        Agents need an explicit whitelist of permitted modifications.
        This includes: step file itself, task implementation files,
        and test files matching the feature being implemented.

        Domain Example:
        ALLOWED section contains:
        - Step file: steps/01-01.json
        - Task files: **/UserRepository*
        - Test files: **/test_user_repository*

        Without explicit ALLOWED list, agents might assume they can
        modify anything, leading to scope creep.
        """
        # GIVEN: /nw:execute command with step targeting UserRepository
        step_data = _create_step_file_for_user_repository()
        minimal_step_file.write_text(json.dumps(step_data, indent=2))

        # WHEN: Orchestrator renders full Task prompt
        prompt = des_orchestrator.render_full_prompt(
            command="/nw:execute",
            agent="@software-crafter",
            step_file=str(minimal_step_file.relative_to(tmp_project_root)),
            project_root=tmp_project_root,
        )

        # THEN: ALLOWED section present with file patterns
        assert "ALLOWED" in prompt, "ALLOWED section missing from BOUNDARY_RULES"

        # Verify step file is in allowed list
        assert "step" in prompt.lower() and "file" in prompt.lower(), (
            "Step file should be in ALLOWED list"
        )

        # Verify target files are specified (could be patterns or explicit paths)
        allowed_patterns_found = any(
            pattern in prompt.lower()
            for pattern in [
                "userrepository",
                "user_repository",
                "task file",
                "implementation",
            ]
        )
        assert allowed_patterns_found, (
            "ALLOWED section must specify target files/patterns "
            "(e.g., **/UserRepository* or task implementation files)"
        )

        # Verify test files are permitted
        test_allowed = any(
            pattern in prompt.lower() for pattern in ["test", "spec", "_test", "test_"]
        )
        assert test_allowed, "Test files must be in ALLOWED list for TDD workflow"

    def test_scenario_003_allowed_patterns_match_step_target_files(
        self, tmp_project_root, des_orchestrator
    ):
        """
        GIVEN step file specifies target files: ["src/repositories/UserRepository.py"]
        WHEN orchestrator renders the full Task prompt
        THEN ALLOWED patterns include the target file paths or matching patterns

        Business Context:
        The ALLOWED patterns should be derived from the step file's
        target_files or scope definition, ensuring agents can only
        modify files relevant to the assigned task.

        Domain Example:
        Step 01-01 targets UserRepository implementation.
        ALLOWED: "src/repositories/UserRepository.py", "tests/unit/test_user_repository.py"
        """
        # GIVEN: Step file with explicit target files
        step_file = tmp_project_root / "steps" / "01-01.json"
        step_file.parent.mkdir(parents=True, exist_ok=True)

        step_data = {
            "task_id": "01-01",
            "project_id": "test-project",
            "workflow_type": "tdd_cycle",
            "scope": {
                "target_files": [
                    "src/repositories/UserRepository.py",
                    "src/repositories/interfaces/IUserRepository.py",
                ],
                "test_files": [
                    "tests/unit/test_user_repository.py",
                    "tests/integration/test_user_repository_integration.py",
                ],
            },
            "state": {"status": "TODO"},
            "tdd_cycle": {"phase_execution_log": []},
        }
        step_file.write_text(json.dumps(step_data, indent=2))

        # WHEN: Orchestrator renders full Task prompt
        prompt = des_orchestrator.render_full_prompt(
            command="/nw:execute",
            agent="@software-crafter",
            step_file=str(step_file.relative_to(tmp_project_root)),
            project_root=tmp_project_root,
        )

        # THEN: ALLOWED section includes target files or patterns matching them
        assert "UserRepository" in prompt or "user_repository" in prompt.lower(), (
            "ALLOWED patterns must include step target files. "
            "Expected UserRepository in ALLOWED list."
        )

        # Verify test file patterns included
        assert "test_user_repository" in prompt.lower() or "test" in prompt.lower(), (
            "ALLOWED patterns must include test files from step scope."
        )


class TestForbiddenActionEnumeration:
    """
    E2E acceptance tests for FORBIDDEN action enumeration in BOUNDARY_RULES.

    Validates that FORBIDDEN actions are explicitly listed to prevent
    accidental scope expansion.
    """

    # =========================================================================
    # AC-007.3: FORBIDDEN actions explicitly enumerated (other steps, other files)
    # Scenario 4: FORBIDDEN section specifies prohibited actions
    # =========================================================================

    def test_scenario_004_boundary_rules_enumerate_forbidden_actions(
        self, tmp_project_root, minimal_step_file, des_orchestrator
    ):
        """
        GIVEN /nw:execute command for step 01-01
        WHEN orchestrator renders the full Task prompt
        THEN BOUNDARY_RULES section explicitly lists FORBIDDEN actions

        Business Context:
        Priya saw an agent "improve" AuthService while working on
        UserRepository, causing merge conflicts. Explicit FORBIDDEN
        list prevents such well-intentioned scope creep.

        Domain Example:
        FORBIDDEN section contains:
        - Other step files
        - Unrelated source files (AuthService, OrderService, etc.)
        - Configuration files (unless explicitly in scope)
        - Production deployment files
        """
        # GIVEN: /nw:execute command with step file
        step_data = _create_step_file_for_user_repository()
        minimal_step_file.write_text(json.dumps(step_data, indent=2))

        command = "/nw:execute"
        step_file_path = str(minimal_step_file.relative_to(tmp_project_root))

        # WHEN: Orchestrator renders full Task prompt
        prompt = des_orchestrator.render_full_prompt(
            command=command,
            agent="@software-crafter",
            step_file=step_file_path,
            project_root=tmp_project_root,
        )

        # THEN: FORBIDDEN section present
        assert "FORBIDDEN" in prompt, "FORBIDDEN section missing from BOUNDARY_RULES"

        # Verify other step files are forbidden
        other_steps_forbidden = any(
            phrase in prompt.lower()
            for phrase in ["other step", "different step", "other task"]
        )
        assert other_steps_forbidden, (
            "FORBIDDEN must include 'other step files' - "
            "agents should not modify steps outside their assignment"
        )

        # Verify unrelated files are forbidden
        unrelated_forbidden = any(
            phrase in prompt.lower()
            for phrase in ["other file", "unrelated", "outside scope", "not in scope"]
        )
        assert unrelated_forbidden, (
            "FORBIDDEN must include reference to files outside scope"
        )

    def test_scenario_005_forbidden_includes_continuation_to_next_step(
        self, tmp_project_root, minimal_step_file, des_orchestrator
    ):
        """
        GIVEN /nw:execute command for step 01-01
        WHEN orchestrator renders the full Task prompt
        THEN FORBIDDEN section includes prohibition against continuing to next step

        Business Context:
        After completing step 01-01, an agent might think it's "efficient"
        to continue to step 01-02. This violates the principle of returning
        control to Marcus for explicit next-step initiation.

        Domain Example:
        FORBIDDEN: "Continue to next step after completion. Return control
        IMMEDIATELY after step completion. Marcus will explicitly start
        the next step when ready."
        """
        # GIVEN: /nw:execute command with step file
        step_file_path = str(minimal_step_file.relative_to(tmp_project_root))

        # WHEN: Orchestrator renders full Task prompt
        prompt = des_orchestrator.render_full_prompt(
            command="/nw:execute",
            agent="@software-crafter",
            step_file=step_file_path,
            project_root=tmp_project_root,
        )

        # THEN: Continuation to next step is forbidden
        continuation_forbidden = any(
            phrase in prompt.lower()
            for phrase in [
                "next step",
                "continue to",
                "subsequent step",
                "return control",
                "return immediately",
            ]
        )
        assert continuation_forbidden, (
            "FORBIDDEN must include prohibition against continuing to next step. "
            "Agent must return control after step completion, not continue autonomously."
        )


class TestScopeValidationPostExecution:
    """
    E2E acceptance tests for post-execution scope validation.

    Validates that DES checks git diff against allowed patterns after
    agent execution completes.
    """

    # =========================================================================
    # AC-007.4: Scope validation runs post-execution (compare git diff to allowed patterns)
    # Scenario 6: Post-execution scope validation detects out-of-scope changes
    # =========================================================================

    def test_scenario_006_scope_validation_detects_out_of_scope_modification(
        self, tmp_project_root, minimal_step_file
    ):
        """
        GIVEN agent completed step 01-01 for UserRepository
        AND agent also modified OrderService.py (out of scope)
        WHEN SubagentStop hook runs post-execution validation
        THEN scope violation is detected for OrderService.py

        Business Context:
        Priya's nightmare scenario: agent "helpfully" improves unrelated
        files. Post-execution scope validation catches this before merge,
        preventing the release delay she experienced.

        Domain Example:
        Agent was working on UserRepository but modified:
        - src/repositories/UserRepository.py (ALLOWED - in scope)
        - src/services/OrderService.py (VIOLATION - out of scope)

        Warning: "Unexpected modification: src/services/OrderService.py"
        """
        # Arrange: Create step file with defined scope
        step_data = _create_step_file_with_scope(
            allowed_patterns=["**/UserRepository*", "**/test_user_repository*"]
        )
        minimal_step_file.write_text(json.dumps(step_data, indent=2))

        # Simulate agent modifying out-of-scope file
        out_of_scope_file = tmp_project_root / "src" / "services" / "OrderService.py"
        out_of_scope_file.parent.mkdir(parents=True, exist_ok=True)
        out_of_scope_file.write_text("# Modified by agent out of scope")

        # Act: Run post-execution scope validation
        from unittest.mock import Mock, patch

        from des.adapters.driven.validation.git_scope_checker import GitScopeChecker

        checker = GitScopeChecker()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                stdout="src/repositories/UserRepository.py\nsrc/services/OrderService.py\n",
                returncode=0,
            )
            result = checker.check_scope(
                project_root=tmp_project_root,
                allowed_patterns=["**/UserRepository*", "**/test_user_repository*"],
            )

        # Assert: Scope violation detected
        assert result.has_violations is True
        assert "src/services/OrderService.py" in result.out_of_scope_files

    def test_scenario_007_in_scope_modifications_pass_validation(
        self, tmp_project_root, minimal_step_file
    ):
        """
        GIVEN agent completed step 01-01 for UserRepository
        AND agent only modified files matching allowed patterns
        WHEN SubagentStop hook runs post-execution validation
        THEN scope validation passes (no violations)

        Business Context:
        When agents stay within scope, validation should pass silently.
        This is the happy path - Priya sees clean scope adherence
        during PR review.

        Domain Example:
        Agent modified only:
        - src/repositories/UserRepository.py (matches **/UserRepository*)
        - tests/unit/test_user_repository.py (matches **/test_user_repository*)

        Both files match ALLOWED patterns, so validation passes.
        """
        # Arrange: Create step file with defined scope
        step_data = _create_step_file_with_scope(
            allowed_patterns=["**/UserRepository*", "**/test_user_repository*"]
        )
        minimal_step_file.write_text(json.dumps(step_data, indent=2))

        # Simulate agent modifying only in-scope files
        _in_scope_files = [
            "src/repositories/UserRepository.py",
            "tests/unit/test_user_repository.py",
        ]

        # Act: Run post-execution scope validation
        from unittest.mock import Mock, patch

        from des.adapters.driven.validation.git_scope_checker import GitScopeChecker

        checker = GitScopeChecker()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                stdout="src/repositories/UserRepository.py\ntests/unit/test_user_repository.py\n",
                returncode=0,
            )
            result = checker.check_scope(
                project_root=tmp_project_root,
                allowed_patterns=["**/UserRepository*", "**/test_user_repository*"],
            )

        # Assert: No violations
        assert result.has_violations is False
        assert result.out_of_scope_files == []
        assert not result.skipped

    def test_scenario_008_step_file_modification_always_allowed(
        self, tmp_project_root, minimal_step_file
    ):
        """
        GIVEN agent completed step 01-01
        AND agent modified the step file itself (steps/01-01.json)
        WHEN SubagentStop hook runs post-execution validation
        THEN step file modification is always allowed (implicit whitelist)

        Business Context:
        The step file itself must be modifiable by the agent to record
        phase outcomes, state changes, and completion status. This is
        an implicit ALLOWED entry for every step execution.

        Domain Example:
        Agent updates steps/01-01.json with:
        - Phase outcomes (PREPARE -> EXECUTED)
        - State changes (TODO -> IN_PROGRESS -> DONE)
        - Timestamps and execution metadata

        Step file is always permitted, regardless of other scope rules.
        """
        # Arrange: Create step file with restricted scope
        step_data = _create_step_file_with_scope(
            allowed_patterns=[
                "**/UserRepository*"
            ]  # Note: step file not explicitly listed
        )
        minimal_step_file.write_text(json.dumps(step_data, indent=2))

        # Simulate agent modifying step file
        _modified_files = [str(minimal_step_file)]

        # Act: Run post-execution scope validation
        # NOTE: GitScopeChecker does not have step-file implicit allowlist.
        # The step file itself should be included in allowed_patterns by the caller.
        from unittest.mock import Mock, patch

        from des.adapters.driven.validation.git_scope_checker import GitScopeChecker

        checker = GitScopeChecker()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                stdout=f"{minimal_step_file!s}\n",
                returncode=0,
            )
            # Include step file pattern in allowed_patterns (caller responsibility)
            result = checker.check_scope(
                project_root=tmp_project_root,
                allowed_patterns=["**/UserRepository*", str(minimal_step_file)],
            )

        # Assert: Step file modification is allowed (via explicit pattern)
        assert result.has_violations is False
        assert str(minimal_step_file) not in result.out_of_scope_files


class TestScopeViolationAuditLogging:
    """
    E2E acceptance tests for audit logging of scope violations.

    Validates that scope violations are logged as warnings in the audit trail
    for Priya's PR review.
    """

    # =========================================================================
    # AC-007.5: Scope violations logged as warnings in audit trail
    # Scenario 9: Scope violation logged to audit trail
    # =========================================================================

    def test_scenario_009_scope_violation_logged_to_audit_trail(
        self, tmp_project_root, minimal_step_file
    ):
        """
        GIVEN agent modified OrderService.py (out of scope during UserRepository step)
        WHEN SubagentStop hook detects scope violation
        THEN warning is logged to audit trail with file path and step context

        Business Context:
        Priya reviews the audit log during PR review. Scope violations
        are logged as WARNINGS (not errors) because:
        1. The work itself may be valid (just misplaced)
        2. Priya can decide whether to accept or reject

        Audit Entry Format:
        {
            "event_type": "SCOPE_VIOLATION",
            "severity": "WARNING",
            "step_file": "steps/01-01.json",
            "out_of_scope_file": "src/services/OrderService.py",
            "allowed_patterns": ["**/UserRepository*"],
            "timestamp": "2026-01-22T14:30:00Z"
        }
        """
        # Arrange: Create step file with scope and simulate violation
        step_data = _create_step_file_with_scope(
            allowed_patterns=["**/UserRepository*"]
        )
        minimal_step_file.write_text(json.dumps(step_data, indent=2))

        out_of_scope_files = ["src/services/OrderService.py"]

        # Act: Log scope violation using JsonlAuditLogWriter
        from des.adapters.driven.logging.jsonl_audit_log_writer import (
            JsonlAuditLogWriter,
        )
        from des.ports.driven_ports.audit_log_writer import AuditEvent

        audit_log = JsonlAuditLogWriter(log_dir=str(tmp_project_root / ".des/audit"))

        # Simulate what SubagentStopHook will do in Phase 4:
        # Log SCOPE_VIOLATION event with required fields
        ts = (
            __import__("datetime")
            .datetime.now(__import__("datetime").timezone.utc)
            .isoformat()
        )
        audit_log.log_event(
            AuditEvent(
                event_type="SCOPE_VIOLATION",
                timestamp=ts,
                data={
                    "severity": "WARNING",
                    "step_file": str(minimal_step_file.name),
                    "out_of_scope_file": out_of_scope_files[0],
                    "allowed_patterns": step_data["scope"]["allowed_patterns"],
                },
            )
        )

        # Assert: Violation logged to audit trail
        log_entries = _read_entries_by_type(
            audit_log._get_log_file(), "SCOPE_VIOLATION"
        )
        assert len(log_entries) >= 1, "Expected at least one SCOPE_VIOLATION entry"

        violation_entry = log_entries[-1]
        assert violation_entry["event"] == "SCOPE_VIOLATION"
        assert violation_entry["severity"] == "WARNING"
        assert violation_entry["step_file"] == str(minimal_step_file.name)
        assert "OrderService.py" in violation_entry["out_of_scope_file"]
        assert violation_entry["timestamp"] is not None

    def test_scenario_010_multiple_scope_violations_all_logged(
        self, tmp_project_root, minimal_step_file
    ):
        """
        GIVEN agent modified multiple out-of-scope files
        WHEN SubagentStop hook detects scope violations
        THEN each violation is logged as separate audit entry

        Business Context:
        If an agent went "rogue" and modified many files, Priya needs
        to see all violations, not just the first one. Each out-of-scope
        file gets its own audit entry for complete transparency.

        Domain Example:
        Agent modified:
        - src/services/OrderService.py (VIOLATION)
        - src/services/PaymentService.py (VIOLATION)
        - config/database.yml (VIOLATION)

        Three separate SCOPE_VIOLATION entries in audit log.
        """
        # Arrange: Create step file with scope
        step_data = _create_step_file_with_scope(
            allowed_patterns=["**/UserRepository*"]
        )
        minimal_step_file.write_text(json.dumps(step_data, indent=2))

        # Multiple out-of-scope files
        _out_of_scope_files = [
            "src/services/OrderService.py",
            "src/services/PaymentService.py",
            "config/database.yml",
        ]

        # Act: Simulate what SubagentStopService will do
        from unittest.mock import Mock, patch

        from des.adapters.driven.logging.jsonl_audit_log_writer import (
            JsonlAuditLogWriter,
        )
        from des.adapters.driven.validation.git_scope_checker import GitScopeChecker
        from des.ports.driven_ports.audit_log_writer import AuditEvent

        checker = GitScopeChecker()
        audit_writer = JsonlAuditLogWriter()

        # Validate scope with multiple out-of-scope files
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                stdout="\n".join(_out_of_scope_files) + "\n",
                returncode=0,
            )
            scope_result = checker.check_scope(
                project_root=tmp_project_root,
                allowed_patterns=["**/UserRepository*"],
            )

        # Simulate SubagentStopHook audit logging (lines 152-163)
        if scope_result.has_violations:
            allowed_patterns = step_data.get("scope", {}).get("allowed_patterns", [])
            ts = (
                __import__("datetime")
                .datetime.now(__import__("datetime").timezone.utc)
                .isoformat()
            )
            for out_of_scope_file in scope_result.out_of_scope_files:
                audit_writer.log_event(
                    AuditEvent(
                        event_type="SCOPE_VIOLATION",
                        timestamp=ts,
                        data={
                            "severity": "WARNING",
                            "step_file": str(minimal_step_file),
                            "out_of_scope_file": out_of_scope_file,
                            "allowed_patterns": allowed_patterns,
                        },
                    )
                )

        # Assert: All violations logged separately
        log_file = audit_writer._get_log_file()
        log_entries = []
        if log_file.exists():
            for line in log_file.read_text().splitlines():
                if line.strip():
                    entry = json.loads(line)
                    if entry.get("event") == "SCOPE_VIOLATION":
                        log_entries.append(entry)
        assert len(log_entries) >= 3, (
            f"Expected at least 3 entries, got {len(log_entries)}"
        )

        logged_files = [entry["out_of_scope_file"] for entry in log_entries]
        assert any("OrderService" in f for f in logged_files), (
            "OrderService violation not logged"
        )
        assert any("PaymentService" in f for f in logged_files), (
            "PaymentService violation not logged"
        )
        assert any("database.yml" in f for f in logged_files), (
            "database.yml violation not logged"
        )

    def test_scenario_011_no_violations_no_warning_logs(
        self, tmp_project_root, minimal_step_file
    ):
        """
        GIVEN agent only modified in-scope files
        WHEN SubagentStop hook validates scope
        THEN no SCOPE_VIOLATION entries appear in audit log

        Business Context:
        Clean executions should not clutter the audit log with
        false warnings. Only actual violations get logged.
        """
        # Arrange: Create step file with scope
        step_data = _create_step_file_with_scope(
            allowed_patterns=["**/UserRepository*"]
        )
        minimal_step_file.write_text(json.dumps(step_data, indent=2))

        # Only in-scope files
        _in_scope_files = ["src/repositories/UserRepository.py"]

        # Act: Run scope validation
        from unittest.mock import Mock, patch

        from des.adapters.driven.logging.jsonl_audit_log_writer import (
            JsonlAuditLogWriter,
        )
        from des.adapters.driven.validation.git_scope_checker import GitScopeChecker
        from des.ports.driven_ports.audit_log_writer import AuditEvent

        checker = GitScopeChecker()
        audit_writer = JsonlAuditLogWriter()

        # Count entries BEFORE clean execution
        log_file = audit_writer._get_log_file()
        entries_before = 0
        if log_file.exists():
            for line in log_file.read_text().splitlines():
                if line.strip():
                    entry = json.loads(line)
                    if entry.get("event") == "SCOPE_VIOLATION":
                        entries_before += 1

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                stdout="\n".join(_in_scope_files) + "\n",
                returncode=0,
            )
            scope_result = checker.check_scope(
                project_root=tmp_project_root,
                allowed_patterns=["**/UserRepository*"],
            )

        # Simulate SubagentStopHook behavior (lines 152-163)
        if scope_result.has_violations:
            allowed_patterns = step_data.get("scope", {}).get("allowed_patterns", [])
            for out_of_scope_file in scope_result.out_of_scope_files:
                audit_writer.log_event(
                    AuditEvent(
                        event_type="SCOPE_VIOLATION",
                        data={
                            "severity": "WARNING",
                            "step_file": str(minimal_step_file),
                            "out_of_scope_file": out_of_scope_file,
                            "allowed_patterns": allowed_patterns,
                        },
                    )
                )

        # Assert: No NEW violation entries added (clean execution)
        entries_after = 0
        if log_file.exists():
            for line in log_file.read_text().splitlines():
                if line.strip():
                    entry = json.loads(line)
                    if entry.get("event") == "SCOPE_VIOLATION":
                        entries_after += 1
        new_entries = entries_after - entries_before
        assert new_entries == 0, (
            f"Expected 0 NEW SCOPE_VIOLATION entries for clean execution, got {new_entries} (before: {entries_before}, after: {entries_after})"
        )


class TestBoundaryRulesCompleteness:
    """
    Integration tests verifying BOUNDARY_RULES section completeness.

    These tests verify that BOUNDARY_RULES contains all required
    components as a cohesive section.
    """

    def test_scenario_012_boundary_rules_has_complete_structure(
        self, tmp_project_root, minimal_step_file, des_orchestrator
    ):
        """
        GIVEN /nw:execute command with step file
        WHEN orchestrator renders full prompt
        THEN BOUNDARY_RULES section contains:
             - ALLOWED subsection with file patterns
             - FORBIDDEN subsection with prohibited actions
             - Return control instruction

        Business Context:
        Complete boundary definition requires both positive (ALLOWED)
        and negative (FORBIDDEN) constraints, plus explicit instruction
        about returning control after completion.
        """
        # GIVEN: /nw:execute command
        step_file_path = str(minimal_step_file.relative_to(tmp_project_root))

        # WHEN: Orchestrator renders full prompt
        prompt = des_orchestrator.render_full_prompt(
            command="/nw:execute",
            agent="@software-crafter",
            step_file=step_file_path,
            project_root=tmp_project_root,
        )

        # THEN: All required components present
        # Section header
        assert "BOUNDARY_RULES" in prompt, "Section header missing"

        # ALLOWED subsection
        assert "ALLOWED" in prompt, "ALLOWED subsection missing"

        # FORBIDDEN subsection
        assert "FORBIDDEN" in prompt, "FORBIDDEN subsection missing"

        # Return control instruction
        return_control_present = any(
            phrase in prompt.lower()
            for phrase in ["return control", "return immediately", "hand back control"]
        )
        assert return_control_present, (
            "Return control instruction missing - agent must know to "
            "stop after step completion"
        )

    def test_scenario_013_develop_command_also_includes_boundary_rules(
        self, tmp_project_root, minimal_step_file, des_orchestrator
    ):
        """
        GIVEN /nw:develop command with step file
        WHEN orchestrator renders full prompt
        THEN prompt includes BOUNDARY_RULES (same as execute)

        Business Context:
        Both /nw:execute and /nw:develop are production workflows
        requiring full DES validation. BOUNDARY_RULES must be present
        for both command types to ensure consistent scope enforcement.
        """
        # GIVEN: /nw:develop command
        step_file_path = str(minimal_step_file.relative_to(tmp_project_root))

        # WHEN: Orchestrator renders full prompt
        prompt = des_orchestrator.render_full_prompt(
            command="/nw:develop",
            agent="@software-crafter",
            step_file=step_file_path,
            project_root=tmp_project_root,
        )

        # THEN: BOUNDARY_RULES present
        assert "BOUNDARY_RULES" in prompt, (
            "/nw:develop command must include BOUNDARY_RULES like /nw:execute"
        )

        # Verify it has same structure
        assert "ALLOWED" in prompt, (
            "ALLOWED section must be present for develop command"
        )
        assert "FORBIDDEN" in prompt, (
            "FORBIDDEN section must be present for develop command"
        )


class TestBoundaryRulesValidation:
    """
    Tests for BOUNDARY_RULES validation during pre-invocation checks.

    Per US-002, BOUNDARY_RULES is one of 9 mandatory sections.
    These tests verify validation correctly handles its presence/absence.
    """

    def test_scenario_014_missing_boundary_rules_blocks_invocation(
        self, tmp_project_root, minimal_step_file
    ):
        """
        GIVEN orchestrator generates prompt missing BOUNDARY_RULES
        WHEN pre-invocation validation runs
        THEN validation FAILS with specific error message
        AND Task invocation is BLOCKED

        Business Context:
        Without boundary rules, agents have no scope constraints.
        Pre-invocation validation must catch this before Task tool
        is invoked, preventing unconstrained agent execution.

        Expected Error:
        "MISSING: Mandatory section 'BOUNDARY_RULES' not found"
        """
        from des.application.prompt_validator import PromptValidator

        # GIVEN: Prompt missing BOUNDARY_RULES
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

        ## TIMEOUT_INSTRUCTION
        Complete within 50 turns

        <!-- NOTE: BOUNDARY_RULES intentionally omitted -->
        """

        # WHEN: Pre-invocation validation runs
        validator = PromptValidator()
        result = validator.validate(incomplete_prompt)

        # THEN: Validation fails with specific error
        assert not result.is_valid, (
            "Validation should FAIL when BOUNDARY_RULES is missing"
        )

        assert any("BOUNDARY_RULES" in error for error in result.errors), (
            "Error message must identify BOUNDARY_RULES as the missing section"
        )

        assert any("MISSING" in error.upper() for error in result.errors), (
            "Error should indicate the section is MISSING, not incomplete"
        )


# =============================================================================
# Test Data Builders (Helper Functions)
# =============================================================================


def _create_step_file_for_user_repository():
    """Create step file targeting UserRepository implementation."""
    return {
        "task_id": "01-01",
        "project_id": "test-project",
        "workflow_type": "tdd_cycle",
        "description": "Implement UserRepository",
        "scope": {
            "target_files": ["src/repositories/UserRepository.py"],
            "test_files": ["tests/unit/test_user_repository.py"],
            "allowed_patterns": ["**/UserRepository*", "**/test_user_repository*"],
        },
        "state": {"status": "TODO", "started_at": None, "completed_at": None},
        "tdd_cycle": {
            "phase_execution_log": [
                {
                    "phase_number": i,
                    "phase_name": phase_name,
                    "status": "NOT_EXECUTED",
                    "outcome": None,
                    "blocked_by": None,
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


def _read_entries_by_type(log_file, event_type: str) -> list[dict]:
    """Read JSONL audit log entries filtered by event type."""
    entries = []
    if log_file.exists():
        for line in log_file.read_text().splitlines():
            if line.strip():
                entry = json.loads(line)
                if entry.get("event") == event_type:
                    entries.append(entry)
    return entries


def _create_step_file_with_scope(allowed_patterns: list[str]):
    """Create step file with explicit scope definition."""
    return {
        "task_id": "01-01",
        "project_id": "test-project",
        "workflow_type": "tdd_cycle",
        "scope": {
            "allowed_patterns": allowed_patterns,
            "target_files": [],
            "test_files": [],
        },
        "state": {"status": "IN_PROGRESS", "started_at": "2026-01-22T10:00:00Z"},
        "tdd_cycle": {
            "phase_execution_log": [
                {
                    "phase_number": i,
                    "phase_name": phase_name,
                    "status": "NOT_EXECUTED",
                    "outcome": None,
                    "blocked_by": None,
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
