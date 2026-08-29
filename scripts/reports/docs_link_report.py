"""Weekly docs link report — runs the docs link checker and posts to Slack.

Runs as a GitHub Actions cron job (see .github/workflows/docs-link-report.yml)
or manually. Checks external URLs (the weekly run is the right place for the
flaky/slow external link-rot pass) on top of the usual relative + placeholder +
nWave-ai org checks.

The job FAILS (non-zero) only on ERRORs (broken internal / placeholder / dead
org links); external warnings (login-walled, rate-limited) never fail it. The
Slack report is always posted regardless of outcome.

Requires: SLACK_WEBHOOK_URL (Slack incoming webhook). Optional GitHub Actions
env (GITHUB_SERVER_URL / GITHUB_REPOSITORY / GITHUB_RUN_ID) for a run link.

Excluded from releases alongside scripts/check_docs_links.py.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


# Make `scripts.check_docs_links` importable when run as a bare script
# (sys.path[0] is this file's dir, not the repo root).
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.check_docs_links import (  # noqa: E402
    Finding,
    LinkChecker,
    Severity,
    _network_reachable,
    build_link_options,
    collect_files,
    compute_exit_code,
)


# Same scan scope as the CI/pre-push gate; path excludes come from the
# auto-loaded .docs-link-ignore.yaml (centralized, not duplicated here).
SCAN_PATHS = ("docs", "nWave/skills", "README.md", "nWave/README.md", "CONTRIBUTING.md")
MAX_LISTED = 15  # cap findings listed in the Slack message


def run_check(project_root: Path) -> list[Finding]:
    # Fail soft like run(): if the runner has no network, skip liveness rather
    # than red-failing the weekly job on infra flakiness instead of link rot.
    network = _network_reachable(10.0)
    if not network:
        print(
            "NOTICE: network unreachable — skipping liveness checks.",
            file=sys.stderr,
        )
    options, excludes = build_link_options(
        project_root,
        check_external=True,
        check_site_links=True,
        network=network,
    )
    paths = [project_root / p for p in SCAN_PATHS]
    files = collect_files(paths, excludes)
    return LinkChecker(project_root, options).check_files(files)


def _run_url() -> str | None:
    server = os.environ.get("GITHUB_SERVER_URL")
    repo = os.environ.get("GITHUB_REPOSITORY")
    run_id = os.environ.get("GITHUB_RUN_ID")
    if server and repo and run_id:
        return f"{server}/{repo}/actions/runs/{run_id}"
    return None


def format_report(findings: list[Finding], *, run_url: str | None = None) -> str:
    """Build the Slack message text. Pure — no IO."""
    errors = [f for f in findings if f.severity is Severity.ERROR]
    warnings = [f for f in findings if f.severity is Severity.WARNING]

    if not findings:
        header = ":white_check_mark: *Weekly docs link report* — all links healthy."
        lines = [header]
        if run_url:
            lines.append(f"<{run_url}|View run>")
        return "\n".join(lines)

    icon = ":rotating_light:" if errors else ":warning:"
    lines = [
        f"{icon} *Weekly docs link report* — "
        f"{len(errors)} error(s), {len(warnings)} warning(s)"
    ]

    def fmt(group: list[Finding], title: str) -> None:
        if not group:
            return
        lines.append(f"\n*{title} ({len(group)}):*")
        for f in group[:MAX_LISTED]:
            lines.append(f"• `{f.file}:{f.line}` {f.message}\n  {f.url}")
        if len(group) > MAX_LISTED:
            lines.append(f"…and {len(group) - MAX_LISTED} more.")

    fmt(errors, "Errors")
    fmt(warnings, "Warnings")
    if run_url:
        lines.append(f"\n<{run_url}|View full run>")
    return "\n".join(lines)


def post_to_slack(message: str, webhook_url: str) -> bool:
    """Post message to Slack via incoming webhook. Returns True on success."""
    import requests  # lazy — keeps format_report importable without the dep

    resp = requests.post(webhook_url, json={"text": message}, timeout=30)
    if resp.status_code != 200:
        print(f"Slack post failed: {resp.status_code} {resp.text}", file=sys.stderr)
        return False
    return True


def main() -> int:
    findings = run_check(_REPO_ROOT)
    message = format_report(findings, run_url=_run_url())
    print(message)

    webhook = os.environ.get("SLACK_WEBHOOK_URL", "")
    if webhook:
        post_to_slack(message, webhook)
    else:
        print("SLACK_WEBHOOK_URL not set — report not posted.", file=sys.stderr)

    # Fail the job on errors only; warnings (external link-rot) never fail it.
    return compute_exit_code(findings, warnings_as_errors=False)


if __name__ == "__main__":
    sys.exit(main())
