"""
E2E Acceptance Test: US-010 Git Commit Verification

PERSONA: Marcus (Senior Developer)
STORY: As a senior developer, I want DES to verify that a real git commit
       exists for each completed step, so that execution log entries cannot
       be fabricated without actual code changes.

BUSINESS VALUE:
- Prevents execution log fraud (orchestrator writing COMMIT/PASS without real commit)
- Provides deterministic evidence that code was actually committed
- Creates audit trail linking step completion to specific git commits

SCOPE: Covers US-010 Acceptance Criteria (AC-010.1 through AC-010.6)
WAVE: DISTILL (Acceptance Test Creation)

TEST BOUNDARY: Port-to-port with real git adapter.
Tests invoke SubagentStopService.validate() directly with real YamlExecutionLogReader
(for actual YAML files) and real GitCommitVerifier (for actual git repos).
Only the audit writer and scope checker are stubbed.
"""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import yaml

from des.adapters.driven.git.git_commit_verifier import GitCommitVerifier
from des.adapters.driven.hooks.yaml_execution_log_reader import (
    YamlExecutionLogReader,
)
from des.adapters.driven.logging.null_audit_log_writer import NullAuditLogWriter
from des.application.subagent_stop_service import SubagentStopService
from des.domain.step_completion_validator import StepCompletionValidator
from des.domain.tdd_schema import get_tdd_schema
from des.ports.driven_ports.scope_checker import ScopeChecker, ScopeCheckResult
from des.ports.driven_ports.time_provider_port import TimeProvider
from des.ports.driver_ports.subagent_stop_port import SubagentStopContext


if TYPE_CHECKING:
    from pathlib import Path


# =============================================================================
# TEST DOUBLES
# =============================================================================


class StubTimeProvider(TimeProvider):
    def now_utc(self) -> datetime:
        return datetime(2026, 2, 8, 12, 0, 0, tzinfo=timezone.utc)


class StubScopeChecker(ScopeChecker):
    def check_scope(
        self, project_root: Path, allowed_patterns: list[str]
    ) -> ScopeCheckResult:
        return ScopeCheckResult(has_violations=False, out_of_scope_files=[])


# =============================================================================
# SERVICE FACTORY
# =============================================================================


def _build_service_with_git(tmp_project_root: Path) -> SubagentStopService:
    """Build SubagentStopService with real YAML reader and real git verifier."""
    schema = get_tdd_schema()
    return SubagentStopService(
        log_reader=YamlExecutionLogReader(),
        completion_validator=StepCompletionValidator(schema=schema),
        scope_checker=StubScopeChecker(),
        audit_writer=NullAuditLogWriter(),
        time_provider=StubTimeProvider(),
        commit_verifier=GitCommitVerifier(),
    )


# =============================================================================
# GIT TEST HELPERS
# =============================================================================


def _init_git_repo(path: Path) -> None:
    """Initialize a git repository with minimal configuration.

    Creates a new git repo at the given path with user identity configured
    so that commits can be created without global git config.

    Args:
        path: Directory to initialize as a git repository
    """
    subprocess.run(
        ["git", "init"],
        cwd=str(path),
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=str(path),
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=str(path),
        capture_output=True,
        check=True,
    )
    # Create initial commit so the repo has a valid HEAD
    initial_file = path / ".gitkeep"
    initial_file.write_text("")
    subprocess.run(
        ["git", "add", ".gitkeep"],
        cwd=str(path),
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=str(path),
        capture_output=True,
        check=True,
    )


