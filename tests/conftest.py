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
    # Bug regression tests
    "tests/bugs/": "acceptance",
    # Root-level tests
    "tests/validation/": "unit",
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
    "tests/bugs/": ("Bugs", "Regression"),
}


def pytest_collection_modifyitems(config, items):
    """Auto-label tests with Allure labels and tier markers from file paths."""
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
