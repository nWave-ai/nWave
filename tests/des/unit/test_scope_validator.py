"""
Unit Tests: GitScopeChecker - Post-Execution Scope Validation

Tests GitScopeChecker class that runs git diff to detect out-of-scope file modifications.
Business context: Prevent agents from "helpfully" modifying files outside step scope.

Domain Language:
- allowed_patterns: Glob patterns defining in-scope files
- out_of_scope_files: Files modified that don't match allowed patterns
- scope violation: Modification of file outside allowed patterns
- skipped: Git command unavailable, validation not performed
"""

import subprocess
from unittest.mock import Mock, patch

from des.adapters.driven.validation.git_scope_checker import GitScopeChecker


class TestGitScopeCheckerGitIntegration:
    """Test git diff execution and error handling."""

    def test_git_timeout_configured_to_5_seconds(self):
        """
        GIVEN GitScopeChecker initialized
        WHEN checking git timeout configuration
        THEN timeout is exactly 5 seconds (not mutated to other values)
        """
        checker = GitScopeChecker()
        assert checker.GIT_TIMEOUT_SECONDS == 5

    def test_executes_git_diff_command_successfully(self, tmp_path):
        """
        GIVEN GitScopeChecker initialized
        WHEN check_scope called
        THEN git diff --name-only HEAD executed successfully
        """
        checker = GitScopeChecker()

        # Mock git command to return modified files
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                stdout="src/repositories/UserRepository.py\n", returncode=0
            )

            # Act
            result = checker.check_scope(
                project_root=tmp_path,
                allowed_patterns=["**/UserRepository*"],
            )

            # Assert: Git command called with correct parameters
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert call_args[0][0] == ["git", "diff", "--name-only", "HEAD"]
            assert call_args[1]["capture_output"] is True
            assert call_args[1]["timeout"] == 5
            assert call_args[1]["check"] is True
            assert call_args[1]["text"] is True
            # Verify result is valid (git succeeded)
            assert result.skipped is False

    def test_git_timeout_returns_skipped(self, tmp_path):
        """
        GIVEN GitScopeChecker initialized
        WHEN git diff times out after 5 seconds
        THEN ScopeCheckResult has skipped=True with timeout reason
        """
        checker = GitScopeChecker()

        # Mock git timeout
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(
                cmd=["git", "diff"], timeout=5
            )

            # Act
            result = checker.check_scope(
                project_root=tmp_path,
                allowed_patterns=["**/UserRepository*"],
            )

            # Assert: Check skipped with timeout reason
            assert result.has_violations is False
            assert result.skipped is True
            assert "timeout" in result.skip_reason.lower()

    def test_git_unavailable_returns_skipped(self, tmp_path):
        """
        GIVEN GitScopeChecker initialized
        WHEN git diff fails (CalledProcessError)
        THEN ScopeCheckResult has skipped=True with unavailable reason
        """
        checker = GitScopeChecker()

        # Mock git command failure
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                returncode=128, cmd=["git", "diff"]
            )

            # Act
            result = checker.check_scope(
                project_root=tmp_path,
                allowed_patterns=["**/UserRepository*"],
            )

            # Assert: Check skipped with unavailable reason
            assert result.has_violations is False
            assert result.skipped is True
            assert (
                "unavailable" in result.skip_reason.lower()
                or "failed" in result.skip_reason.lower()
            )

    def test_empty_lines_in_git_output_all_files_still_processed(self, tmp_path):
        """
        GIVEN git output with empty lines interspersed
        WHEN check_scope processes modified files
        THEN all files are processed (continue skips empty, doesn't break loop)
        """
        checker = GitScopeChecker()

        with patch("subprocess.run") as mock_run:
            # Git output: in-scope file, empty lines, out-of-scope file
            mock_run.return_value = Mock(
                stdout="src/UserRepo.py\n\n\nsrc/OrderService.py\n\n", returncode=0
            )

            result = checker.check_scope(
                project_root=tmp_path,
                allowed_patterns=["**/User*"],
            )

            # Must detect OrderService (second file after empty lines)
            # This proves continue (not break) was used
            assert result.has_violations is True
            assert "src/OrderService.py" in result.out_of_scope_files


