"""CLI: Verify nWave installation health with 7 diagnostic checks.

Usage:
    des-health-check
    des-health-check --json

Checks:
    1. version         - Read VERSION file, report version
    2. module_import   - Try importing des module
    3. templates       - Verify step-tdd-cycle-schema.json exists
    4. hook_actions    - Verify hook adapter module is importable
    5. log_directory   - Verify ~/.nwave/logs/ is writable
    6. agents_installed - Count .md files in agents directory
    7. skills_installed - Count nw-*/SKILL.md in skills directory

Exit codes:
    0 = All checks pass (HEALTHY)
    1 = One or more checks failed (UNHEALTHY)
    2 = Usage error (argparse default)
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class CheckResult:
    """Result of a single health check."""

    name: str
    passed: bool
    detail: str


def _check_version(version_path: Path) -> CheckResult:
    """Check 1: Report nWave version.

    Resolution order:
    1. Explicit VERSION file (when passed by test or custom path)
    2. PyPI/pipx package metadata (importlib.metadata)
    3. pyproject.toml in project root (source development)
    4. Presence of templates dir as fallback
    """
    try:
        # Strategy 1: Explicit VERSION file (test-injectable)
        if version_path.is_file():
            ver = version_path.read_text(encoding="utf-8").strip()
            if ver:
                return CheckResult("version", True, ver)

        # Strategy 2: PyPI/pipx installation — importlib.metadata
        from importlib.metadata import version as pkg_version

        try:
            ver = pkg_version("nwave-ai")
            return CheckResult("version", True, ver)
        except Exception:
            pass

        # Strategy 3: Source — pyproject.toml in project root
        for candidate in [Path.cwd(), *Path.cwd().parents]:
            pyproject = candidate / "pyproject.toml"
            if pyproject.exists():
                for line in pyproject.read_text().splitlines():
                    if line.strip().startswith("version") and "=" in line:
                        ver = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if ver and ver[0].isdigit():
                            return CheckResult("version", True, f"{ver} (source)")
                        break
                break

        # Strategy 4: Check if installed at all (claude_dir heuristic)
        if (
            version_path.parent.is_dir()
            and (version_path.parent / "templates").exists()
        ):
            return CheckResult("version", True, "installed (version unknown)")

        return CheckResult("version", False, "nWave not detected")
    except Exception as exc:
        return CheckResult("version", False, str(exc))


def _check_module_import() -> CheckResult:
    """Check 2: Try importing des module."""
    try:
        importlib.import_module("des")
        return CheckResult("module_import", True, "des module loaded")
    except ImportError as exc:
        return CheckResult("module_import", False, f"import failed: {exc}")
    except Exception as exc:
        return CheckResult("module_import", False, str(exc))


def _check_templates(templates_dir: Path) -> CheckResult:
    """Check 3: Verify step-tdd-cycle-schema.json exists."""
    try:
        schema_path = templates_dir / "step-tdd-cycle-schema.json"
        if schema_path.exists():
            return CheckResult("templates", True, "step-tdd-cycle-schema.json found")
        return CheckResult("templates", False, "step-tdd-cycle-schema.json not found")
    except Exception as exc:
        return CheckResult("templates", False, str(exc))


def _check_hook_actions() -> CheckResult:
    """Check 4: Verify hook adapter module is importable."""
    try:
        mod = importlib.import_module(
            "des.adapters.drivers.hooks.claude_code_hook_adapter"
        )
        action_count = 0
        for name in dir(mod):
            if name.startswith("handle_"):
                action_count += 1
        return CheckResult("hook_actions", True, f"{action_count} actions respond")
    except ImportError as exc:
        return CheckResult("hook_actions", False, f"import failed: {exc}")
    except Exception as exc:
        return CheckResult("hook_actions", False, str(exc))


def _check_log_directory(logs_dir: Path) -> CheckResult:
    """Check 5: Verify logs directory is writable (or can be created)."""
    try:
        if logs_dir.exists():
            if logs_dir.is_dir():
                test_file = logs_dir / ".health_check_probe"
                try:
                    test_file.write_text("")
                    test_file.unlink()
                    return CheckResult("log_directory", True, f"{logs_dir} writable")
                except OSError as exc:
                    return CheckResult(
                        "log_directory", False, f"{logs_dir} not writable: {exc}"
                    )
            return CheckResult(
                "log_directory", False, f"{logs_dir} exists but is not a directory"
            )
        try:
            logs_dir.mkdir(parents=True, exist_ok=True)
            return CheckResult("log_directory", True, f"{logs_dir} created")
        except OSError as exc:
            return CheckResult(
                "log_directory", False, f"cannot create {logs_dir}: {exc}"
            )
    except Exception as exc:
        return CheckResult("log_directory", False, str(exc))


def _check_artifact_count(
    check_name: str, target_dir: Path, glob_pattern: str, noun: str
) -> CheckResult:
    """Shared count-based health check: glob a pattern under target_dir.

    Extracted 2026-05-03 (RPP L3) — `_check_agents_installed` and
    `_check_skills_installed` were 9-line clones differing only in
    check name, glob pattern, and noun.
    """
    try:
        if not target_dir.exists():
            return CheckResult(check_name, False, f"{noun} directory not found")
        matches = list(target_dir.glob(glob_pattern))
        return CheckResult(check_name, True, f"{len(matches)} {noun}")
    except Exception as exc:
        return CheckResult(check_name, False, str(exc))


def _check_agents_installed(agents_dir: Path) -> CheckResult:
    """Check 6: Count .md files in agents directory."""
    return _check_artifact_count("agents_installed", agents_dir, "*.md", "agents")


def _check_skills_installed(skills_dir: Path) -> CheckResult:
    """Check 7: Count nw-*/SKILL.md dirs in skills directory."""
    return _check_artifact_count(
        "skills_installed", skills_dir, "nw-*/SKILL.md", "skills"
    )


def _run_all_checks(
    version_file: Path,
    templates_dir: Path,
    logs_dir: Path,
    agents_dir: Path,
    skills_dir: Path,
) -> list[CheckResult]:
    """Run all 7 checks, each independently (one failure does not block others)."""
    return [
        _check_version(version_file),
        _check_module_import(),
        _check_templates(templates_dir),
        _check_hook_actions(),
        _check_log_directory(logs_dir),
        _check_agents_installed(agents_dir),
        _check_skills_installed(skills_dir),
    ]


def _format_human(checks: list[CheckResult]) -> str:
    """Format checks as human-readable output."""
    lines = ["nWave Health Check"]
    for check in checks:
        icon = "PASS" if check.passed else "FAIL"
        lines.append(f"  [{icon}] {check.name}: {check.detail}")

    passed_count = sum(1 for c in checks if c.passed)
    total = len(checks)
    status = "HEALTHY" if passed_count == total else "UNHEALTHY"
    lines.append("")
    lines.append(f"Status: {status} ({passed_count}/{total} checks passed)")
    return "\n".join(lines)


def _format_json(checks: list[CheckResult]) -> str:
    """Format checks as JSON output."""
    passed_count = sum(1 for c in checks if c.passed)
    total = len(checks)
    status = "healthy" if passed_count == total else "unhealthy"

    version_check = next((c for c in checks if c.name == "version"), None)
    version = (
        version_check.detail if version_check and version_check.passed else "unknown"
    )

    data = {
        "status": status,
        "checks": [asdict(c) for c in checks],
        "version": version,
    }
    return json.dumps(data, indent=2)


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for health_check CLI."""
    parser = argparse.ArgumentParser(
        prog="des.cli.health_check",
        description="Verify nWave installation health.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output results as JSON for machine consumption",
    )
    return parser


