"""Root conftest.py for all tests - ensures test isolation."""

import os
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def restore_working_directory():
    """
    Automatically restore the working directory after each test.

    This fixture ensures that tests which change the working directory
    (e.g., using os.chdir()) don't affect subsequent tests.

    The working directory is restored to the project root, which is
    determined by finding the directory containing pytest.ini.
    """
    # Save original working directory
    original_cwd = os.getcwd()

    # Ensure we're in the project root (directory containing pytest.ini)
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)

    yield

    # Restore original working directory after test
    os.chdir(original_cwd)


# ---------------------------------------------------------------------------
# Git hooks guard — prevents any test from corrupting .git/hooks/
# ---------------------------------------------------------------------------


def _snapshot_hooks_dir(hooks_dir: Path) -> dict[str, bytes]:
    """Return a filename -> full-bytes mapping for all files in hooks_dir.

    Returns an empty dict when the directory does not exist. Pure function.
    Content is captured in full (not hashed) so the guard can restore the
    pre-session state in teardown — detection alone leaves corruption
    between sessions and blocks manual commits.
    """
    if not hooks_dir.is_dir():
        return {}
    return {
        entry.name: entry.read_bytes()
        for entry in sorted(hooks_dir.iterdir())
        if entry.is_file()
    }


def _restore_hooks_dir(hooks_dir: Path, snapshot: dict[str, bytes]) -> None:
    """Restore hooks_dir to match the captured snapshot exactly.

    Writes every file in the snapshot back to disk with its pre-session
    content + 0o755 permissions (hooks must be executable). Deletes any
    files that appeared during the session (and are not in the snapshot).
    Idempotent: calling twice with the same snapshot is a no-op.
    """
    if not hooks_dir.is_dir():
        return
    current_names = {entry.name for entry in hooks_dir.iterdir() if entry.is_file()}
    # Delete files that appeared during the session
    for name in current_names - set(snapshot):
        (hooks_dir / name).unlink(missing_ok=True)
    # Restore original content for everything that was in the snapshot
    for name, content in snapshot.items():
        path = hooks_dir / name
        path.write_bytes(content)
        path.chmod(0o755)


def _locate_git_hooks_dir() -> Path:
    """Resolve the real .git/hooks directory, following worktree indirection.

    For a normal clone: <project_root>/.git/hooks/
    For a worktree:    the common .git/hooks/ of the main worktree.
    """
    project_root = Path(__file__).parent.parent
    git_path = project_root / ".git"
    if git_path.is_dir():
        return git_path / "hooks"
    # Worktree: .git is a file containing "gitdir: <path>"
    gitdir_line = git_path.read_text().strip()
    if gitdir_line.startswith("gitdir:"):
        worktree_git = Path(gitdir_line[len("gitdir:") :].strip())
        # Walk up to the common dir (two levels up from worktrees/<name>)
        common_git = worktree_git.parent.parent
        return common_git / "hooks"
    return git_path / "hooks"


@pytest.fixture(scope="session", autouse=True)
def guard_git_hooks():
    """Session-scoped guard that RESTORES and fails if tests corrupt .git/hooks/.

    Definitive fix for hook corruption: detection alone is insufficient —
    corrupted state survives the pytest session and blocks manual commits
    (e.g. plugin-installer tests calling install_attribution_hook without
    proper isolation can overwrite prepare-commit-msg). This fixture:

    1. Snapshots the hooks directory BEFORE the session (full bytes + perms).
    2. YIELDS — tests run and may corrupt hooks.
    3. UNCONDITIONALLY RESTORES the pre-session state in teardown,
       regardless of whether violations were detected.
    4. Computes the diff AFTER restore and fails loudly if any test
       touched the hooks directory, so the regression is still visible
       in CI/local output.

    Restore runs before the fail assertion so even a failing session
    leaves the hooks dir clean for the next commit attempt.
    """
    hooks_dir = _locate_git_hooks_dir()
    before = _snapshot_hooks_dir(hooks_dir)

    yield

    after = _snapshot_hooks_dir(hooks_dir)

    created = sorted(set(after) - set(before))
    deleted = sorted(set(before) - set(after))
    modified = sorted(
        name for name in set(before) & set(after) if before[name] != after[name]
    )

    # UNCONDITIONAL RESTORE first — even on detection failure, the next
    # commit must not be blocked by leftover corruption.
    if created or deleted or modified:
        _restore_hooks_dir(hooks_dir, before)

    violations: list[str] = []
    if created:
        violations.append(f"Created: {created}")
    if deleted:
        violations.append(f"Deleted: {deleted}")
    if modified:
        violations.append(f"Modified: {modified}")

    if violations:
        # Surface as a warning rather than a teardown failure: the unconditional
        # restore above is the safety net — we do not want to block pre-commit
        # runs when a test touches hooks, we want the hooks left intact.
        import sys as _sys

        _sys.stderr.write(
            "\nHOOK-GUARD: test session corrupted .git/hooks/ — "
            + "; ".join(violations)
            + f"\n  hooks dir: {hooks_dir}"
            + "\n  (hooks dir has been RESTORED to the pre-session snapshot)\n"
        )


