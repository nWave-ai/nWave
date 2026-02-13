#!/usr/bin/env python3
"""Pytest Test Validation Hook

Ensures all tests pass before commit.
"""

import os
import re
import subprocess
import sys
from pathlib import Path


# Color codes
RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
BLUE = "\033[0;34m"
NC = "\033[0m"


def clear_git_environment():
    """Clear git environment variables that pre-commit sets.

    These can interfere with tests that create temporary git repositories.
    """
    git_vars = [
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_INDEX_FILE",
        "GIT_AUTHOR_DATE",
        "GIT_AUTHOR_NAME",
        "GIT_AUTHOR_EMAIL",
    ]
    for var in git_vars:
        os.environ.pop(var, None)


def main():
    """Run test validation."""
    clear_git_environment()

    print(f"{BLUE}Running test validation...{NC}")

    # Check if pytest is available
    try:
        subprocess.run(
            ["python3", "--version"], check=True, capture_output=True, text=True
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(f"{YELLOW}Warning: python3 not available, skipping tests{NC}")
        return 0

    # Determine pytest command: prefer pipenv run (matches CI) over bare python3
    use_pipenv = False
    try:
        subprocess.run(
            ["pipenv", "run", "python3", "-m", "pytest", "--version"],
            check=True,
            capture_output=True,
            text=True,
        )
        use_pipenv = True
    except (subprocess.CalledProcessError, FileNotFoundError):
        try:
            subprocess.run(
                ["python3", "-m", "pytest", "--version"],
                check=True,
                capture_output=True,
                text=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"{YELLOW}Warning: pytest not available, skipping tests{NC}")
            return 0

    # Check if tests directory exists
    if not Path("tests").is_dir():
        print(f"{YELLOW}No tests directory found, skipping tests{NC}")
        return 0

    # Run tests and capture output
    try:
        # Configure environment for subprocess - ensure Python can find project modules
        env = os.environ.copy()
        env["PYTHONPATH"] = os.getcwd() + ":" + env.get("PYTHONPATH", "")

        # Pre-commit runs unit/acceptance tests only.
        # Integration and e2e tests run at pre-push (validate_tests_slow.py).
        base_args = [
            "tests/",
            "-v",
            "--tb=short",
            "--ignore-glob=**/integration/**",
            "--ignore-glob=**/e2e/**",
        ]
        cmd = (
            ["pipenv", "run", "python3", "-m", "pytest", *base_args]
            if use_pipenv
            else ["python3", "-m", "pytest", *base_args]
        )
        result = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )
        test_output = result.stdout + result.stderr
        test_exit_code = result.returncode
    except Exception as e:
        print(f"{RED}Error running tests: {e}{NC}")
        return 1

    # Count tests using regex
    passed_match = re.search(r"(\d+) passed", test_output)
    failed_match = re.search(r"(\d+) failed", test_output)

    total_tests = int(passed_match.group(1)) if passed_match else 0
    failed_tests = int(failed_match.group(1)) if failed_match else 0

    if test_exit_code == 0:
        print(f"{GREEN}All tests passing ({total_tests}/{total_tests}){NC}")
        return 0
    elif test_exit_code == 5:
        # Exit code 5 = no tests collected
        print(f"{YELLOW}No tests found, skipping test validation{NC}")
        return 0
    else:
        print()
        print(f"{RED}COMMIT BLOCKED: Tests failed{NC}")
        print()

        # Print full pytest output to see actual error details
        print(f"{RED}Full pytest output:{NC}")
        print(test_output)
        print()

        print(f"{RED}Failed tests:{NC}")

        # Extract and display failed test lines
        for line in test_output.split("\n"):
            if "FAILED" in line or "ERROR" in line:
                print(f"  {line}")

        print()

        if failed_tests > 0:
            passing_tests = total_tests - failed_tests
            print(
                f"{RED}Test Results: {passing_tests}/{total_tests} passing ({failed_tests} failed){NC}"
            )

        print()
        print(f"{YELLOW}Fix failing tests before committing.{NC}")
        print(f"{YELLOW}Emergency bypass: git commit --no-verify{NC}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
