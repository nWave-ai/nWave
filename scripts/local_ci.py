#!/usr/bin/env python3
"""
Local CI/CD Validation Script

Runs the same validation checks as GitHub Actions CI/CD pipelines locally.
This allows catching issues before pushing to remote.

Usage:
    python scripts/local_ci.py [--verbose] [--fast]

Options:
    --verbose    Show detailed output
    --fast       Skip slower checks (build validation)
    --help       Show this help message
"""

import argparse
import subprocess
import sys
from pathlib import Path


try:
    from colorama import Fore, Style, init

    init(autoreset=True)
    HAS_COLOR = True
except ImportError:
    # Fallback if colorama not available
    HAS_COLOR = False

    class Fore:
        RED = GREEN = YELLOW = BLUE = CYAN = ""

    class Style:
        RESET_ALL = BRIGHT = ""


class LocalCIValidator:
    """Local CI/CD validation orchestrator."""

    def __init__(self, verbose: bool = False, fast_mode: bool = False):
        self.verbose = verbose
        self.fast_mode = fast_mode
        self.project_root = Path(__file__).parent.parent
        self.tests_passed = 0
        self.tests_failed = 0

    def print_header(self, text: str) -> None:
        """Print a section header."""
        separator = "━" * 50
        print(f"\n{Fore.BLUE}{separator}{Style.RESET_ALL}")
        print(f"{Fore.BLUE}{text}{Style.RESET_ALL}")
        print(f"{Fore.BLUE}{separator}{Style.RESET_ALL}")

    def print_success(self, text: str) -> None:
        """Print a success message."""
        print(f"{Fore.GREEN}✓{Style.RESET_ALL} {text}")

    def print_error(self, text: str) -> None:
        """Print an error message."""
        print(f"{Fore.RED}✗{Style.RESET_ALL} {text}")

    def print_warning(self, text: str) -> None:
        """Print a warning message."""
        print(f"{Fore.YELLOW}⚠{Style.RESET_ALL} {text}")

    def print_info(self, text: str) -> None:
        """Print an info message."""
        if self.verbose:
            print(f"{Fore.CYAN}ℹ{Style.RESET_ALL} {text}")

    def run_command(
        self, command: list[str], check_name: str, cwd: Path | None = None
    ) -> bool:
        """
        Run a command and track success/failure.

        Args:
            command: Command to run as list of strings
            check_name: Human-readable name for the check
            cwd: Working directory (defaults to project root)

        Returns:
            True if command succeeded, False otherwise
        """
        if cwd is None:
            cwd = self.project_root

        self.print_info(f"Running: {' '.join(command)}")

        try:
            if self.verbose:
                # In verbose mode, show output directly
                subprocess.run(command, cwd=cwd, check=True, text=True)
            else:
                # In non-verbose mode, capture output
                subprocess.run(
                    command,
                    cwd=cwd,
                    check=True,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                )

            self.print_success(check_name)
            self.tests_passed += 1
            return True

        except subprocess.CalledProcessError as e:
            self.print_error(check_name)
            if not self.verbose and hasattr(e, "output") and e.output:
                # In non-verbose mode, show output on error
                print(e.output)
            self.tests_failed += 1
            return False
        except FileNotFoundError:
            self.print_warning(f"{check_name} - command not found")
            return False

    def validate_yaml(self) -> None:
        """Validate YAML files using our validation script."""
        self.print_header("1. YAML File Validation")

        validator_script = (
            self.project_root / "scripts/validation/validate_yaml_files.py"
        )
        if validator_script.exists():
            self.run_command(
                [sys.executable, str(validator_script)], "YAML syntax validation"
            )
        else:
            self.print_warning("YAML validator script not found")

    def validate_pipenv_dependencies(self) -> None:
        """Validate pipenv dependencies match CI workflow requirements."""
        self.print_header("2. Pipenv Dependency Validation")

        pipfile = self.project_root / "Pipfile"
        pipfile_lock = self.project_root / "Pipfile.lock"

        if not pipfile.exists():
            self.print_error("Pipfile missing - pipenv install will fail")
            self.tests_failed += 1
            return

        self.print_success("Pipfile exists")

        # Check Pipfile.lock exists (required for pipenv install --deploy)
        if not pipfile_lock.exists():
            self.print_warning(
                "Pipfile.lock missing - run: pipenv lock (CI uses --deploy flag)"
            )
            # Generate lock file
            try:
                subprocess.run(
                    ["pipenv", "lock"],
                    cwd=self.project_root,
                    check=True,
                    capture_output=not self.verbose,
                    text=True,
                )
                self.print_success("Pipfile.lock generated")
            except (FileNotFoundError, subprocess.CalledProcessError) as e:
                self.print_error(f"Failed to generate Pipfile.lock: {e}")
                self.tests_failed += 1
                return

        self.print_success("Pipfile.lock exists")

        # Validate pipenv install works (mirrors CI exactly)
        try:
            subprocess.run(["pipenv", "--version"], capture_output=True, check=True)
            self.run_command(
                ["pipenv", "install", "--dev"],
                "pipenv install --dev (dependency installation)",
            )
        except FileNotFoundError:
            self.print_warning(
                "pipenv not available - install with: pip install pipenv"
            )

    def run_python_tests(self) -> None:
        """Run Python test suite."""
        self.print_header("3. Python Test Suite")

        # Use pipenv run test (mirrors CI exactly)
        try:
            subprocess.run(["pipenv", "--version"], capture_output=True, check=True)
            self.run_command(["pipenv", "run", "test"], "Python tests (pytest)")
        except FileNotFoundError:
            # Fall back to direct pytest if pipenv not available
            self.run_command(
                [sys.executable, "-m", "pytest", "tests/", "-v"],
                "Python tests (pytest)",
            )

    def validate_build(self) -> None:
        """Validate the build process."""
        if self.fast_mode:
            self.print_info("Skipping build (fast mode)")
            return

        self.print_header("4. Build Process Validation")

        # Use pipenv run build (mirrors CI exactly)
        try:
            subprocess.run(["pipenv", "--version"], capture_output=True, check=True)
            self.run_command(["pipenv", "run", "build"], "Build process")
        except FileNotFoundError:
            # Fall back to direct Python if pipenv not available
            build_script = self.project_root / "tools" / "build.py"
            if build_script.exists():
                self.run_command([sys.executable, str(build_script)], "Build process")
            else:
                self.print_warning("Build script not found")

    def validate_shell_scripts(self) -> None:
        """Validate shell scripts."""
        self.print_header("5. Shell Script Validation")

        scripts_dir = self.project_root / "scripts"
        shell_scripts = list(scripts_dir.glob("*.sh"))

        if not shell_scripts:
            self.print_info("No shell scripts found in scripts/")
            return

        shell_errors = 0

        # Syntax validation
        for script in shell_scripts:
            try:
                subprocess.run(
                    ["bash", "-n", str(script)],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                self.print_success(f"Shell syntax: {script.name}")
            except subprocess.CalledProcessError:
                self.print_error(f"Shell syntax: {script.name}")
                shell_errors += 1

        # Shellcheck linting (non-blocking if not available)
        try:
            result = subprocess.run(
                ["shellcheck", "--version"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                self.print_info("Running shellcheck analysis...")
                all_scripts = list(scripts_dir.rglob("*.sh"))
                try:
                    subprocess.run(
                        ["shellcheck", "-x"] + [str(s) for s in all_scripts],
                        check=True,
                        capture_output=not self.verbose,
                        text=True,
                    )
                    self.print_success("Shellcheck linting passed")
                except subprocess.CalledProcessError:
                    self.print_warning("Shellcheck found issues (non-blocking)")
            else:
                self.print_warning(
                    "Shellcheck not available - install for additional validation"
                )
        except FileNotFoundError:
            self.print_warning(
                "Shellcheck not available - install for additional validation"
            )

        if shell_errors == 0:
            self.tests_passed += 1
        else:
            self.tests_failed += 1

    def validate_python_linting(self) -> None:
        """Run Python linting with Ruff."""
        self.print_header("6. Python Linting (Ruff)")

        try:
            subprocess.run(["pipenv", "--version"], capture_output=True, check=True)
            self.run_command(["pipenv", "run", "lint"], "Ruff linting passed")
        except FileNotFoundError:
            # Fall back to direct ruff if pipenv not available
            try:
                subprocess.run(["ruff", "--version"], capture_output=True, check=True)
                self.run_command(
                    ["ruff", "check", "scripts/", "tools/", "tests/"],
                    "Ruff linting passed",
                )
            except (FileNotFoundError, subprocess.CalledProcessError):
                self.print_warning(
                    "Ruff not available - install with: pipenv install --dev"
                )

    def validate_python_formatting(self) -> None:
        """Check Python formatting with Ruff."""
        self.print_header("7. Python Formatting Check (Ruff)")

        try:
            subprocess.run(["pipenv", "--version"], capture_output=True, check=True)
            self.run_command(
                ["pipenv", "run", "format-check"], "Ruff formatting check passed"
            )
        except FileNotFoundError:
            # Fall back to direct ruff if pipenv not available
            try:
                subprocess.run(["ruff", "--version"], capture_output=True, check=True)
                self.run_command(
                    ["ruff", "format", "--check", "scripts/", "tools/", "tests/"],
                    "Ruff formatting check passed",
                )
            except (FileNotFoundError, subprocess.CalledProcessError):
                self.print_warning(
                    "Ruff not available - install with: pipenv install --dev"
                )

    def validate_security(self) -> None:
        """Run basic security validation."""
        self.print_header("8. Security Validation")

        # Simple grep-based check for hardcoded credentials
        scripts_dir = self.project_root / "scripts"
        patterns = [
            r"password\s*=\s*['\"][^'\"]+['\"]",
            r"secret\s*=\s*['\"][^'\"]+['\"]",
            r"token\s*=\s*['\"][^'\"]+['\"]",
        ]

        found_issues = False
        for script_file in scripts_dir.rglob("*.sh"):
            content = script_file.read_text()
            for pattern in patterns:
                import re

                if re.search(pattern, content, re.IGNORECASE):
                    # Exclude examples, tests, comments
                    if not re.search(
                        r"(example|test|comment|TODO)", content, re.IGNORECASE
                    ):
                        self.print_error(
                            f"Potential credential in {script_file.relative_to(self.project_root)}"
                        )
                        found_issues = True

        if not found_issues:
            self.print_success("No hardcoded credentials detected")
            self.tests_passed += 1
        else:
            self.print_error("Potential hardcoded credentials detected")
            self.tests_failed += 1

    def validate_nwave_framework(self) -> None:
        """Validate nWave framework structure."""
        self.print_header("9. nWave Framework Validation")

        # Check agent definitions
        agents_dir = self.project_root / "nWave" / "agents"
        if agents_dir.exists():
            agent_count = len(list(agents_dir.glob("*.md")))
            if agent_count >= 10:
                self.print_success(f"Agent definitions: {agent_count} found")
                self.tests_passed += 1
            else:
                self.print_warning(
                    f"Agent definitions: only {agent_count} found (expected >= 10)"
                )
                self.tests_failed += 1
        else:
            self.print_info("nWave agents directory not found")

        # Check command/task definitions
        tasks_dir = self.project_root / "nWave" / "tasks"
        if tasks_dir.exists():
            command_count = len(list(tasks_dir.glob("*.md")))
            self.print_success(f"Command definitions: {command_count} found")
            self.tests_passed += 1
        else:
            self.print_info("nWave tasks directory not found")

    def validate_documentation(self) -> None:
        """Validate required documentation exists."""
        self.print_header("10. Documentation Validation")

        required_docs = [
            "README.md",
            "docs/installation/INSTALL.md",
        ]

        doc_errors = 0
        for doc_path in required_docs:
            doc_file = self.project_root / doc_path
            if doc_file.exists():
                self.print_success(f"Documentation: {doc_path}")
            else:
                self.print_warning(f"Missing documentation: {doc_path}")
                doc_errors += 1

        if doc_errors == 0:
            self.tests_passed += 1
        else:
            self.tests_failed += 1

    def print_summary(self) -> None:
        """Print validation summary."""
        self.print_header("CI/CD Validation Results")

        if self.tests_failed == 0:
            print(f"{Fore.GREEN}{'━' * 50}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}✅ ALL CHECKS PASSED{Style.RESET_ALL}")
            print(f"{Fore.GREEN}{'━' * 50}{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}{'━' * 50}{Style.RESET_ALL}")
            print(f"{Fore.RED}❌ VALIDATION FAILED{Style.RESET_ALL}")
            print(f"{Fore.RED}{'━' * 50}{Style.RESET_ALL}")

        print(f"\n  Passed: {self.tests_passed}")
        print(f"  Failed: {self.tests_failed}")

        if self.tests_failed > 0:
            print(
                f"\n{Fore.YELLOW}⚠ Fix the above issues before pushing{Style.RESET_ALL}"
            )
            print(
                f"{Fore.YELLOW}⚠ CI/CD pipeline will fail with these errors{Style.RESET_ALL}"
            )
        else:
            print(f"\n{Fore.GREEN}✓ Your code is ready for CI/CD!{Style.RESET_ALL}")
            print(f"{Fore.GREEN}✓ Safe to push to remote repository{Style.RESET_ALL}")

    def run_all_validations(self) -> bool:
        """
        Run all validation checks.

        Returns:
            True if all validations passed, False otherwise
        """
        self.print_header("Local CI/CD Validation")
        print("Simulating GitHub Actions CI/CD pipeline locally")
        print(f"Project: {self.project_root}")

        # Run all validation phases
        self.validate_yaml()
        self.validate_pipenv_dependencies()
        self.run_python_tests()
        self.validate_build()
        self.validate_shell_scripts()
        self.validate_python_linting()
        self.validate_python_formatting()
        self.validate_security()
        self.validate_nwave_framework()
        self.validate_documentation()

        # Print summary
        self.print_summary()

        return self.tests_failed == 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Local CI/CD validation - mirrors GitHub Actions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show detailed output"
    )
    parser.add_argument(
        "--fast",
        "-f",
        action="store_true",
        help="Skip slower checks (build validation)",
    )

    args = parser.parse_args()

    validator = LocalCIValidator(verbose=args.verbose, fast_mode=args.fast)
    success = validator.run_all_validations()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