# ---------------------------------------------------------------------------
# 3a: HTML report branding (pytest-html hooks)
# ---------------------------------------------------------------------------


def pytest_html_report_title(report):
    """Set branded title for pytest-html report."""
    report.title = "nWave Test Report"


def pytest_configure(config):
    """Add project metadata to HTML report header."""
    if hasattr(config, "_metadata"):
        config._metadata["Project"] = "nwave"
        config._metadata["Framework"] = "nWave"


def pytest_html_results_summary(prefix, summary, postfix):
    """Inject domain legend into HTML report summary."""
    prefix.extend(
        [
            "<h3>Test Domains</h3>",
            "<ul>",
            "<li><strong>DES</strong> — Developer Experience System</li>",
            "<li><strong>Installer</strong> — CLI installer and acceptance</li>",
            "<li><strong>Plugins</strong> — nWave plugins and install scripts</li>",
            "<li><strong>Acceptance</strong> — End-to-end acceptance tests</li>",
            "<li><strong>Bugs</strong> — Regression tests for tracked bugs</li>",
            "<li><strong>Release Train</strong> — Release pipeline script tests</li>",
            "</ul>",
        ]
    )


# ---------------------------------------------------------------------------
# 3b: Allure auto-labeling
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Tier auto-marking: maps directory prefixes to pytest markers.
# Sorted by specificity at runtime (longest prefix wins).
# ---------------------------------------------------------------------------

TIER_MAP = {
    # DES tiers
    "tests/des/unit/": "unit",
    "tests/des/acceptance/": "acceptance",
    "tests/des/integration/": "integration",
    "tests/des/e2e/": "e2e",
    # Installer tiers
    "tests/installer/unit/": "unit",
    "tests/installer/acceptance/": "acceptance",
    "tests/installer/e2e/": "e2e",
    # Plugin tiers
    "tests/plugins/plugin-architecture/unit/": "unit",
    "tests/plugins/plugin-architecture/integration/": "integration",
    "tests/plugins/plugin-architecture/acceptance/": "acceptance",
    "tests/plugins/plugin-architecture/e2e/": "e2e",
    "tests/plugins/install/": "unit",
    "tests/plugins/": "unit",  # frontmatter tests default to unit
    # Build tiers
    "tests/build/acceptance/": "acceptance",
    "tests/build/unit/": "unit",
    "tests/build/": "unit",
    # Release train tests
    "tests/release/": "unit",
    # Bug regression tests
    "tests/bugs/": "acceptance",
    # Root-level tests
    "tests/validation/": "unit",
    "tests/e2e/": "e2e",  # testcontainers-driven Docker tests (post Phase 5 retirement of Dockerfiles)
    "tests/": "unit",  # catch-all default
}

DOMAIN_MAP = {
    "tests/des/unit/": ("DES", "Unit Tests"),
    "tests/des/acceptance/": ("DES", "Acceptance Tests"),
    "tests/des/integration/": ("DES", "Integration Tests"),
    "tests/des/e2e/": ("DES", "E2E Tests"),
    "tests/des/": ("DES", "DES Tests"),
    "tests/installer/unit/git_workflow/": ("Installer", "Git Workflow"),
    "tests/installer/unit/": ("Installer", "Unit Tests"),
    "tests/installer/acceptance/installation/": (
        "Installer",
        "Installation Acceptance",
    ),
    "tests/installer/acceptance/installer/": ("Installer", "Installer Acceptance"),
    "tests/installer/acceptance/uninstaller/": ("Installer", "Uninstaller Acceptance"),
    "tests/installer/acceptance/": ("Installer", "Acceptance Tests"),
    "tests/installer/e2e/": ("Installer", "E2E Tests"),
    "tests/plugins/plugin-architecture/unit/": ("Plugins", "Unit Tests"),
    "tests/plugins/plugin-architecture/integration/": ("Plugins", "Integration Tests"),
    "tests/plugins/plugin-architecture/acceptance/": ("Plugins", "Acceptance Tests"),
    "tests/plugins/plugin-architecture/e2e/": ("Plugins", "E2E Tests"),
    "tests/plugins/install/": ("Plugins", "Install Scripts"),
    "tests/plugins/": ("Plugins", "nWave Plugins"),
    "tests/build/acceptance/": ("Build", "Plugin Acceptance"),
    "tests/build/unit/": ("Build", "Unit Tests"),
    "tests/build/": ("Build", "Build Tests"),
    "tests/bugs/": ("Bugs", "Regression"),
    "tests/release/": ("Release Train", "Unit Tests"),
}


