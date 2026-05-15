#!/usr/bin/env python3
"""Install-and-import smoke validation for the nwave wheel.

Validates that a wheel installed in a clean venv produces a working
DES runtime and nwave-ai CLI -- no dev dependencies required.

Pure validation pipeline:
  check_importable(venv_python, module)    -> CheckResult
  check_module_runnable(venv_python, module, args) -> CheckResult
  check_no_src_imports(site_packages, pkg) -> CheckResult
  find_site_packages(venv_python)          -> Path
  run_install_smoke(venv_python)           -> InstallSmokeReport

Usage:
    python scripts/validation/validate_installed_wheel.py <path-to-venv-python>
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


# ---------------------------------------------------------------------------
# Domain types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CheckResult:
    """Result of a single smoke check."""

    check_name: str
    passed: bool
    message: str


@dataclass(frozen=True)
class InstallSmokeReport:
    """Aggregated results from all smoke checks."""

    results: list[CheckResult] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        """True if every check passed."""
        return all(r.passed for r in self.results)


# ---------------------------------------------------------------------------
# Pure functions: venv introspection
# ---------------------------------------------------------------------------


def find_site_packages(venv_python: Path) -> Path:
    """Locate the site-packages directory for a venv's Python interpreter.

    Runs a subprocess to ask the interpreter for its site-packages path.
    Raises RuntimeError if the interpreter cannot be queried.
    """
    result = subprocess.run(
        [
            str(venv_python),
            "-c",
            (
                "import site; "
                "paths = site.getsitepackages(); "
                "print(paths[0] if paths else '')"
            ),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        msg = f"Failed to query site-packages: {result.stderr.strip()}"
        raise RuntimeError(msg)

    site_packages_path = Path(result.stdout.strip())
    if not site_packages_path.exists():
        msg = f"site-packages path does not exist: {site_packages_path}"
        raise RuntimeError(msg)

    return site_packages_path


# ---------------------------------------------------------------------------
# Pure functions: individual checks
# ---------------------------------------------------------------------------


def check_importable(venv_python: Path, module_name: str) -> CheckResult:
    """Check whether a module is importable in the given venv.

    Runs ``python -c "import <module>"`` in a subprocess using the
    venv's interpreter. Returns a CheckResult indicating success or failure.
    """
    result = subprocess.run(
        [str(venv_python), "-c", f"import {module_name}"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode == 0:
        return CheckResult(
            check_name=f"import:{module_name}",
            passed=True,
            message=f"Module {module_name} imported successfully",
        )
    return CheckResult(
        check_name=f"import:{module_name}",
        passed=False,
        message=(
            f"Module {module_name} not importable: "
            f"{result.stderr.strip().splitlines()[-1] if result.stderr.strip() else 'unknown error'}"
        ),
    )


def check_module_runnable(
    venv_python: Path,
    module_name: str,
    args: list[str] | None = None,
    allow_nonzero: bool = False,
) -> CheckResult:
    """Check whether a module is runnable via ``python -m <module>``.

    If allow_nonzero is True, any exit code is accepted as long as the
    process does not crash with a traceback (ModuleNotFoundError, etc.).
    """
    cmd = [str(venv_python), "-m", module_name, *(args or [])]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=60,
    )

    has_import_error = any(
        err_type in result.stderr
        for err_type in ["ModuleNotFoundError", "ImportError", "Traceback"]
    )

    if allow_nonzero:
        if has_import_error:
            return CheckResult(
                check_name=f"run:{module_name}",
                passed=False,
                message=(
                    f"Module {module_name} crashed on run: "
                    f"{result.stderr.strip().splitlines()[-1] if result.stderr.strip() else 'unknown error'}"
                ),
            )
        return CheckResult(
            check_name=f"run:{module_name}",
            passed=True,
            message=f"Module {module_name} runnable (exit code {result.returncode})",
        )

    if result.returncode != 0:
        return CheckResult(
            check_name=f"run:{module_name}",
            passed=False,
            message=(
                f"Module {module_name} exited with code {result.returncode}: "
                f"{result.stderr.strip().splitlines()[-1] if result.stderr.strip() else result.stdout.strip()}"
            ),
        )
    return CheckResult(
        check_name=f"run:{module_name}",
        passed=True,
        message=f"Module {module_name} ran successfully: {result.stdout.strip()[:200]}",
    )


def check_no_src_imports(site_packages: Path, package_name: str) -> CheckResult:
    """Check that no files in the installed package contain 'src.des' imports.

    Scans all .py files in site_packages/<package_name>/ for occurrences of
    'from src.des' or 'import src.des'. Returns a CheckResult with any
    offending files listed in the message.
    """
    package_dir = site_packages / package_name
    if not package_dir.exists():
        return CheckResult(
            check_name=f"no_src_imports:{package_name}",
            passed=False,
            message=f"Package directory not found: {package_dir}",
        )

    offending_files: list[str] = []
    for py_file in package_dir.rglob("*.py"):
        try:
            content = py_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        for line_number, line in enumerate(content.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if "from src.des" in line or "import src.des" in line:
                relative_path = py_file.relative_to(site_packages)
                offending_files.append(f"{relative_path}:{line_number}: {stripped}")

    if offending_files:
        return CheckResult(
            check_name=f"no_src_imports:{package_name}",
            passed=False,
            message=(
                f"Found {len(offending_files)} src.des import(s):\n"
                + "\n".join(f"  {f}" for f in offending_files)
            ),
        )
    return CheckResult(
        check_name=f"no_src_imports:{package_name}",
        passed=True,
        message=f"No src.des imports found in {package_name}/",
    )


# ---------------------------------------------------------------------------
# Composition: full smoke pipeline
# ---------------------------------------------------------------------------


SMOKE_CHECK_MODULES = [
    "des.domain",
    "des.application",
    "des.adapters",
    "des.ports",
    "des.cli",
    "des.config",
    "des.adapters.drivers.hooks.claude_code_hook_adapter",
    "nwave_ai.cli",
]


def run_install_smoke(venv_python: Path) -> InstallSmokeReport:
    """Run all install smoke checks against a venv.

    Returns an InstallSmokeReport with results for each check:
      - Import checks for all DES modules and nwave_ai.cli
      - No src.des import paths check
      - DES hook adapter runnability check
    """
    results: list[CheckResult] = []

    # Check all required modules are importable
    for module_name in SMOKE_CHECK_MODULES:
        results.append(check_importable(venv_python, module_name))

    # Check no src.des imports remain
    try:
        site_packages = find_site_packages(venv_python)
        results.append(check_no_src_imports(site_packages, "des"))
    except RuntimeError as exc:
        results.append(
            CheckResult(
                check_name="no_src_imports:des",
                passed=False,
                message=str(exc),
            )
        )

    # Check DES hook adapter is runnable as module
    results.append(
        check_module_runnable(
            venv_python,
            "des.adapters.drivers.hooks.claude_code_hook_adapter",
            args=[],
            allow_nonzero=True,
        )
    )

    return InstallSmokeReport(results=results)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> int:
    """Validate an installed wheel from the command line.

    Usage: python validate_installed_wheel.py <path-to-venv-python>

    Returns 0 if all checks pass, 1 if any fail, 2 if usage error.
    """
    if len(sys.argv) != 2:
        print(
            f"Usage: {sys.argv[0]} <path-to-venv-python>",
            file=sys.stderr,
        )
        return 2

    venv_python = Path(sys.argv[1])
    if not venv_python.exists():
        print(f"ERROR: Python interpreter not found: {venv_python}", file=sys.stderr)
        return 2

    report = run_install_smoke(venv_python)

    if report.all_passed:
        print(f"PASS: All {len(report.results)} smoke checks passed.")
        return 0

    failures = [r for r in report.results if not r.passed]
    passes = [r for r in report.results if r.passed]
    print(f"FAIL: {len(failures)} of {len(report.results)} check(s) failed:")
    for result in failures:
        print(f"  [FAIL] {result.check_name}: {result.message}")
    if passes:
        print(f"\n  {len(passes)} check(s) passed:")
        for result in passes:
            print(f"  [PASS] {result.check_name}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