class TestGitScopeCheckerPatternMatching:
    """Test file pattern matching against allowed patterns."""

    def test_in_scope_files_pass_validation(self, tmp_path):
        """
        GIVEN allowed patterns include **/UserRepository*
        WHEN git diff shows only UserRepository.py modified
        THEN validation passes (has_violations=False)
        """
        checker = GitScopeChecker()

        # Mock git showing in-scope file
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                stdout="src/repositories/UserRepository.py\n", returncode=0
            )

            # Act
            result = checker.check_scope(
                project_root=tmp_path,
                allowed_patterns=["**/UserRepository*"],
            )

            # Assert: No violations for in-scope file
            assert result.has_violations is False
            assert len(result.out_of_scope_files) == 0

    def test_out_of_scope_files_detected(self, tmp_path):
        """
        GIVEN allowed patterns include only **/UserRepository*
        WHEN git diff shows OrderService.py modified (out of scope)
        THEN validation detects violation with OrderService in out_of_scope_files
        """
        checker = GitScopeChecker()

        # Mock git showing out-of-scope file
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                stdout="src/repositories/UserRepository.py\nsrc/services/OrderService.py\n",
                returncode=0,
            )

            # Act
            result = checker.check_scope(
                project_root=tmp_path,
                allowed_patterns=["**/UserRepository*"],
            )

            # Assert: Violation detected for OrderService
            assert result.has_violations is True
            assert "src/services/OrderService.py" in result.out_of_scope_files

    def test_multiple_out_of_scope_files_all_detected(self, tmp_path):
        """
        GIVEN allowed patterns include only **/UserRepository*
        WHEN git diff shows multiple out-of-scope files
        THEN all violations detected in out_of_scope_files list
        """
        checker = GitScopeChecker()

        # Mock git showing multiple out-of-scope files
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                stdout="src/services/OrderService.py\nsrc/controllers/PaymentController.py\n",
                returncode=0,
            )

            # Act
            result = checker.check_scope(
                project_root=tmp_path,
                allowed_patterns=["**/UserRepository*"],
            )

            # Assert: All violations detected
            assert result.has_violations is True
            assert len(result.out_of_scope_files) == 2
            assert "src/services/OrderService.py" in result.out_of_scope_files
            assert "src/controllers/PaymentController.py" in result.out_of_scope_files

    def test_multiple_patterns_any_match_passes(self, tmp_path):
        """
        GIVEN allowed patterns: **/UserRepository*, **/test_user_repository*
        WHEN git diff shows files matching different patterns
        THEN all files pass validation (each matches at least one pattern)
        """
        checker = GitScopeChecker()

        # Mock git showing files matching different patterns
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                stdout="src/repositories/UserRepository.py\ntests/unit/test_user_repository.py\n",
                returncode=0,
            )

            # Act
            result = checker.check_scope(
                project_root=tmp_path,
                allowed_patterns=[
                    "**/UserRepository*",
                    "**/test_user_repository*",
                ],
            )

            # Assert: All files pass (each matches at least one pattern)
            assert result.has_violations is False
            assert len(result.out_of_scope_files) == 0

    def test_glob_pattern_matches_nested_directories(self, tmp_path):
        """
        GIVEN allowed patterns include **/UserRepository*
        WHEN git diff shows UserRepository in deeply nested path
        THEN validation passes (** matches any directory depth)
        """
        checker = GitScopeChecker()

        # Mock git showing file in deeply nested path
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                stdout="src/deep/nested/path/to/repositories/UserRepository.py\n",
                returncode=0,
            )

            # Act
            result = checker.check_scope(
                project_root=tmp_path,
                allowed_patterns=["**/UserRepository*"],
            )

            # Assert: Nested path matches pattern
            assert result.has_violations is False
            assert len(result.out_of_scope_files) == 0

    def test_wildcard_suffix_matches_extensions(self, tmp_path):
        """
        GIVEN allowed patterns include **/UserRepository* (ends with *)
        WHEN git diff shows UserRepository files with different extensions
        THEN all extensions pass validation (* matches any suffix)
        """
        checker = GitScopeChecker()

        # Mock git showing files with different extensions
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                stdout="src/repositories/UserRepository.py\nsrc/repositories/UserRepositoryTest.cs\n",
                returncode=0,
            )

            # Act
            result = checker.check_scope(
                project_root=tmp_path,
                allowed_patterns=["**/UserRepository*"],
            )

            # Assert: Both files match pattern (suffix wildcard)
            assert result.has_violations is False
            assert len(result.out_of_scope_files) == 0

    def test_partial_name_match_fails_without_wildcard(self, tmp_path):
        """
        GIVEN allowed patterns include UserRepository.py (exact, no wildcards)
        WHEN git diff shows src/repositories/UserRepository.py (different path)
        THEN validation detects violation (exact match required without wildcards)
        """
        checker = GitScopeChecker()

        # Mock git showing file with path prefix
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                stdout="src/repositories/UserRepository.py\n", returncode=0
            )

            # Act
            result = checker.check_scope(
                project_root=tmp_path,
                allowed_patterns=["UserRepository.py"],  # No wildcards
            )

            # Assert: Violation detected (path doesn't match exactly)
            assert result.has_violations is True
            assert "src/repositories/UserRepository.py" in result.out_of_scope_files

    def test_file_matches_pattern_returns_true_not_inverted(self):
        """
        GIVEN file matches allowed pattern
        WHEN _matches_any_pattern called
        THEN returns True (not inverted to False with 'not')
        """
        # Test positive case explicitly
        matches = GitScopeChecker._matches_any_pattern(
            "src/repositories/UserRepository.py", ["**/UserRepository*"]
        )
        assert matches is True  # Explicit True check (not just truthy)

        # Test negative case explicitly
        no_match = GitScopeChecker._matches_any_pattern(
            "src/services/OrderService.py", ["**/UserRepository*"]
        )
        assert no_match is False  # Explicit False check (not just falsy)