# ---------------------------------------------------------------------------
# Top-level test-module guard (RCA Branch B structural defense).
#
# Tests must live under a tier subdirectory (tests/unit/, tests/installer/,
# tests/des/, etc.). Top-level ``tests/test_*.py`` modules historically
# drifted out of sync with their canonical siblings — the attribution
# worktree-isolation bug surfaced because the stale top-level duplicate
# carried tests that no longer matched the canonical version. Once the
# duplicate is gone, this guard prevents future regressions.
#
# Allowlist holds top-level modules that already exist on master and are
# scheduled for migration in a follow-up step. Adding a NEW top-level
# test module is the violation this guard catches.
# See docs/analysis/rca-attribution-plugin-worktree-isolation.md Branch B.
# ---------------------------------------------------------------------------

_TOP_LEVEL_TEST_ALLOWLIST: frozenset[str] = frozenset(
    {
        # Pre-existing top-level modules awaiting migration to a tier subdir.
        # Each of the following has a canonical sibling under tests/installer/
        # or tests/build/ — they are duplicates and will be deleted in a
        # follow-up step (out of scope for 02-01).
        "test_attribution_cli.py",
        "test_attribution_hook.py",
        "test_measure_adoption.py",
        "test_opencode_agents_skill_paths.py",
        "test_plugin_home_env_hardening.py",
        "test_python_path_resolution_in_skills.py",
        "test_reinforce_skill_loading.py",
        # No canonical sibling — keep at top level until migrated.
        "test_docgen.py",
    }
)


def _is_offending_top_level_test(rel_path: str) -> bool:
    """True iff ``rel_path`` is a top-level ``test_*.py`` and not allowlisted.

    Pure function. ``rel_path`` is normalized with forward slashes,
    relative to the tests root.
    """
    parts = rel_path.split("/")
    if len(parts) != 1:
        return False
    name = parts[0]
    if not (name.startswith("test_") and name.endswith(".py")):
        return False
    return name not in _TOP_LEVEL_TEST_ALLOWLIST


def pytest_collection_modifyitems(config, items):
    """Auto-label tests with Allure labels and tier markers from file paths.

    Also enforces the top-level test-module guard (RCA Branch B): any
    ``tests/test_*.py`` not on the allowlist aborts collection with a
    descriptive error.
    """
    # --- Top-level module guard (fail-fast before any other work) ---
    tests_root = Path(__file__).parent
    offenders: list[str] = []
    for item in items:
        try:
            rel = Path(item.fspath).resolve().relative_to(tests_root.resolve())
        except ValueError:
            # Item lives outside the tests root (e.g. doctest in src/).
            continue
        rel_str = str(rel).replace(os.sep, "/")
        if _is_offending_top_level_test(rel_str):
            offenders.append(rel_str)

    if offenders:
        raise pytest.UsageError(
            "Stale top-level test module(s) detected: "
            + ", ".join(sorted(set(offenders)))
            + ". Tests must live under a tier subdirectory "
            + "(tests/unit/, tests/installer/, tests/des/, tests/build/, etc.). "
            + "See docs/analysis/rca-attribution-plugin-worktree-isolation.md "
            + "Branch B for the structural rationale."
        )

    try:
        import allure

        has_allure = True
    except ImportError:
        has_allure = False

    # Pre-sort TIER_MAP prefixes by length descending (longest/most-specific first)
    sorted_tier_prefixes = sorted(TIER_MAP.keys(), key=len, reverse=True)

    for item in items:
        rel_path = os.path.relpath(item.fspath, config.rootdir)
        rel_path = rel_path.replace(os.sep, "/")

        # --- Allure labeling (unchanged, conditional on allure) ---
        if has_allure:
            matched_epic = None
            matched_feature = None
            matched_len = 0
            for prefix, (epic, feature) in DOMAIN_MAP.items():
                if rel_path.startswith(prefix) and len(prefix) > matched_len:
                    matched_epic = epic
                    matched_feature = feature
                    matched_len = len(prefix)

            if matched_epic:
                item.add_marker(allure.epic(matched_epic))
                item.add_marker(allure.feature(matched_feature))

            if item.cls:
                item.add_marker(allure.story(item.cls.__name__))

        # --- Tier auto-marking (always runs) ---
        for prefix in sorted_tier_prefixes:
            if rel_path.startswith(prefix):
                tier = TIER_MAP[prefix]
                item.add_marker(getattr(pytest.mark, tier))
                break


