"""Unit tests for context_detector module.

Tests validate TTY detection, Claude Code context detection,
CI environment detection, container environment detection,
and the combined is_interactive check for execution context
determination.
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch


class TestIsTTY:
    """Verify TTY detection via stdout.isatty()."""

    def test_is_tty_returns_true_when_tty(self):
        """is_tty() returns True when stdout is a TTY."""
        from scripts.install.context_detector import is_tty

        with patch.object(sys.stdout, "isatty", return_value=True):
            assert is_tty() is True

    def test_is_tty_returns_false_when_not_tty(self):
        """is_tty() returns False when stdout is not a TTY."""
        from scripts.install.context_detector import is_tty

        with patch.object(sys.stdout, "isatty", return_value=False):
            assert is_tty() is False


class TestIsClaudeCodeContext:
    """Verify Claude Code context detection via environment variable."""

    def test_is_claude_code_context_true_when_env_set(self):
        """is_claude_code_context() returns True when CLAUDE_CODE env var is set."""
        from scripts.install.context_detector import is_claude_code_context

        with patch.dict(os.environ, {"CLAUDE_CODE": "1"}):
            assert is_claude_code_context() is True

    def test_is_claude_code_context_true_when_env_set_to_any_value(self):
        """is_claude_code_context() returns True for any non-empty CLAUDE_CODE value."""
        from scripts.install.context_detector import is_claude_code_context

        with patch.dict(os.environ, {"CLAUDE_CODE": "true"}):
            assert is_claude_code_context() is True

    def test_is_claude_code_context_false_when_env_not_set(self):
        """is_claude_code_context() returns False when CLAUDE_CODE env var is not set."""
        from scripts.install.context_detector import is_claude_code_context

        env_copy = os.environ.copy()
        env_copy.pop("CLAUDE_CODE", None)
        with patch.dict(os.environ, env_copy, clear=True):
            assert is_claude_code_context() is False

    def test_is_claude_code_context_false_when_env_empty(self):
        """is_claude_code_context() returns False when CLAUDE_CODE is empty string."""
        from scripts.install.context_detector import is_claude_code_context

        with patch.dict(os.environ, {"CLAUDE_CODE": ""}):
            assert is_claude_code_context() is False


class TestIsInteractive:
    """Verify combined interactive check logic."""

    def test_is_interactive_true_when_tty_and_not_claude_code(self):
        """is_interactive() returns True when TTY and NOT in Claude Code context."""
        from scripts.install.context_detector import is_interactive

        with patch("scripts.install.context_detector.is_tty", return_value=True):
            with patch(
                "scripts.install.context_detector.is_claude_code_context",
                return_value=False,
            ):
                assert is_interactive() is True

    def test_is_interactive_false_when_not_tty(self):
        """is_interactive() returns False when not a TTY (even without Claude Code)."""
        from scripts.install.context_detector import is_interactive

        with patch("scripts.install.context_detector.is_tty", return_value=False):
            with patch(
                "scripts.install.context_detector.is_claude_code_context",
                return_value=False,
            ):
                assert is_interactive() is False

    def test_is_interactive_false_when_claude_code_context(self):
        """is_interactive() returns False when in Claude Code context (even if TTY)."""
        from scripts.install.context_detector import is_interactive

        with patch("scripts.install.context_detector.is_tty", return_value=True):
            with patch(
                "scripts.install.context_detector.is_claude_code_context",
                return_value=True,
            ):
                assert is_interactive() is False

    def test_is_interactive_false_when_both_not_tty_and_claude_code(self):
        """is_interactive() returns False when neither TTY nor outside Claude Code."""
        from scripts.install.context_detector import is_interactive

        with patch("scripts.install.context_detector.is_tty", return_value=False):
            with patch(
                "scripts.install.context_detector.is_claude_code_context",
                return_value=True,
            ):
                assert is_interactive() is False


class TestExecutionContextEnum:
    """Verify ExecutionContext enum is properly defined."""

    def test_execution_context_has_terminal_value(self):
        """ExecutionContext enum has TERMINAL value."""
        from scripts.install.context_detector import ExecutionContext

        assert hasattr(ExecutionContext, "TERMINAL")
        assert ExecutionContext.TERMINAL.value == "terminal"

    def test_execution_context_has_claude_code_value(self):
        """ExecutionContext enum has CLAUDE_CODE value."""
        from scripts.install.context_detector import ExecutionContext

        assert hasattr(ExecutionContext, "CLAUDE_CODE")
        assert ExecutionContext.CLAUDE_CODE.value == "claude_code"


class TestGetExecutionContext:
    """Verify get_execution_context() returns appropriate context."""

    def test_get_execution_context_returns_claude_code_when_in_claude_code(self):
        """get_execution_context() returns CLAUDE_CODE when in Claude Code context."""
        from scripts.install.context_detector import (
            ExecutionContext,
            get_execution_context,
        )

        with patch(
            "scripts.install.context_detector.is_claude_code_context", return_value=True
        ):
            assert get_execution_context() == ExecutionContext.CLAUDE_CODE

    def test_get_execution_context_returns_terminal_when_not_claude_code(self):
        """get_execution_context() returns TERMINAL when not in Claude Code context."""
        from scripts.install.context_detector import (
            ExecutionContext,
            get_execution_context,
        )

        with patch(
            "scripts.install.context_detector.is_claude_code_context",
            return_value=False,
        ):
            assert get_execution_context() == ExecutionContext.TERMINAL


class TestIsCIEnvironmentGitHubActions:
    """Verify CI detection via GITHUB_ACTIONS environment variable."""

    def test_is_ci_github_actions_returns_true_when_set(self):
        """is_ci_environment() returns True when GITHUB_ACTIONS is set."""
        from scripts.install.context_detector import is_ci_environment

        with patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}, clear=False):
            assert is_ci_environment() is True

    def test_is_ci_github_actions_any_value(self):
        """is_ci_environment() returns True for any non-empty GITHUB_ACTIONS value."""
        from scripts.install.context_detector import is_ci_environment

        with patch.dict(os.environ, {"GITHUB_ACTIONS": "1"}, clear=False):
            assert is_ci_environment() is True


class TestIsCIEnvironmentGitLabCI:
    """Verify CI detection via GITLAB_CI environment variable."""

    def test_is_ci_gitlab_returns_true_when_set(self):
        """is_ci_environment() returns True when GITLAB_CI is set."""
        from scripts.install.context_detector import is_ci_environment

        with patch.dict(os.environ, {"GITLAB_CI": "true"}, clear=False):
            assert is_ci_environment() is True


class TestIsCIEnvironmentGenericCI:
    """Verify CI detection via generic CI environment variable."""

    def test_is_ci_generic_returns_true_when_set(self):
        """is_ci_environment() returns True when CI is set."""
        from scripts.install.context_detector import is_ci_environment

        with patch.dict(os.environ, {"CI": "true"}, clear=False):
            assert is_ci_environment() is True


class TestIsCIEnvironmentJenkins:
    """Verify CI detection via JENKINS_URL environment variable."""

    def test_is_ci_jenkins_returns_true_when_set(self):
        """is_ci_environment() returns True when JENKINS_URL is set."""
        from scripts.install.context_detector import is_ci_environment

        with patch.dict(
            os.environ, {"JENKINS_URL": "http://jenkins.example.com"}, clear=False
        ):
            assert is_ci_environment() is True


class TestIsCIEnvironmentNone:
    """Verify CI detection returns False when no CI variables are set."""

    def test_is_ci_returns_false_when_no_ci_vars(self):
        """is_ci_environment() returns False when no CI env vars are set."""
        from scripts.install.context_detector import is_ci_environment

        # Create a clean environment without CI variables
        clean_env = {
            k: v
            for k, v in os.environ.items()
            if k not in ["GITHUB_ACTIONS", "GITLAB_CI", "CI", "JENKINS_URL"]
        }
        with patch.dict(os.environ, clean_env, clear=True):
            assert is_ci_environment() is False

    def test_is_ci_returns_false_when_ci_vars_empty(self):
        """is_ci_environment() returns False when CI env vars are empty strings."""
        from scripts.install.context_detector import is_ci_environment

        clean_env = {
            k: v
            for k, v in os.environ.items()
            if k not in ["GITHUB_ACTIONS", "GITLAB_CI", "CI", "JENKINS_URL"]
        }
        clean_env.update(
            {"GITHUB_ACTIONS": "", "GITLAB_CI": "", "CI": "", "JENKINS_URL": ""}
        )
        with patch.dict(os.environ, clean_env, clear=True):
            assert is_ci_environment() is False


class TestGetCIPlatform:
    """Verify get_ci_platform() returns correct platform names."""

    def test_get_ci_platform_github_actions(self):
        """get_ci_platform() returns 'github_actions' when GITHUB_ACTIONS is set."""
        from scripts.install.context_detector import get_ci_platform

        clean_env = {
            k: v
            for k, v in os.environ.items()
            if k not in ["GITHUB_ACTIONS", "GITLAB_CI", "CI", "JENKINS_URL"]
        }
        clean_env["GITHUB_ACTIONS"] = "true"
        with patch.dict(os.environ, clean_env, clear=True):
            assert get_ci_platform() == "github_actions"

    def test_get_ci_platform_gitlab_ci(self):
        """get_ci_platform() returns 'gitlab_ci' when GITLAB_CI is set."""
        from scripts.install.context_detector import get_ci_platform

        clean_env = {
            k: v
            for k, v in os.environ.items()
            if k not in ["GITHUB_ACTIONS", "GITLAB_CI", "CI", "JENKINS_URL"]
        }
        clean_env["GITLAB_CI"] = "true"
        with patch.dict(os.environ, clean_env, clear=True):
            assert get_ci_platform() == "gitlab_ci"

    def test_get_ci_platform_jenkins(self):
        """get_ci_platform() returns 'jenkins' when JENKINS_URL is set."""
        from scripts.install.context_detector import get_ci_platform

        clean_env = {
            k: v
            for k, v in os.environ.items()
            if k not in ["GITHUB_ACTIONS", "GITLAB_CI", "CI", "JENKINS_URL"]
        }
        clean_env["JENKINS_URL"] = "http://jenkins.example.com"
        with patch.dict(os.environ, clean_env, clear=True):
            assert get_ci_platform() == "jenkins"

    def test_get_ci_platform_generic(self):
        """get_ci_platform() returns 'generic' when only CI is set."""
        from scripts.install.context_detector import get_ci_platform

        clean_env = {
            k: v
            for k, v in os.environ.items()
            if k not in ["GITHUB_ACTIONS", "GITLAB_CI", "CI", "JENKINS_URL"]
        }
        clean_env["CI"] = "true"
        with patch.dict(os.environ, clean_env, clear=True):
            assert get_ci_platform() == "generic"

    def test_get_ci_platform_none_when_no_ci(self):
        """get_ci_platform() returns None when no CI env vars are set."""
        from scripts.install.context_detector import get_ci_platform

        clean_env = {
            k: v
            for k, v in os.environ.items()
            if k not in ["GITHUB_ACTIONS", "GITLAB_CI", "CI", "JENKINS_URL"]
        }
        with patch.dict(os.environ, clean_env, clear=True):
            assert get_ci_platform() is None

    def test_get_ci_platform_github_takes_precedence(self):
        """get_ci_platform() returns 'github_actions' even if generic CI is also set."""
        from scripts.install.context_detector import get_ci_platform

        clean_env = {
            k: v
            for k, v in os.environ.items()
            if k not in ["GITHUB_ACTIONS", "GITLAB_CI", "CI", "JENKINS_URL"]
        }
        clean_env["GITHUB_ACTIONS"] = "true"
        clean_env["CI"] = "true"
        with patch.dict(os.environ, clean_env, clear=True):
            assert get_ci_platform() == "github_actions"


class TestIsContainerEnvironmentDocker:
    """Verify container detection via Docker marker file."""

    def test_is_container_docker_returns_true_when_dockerenv_exists(self):
        """is_container_environment() returns True when /.dockerenv exists."""
        from scripts.install.context_detector import is_container_environment

        with patch.object(Path, "exists", return_value=True):
            # Also ensure KUBERNETES_SERVICE_HOST is not set
            clean_env = {
                k: v for k, v in os.environ.items() if k != "KUBERNETES_SERVICE_HOST"
            }
            with patch.dict(os.environ, clean_env, clear=True):
                assert is_container_environment() is True


class TestIsContainerEnvironmentKubernetes:
    """Verify container detection via Kubernetes environment variable."""

    def test_is_container_kubernetes_returns_true_when_k8s_host_set(self):
        """is_container_environment() returns True when KUBERNETES_SERVICE_HOST is set."""
        from scripts.install.context_detector import is_container_environment

        with (
            patch.object(Path, "exists", return_value=False),
            patch.dict(
                os.environ, {"KUBERNETES_SERVICE_HOST": "10.0.0.1"}, clear=False
            ),
        ):
            assert is_container_environment() is True


class TestIsContainerEnvironmentNone:
    """Verify container detection returns False when not in container."""

    def test_is_container_returns_false_when_no_markers(self):
        """is_container_environment() returns False when no container markers present."""
        from scripts.install.context_detector import is_container_environment

        with patch.object(Path, "exists", return_value=False):
            clean_env = {
                k: v for k, v in os.environ.items() if k != "KUBERNETES_SERVICE_HOST"
            }
            with patch.dict(os.environ, clean_env, clear=True):
                assert is_container_environment() is False


class TestCIInsideContainer:
    """Verify detection of CI running inside container."""

    def test_ci_inside_container_both_detected(self):
        """Both CI and container environments are detected when both markers present."""
        from scripts.install.context_detector import (
            is_ci_environment,
            is_container_environment,
        )

        with (
            patch.object(Path, "exists", return_value=True),
            patch.dict(
                os.environ,
                {"GITHUB_ACTIONS": "true", "KUBERNETES_SERVICE_HOST": "10.0.0.1"},
                clear=False,
            ),
        ):
            assert is_ci_environment() is True
            assert is_container_environment() is True


class TestDefaultNonCINonContainer:
    """Verify default behavior when not in CI or container."""

    def test_default_non_ci_non_container_uses_standard_detection(self):
        """Non-CI non-container environment uses default context detection."""
        from scripts.install.context_detector import (
            get_execution_context,
            is_ci_environment,
            is_container_environment,
        )

        with patch.object(Path, "exists", return_value=False):
            clean_env = {
                k: v
                for k, v in os.environ.items()
                if k
                not in [
                    "GITHUB_ACTIONS",
                    "GITLAB_CI",
                    "CI",
                    "JENKINS_URL",
                    "KUBERNETES_SERVICE_HOST",
                    "CLAUDE_CODE",
                ]
            }
            with patch.dict(os.environ, clean_env, clear=True):
                assert is_ci_environment() is False
                assert is_container_environment() is False
                # Default behavior should still work
                context = get_execution_context()
                assert context is not None