def _create_commit_with_step_id(
    path: Path, step_id: str, message: str = "Implement feature"
) -> str:
    """Create a git commit containing a Step-ID trailer in the message body.

    Args:
        path: Git repository directory
        step_id: Step identifier to embed as trailer (e.g., "01-01")
        message: Subject line for the commit message

    Returns:
        The commit hash (short form) of the created commit
    """
    import uuid

    change_file = path / f"change-{uuid.uuid4().hex[:8]}.txt"
    change_file.write_text(f"Implementation for step {step_id}")

    subprocess.run(
        ["git", "add", str(change_file.name)],
        cwd=str(path),
        capture_output=True,
        check=True,
    )

    commit_message = f"{message}\n\nStep-ID: {step_id}"
    subprocess.run(
        ["git", "commit", "-m", commit_message],
        cwd=str(path),
        capture_output=True,
        check=True,
    )

    result = subprocess.run(
        ["git", "log", "--format=%H", "-1"],
        cwd=str(path),
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _create_commit_without_step_id(
    path: Path, message: str = "Unrelated change"
) -> str:
    """Create a git commit without any Step-ID trailer.

    Args:
        path: Git repository directory
        message: Commit message (no Step-ID trailer)

    Returns:
        The commit hash (short form) of the created commit
    """
    import uuid

    change_file = path / f"other-{uuid.uuid4().hex[:8]}.txt"
    change_file.write_text("Some unrelated content")

    subprocess.run(
        ["git", "add", str(change_file.name)],
        cwd=str(path),
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "-m", message],
        cwd=str(path),
        capture_output=True,
        check=True,
    )

    result = subprocess.run(
        ["git", "log", "--format=%H", "-1"],
        cwd=str(path),
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


# =============================================================================
# EXECUTION LOG HELPERS
# =============================================================================


def _create_execution_log_all_phases_pass(tdd_phases) -> dict:
    """Create execution-log.yaml data with all phases EXECUTED and PASS."""
    events = []
    for phase in tdd_phases:
        events.append(f"01-01|{phase}|EXECUTED|PASS|2026-02-08T10:00:00+00:00")

    return {
        "project_id": "test-project",
        "created_at": "2026-02-08T09:00:00+00:00",
        "total_steps": 1,
        "events": events,
    }


def _create_execution_log_missing_phases(tdd_phases, phases_to_include) -> dict:
    """Create execution-log.yaml with only some phases present."""
    events = []
    for phase in tdd_phases:
        if phase in phases_to_include:
            events.append(f"01-01|{phase}|EXECUTED|PASS|2026-02-08T10:00:00+00:00")

    return {
        "project_id": "test-project",
        "created_at": "2026-02-08T09:00:00+00:00",
        "total_steps": 1,
        "events": events,
    }


# =============================================================================
# ACCEPTANCE TESTS
# =============================================================================


class TestGitCommitVerification:
    """E2E acceptance tests for US-010: Git commit verification for step completion.

    Tests invoke SubagentStopService.validate() directly through the driving port,
    with real YamlExecutionLogReader and GitCommitVerifier adapters.
    Git operations are real (integration test requirement).
    """

    # =========================================================================
    # AC-010.1: Commit with Step-ID trailer found
    # Scenario 1: Step completion verified when matching git commit exists
    # =========================================================================

    def test_commit_verified_when_step_id_trailer_found(
        self, tmp_project_root, minimal_step_file, tdd_phases
    ):
        """
        GIVEN all phases are complete in execution-log.yaml
        AND a git commit exists with trailer "Step-ID: 01-01"
        WHEN the completion hook fires after agent finishes
        THEN the step is allowed to proceed
        AND the verification confirms the commit exists

        Business Value: Marcus receives confirmation that code was actually
                       committed, not just logged as committed. This prevents
                       orchestrator fraud where COMMIT phase is marked PASS
                       without a real git commit.

        Domain Example: Software-crafter finishes step 01-01, commits code
                       with "Step-ID: 01-01" trailer. Hook finds the commit
                       and confirms the step is genuinely complete.
        """
        # Arrange: Initialize git repo and create commit with Step-ID trailer
        _init_git_repo(tmp_project_root)
        _create_commit_with_step_id(
            tmp_project_root, "01-01", "Implement user authentication"
        )

        # Arrange: Create execution-log.yaml with all phases complete
        log_data = _create_execution_log_all_phases_pass(tdd_phases)
        log_file = tmp_project_root / "execution-log.yaml"
        log_file.write_text(yaml.dump(log_data, default_flow_style=False))

        # Act: Invoke service directly
        service = _build_service_with_git(tmp_project_root)
        decision = service.validate(
            SubagentStopContext(
                execution_log_path=str(log_file),
                project_id="test-project",
                step_id="01-01",
                cwd=str(tmp_project_root),
            )
        )

        # Assert: Hook allows the step (commit verified)
        assert decision.action == "allow", (
            f"Expected allow, got {decision.action}: {decision.reason}"
        )

    # =========================================================================
    # AC-010.2: No commit with matching Step-ID trailer
    # Scenario 2: Step blocked when no git commit has matching trailer
    # =========================================================================

    def test_commit_not_verified_when_no_matching_trailer(
        self, tmp_project_root, minimal_step_file, tdd_phases
    ):
        """
        GIVEN all phases are complete in execution-log.yaml
        BUT no git commit contains trailer "Step-ID: 01-01"
        WHEN the completion hook fires after agent finishes
        THEN the step is blocked with commit verification failure
        AND the reason mentions missing commit verification

        Business Value: Marcus catches cases where the orchestrator or agent
                       claims step completion without actually committing code.
                       This is the core fraud-prevention scenario.

        Domain Example: Agent writes all phases as PASS in execution-log.yaml
                       but never ran git commit. Hook catches the discrepancy
                       and blocks the step from being marked complete.
        """
        # Arrange: Initialize git repo but create commits WITHOUT Step-ID trailer
        _init_git_repo(tmp_project_root)
        _create_commit_without_step_id(tmp_project_root, "Some unrelated work")
        _create_commit_without_step_id(tmp_project_root, "Another unrelated change")

        # Arrange: Create execution-log.yaml with all phases complete
        log_data = _create_execution_log_all_phases_pass(tdd_phases)
        log_file = tmp_project_root / "execution-log.yaml"
        log_file.write_text(yaml.dump(log_data, default_flow_style=False))

        # Act: Invoke service directly
        service = _build_service_with_git(tmp_project_root)
        decision = service.validate(
            SubagentStopContext(
                execution_log_path=str(log_file),
                project_id="test-project",
                step_id="01-01",
                cwd=str(tmp_project_root),
            )
        )

        # Assert: Hook blocks the step (no matching commit found)
        assert decision.action == "block", (
            f"Expected block, got {decision.action}: {decision.reason}"
        )
        # Reason should mention commit verification failure
        reason = decision.reason or ""
        assert "commit" in reason.lower() or "COMMIT_NOT_VERIFIED" in reason, (
            f"Block reason should mention commit verification, got: {reason}"
        )

    # =========================================================================
    # AC-010.3: Git not available or not a repository
    # Scenario 3: Step blocked when working directory is not a git repo
    # =========================================================================

    def test_commit_verify_error_when_not_git_repo(
        self, tmp_project_root, minimal_step_file, tdd_phases
    ):
        """
        GIVEN all phases are complete in execution-log.yaml
        BUT the working directory is not a git repository
        WHEN the completion hook fires after agent finishes
        THEN the step is blocked with a verification error (fail-closed)

        Business Value: Marcus ensures that git verification fails safely
                       rather than silently passing. A non-git directory
                       cannot have commits, so allowing would be incorrect.
                       Fail-closed prevents false positives.

        Domain Example: Developer runs DES in a directory that was not
                       initialized with git. Rather than assuming commits
                       exist, the hook blocks and reports the error.
        """
        # Arrange: Do NOT initialize git repo (tmp_project_root is just a directory)

        # Arrange: Create execution-log.yaml with all phases complete
        log_data = _create_execution_log_all_phases_pass(tdd_phases)
        log_file = tmp_project_root / "execution-log.yaml"
        log_file.write_text(yaml.dump(log_data, default_flow_style=False))

        # Act: Invoke service directly
        service = _build_service_with_git(tmp_project_root)
        decision = service.validate(
            SubagentStopContext(
                execution_log_path=str(log_file),
                project_id="test-project",
                step_id="01-01",
                cwd=str(tmp_project_root),
            )
        )

        # Assert: Hook blocks the step (fail-closed on git error)
        assert decision.action == "block", (
            f"Expected block, got {decision.action}: {decision.reason}"
        )
        reason = decision.reason or ""
        assert "commit" in reason.lower() or "git" in reason.lower(), (
            f"Block reason should mention commit/git error, got: {reason}"
        )

    # =========================================================================
    # AC-010.4: Execution-log validation fails, git verification skipped
    # Scenario 4: Git verification skipped when phase validation already fails
    # =========================================================================

    def test_git_verification_skipped_when_phases_incomplete(
        self, tmp_project_root, minimal_step_file, tdd_phases
    ):
        """
        GIVEN execution-log.yaml has missing phases (validation fails)
        AND a git commit exists with trailer "Step-ID: 01-01"
        WHEN the completion hook fires after agent finishes
        THEN the step is blocked for the missing phases reason
        AND git verification is never performed

        Business Value: Marcus sees the most actionable error first. When
                       phases are missing, the developer needs to complete
                       the TDD cycle before worrying about commit verification.
                       Layered validation prevents confusing error cascades.

        Domain Example: Agent crashes during GREEN phase. Execution log shows
                       only PREPARE and RED phases complete. Even though a
                       git commit with Step-ID exists from a previous attempt,
                       the hook correctly blocks on missing phases first.
        """
        # Arrange: Initialize git repo with a Step-ID commit (should be irrelevant)
        _init_git_repo(tmp_project_root)
        _create_commit_with_step_id(tmp_project_root, "01-01", "Previous attempt")

        # Arrange: Create execution-log.yaml with MISSING phases (only first 3)
        first_three = list(tdd_phases[:3])
        log_data = _create_execution_log_missing_phases(tdd_phases, first_three)
        log_file = tmp_project_root / "execution-log.yaml"
        log_file.write_text(yaml.dump(log_data, default_flow_style=False))

        # Act: Invoke service directly
        service = _build_service_with_git(tmp_project_root)
        decision = service.validate(
            SubagentStopContext(
                execution_log_path=str(log_file),
                project_id="test-project",
                step_id="01-01",
                cwd=str(tmp_project_root),
            )
        )

        # Assert: Blocked for missing phases, NOT for commit verification
        assert decision.action == "block", (
            f"Expected block, got {decision.action}: {decision.reason}"
        )
        reason = decision.reason or ""
        assert "Missing phases" in reason, (
            f"Should block on missing phases, got: {reason}"
        )
        # The reason should NOT mention commit verification (it was skipped)
        assert "COMMIT_NOT_VERIFIED" not in reason, (
            "Git verification should be skipped when phases are incomplete"
        )

    # =========================================================================
    # AC-010.5: Correct commit found among multiple commits
    # Scenario 5: Verification finds the right commit in busy history
    # =========================================================================

    def test_correct_commit_found_among_multiple(
        self, tmp_project_root, minimal_step_file, tdd_phases
    ):
        """
        GIVEN all phases are complete in execution-log.yaml
        AND multiple git commits exist in the repository
        AND only one commit contains trailer "Step-ID: 01-01"
        WHEN the completion hook fires after agent finishes
        THEN the correct commit is found and verified

        Business Value: Marcus confirms that commit verification works
                       correctly in realistic repositories with many commits.
                       The search must find the specific Step-ID trailer
                       regardless of how many other commits exist.

        Domain Example: Repository has 50 commits from various developers.
                       Only the latest from software-crafter has the
                       "Step-ID: 01-01" trailer. Hook correctly identifies
                       this specific commit.
        """
        # Arrange: Initialize git repo with multiple commits
        _init_git_repo(tmp_project_root)
        _create_commit_without_step_id(tmp_project_root, "Earlier feature work")
        _create_commit_without_step_id(tmp_project_root, "Bug fix for login")
        _create_commit_without_step_id(tmp_project_root, "Update documentation")
        # The one commit with the Step-ID trailer
        _create_commit_with_step_id(
            tmp_project_root, "01-01", "Implement authentication module"
        )
        _create_commit_without_step_id(tmp_project_root, "Later unrelated work")

        # Arrange: Create execution-log.yaml with all phases complete
        log_data = _create_execution_log_all_phases_pass(tdd_phases)
        log_file = tmp_project_root / "execution-log.yaml"
        log_file.write_text(yaml.dump(log_data, default_flow_style=False))

        # Act: Invoke service directly
        service = _build_service_with_git(tmp_project_root)
        decision = service.validate(
            SubagentStopContext(
                execution_log_path=str(log_file),
                project_id="test-project",
                step_id="01-01",
                cwd=str(tmp_project_root),
            )
        )

        # Assert: Hook allows the step (correct commit found)
        assert decision.action == "allow", (
            f"Expected allow, got {decision.action}: {decision.reason}"
        )

    # =========================================================================
    # AC-010.6: Step-ID in commit body (not subject line)
    # Scenario 6: Verification finds Step-ID trailer in message body
    # =========================================================================

    def test_step_id_found_in_commit_body(
        self, tmp_project_root, minimal_step_file, tdd_phases
    ):
        """
        GIVEN all phases are complete in execution-log.yaml
        AND a git commit has "Step-ID: 01-01" in its message body (not subject)
        WHEN the completion hook fires after agent finishes
        THEN the commit is found and verified

        Business Value: Marcus confirms that the Step-ID trailer placement
                       follows git conventions (trailers in message body,
                       not subject line). The search must check the full
                       commit message, not just the subject.

        Domain Example: Software-crafter creates a commit with:
                       Subject: "Implement user registration"
                       Body: "Added registration endpoint...\\n\\nStep-ID: 01-01"
                       Hook searches full commit message and finds the trailer.
        """
        # Arrange: Initialize git repo
        _init_git_repo(tmp_project_root)

        # Create a commit where Step-ID is ONLY in the body, not the subject
        import uuid

        change_file = tmp_project_root / f"feature-{uuid.uuid4().hex[:8]}.py"
        change_file.write_text("def register_user(): pass")
        subprocess.run(
            ["git", "add", str(change_file.name)],
            cwd=str(tmp_project_root),
            capture_output=True,
            check=True,
        )
        # Multi-line commit message with Step-ID trailer in body
        commit_msg = (
            "Implement user registration\n"
            "\n"
            "Added registration endpoint with email validation.\n"
            "Includes password hashing and session management.\n"
            "\n"
            "Step-ID: 01-01"
        )
        subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=str(tmp_project_root),
            capture_output=True,
            check=True,
        )

        # Arrange: Create execution-log.yaml with all phases complete
        log_data = _create_execution_log_all_phases_pass(tdd_phases)
        log_file = tmp_project_root / "execution-log.yaml"
        log_file.write_text(yaml.dump(log_data, default_flow_style=False))

        # Act: Invoke service directly
        service = _build_service_with_git(tmp_project_root)
        decision = service.validate(
            SubagentStopContext(
                execution_log_path=str(log_file),
                project_id="test-project",
                step_id="01-01",
                cwd=str(tmp_project_root),
            )
        )

        # Assert: Hook allows the step (Step-ID found in body)
        assert decision.action == "allow", (
            f"Expected allow, got {decision.action}: {decision.reason}"
        )