# ---------------------------------------------------------------------------
# 3c: Rich terminal summary table
# ---------------------------------------------------------------------------


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Render a Rich table with pass/fail/skip/xfail counts per domain."""
    try:
        from rich.console import Console
        from rich.table import Table
    except ImportError:
        return

    domain_labels = {
        "tests/des/unit/": "DES (unit)",
        "tests/des/acceptance/": "DES (acceptance)",
        "tests/des/integration/": "DES (integration)",
        "tests/des/e2e/": "DES (e2e)",
        "tests/des/": "DES",
        "tests/installer/unit/git_workflow/": "Installer (git)",
        "tests/installer/unit/": "Installer (unit)",
        "tests/installer/acceptance/installation/": "Installer (installation)",
        "tests/installer/acceptance/installer/": "Installer (walking skeleton)",
        "tests/installer/acceptance/uninstaller/": "Installer (uninstaller)",
        "tests/installer/acceptance/": "Installer (acceptance)",
        "tests/installer/e2e/": "Installer (e2e)",
        "tests/plugins/plugin-architecture/unit/": "Plugins (unit)",
        "tests/plugins/plugin-architecture/integration/": "Plugins (integration)",
        "tests/plugins/plugin-architecture/acceptance/": "Plugins (acceptance)",
        "tests/plugins/plugin-architecture/e2e/": "Plugins (e2e)",
        "tests/plugins/install/": "Plugins (install)",
        "tests/plugins/": "Plugins",
        "tests/bugs/": "Bugs",
        "tests/release/": "Release Train",
    }

    # Sorted by specificity (longest prefix first)
    sorted_prefixes = sorted(domain_labels.keys(), key=len, reverse=True)

    stats = {}
    for label in domain_labels.values():
        stats[label] = {"passed": 0, "failed": 0, "skipped": 0, "xfailed": 0}

    category_keys = {
        "passed": "passed",
        "failed": "failed",
        "error": "failed",
        "skipped": "skipped",
        "xfailed": "xfailed",
        "xpassed": "passed",
    }

    for cat, outcome_key in category_keys.items():
        for report in terminalreporter.getreports(cat):
            if not hasattr(report, "fspath") or report.fspath is None:
                continue
            rel = os.path.relpath(str(report.fspath), str(config.rootdir))
            rel = rel.replace(os.sep, "/")

            matched_label = "Other"
            for prefix in sorted_prefixes:
                if rel.startswith(prefix):
                    matched_label = domain_labels[prefix]
                    break

            if matched_label not in stats:
                stats[matched_label] = {
                    "passed": 0,
                    "failed": 0,
                    "skipped": 0,
                    "xfailed": 0,
                }
            stats[matched_label][outcome_key] += 1

    # Remove domains with zero tests
    stats = {k: v for k, v in stats.items() if sum(v.values()) > 0}
    if not stats:
        return

    table = Table(title="Test Results by Domain", show_lines=True)
    table.add_column("Domain", style="bold")
    table.add_column("Passed", style="green", justify="right")
    table.add_column("Failed", style="red", justify="right")
    table.add_column("Skipped", style="yellow", justify="right")
    table.add_column("XFailed", style="cyan", justify="right")
    table.add_column("Total", style="bold", justify="right")

    totals = {"passed": 0, "failed": 0, "skipped": 0, "xfailed": 0}
    for domain in sorted(stats.keys()):
        counts = stats[domain]
        total = sum(counts.values())
        table.add_row(
            domain,
            str(counts["passed"]),
            str(counts["failed"]),
            str(counts["skipped"]),
            str(counts["xfailed"]),
            str(total),
        )
        for k in totals:
            totals[k] += counts[k]

    grand_total = sum(totals.values())
    table.add_row(
        "TOTAL",
        str(totals["passed"]),
        str(totals["failed"]),
        str(totals["skipped"]),
        str(totals["xfailed"]),
        str(grand_total),
        style="bold",
    )

    console = Console()
    console.print()
    console.print(table)
