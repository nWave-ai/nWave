#!/usr/bin/env python3
"""Pytest Test Validation Hook

Ensures all tests pass before commit.

Optimizations (v2):
  - Fail-fast (-x): stops at first failure
  - Changed-file targeting: maps staged files to relevant test directories
  - Build acceptance tests moved to pre-push (slow plugin assembly)
  - Parallel execution via pytest-xdist (-n auto)
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

# Source prefix → test directories mapping
_SOURCE_TO_TESTS: dict[str, list[str]] = {
    "src/des/": ["tests/des/", "tests/bugs/des/"],
    "scripts/install/plugins/": ["tests/plugins/", "tests/bugs/plugins/"],
    "scripts/install/": ["tests/installer/", "tests/bugs/installer/"],
    "scripts/validation/": ["tests/validation/"],
    "scripts/framework/": ["tests/build/"],
    "scripts/build_dist.py": ["tests/build/"],
    "scripts/shared/": ["tests/plugins/", "tests/installer/"],
    "scripts/observability/": ["tests/observability/"],
    "scripts/hooks/": [],
    "scripts/docgen.py": [],
    "nWave/": ["tests/build/"],
    "nwave_ai/": ["tests/installer/"],
    "docs/": [],
    ".github/": [],
}

# Files that force a full test run (config changes can affect anything)
_RUN_ALL_TRIGGERS = {
    "pyproject.toml",
    "setup.cfg",
    "conftest.py",
    "tests/conftest.py",
    "Pipfile",
    "Pipfile.lock",
}


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


def get_targeted_test_dirs() -> list[str] | None | str:
    """Map staged files to relevant test directories.

    Returns:
      - list[str]: targeted test directories to run (non-empty)
      - None: run the full suite (config changed, unknown file, git failed)
      - "skip": no relevant tests for these staged files (docs/CI only)
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

    staged = [f for f in result.stdout.strip().split("\n") if f]
    if not staged:
        return None

    test_dirs: set[str] = set()

    for filepath in staged:
        # Config files → run everything
        if filepath in _RUN_ALL_TRIGGERS:
            return None

        # Changed test files → include their top-level test directory
        if filepath.startswith("tests/"):
            parts = filepath.split("/")
            if len(parts) >= 2:
                test_dirs.add(f"tests/{parts[1]}/")
            continue

        # Match against source prefix map (longest prefix first)
        matched = False
        for prefix, dirs in sorted(
            _SOURCE_TO_TESTS.items(), key=lambda x: len(x[0]), reverse=True
        ):
            if filepath.startswith(prefix) or filepath == prefix:
                test_dirs.update(dirs)
                matched = True
                break

        # Unknown file → run everything (safe fallback)
        if not matched:
            return None

    if not test_dirs:
        # Every staged file matched a known prefix mapped to no test dirs
        # (docs/, scripts/hooks/, .github/, etc.). Skip pytest entirely —
        # these files have no runtime impact on Python code under test.
        # An "unknown file" path returns None earlier (full-suite safety net).
        return "skip"

    # Keep only directories that actually exist
    existing = sorted(d for d in test_dirs if Path(d).is_dir())
    return existing if existing else None


def has_xdist() -> bool:
    """Check if pytest-xdist is available."""
    try:
        import importlib.util

        return importlib.util.find_spec("xdist") is not None
    except Exception:
        return False


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

    # Determine test scope: skip / targeted / full suite
    targeted = get_targeted_test_dirs()
    if targeted == "skip":
        print(
            f"{GREEN}Skip mode: only doc / CI / hook files staged — "
            f"no Python runtime impact{NC}"
        )
        return 0
    if isinstance(targeted, list) and targeted:
        test_targets = targeted
        print(
            f"{BLUE}Targeted mode: {len(targeted)} directories "
            f"({', '.join(t.rstrip('/').split('/')[-1] for t in targeted)}){NC}"
        )
    else:
        test_targets = ["tests/"]
        print(f"{BLUE}Full suite mode{NC}")

    # Run tests and capture output
    try:
        # Configure environment for subprocess - ensure Python can find project modules
        env = os.environ.copy()
        env["PYTHONPATH"] = os.getcwd() + ":" + env.get("PYTHONPATH", "")

        # Pre-commit runs unit/acceptance tests only.
        # Integration, e2e, and build acceptance tests run at pre-push.
        base_args = [
            *test_targets,
            "-x",
            "--tb=short",
            "--ignore-glob=**/integration/**",
            "--ignore-glob=**/e2e/**",
            "--ignore-glob=**/build/acceptance/**",
        ]

        # Parallel execution with pytest-xdist (if available)
        # --dist loadfile keeps tests from the same file on one worker
        # (prevents shared-fixture conflicts between BDD scenarios)
        if has_xdist():
            base_args.extend(["-n", "auto", "--dist", "loadfile"])
        else:
            base_args.append("-v")

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

    # Observation-only telemetry: collect runtime, never blocks
    try:
        from scripts.hooks.test_runtime_observe import observe_runtime

        scope = "targeted" if isinstance(targeted, list) else "full"
        observe_runtime(test_output, scope=scope, project_root=Path())
    except Exception:
        pass  # telemetry must never block the pipeline

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