def _default_paths() -> dict[str, Path]:
    """Return default paths for health check targets."""
    home = Path.home()
    claude_dir = home / ".claude"
    return {
        "version_file": claude_dir / "VERSION",
        "templates_dir": claude_dir / "templates",
        "logs_dir": home / ".nwave" / "logs",
        "agents_dir": claude_dir / "agents" / "nw",
        "skills_dir": claude_dir / "skills",
    }


def main(
    argv: list[str] | None = None,
    *,
    version_file: Path | None = None,
    templates_dir: Path | None = None,
    logs_dir: Path | None = None,
    agents_dir: Path | None = None,
    skills_dir: Path | None = None,
) -> int:
    """Entry point for the health_check CLI tool.

    Args:
        argv: Command-line arguments. Uses sys.argv[1:] if None.
        version_file: Override path to VERSION file (for testing).
        templates_dir: Override path to templates directory (for testing).
        logs_dir: Override path to logs directory (for testing).
        agents_dir: Override path to agents directory (for testing).
        skills_dir: Override path to skills directory (for testing).

    Returns:
        Exit code: 0=all healthy, 1=one or more checks failed.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    defaults = _default_paths()
    resolved_version_file = version_file or defaults["version_file"]
    resolved_templates_dir = templates_dir or defaults["templates_dir"]
    resolved_logs_dir = logs_dir or defaults["logs_dir"]
    resolved_agents_dir = agents_dir or defaults["agents_dir"]
    resolved_skills_dir = skills_dir or defaults["skills_dir"]

    checks = _run_all_checks(
        resolved_version_file,
        resolved_templates_dir,
        resolved_logs_dir,
        resolved_agents_dir,
        resolved_skills_dir,
    )

    if args.json_output:
        print(_format_json(checks))
    else:
        print(_format_human(checks))

    all_passed = all(c.passed for c in checks)
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
