"""Release simulation — validate pipeline steps locally without side effects.

Each simulate_* function returns a StepResult with PASS/WARN/FAIL status.
No tags are created, no releases are published, no artifacts are uploaded.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from scripts.build_plugin import BuildConfig, build


MINIMUM_WHEEL_SIZE_BYTES = 10_240


class Status(Enum):
    """Outcome status for a simulation step."""

    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


@dataclass(frozen=True)
class StepResult:
    """Immutable result of a single simulation step."""

    name: str
    status: Status
    message: str
    data: dict | None = None


# ---------------------------------------------------------------------------
# Version calculation (step 01-01)
# ---------------------------------------------------------------------------


def _compute_forced_base_version(current_version: str, bump_type: str) -> str | None:
    """Compute a base version from current version and bump type.

    Maps force_bump choices (patch/minor/major) to a concrete base version
    string compatible with next_version.py --base-version.

    Returns None if current_version cannot be parsed.
    """
    try:
        parts = [int(p) for p in current_version.split(".")[:3]]
    except (ValueError, IndexError):
        return None

    major, minor, micro = (
        parts[0],
        parts[1] if len(parts) > 1 else 0,
        parts[2] if len(parts) > 2 else 0,
    )

    if bump_type == "major":
        return f"{major + 1}.0.0"
    elif bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    else:  # patch
        return f"{major}.{minor}.{micro + 1}"


def simulate_version(stage: str, force_bump: str | None = None) -> StepResult:
    """Simulate version calculation using discover_tag + next_version."""
    try:
        from scripts.release.discover_tag import _filter_by_pattern, _git_tags

        # Discover latest tag for this stage
        pattern = "*.dev*" if stage == "dev" else "*rc*" if stage == "rc" else "*"
        tags = _git_tags()
        matches = _filter_by_pattern(tags, pattern)

        if matches:
            latest_tag, latest_ver = matches[-1]
            current_info = f"{latest_tag} ({latest_ver})"
        else:
            latest_tag = "none"
            current_info = "no existing tags"

        # Read current version from pyproject.toml
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                # Py3.10 fallback: tomllib is stdlib only on 3.11+
                "try:\n import tomllib\nexcept ImportError:\n import tomli as tomllib\n"
                "print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        current_version = result.stdout.strip() if result.returncode == 0 else "unknown"

        # Calculate next version
        args_list = ["--stage", stage, "--current-version", current_version]
        if force_bump:
            forced_base = _compute_forced_base_version(current_version, force_bump)
            if forced_base:
                args_list.extend(["--base-version", forced_base])
        calc_result = subprocess.run(
            [sys.executable, "scripts/release/next_version.py", *args_list],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if calc_result.returncode == 0:
            # Parse version from JSON output
            try:
                output = json.loads(calc_result.stdout)
                next_version = output.get("version", current_version)
            except json.JSONDecodeError:
                next_version = calc_result.stdout.strip().split("\n")[-1]
        else:
            next_version = f"{current_version}+"

        return StepResult(
            name="Version calculation",
            status=Status.PASS,
            message=f"{current_info} → {next_version} (stage={stage})",
            data={"version": next_version, "current": current_version, "stage": stage},
        )
    except Exception as exc:
        return StepResult(
            name="Version calculation",
            status=Status.FAIL,
            message=f"Version calculation failed: {exc}",
        )


# ---------------------------------------------------------------------------
# Build distribution (step 02-01)
# ---------------------------------------------------------------------------


def simulate_build(version: str) -> StepResult:
    """Simulate wheel build in temp directory."""
    build_dir = tempfile.mkdtemp(prefix="nwave-sim-build-")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "build", "--wheel", "--outdir", build_dir, "."],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(Path(__file__).parent.parent.parent),
        )
        if result.returncode != 0:
            return StepResult(
                name="Build distribution",
                status=Status.FAIL,
                message=f"Build failed: {result.stderr[:200]}",
            )

        wheels = [
            f for f in [p.name for p in Path(build_dir).iterdir()] if f.endswith(".whl")
        ]
        if not wheels:
            return StepResult(
                name="Build distribution",
                status=Status.FAIL,
                message="No wheel file produced",
            )

        wheel = wheels[0]
        wheel_path = Path(build_dir) / wheel
        size = wheel_path.stat().st_size

        if size < MINIMUM_WHEEL_SIZE_BYTES:
            return StepResult(
                name="Build distribution",
                status=Status.FAIL,
                message=f"Wheel too small: {size} bytes (expected >10KB)",
            )

        return StepResult(
            name="Build distribution",
            status=Status.PASS,
            message=f"{wheel} ({size // 1024}KB)",
        )
    except Exception as exc:
        return StepResult(
            name="Build distribution",
            status=Status.FAIL,
            message=f"Build error: {exc}",
        )
    finally:
        shutil.rmtree(build_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Tag conflict detection (step 01-02)
# ---------------------------------------------------------------------------


def _check_local_tag(tag_name: str) -> str | None:
    """Check if tag exists locally. Returns tag output or None."""
    result = subprocess.run(
        ["git", "tag", "-l", tag_name],
        capture_output=True,
        text=True,
        timeout=10,
    )
    output = result.stdout.strip()
    return output if output else None


def _check_remote_tag(tag_name: str) -> str | None:
    """Check if tag exists on remote. Returns ref line or None.

    Raises subprocess.SubprocessError on network failure or non-zero exit.
    """
    result = subprocess.run(
        ["git", "ls-remote", "--tags", "origin", tag_name],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise subprocess.SubprocessError(result.stderr[:200])

    output = result.stdout.strip()
    return output if output else None


def simulate_tag_check(tag_name: str) -> StepResult:
    """Check whether a tag already exists locally or on the remote.

    Returns:
        StepResult with FAIL if local conflict, WARN if remote-only
        conflict or network error, PASS if tag is new.
    """
    step_name = "Tag conflict check"

    # 1. Check local tags — always possible, no network needed
    local_match = _check_local_tag(tag_name)
    if local_match:
        return StepResult(
            name=step_name,
            status=Status.FAIL,
            message=f"Tag {tag_name} already exists locally",
        )

    # 2. Check remote tags — network may fail
    try:
        remote_match = _check_remote_tag(tag_name)
    except (subprocess.SubprocessError, OSError):
        return StepResult(
            name=step_name,
            status=Status.WARN,
            message=f"Could not check remote tags for {tag_name} (network error)",
        )

    if remote_match:
        return StepResult(
            name=step_name,
            status=Status.WARN,
            message=f"Tag {tag_name} exists on remote but not locally",
        )

    # 3. Tag is new
    return StepResult(
        name=step_name,
        status=Status.PASS,
        message=f"Tag {tag_name} is available (no conflicts)",
    )


# ---------------------------------------------------------------------------
# Plugin build simulation (step 02-02)
# ---------------------------------------------------------------------------

EXPECTED_HOOK_EVENT_TYPES = frozenset(
    ["PreToolUse", "PostToolUse", "SubagentStop", "SessionStart", "SubagentStart"]
)

MINIMUM_AGENT_COUNT = 20


def _validate_hooks_json(plugin_dir: Path) -> tuple[bool, str]:
    """Validate hooks.json has all 5 expected event types.

    Returns (ok, message). Pure validation on filesystem content.
    """
    hooks_path = plugin_dir / "hooks" / "hooks.json"
    if not hooks_path.exists():
        return False, "hooks.json not found"

    try:
        data = json.loads(hooks_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return False, f"hooks.json unreadable: {exc}"

    hooks_section = data.get("hooks", {})
    found_event_types = frozenset(hooks_section.keys())
    missing = EXPECTED_HOOK_EVENT_TYPES - found_event_types

    if missing:
        return False, f"Missing event types in hooks.json: {sorted(missing)}"

    return True, f"{len(found_event_types)} event types present"


def _count_agents(plugin_dir: Path) -> int:
    """Count agent .md files in the plugin agents directory."""
    agents_dir = plugin_dir / "agents"
    if not agents_dir.exists():
        return 0
    return len(list(agents_dir.glob("*.md")))


def _count_skills(plugin_dir: Path) -> int:
    """Count skill directories in the plugin skills directory."""
    skills_dir = plugin_dir / "skills"
    if not skills_dir.exists():
        return 0
    return len([d for d in skills_dir.iterdir() if d.is_dir()])


def _validate_plugin_structure(
    plugin_dir: Path,
) -> tuple[bool, list[str], dict[str, int]]:
    """Validate the built plugin structure.

    Returns (ok, errors, counts).
    """
    errors: list[str] = []
    counts: dict[str, int] = {}

    # Hooks validation
    hooks_ok, hooks_message = _validate_hooks_json(plugin_dir)
    if not hooks_ok:
        errors.append(hooks_message)

    # Agent count
    agent_count = _count_agents(plugin_dir)
    counts["agents"] = agent_count
    if agent_count < MINIMUM_AGENT_COUNT:
        errors.append(
            f"Only {agent_count} agents found, minimum is {MINIMUM_AGENT_COUNT}"
        )

    # Skills presence
    skill_count = _count_skills(plugin_dir)
    counts["skills"] = skill_count
    if skill_count == 0:
        errors.append("No skills found in plugin")

    return len(errors) == 0, errors, counts


def simulate_plugin(version: str) -> StepResult:
    """Build plugin in a temp directory and validate structure.

    Pipeline: create temp dir -> build plugin -> validate -> cleanup -> report.

    Returns StepResult with PASS and counts, or FAIL with what is missing.
    """
    step_name = "Plugin build"
    temp_dir = tempfile.mkdtemp(prefix="nwave-plugin-sim-")
    temp_path = Path(temp_dir)

    try:
        # Build plugin into temp directory
        project_root = Path(__file__).resolve().parent.parent.parent
        config = BuildConfig.from_project_root(project_root, temp_path / "plugin")

        build_result = build(config, version_override=version)

        if not build_result.is_success():
            return StepResult(
                name=step_name,
                status=Status.FAIL,
                message=f"Build failed: {build_result.error}",
            )

        # Validate plugin structure
        plugin_dir = build_result.output_dir
        valid, errors, counts = _validate_plugin_structure(plugin_dir)

        if not valid:
            return StepResult(
                name=step_name,
                status=Status.FAIL,
                message=f"Validation failed: {'; '.join(errors)}",
            )

        return StepResult(
            name=step_name,
            status=Status.PASS,
            message=(
                f"Plugin built and validated: "
                f"5 event types, "
                f"{counts['agents']} agents, "
                f"{counts['skills']} skills"
            ),
        )

    except Exception as exc:
        return StepResult(
            name=step_name,
            status=Status.FAIL,
            message=f"Unexpected error: {exc}",
        )

    finally:
        # Always clean up temp directory
        shutil.rmtree(temp_path, ignore_errors=True)


# ---------------------------------------------------------------------------
# Changelog generation simulation (step 03-01)
# ---------------------------------------------------------------------------


def simulate_changelog(version: str, stage: str) -> StepResult:
    """Generate changelog preview and validate non-empty output.

    Pipeline: find previous tag -> fetch commits -> categorize -> render -> validate.

    Returns StepResult with PASS and preview (first 5 lines), or FAIL with error.
    """
    step_name = "Changelog generation"

    try:
        import scripts.release.generate_changelog as changelog_mod

        prev_tag = changelog_mod._find_previous_tag(stage, version)
        raw_log = changelog_mod._fetch_commits(prev_tag)
        categories = changelog_mod._categorize_commits(raw_log)
        release_date = "SIMULATED"

        changelog = changelog_mod._render_markdown(
            stage=stage,
            version=version,
            source_tag="",
            repo="",
            prev_tag=prev_tag,
            categories=categories,
            release_date=release_date,
        )

        if not changelog.strip():
            return StepResult(
                name=step_name,
                status=Status.FAIL,
                message="Changelog output is empty",
            )

        # Preview: first 5 lines
        preview_lines = changelog.strip().splitlines()[:5]
        preview = "\n".join(preview_lines)

        return StepResult(
            name=step_name,
            status=Status.PASS,
            message=f"Changelog preview ({len(changelog)} chars):\n{preview}",
        )

    except Exception as exc:
        return StepResult(
            name=step_name,
            status=Status.FAIL,
            message=f"Unexpected error: {exc}",
        )


# ---------------------------------------------------------------------------
# Preflight checks (step 03-02)
# ---------------------------------------------------------------------------


def _check_ci_status() -> tuple[Status, str]:
    """Check latest CI run status via gh CLI.

    Returns (status, message). Network failures produce WARN, never FAIL.
    """
    try:
        result = subprocess.run(
            [
                "gh",
                "run",
                "list",
                "--workflow=ci.yml",
                "--limit",
                "1",
                "--json",
                "conclusion",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        runs = json.loads(result.stdout.strip() or "[]")

        if not runs:
            return Status.WARN, "No CI runs found"

        conclusion = runs[0].get("conclusion", "")
        if conclusion == "success":
            return Status.PASS, "CI status: success"

        return Status.WARN, f"CI status: {conclusion or 'unknown'}"

    except (subprocess.SubprocessError, OSError, json.JSONDecodeError) as exc:
        return Status.WARN, f"CI status unavailable ({exc})"


def _check_worktrees() -> tuple[Status, str]:
    """Check for unmerged git worktrees.

    Returns WARN if extra worktrees exist besides the main one.
    """
    try:
        result = subprocess.run(
            ["git", "worktree", "list"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except subprocess.TimeoutExpired:
        return Status.WARN, "Worktree check timed out"

    lines = [
        line.strip() for line in result.stdout.strip().splitlines() if line.strip()
    ]

    if len(lines) <= 1:
        return Status.PASS, "No extra worktrees"

    extra_count = len(lines) - 1
    return (
        Status.WARN,
        f"{extra_count} extra worktree(s) detected — consider merging before release",
    )


def _check_git_cleanliness() -> tuple[Status, str]:
    """Check for uncommitted changes in the working tree.

    Returns WARN if dirty (uncommitted changes present).
    """
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except subprocess.TimeoutExpired:
        return Status.WARN, "Git status check timed out"

    output = result.stdout.strip()

    if not output:
        return Status.PASS, "Working tree is clean"

    changed_count = len(output.splitlines())
    return (
        Status.WARN,
        f"Dirty working tree: {changed_count} uncommitted change(s)",
    )


def _combine_sub_checks(
    sub_checks: list[tuple[Status, str]],
) -> tuple[Status, str]:
    """Combine multiple sub-check results into a single status and message.

    FAIL if any sub-check FAIL, WARN if any WARN, PASS if all clean.
    """
    statuses = [status for status, _ in sub_checks]
    messages = [msg for _, msg in sub_checks]

    if Status.FAIL in statuses:
        combined_status = Status.FAIL
    elif Status.WARN in statuses:
        combined_status = Status.WARN
    else:
        combined_status = Status.PASS

    return combined_status, "; ".join(messages)


def simulate_preflight() -> StepResult:
    """Run preflight checks: CI status, worktree state, git cleanliness.

    Pipeline: check CI -> check worktrees -> check cleanliness -> combine results.

    Network-dependent checks (CI) produce WARN on failure, never FAIL.
    Returns StepResult with combined PASS/WARN/FAIL status.
    """
    step_name = "Preflight checks"

    sub_checks = [
        _check_ci_status(),
        _check_worktrees(),
        _check_git_cleanliness(),
    ]

    combined_status, combined_message = _combine_sub_checks(sub_checks)

    return StepResult(
        name=step_name,
        status=combined_status,
        message=combined_message,
    )


# ---------------------------------------------------------------------------
# Summary and CLI entry point
# ---------------------------------------------------------------------------

_STATUS_SYMBOLS = {
    Status.PASS: "PASS",
    Status.WARN: "WARN",
    Status.FAIL: "FAIL",
}


def print_summary(results: list[StepResult]) -> None:
    """Print a formatted summary table of all simulation results."""
    print("\n" + "=" * 60)
    print("Release Simulation Summary")
    print("=" * 60)

    for result in results:
        symbol = _STATUS_SYMBOLS[result.status]
        print(f"\n  [{symbol}] {result.name}")
        for line in result.message.splitlines():
            print(f"         {line}")

    print("\n" + "-" * 60)

    statuses = [r.status for r in results]
    if Status.FAIL in statuses:
        overall = "FAIL"
    elif Status.WARN in statuses:
        overall = "WARN"
    else:
        overall = "PASS"

    fail_count = statuses.count(Status.FAIL)
    warn_count = statuses.count(Status.WARN)
    pass_count = statuses.count(Status.PASS)

    print(
        f"  Overall: {overall}  "
        f"({pass_count} passed, {warn_count} warnings, {fail_count} failures)"
    )
    print("=" * 60 + "\n")


def main(argv: list[str] | None = None) -> int:
    """Run all simulation steps and print summary.

    Returns 0 on PASS/WARN, 1 on FAIL.
    """
    parser = argparse.ArgumentParser(
        description="Simulate release pipeline steps locally."
    )
    parser.add_argument(
        "--stage",
        choices=["dev", "rc", "prod"],
        default="dev",
        help="Release stage (default: dev)",
    )
    parser.add_argument(
        "--force-bump",
        choices=["patch", "minor", "major"],
        default=None,
        help="Force a specific version bump type",
    )
    args = parser.parse_args(argv)

    results: list[StepResult] = []

    # Step 1: Version calculation
    version_result = simulate_version(args.stage, args.force_bump)
    results.append(version_result)

    # Extract version from result for downstream steps
    version = (
        version_result.message.split("→")[-1].strip().split()[0]
        if version_result.status == Status.PASS
        else "0.0.0-sim"
    )
    tag_name = f"v{version}"

    # Step 2: Tag conflict check
    results.append(simulate_tag_check(tag_name))

    # Step 3: Build distribution
    results.append(simulate_build(version))

    # Step 4: Plugin build
    results.append(simulate_plugin(version))

    # Step 5: Changelog generation
    results.append(simulate_changelog(version, args.stage))

    # Step 6: Preflight checks
    results.append(simulate_preflight())

    # Print summary
    print_summary(results)

    # Return exit code: 0 for PASS/WARN, 1 for FAIL
    has_failure = any(r.status == Status.FAIL for r in results)
    return 1 if has_failure else 0


if __name__ == "__main__":
    sys.exit(main())
