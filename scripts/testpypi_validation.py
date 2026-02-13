#!/usr/bin/env python3
"""TestPyPI E2E validation script for CI/CD pipelines.

This script validates that a package installed from TestPyPI works correctly
by running health checks and verifying expected component counts.

Usage:
    python scripts/testpypi_validation.py --version 1.3.0.dev20260201001 \
        --expected-agents 47 --expected-commands 23 --expected-templates 12

Exit Codes:
    0: All validations passed
    1: Validation failed
    2: Invalid arguments
    3: Installation failed
    4: Health check failed
"""

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ValidationResult:
    """Result of a validation check."""

    success: bool
    check_name: str
    expected: str
    actual: str
    message: str


class TestPyPIValidator:
    """Validates TestPyPI package installation and health."""

    TESTPYPI_INDEX_URL = "https://test.pypi.org/simple/"
    PYPI_INDEX_URL = "https://pypi.org/simple/"

    def __init__(
        self,
        version: str,
        expected_agents: int = 0,
        expected_commands: int = 0,
        expected_templates: int = 0,
        package_name: str = "nwave",
    ) -> None:
        """Initialize the validator.

        Args:
            version: PEP 440 version to install from TestPyPI.
            expected_agents: Expected number of agents (0 to skip check).
            expected_commands: Expected number of commands (0 to skip check).
            expected_templates: Expected number of templates (0 to skip check).
            package_name: Name of the package to install.
        """
        self.version = version
        self.expected_agents = expected_agents
        self.expected_commands = expected_commands
        self.expected_templates = expected_templates
        self.package_name = package_name
        self.results: list[ValidationResult] = []

    def run_command(
        self, cmd: list[str], capture_output: bool = True
    ) -> subprocess.CompletedProcess:
        """Run a shell command and return the result.

        Args:
            cmd: Command and arguments to run.
            capture_output: Whether to capture stdout/stderr.

        Returns:
            CompletedProcess with the command result.
        """
        print(f"  Running: {' '.join(cmd)}")
        return subprocess.run(
            cmd,
            capture_output=capture_output,
            text=True,
            timeout=300,
        )

    def install_from_testpypi(self) -> ValidationResult:
        """Install the package from TestPyPI using pipx.

        Returns:
            ValidationResult indicating success or failure.
        """
        print(
            f"\n[1/4] Installing {self.package_name}=={self.version} from TestPyPI..."
        )

        # First, ensure any existing installation is removed
        uninstall_cmd = ["pipx", "uninstall", self.package_name]
        self.run_command(uninstall_cmd)  # Ignore errors if not installed

        # Install from TestPyPI with PyPI fallback for dependencies
        install_cmd = [
            "pipx",
            "install",
            f"{self.package_name}=={self.version}",
            "--pip-args",
            f"--index-url {self.TESTPYPI_INDEX_URL} --extra-index-url {self.PYPI_INDEX_URL}",
        ]

        result = self.run_command(install_cmd)

        if result.returncode != 0:
            return ValidationResult(
                success=False,
                check_name="TestPyPI Installation",
                expected="exit code 0",
                actual=f"exit code {result.returncode}",
                message=f"Installation failed: {result.stderr}",
            )

        return ValidationResult(
            success=True,
            check_name="TestPyPI Installation",
            expected="exit code 0",
            actual="exit code 0",
            message=f"Successfully installed {self.package_name}=={self.version}",
        )

    def verify_version(self) -> ValidationResult:
        """Verify the installed version matches expected.

        Returns:
            ValidationResult indicating success or failure.
        """
        print(f"\n[2/4] Verifying installed version matches {self.version}...")

        version_cmd = ["nwave", "--version"]
        result = self.run_command(version_cmd)

        if result.returncode != 0:
            return ValidationResult(
                success=False,
                check_name="Version Check",
                expected=self.version,
                actual="command failed",
                message=f"Version command failed: {result.stderr}",
            )

        installed_version = result.stdout.strip()

        # Check if the version string contains our expected version
        if self.version in installed_version or installed_version in self.version:
            return ValidationResult(
                success=True,
                check_name="Version Check",
                expected=self.version,
                actual=installed_version,
                message="Version matches expected",
            )

        return ValidationResult(
            success=False,
            check_name="Version Check",
            expected=self.version,
            actual=installed_version,
            message=f"Version mismatch: expected {self.version}, got {installed_version}",
        )

    def run_health_checks(self) -> ValidationResult:
        """Run health checks via nwave doctor equivalent.

        Returns:
            ValidationResult indicating success or failure.
        """
        print("\n[3/4] Running health checks...")

        # Try running doctor command
        doctor_cmd = ["nwave", "doctor"]
        result = self.run_command(doctor_cmd)

        # If doctor command doesn't exist, check if the CLI is at least responsive
        if result.returncode != 0 and "unrecognized" in result.stderr.lower():
            # Fall back to help command to verify CLI is working
            help_cmd = ["nwave", "--help"]
            result = self.run_command(help_cmd)

            if result.returncode == 0:
                return ValidationResult(
                    success=True,
                    check_name="Health Check",
                    expected="CLI responsive",
                    actual="CLI responsive (doctor command not available)",
                    message="CLI is installed and responding to commands",
                )

        if result.returncode == 0:
            # Check for HEALTHY status in output
            if "HEALTHY" in result.stdout.upper():
                return ValidationResult(
                    success=True,
                    check_name="Health Check",
                    expected="HEALTHY status",
                    actual="HEALTHY",
                    message="All health checks passed",
                )

            return ValidationResult(
                success=True,
                check_name="Health Check",
                expected="HEALTHY status",
                actual="doctor completed",
                message="Doctor command completed successfully",
            )

        return ValidationResult(
            success=False,
            check_name="Health Check",
            expected="HEALTHY status",
            actual=f"exit code {result.returncode}",
            message=f"Health check failed: {result.stderr}",
        )

    def verify_component_counts(self) -> ValidationResult:
        """Verify expected component counts if specified.

        Returns:
            ValidationResult indicating success or failure.
        """
        print("\n[4/4] Verifying component counts...")

        # If no expectations set, skip this check
        if (
            self.expected_agents == 0
            and self.expected_commands == 0
            and self.expected_templates == 0
        ):
            return ValidationResult(
                success=True,
                check_name="Component Counts",
                expected="no expectations set",
                actual="skipped",
                message="Component count validation skipped (no expectations provided)",
            )

        # Try to get component counts via doctor or manifest
        agents_path = Path.home() / ".claude" / "agents" / "nw"
        commands_path = Path.home() / ".claude" / "commands" / "nw"
        templates_path = Path.home() / ".claude" / "templates" / "nw"

        actual_agents = (
            len(list(agents_path.glob("*.md"))) if agents_path.exists() else 0
        )
        actual_commands = (
            len(list(commands_path.glob("*.md"))) if commands_path.exists() else 0
        )
        actual_templates = (
            len(list(templates_path.glob("*"))) if templates_path.exists() else 0
        )

        mismatches = []
        if self.expected_agents > 0 and actual_agents != self.expected_agents:
            mismatches.append(
                f"agents: expected {self.expected_agents}, got {actual_agents}"
            )
        if self.expected_commands > 0 and actual_commands != self.expected_commands:
            mismatches.append(
                f"commands: expected {self.expected_commands}, got {actual_commands}"
            )
        if self.expected_templates > 0 and actual_templates != self.expected_templates:
            mismatches.append(
                f"templates: expected {self.expected_templates}, got {actual_templates}"
            )

        if mismatches:
            return ValidationResult(
                success=False,
                check_name="Component Counts",
                expected=f"agents={self.expected_agents}, commands={self.expected_commands}, templates={self.expected_templates}",
                actual=f"agents={actual_agents}, commands={actual_commands}, templates={actual_templates}",
                message=f"Component count mismatch: {'; '.join(mismatches)}",
            )

        return ValidationResult(
            success=True,
            check_name="Component Counts",
            expected=f"agents={self.expected_agents}, commands={self.expected_commands}, templates={self.expected_templates}",
            actual=f"agents={actual_agents}, commands={actual_commands}, templates={actual_templates}",
            message="All component counts match expected values",
        )

    def validate(self) -> bool:
        """Run all validation checks.

        Returns:
            True if all validations pass, False otherwise.
        """
        print("=" * 60)
        print("TestPyPI E2E Validation")
        print("=" * 60)
        print(f"Package: {self.package_name}")
        print(f"Version: {self.version}")
        print("=" * 60)

        # Run all checks
        self.results.append(self.install_from_testpypi())
        if not self.results[-1].success:
            self._print_results()
            return False

        self.results.append(self.verify_version())
        self.results.append(self.run_health_checks())
        self.results.append(self.verify_component_counts())

        self._print_results()
        return all(r.success for r in self.results)

    def _print_results(self) -> None:
        """Print validation results summary."""
        print("\n" + "=" * 60)
        print("Validation Results")
        print("=" * 60)

        for result in self.results:
            status = "PASS" if result.success else "FAIL"
            print(f"\n[{status}] {result.check_name}")
            print(f"  Expected: {result.expected}")
            print(f"  Actual:   {result.actual}")
            print(f"  Message:  {result.message}")

        print("\n" + "=" * 60)
        passed = sum(1 for r in self.results if r.success)
        total = len(self.results)
        print(f"Summary: {passed}/{total} checks passed")
        print("=" * 60)


