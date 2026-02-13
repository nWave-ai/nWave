"""
pytest-bdd configuration for installation acceptance tests (APEX-002).

CRITICAL: Hexagonal boundary enforcement
- ALL tests invoke scripts through subprocess (driving ports)
- NO direct imports of internal components
- Tests validate USER EXPERIENCE, not implementation details

Cross-platform compatible (Windows, macOS, Linux).
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


# ============================================================================
# Constants
# ============================================================================

SUBPROCESS_TIMEOUT = 30  # Longer timeout for build operations
EXIT_SUCCESS = 0
EXIT_FAILURE = 1

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
INSTALLER_SCRIPT = PROJECT_ROOT / "scripts" / "install" / "install_nwave.py"
VERIFY_SCRIPT = PROJECT_ROOT / "scripts" / "install" / "verify_nwave.py"


# ============================================================================
# Custom Markers
# ============================================================================


def pytest_configure(config):
    """Register custom markers for installation tests."""
    config.addinivalue_line(
        "markers",
        "requires_no_venv: test requires execution outside virtual environment",
    )
    config.addinivalue_line(
        "markers",
        "requires_venv: test requires active virtual environment",
    )
    config.addinivalue_line(
        "markers",
        "requires_no_pipenv: test requires pipenv to be unavailable",
    )
    config.addinivalue_line(
        "markers",
        "manual: test requires manual verification",
    )
    config.addinivalue_line(
        "markers",
        "ac01: AC-01 Pre-flight Environment Check",
    )
    config.addinivalue_line(
        "markers",
        "ac02: AC-02 Virtual Environment Hard Block",
    )
    config.addinivalue_line(
        "markers",
        "ac03: AC-03 Pipenv-Only Enforcement",
    )
    config.addinivalue_line(
        "markers",
        "ac04: AC-04 Context-Aware Terminal Errors",
    )
    config.addinivalue_line(
        "markers",
        "ac05: AC-05 Context-Aware Claude Code Errors",
    )
    config.addinivalue_line(
        "markers",
        "ac06: AC-06 Dependency Verification",
    )
    config.addinivalue_line(
        "markers",
        "ac07: AC-07 Automatic Post-Installation Verification",
    )
    config.addinivalue_line(
        "markers",
        "ac08: AC-08 Standalone Verification Command",
    )
    config.addinivalue_line(
        "markers",
        "ac09: AC-09 Installation Logging",
    )
    config.addinivalue_line(
        "markers",
        "ac10: AC-10 Documentation Accuracy",
    )
    config.addinivalue_line(
        "markers",
        "ac11: AC-11 CI Environment Detection",
    )
    config.addinivalue_line(
        "markers",
        "ac12: AC-12 CI Mode Output Behavior",
    )
    config.addinivalue_line(
        "markers",
        "ac13: AC-13 CI Exit Codes",
    )
    config.addinivalue_line(
        "markers",
        "ac14: AC-14 Container Environment Detection",
    )
    config.addinivalue_line(
        "markers",
        "ac15: AC-15 CI and Container Combined Detection",
    )


# ============================================================================
# Test Installation Fixtures
# ============================================================================


@pytest.fixture
def project_root():
    """Return the project root directory."""
    return PROJECT_ROOT


@pytest.fixture
def installer_script():
    """Return path to the nWave installer script."""
    return INSTALLER_SCRIPT


@pytest.fixture
def verify_script():
    """Return path to the verification script."""
    return VERIFY_SCRIPT


@pytest.fixture(scope="function")
def isolated_claude_home(tmp_path, monkeypatch):
    """
    Create isolated ~/.claude directory for each test.

    Prevents tests from affecting real installation.
    Provides clean state for each test execution.
    """
    fake_home = tmp_path / "test-home"
    fake_home.mkdir()

    fake_claude = fake_home / ".claude"
    fake_claude.mkdir()

    # Create subdirectories for installation
    (fake_claude / "agents" / "nw").mkdir(parents=True)
    (fake_claude / "commands" / "nw").mkdir(parents=True)
    (fake_claude / "templates").mkdir(parents=True)

    # Set environment variables
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("USERPROFILE", str(fake_home))  # Windows

    return {
        "home": fake_home,
        "claude_dir": fake_claude,
        "agents_dir": fake_claude / "agents" / "nw",
        "commands_dir": fake_claude / "commands" / "nw",
        "templates_dir": fake_claude / "templates",
        "log_file": fake_claude / "nwave-install.log",
        "manifest_file": fake_claude / "nwave-manifest.txt",
    }


@pytest.fixture
def cli_result():
    """Container for CLI execution results."""
    return {
        "stdout": "",
        "stderr": "",
        "returncode": None,
        "exception": None,
        "json_output": None,
    }


@pytest.fixture
def execution_environment(isolated_claude_home, monkeypatch):
    """
    Environment variables for script execution.

    CRITICAL: Inherits system environment to ensure subprocess can find
    Python, pipenv, and other required executables.
    """
    env = os.environ.copy()

    # Override home directory for isolation
    env["HOME"] = str(isolated_claude_home["home"])
    env["USERPROFILE"] = str(isolated_claude_home["home"])

    # Ensure PYTHONPATH includes project root
    pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{PROJECT_ROOT}{os.pathsep}{pythonpath}"

    return env


# ============================================================================
# Environment Simulation Fixtures
# ============================================================================


@pytest.fixture
def mock_venv_status(monkeypatch):
    """
    Fixture to mock virtual environment detection.

    Returns a controller object to set venv status for tests.
    """

    class VenvController:
        def __init__(self):
            self._in_venv = True

        def set_in_venv(self, status: bool):
            """Set whether we appear to be in a virtual environment."""
            self._in_venv = status
            if status:
                # In venv: sys.prefix != sys.base_prefix
                monkeypatch.setattr(sys, "prefix", "/fake/venv")
                monkeypatch.setattr(sys, "base_prefix", "/usr/local")
            else:
                # Not in venv: sys.prefix == sys.base_prefix
                monkeypatch.setattr(sys, "prefix", sys.base_prefix)

        @property
        def in_venv(self) -> bool:
            return self._in_venv

    return VenvController()


@pytest.fixture
def mock_pipenv_status():
    """
    Fixture to simulate pipenv availability.

    Note: This is used to set environment variables that the installer
    will check, not to actually modify pipenv installation.
    """

    class PipenvController:
        def __init__(self):
            self._installed = True

        def set_installed(self, status: bool):
            """Set whether pipenv appears to be installed."""
            self._installed = status

        @property
        def installed(self) -> bool:
            return self._installed

        def get_env_vars(self) -> dict[str, str]:
            """Get environment variables to simulate pipenv status."""
            if not self._installed:
                return {"NWAVE_TEST_NO_PIPENV": "1"}
            return {}

    return PipenvController()


@pytest.fixture
def mock_dependencies():
    """
    Fixture to simulate dependency availability.

    Returns a controller to configure which dependencies appear missing.
    """

    class DependencyController:
        def __init__(self):
            self._missing: list[str] = []

        def set_missing(self, modules: list[str]):
            """Set which modules should appear missing."""
            self._missing = modules

        def add_missing(self, module: str):
            """Add a module to the missing list."""
            if module not in self._missing:
                self._missing.append(module)

        @property
        def missing(self) -> list[str]:
            return self._missing.copy()

        def get_env_vars(self) -> dict[str, str]:
            """Get environment variables to simulate dependency status."""
            if self._missing:
                return {"NWAVE_TEST_MISSING_DEPS": ",".join(self._missing)}
            return {}

    return DependencyController()


@pytest.fixture
def output_context():
    """
    Fixture to control output context (terminal vs claude_code).
    """

    class OutputContextController:
        def __init__(self):
            self._context = "terminal"

        def set_context(self, context: str):
            """Set output context: 'terminal' or 'claude_code'."""
            assert context in ("terminal", "claude_code")
            self._context = context

        @property
        def context(self) -> str:
            return self._context

        def get_env_vars(self) -> dict[str, str]:
            """Get environment variables to set output context."""
            return {"NWAVE_OUTPUT_CONTEXT": self._context}

    return OutputContextController()


# ============================================================================
# CI/CD Environment Simulation Fixtures
# ============================================================================


@pytest.fixture
def ci_environment(execution_environment):
    """
    Fixture to simulate CI environment.

    Returns a controller to configure CI environment variables.
    Tests use this to simulate GitHub Actions, GitLab CI, Jenkins, etc.
    """

    class CIEnvironmentController:
        """Controller for CI environment simulation."""

        # Standard CI environment variables
        CI_VARS = {
            "github_actions": {"GITHUB_ACTIONS": "true", "CI": "true"},
            "gitlab_ci": {"GITLAB_CI": "true", "CI": "true"},
            "jenkins": {"JENKINS_URL": "http://jenkins.local", "CI": "true"},
            "circleci": {"CIRCLECI": "true", "CI": "true"},
            "travis": {"TRAVIS": "true", "CI": "true"},
            "azure_devops": {"TF_BUILD": "True", "CI": "true"},
            "generic_ci": {"CI": "true"},
        }

        def __init__(self, env: dict[str, str]):
            self._env = env
            self._active_ci: str | None = None

        def set_ci_platform(self, ci_platform: str):
            """
            Set CI platform environment variables.

            Args:
                ci_platform: One of 'github_actions', 'gitlab_ci', 'jenkins',
                             'circleci', 'travis', 'azure_devops', 'generic_ci'
            """
            if ci_platform not in self.CI_VARS:
                raise ValueError(f"Unknown CI platform: {ci_platform}")

            # Clear any existing CI variables
            self.clear_ci()

            # Set new CI variables
            for var, value in self.CI_VARS[ci_platform].items():
                self._env[var] = value
            self._active_ci = ci_platform

        def clear_ci(self):
            """Remove all CI environment variables."""
            all_ci_vars = set()
            for vars_dict in self.CI_VARS.values():
                all_ci_vars.update(vars_dict.keys())

            for var in all_ci_vars:
                self._env.pop(var, None)
            self._active_ci = None

        @property
        def is_ci(self) -> bool:
            """Return True if CI environment is configured."""
            return self._active_ci is not None

        @property
        def ci_platform_name(self) -> str | None:
            """Return the active CI platform name."""
            return self._active_ci

        def get_env_vars(self) -> dict[str, str]:
            """Get the current CI environment variables."""
            if not self._active_ci:
                return {}
            return self.CI_VARS.get(self._active_ci, {}).copy()

    return CIEnvironmentController(execution_environment)


@pytest.fixture
def container_environment(execution_environment):
    """
    Fixture to simulate container environment (Docker, Kubernetes, etc.).

    Note: Real container detection checks /.dockerenv or /proc/1/cgroup.
    For testing, we use environment variables that the installer will check.
    """

    class ContainerEnvironmentController:
        """Controller for container environment simulation."""

        CONTAINER_VARS = {
            "docker": {"NWAVE_TEST_CONTAINER": "docker"},
            "kubernetes": {
                "NWAVE_TEST_CONTAINER": "kubernetes",
                "KUBERNETES_SERVICE_HOST": "10.0.0.1",
            },
            "podman": {"NWAVE_TEST_CONTAINER": "podman"},
        }

        def __init__(self, env: dict[str, str]):
            self._env = env
            self._container_type: str | None = None

        def set_container_type(self, container_type: str):
            """
            Set container environment variables.

            Args:
                container_type: One of 'docker', 'kubernetes', 'podman'
            """
            if container_type not in self.CONTAINER_VARS:
                raise ValueError(f"Unknown container type: {container_type}")

            # Clear any existing container variables
            self.clear_container()

            # Set new container variables
            for var, value in self.CONTAINER_VARS[container_type].items():
                self._env[var] = value
            self._container_type = container_type

        def clear_container(self):
            """Remove all container environment variables."""
            all_container_vars = set()
            for vars_dict in self.CONTAINER_VARS.values():
                all_container_vars.update(vars_dict.keys())

            for var in all_container_vars:
                self._env.pop(var, None)
            self._container_type = None

        @property
        def is_container(self) -> bool:
            """Return True if container environment is configured."""
            return self._container_type is not None

        @property
        def container_type(self) -> str | None:
            """Return the active container type."""
            return self._container_type

        def get_env_vars(self) -> dict[str, str]:
            """Get the current container environment variables."""
            if not self._container_type:
                return {}
            return self.CONTAINER_VARS.get(self._container_type, {}).copy()

    return ContainerEnvironmentController(execution_environment)


# ============================================================================
# CLI Execution Utilities
# ============================================================================


@pytest.fixture
def run_installer(
    project_root,
    installer_script,
    execution_environment,
    cli_result,
    mock_pipenv_status,
    mock_dependencies,
    output_context,
):
    """
    Fixture providing a function to run the nWave installer.

    CRITICAL: This is the DRIVING PORT - tests invoke through here.
    """

    def _run(
        args: list[str] | None = None,
        env_overrides: dict[str, str] | None = None,
        timeout: int = SUBPROCESS_TIMEOUT,
    ) -> dict:
        """
        Run the nWave installer script.

        Args:
            args: Additional command-line arguments
            env_overrides: Additional environment variables
            timeout: Execution timeout in seconds

        Returns:
            Dictionary with stdout, stderr, returncode, json_output
        """
        cmd = [sys.executable, str(installer_script)]
        if args:
            cmd.extend(args)

        # Build environment
        env = execution_environment.copy()
        env.update(mock_pipenv_status.get_env_vars())
        env.update(mock_dependencies.get_env_vars())
        env.update(output_context.get_env_vars())
        if env_overrides:
            env.update(env_overrides)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
                cwd=str(project_root),
            )

            cli_result["stdout"] = result.stdout
            cli_result["stderr"] = result.stderr
            cli_result["returncode"] = result.returncode

            # Try to parse JSON if output context is claude_code
            if output_context.context == "claude_code":
                try:
                    # Look for JSON in stdout or stderr
                    output = result.stdout or result.stderr
                    cli_result["json_output"] = json.loads(output)
                except (json.JSONDecodeError, TypeError):
                    cli_result["json_output"] = None

        except subprocess.TimeoutExpired as e:
            cli_result["exception"] = e
            cli_result["stderr"] = f"Command timed out after {timeout} seconds"
            cli_result["returncode"] = 124

        except Exception as e:
            cli_result["exception"] = e
            cli_result["stderr"] = str(e)
            cli_result["returncode"] = 1

        return cli_result

    return _run


@pytest.fixture
def run_verifier(
    project_root,
    verify_script,
    execution_environment,
    cli_result,
    output_context,
):
    """
    Fixture providing a function to run the standalone verification script.
    """

    def _run(
        args: list[str] | None = None,
        env_overrides: dict[str, str] | None = None,
        timeout: int = SUBPROCESS_TIMEOUT,
    ) -> dict:
        """
        Run the standalone verification script.

        Args:
            args: Additional command-line arguments
            env_overrides: Additional environment variables
            timeout: Execution timeout in seconds

        Returns:
            Dictionary with stdout, stderr, returncode
        """
        if not verify_script.exists():
            cli_result["stdout"] = ""
            cli_result["stderr"] = f"Verification script not found: {verify_script}"
            cli_result["returncode"] = 127
            return cli_result

        cmd = [sys.executable, str(verify_script)]
        if args:
            cmd.extend(args)

        env = execution_environment.copy()
        env.update(output_context.get_env_vars())
        if env_overrides:
            env.update(env_overrides)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
                cwd=str(project_root),
            )

            cli_result["stdout"] = result.stdout
            cli_result["stderr"] = result.stderr
            cli_result["returncode"] = result.returncode

        except subprocess.TimeoutExpired as e:
            cli_result["exception"] = e
            cli_result["stderr"] = f"Command timed out after {timeout} seconds"
            cli_result["returncode"] = 124

        except Exception as e:
            cli_result["exception"] = e
            cli_result["stderr"] = str(e)
            cli_result["returncode"] = 1

        return cli_result

    return _run


# ============================================================================
# Assertion Helpers
# ============================================================================


@pytest.fixture
def assert_output():
    """Helper for asserting CLI output patterns."""

    class OutputAssertions:
        @staticmethod
        def contains(result: dict, expected: str, in_stderr: bool = False):
            """Assert output contains expected text."""
            output = result["stderr"] if in_stderr else result["stdout"]
            all_output = f"{result['stdout']}\n{result['stderr']}"
            assert expected in output or expected in all_output, (
                f"Expected '{expected}' not found in output:\n"
                f"STDOUT: {result['stdout']!r}\n"
                f"STDERR: {result['stderr']!r}"
            )

        @staticmethod
        def not_contains(result: dict, unexpected: str):
            """Assert output does not contain unexpected text."""
            all_output = f"{result['stdout']}\n{result['stderr']}"
            assert unexpected not in all_output, (
                f"Unexpected '{unexpected}' found in output:\n"
                f"STDOUT: {result['stdout']!r}\n"
                f"STDERR: {result['stderr']!r}"
            )

        @staticmethod
        def exit_code(result: dict, expected: int):
            """Assert command exit code."""
            assert result["returncode"] == expected, (
                f"Expected exit code {expected}, got {result['returncode']}\n"
                f"STDOUT: {result['stdout']!r}\n"
                f"STDERR: {result['stderr']!r}"
            )

        @staticmethod
        def is_valid_json(result: dict):
            """Assert output is valid JSON."""
            output = result["stdout"] or result["stderr"]
            try:
                json.loads(output)
            except (json.JSONDecodeError, TypeError) as e:
                pytest.fail(f"Output is not valid JSON: {e}\nOutput: {output!r}")

        @staticmethod
        def json_has_field(result: dict, field: str, value=None):
            """Assert JSON output has specified field."""
            output = result["stdout"] or result["stderr"]
            try:
                data = json.loads(output)
            except (json.JSONDecodeError, TypeError):
                pytest.fail(f"Output is not valid JSON: {output!r}")

            assert field in data, f"JSON field '{field}' not found in: {data}"
            if value is not None:
                assert data[field] == value, (
                    f"JSON field '{field}' has value {data[field]!r}, expected {value!r}"
                )

    return OutputAssertions()


# ============================================================================
# File System Helpers
# ============================================================================


@pytest.fixture
def file_assertions(isolated_claude_home):
    """Helper for file system assertions."""

    class FileAssertions:
        def __init__(self, claude_home):
            self.claude_home = claude_home

        def log_exists(self) -> bool:
            """Check if installation log exists."""
            return self.claude_home["log_file"].exists()

        def manifest_exists(self) -> bool:
            """Check if manifest file exists."""
            return self.claude_home["manifest_file"].exists()

        def log_contains(self, text: str) -> bool:
            """Check if log file contains text."""
            if not self.log_exists():
                return False
            content = self.claude_home["log_file"].read_text()
            return text in content

        def agent_count(self) -> int:
            """Count installed agent files."""
            return len(list(self.claude_home["agents_dir"].glob("*.md")))

        def command_count(self) -> int:
            """Count installed command files."""
            return len(list(self.claude_home["commands_dir"].glob("*.md")))

        def file_exists(self, relative_path: str) -> bool:
            """Check if file exists relative to claude directory."""
            path = self.claude_home["claude_dir"] / relative_path
            return path.exists()

    return FileAssertions(isolated_claude_home)


# ============================================================================
# Test Data Builders
# ============================================================================


@pytest.fixture
def partial_installation_builder(isolated_claude_home):
    """Builder for creating partial installations for testing."""

    class PartialInstallationBuilder:
        def __init__(self, claude_home):
            self.claude_home = claude_home

        def create_minimal(self):
            """Create minimal installation with some missing files."""
            # Create some agent files
            agents_dir = self.claude_home["agents_dir"]
            for i in range(5):
                (agents_dir / f"agent-{i}.md").write_text(f"# Agent {i}")

            # Create some command files (but not all essential ones)
            commands_dir = self.claude_home["commands_dir"]
            (commands_dir / "discuss.md").write_text("# Discuss")
            (commands_dir / "design.md").write_text("# Design")
            # Missing: distill, develop, deliver

        def remove_file(self, relative_path: str):
            """Remove a specific file from installation."""
            path = self.claude_home["claude_dir"] / relative_path
            if path.exists():
                path.unlink()

        def create_log_file(self, content: str = ""):
            """Create log file with optional content."""
            self.claude_home["log_file"].write_text(content)

    return PartialInstallationBuilder(isolated_claude_home)


# ============================================================================
# pytest Hooks
# ============================================================================


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Store test result on test item for access in fixtures."""
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)