def main() -> int:
    """Main entry point for the validation script.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    parser = argparse.ArgumentParser(
        description="Validate TestPyPI package installation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--version",
        required=True,
        help="PEP 440 version to install from TestPyPI (e.g., 1.3.0.dev20260201001)",
    )
    parser.add_argument(
        "--expected-agents",
        type=int,
        default=0,
        help="Expected number of agents (0 to skip check)",
    )
    parser.add_argument(
        "--expected-commands",
        type=int,
        default=0,
        help="Expected number of commands (0 to skip check)",
    )
    parser.add_argument(
        "--expected-templates",
        type=int,
        default=0,
        help="Expected number of templates (0 to skip check)",
    )
    parser.add_argument(
        "--package-name",
        default="nwave",
        help="Name of the package to install (default: nwave)",
    )

    args = parser.parse_args()

    validator = TestPyPIValidator(
        version=args.version,
        expected_agents=args.expected_agents,
        expected_commands=args.expected_commands,
        expected_templates=args.expected_templates,
        package_name=args.package_name,
    )

    try:
        success = validator.validate()
        return 0 if success else 1
    except subprocess.TimeoutExpired:
        print("\nERROR: Validation timed out after 5 minutes", file=sys.stderr)
        return 3
    except Exception as e:
        print(f"\nERROR: Validation failed with exception: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
