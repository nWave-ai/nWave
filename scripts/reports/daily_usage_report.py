"""Daily nWave usage report — searches GitHub for attribution commits and posts to Slack.

Runs as GitHub Actions cron job (6:57 UTC daily) or manually.
Requires: GH_TOKEN (GitHub), SLACK_ADOPTION_WEBHOOK_URL (Slack incoming webhook
scoped to the #nwave_adoption_report channel).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path


# Sidecar JSON of repos discovered automatically. Seeded at first run, then
# auto-updated every subsequent run so new adopters are labelled without a
# manual code edit. Committed to the repo so the cron job's state persists.
DISCOVERED_REPOS_PATH = Path(__file__).parent / "known_repos_discovered.json"


INTERNAL_ORGS = {"nWave-ai", "Alcor-Academy"}
INTERNAL_USERS = {"11PJ11", "conso"}
# Dedicated webhook for #nwave_adoption_report. Falls back to the legacy
# SLACK_WEBHOOK_URL for local runs that still use the old secret.
SLACK_WEBHOOK_URL = os.environ.get("SLACK_ADOPTION_WEBHOOK_URL") or os.environ.get(
    "SLACK_WEBHOOK_URL", ""
)

# Known user context — enriched manually as we learn about adopters.
# Key: GitHub login. Values: type label for the report.
KNOWN_USERS: dict[str, str] = {
    "SDiamante13": "External (dotfiles — stable adopter)",
    "pmvanev": "External (SBIR — US gov research)",
    "christianBorrello": "External",
    "andlaf-ak": "External",
    "11PJ11": "Internal (Ale)",
    "conso": "Internal (Marco)",
}

# Known repo context — enriched manually.
KNOWN_REPOS: dict[str, str] = {
    "SDiamante13/dotfiles": "Personal dotfiles (nWave as daily tool)",
    "pmvanev/sbir-plugin-cc": "SBIR plugin for Claude Code",
    "christianBorrello/the-augmented-craftsman": "AI-augmented development",
    "SagitterSpa/SagitterHub": "Corporate repo (Sagitter Spa)",
    "andlaf-ak/claude-code-agents": "Claude Code agent collection",
    "Alcor-Academy/nwave-landing": "nWave landing page",
    "nWave-ai/nwave-dev": "nWave framework (internal)",
}


def load_discovered_repos() -> dict[str, str]:
    """Load auto-discovered repo labels from the sidecar JSON (empty if missing)."""
    if not DISCOVERED_REPOS_PATH.exists():
        return {}
    try:
        with DISCOVERED_REPOS_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError) as e:
        print(f"Failed to load {DISCOVERED_REPOS_PATH}: {e}", file=sys.stderr)
        return {}


def save_discovered_repos(discovered: dict[str, str]) -> None:
    """Persist auto-discovered repo labels to the sidecar JSON (sorted, pretty)."""
    try:
        with DISCOVERED_REPOS_PATH.open("w", encoding="utf-8") as f:
            json.dump(dict(sorted(discovered.items())), f, indent=2)
            f.write("\n")
    except OSError as e:
        print(f"Failed to write {DISCOVERED_REPOS_PATH}: {e}", file=sys.stderr)


def search_attribution_commits(hours: int = 24) -> list[dict]:
    """Search GitHub for commits with nWave attribution trailer in the last N hours.

    Uses server-side --author-date filter so the result budget is not consumed
    by older commits before client-side filtering.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    cutoff_str = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")
    result = subprocess.run(
        [
            "gh",
            "search",
            "commits",
            "Co-Authored-By: nWave",
            f"--author-date=>={cutoff_str}",
            "--sort=author-date",
            "--order=desc",
            "--limit",
            "200",
            "--json",
            "repository,author,commit,sha",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        print(f"GitHub search failed: {result.stderr}", file=sys.stderr)
        return []

    return json.loads(result.stdout) if result.stdout.strip() else []


def is_external_user(login: str) -> bool:
    """Check if a user is external (not internal org member or known internal)."""
    return login not in INTERNAL_USERS


def is_external_repo(repo_full_name: str) -> bool:
    """Check if a repo belongs to an external org."""
    org = repo_full_name.split("/", maxsplit=1)[0] if "/" in repo_full_name else ""
    return org not in INTERNAL_ORGS


def filter_external(commits: list[dict]) -> list[dict]:
    """Filter out internal org commits."""
    return [
        c
        for c in commits
        if is_external_repo(c.get("repository", {}).get("fullName", ""))
    ]


# Earliest known nWave attribution commit. Probed empirically — there are zero
# attribution commits before 2026-01-01, so sharding starts here.
ATTRIBUTION_EPOCH = datetime(2026, 1, 1, tzinfo=timezone.utc)
# Window size for date-range sharding. A single `gh search commits` call caps
# at 500 hits; high-volume weeks can saturate larger windows and bury the long
# tail of adopters (which is why the report stopped changing). 10 days keeps
# each shard under the cap while minimising the total number of API calls —
# GitHub's secondary (abuse) rate limit kicks in well before the documented
# 30/min primary limit, so fewer calls = more reliable runs.
SHARD_DAYS = 10


def _search_commits_window(start: datetime, end: datetime) -> list[dict]:
    """Fetch all attribution commits within [start, end) via gh search.

    Retries once after a 60s back-off if GitHub returns a rate-limit error,
    so a single secondary-limit hiccup doesn't silently drop a whole shard.
    """
    cmd = [
        "gh",
        "search",
        "commits",
        "Co-Authored-By: nWave",
        f"--author-date={start.strftime('%Y-%m-%d')}..{end.strftime('%Y-%m-%d')}",
        "--sort=author-date",
        "--order=desc",
        "--limit",
        "500",
        "--json",
        "repository,author,sha",
    ]
    for attempt in range(2):
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            break
        is_rate_limit = "rate limit" in result.stderr.lower()
        if is_rate_limit and attempt == 0:
            print(
                f"gh rate-limit for {start:%Y-%m-%d}..{end:%Y-%m-%d}, "
                "backing off 60s and retrying",
                file=sys.stderr,
            )
            time.sleep(60)
            continue
        print(
            f"gh search failed for {start:%Y-%m-%d}..{end:%Y-%m-%d}: {result.stderr}",
            file=sys.stderr,
        )
        return []
    commits = json.loads(result.stdout) if result.stdout.strip() else []
    if len(commits) >= 500:
        print(
            f"WARNING: window {start:%Y-%m-%d}..{end:%Y-%m-%d} hit 500-result cap — "
            "results may be truncated; shrink SHARD_DAYS.",
            file=sys.stderr,
        )
    return commits


def get_cumulative_data() -> tuple[dict[str, set[str]], set[str]]:
    """Get all-time user -> repos mapping and all external repos.

    Returns (user_repos, all_repos) where user_repos maps login -> set of repo names.

    Shards the query across fixed date windows from ATTRIBUTION_EPOCH to today
    because a single `gh search commits` call tops out at 500 results and that
    window only spans ~2 weeks of recent high-volume activity, hiding every
    older adopter. External repo discovery is decoupled from author identity:
    an external repo counts as an adopter even when the commit author is
    internal (e.g., during coaching sessions).
    """
    user_repos: dict[str, set[str]] = {}
    all_repos: set[str] = set()
    seen_shas: set[str] = set()

    now = datetime.now(timezone.utc)
    window_start = ATTRIBUTION_EPOCH
    while window_start < now:
        window_end = min(window_start + timedelta(days=SHARD_DAYS), now)
        # gh's --author-date uses date-only ranges, so extend end by 1 day to be inclusive.
        commits = _search_commits_window(window_start, window_end + timedelta(days=1))
        for c in commits:
            sha = c.get("sha", "")
            if sha and sha in seen_shas:
                continue
            if sha:
                seen_shas.add(sha)
            repo = c.get("repository", {}).get("fullName", "")
            author = c.get("author", {}).get("login", "")
            if not repo or not is_external_repo(repo):
                continue
            all_repos.add(repo)
            if author and is_external_user(author):
                user_repos.setdefault(author, set()).add(repo)
        window_start = window_end
        # GitHub search primary limit is 30/min but the secondary (abuse)
        # limit trips sooner — 4s between calls keeps sustained throughput
        # around 15/min which both limits tolerate.
        time.sleep(4)

    return user_repos, all_repos


def _user_type(login: str) -> str:
    """Get the type label for a user."""
    return KNOWN_USERS.get(login, "External")


def _repo_description(repo: str) -> str:
    """Get a short description for a repo (KNOWN_REPOS merged with discovered sidecar)."""
    if repo in KNOWN_REPOS:
        return KNOWN_REPOS[repo]
    return _DISCOVERED_CACHE.get(repo, "")


# Populated at main() entry; kept module-global so _repo_description stays pure-lookup.
_DISCOVERED_CACHE: dict[str, str] = {}


def format_report(
    recent_external: list[dict],
    user_repos: dict[str, set[str]],
    all_repos: set[str],
) -> str:
    """Format the Slack message with user/repo table."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    lines = [f":bar_chart: *nWave Daily Usage Report — {today}*", ""]

    # Recent activity section
    if recent_external:
        lines.append(
            f":new: *New external activity (last 24h): {len(recent_external)} commits*"
        )
        for c in recent_external:
            repo = c.get("repository", {}).get("fullName", "")
            author = c.get("author", {}).get("login", "unknown")
            msg = c.get("commit", {}).get("message", "").split("\n")[0][:60]
            lines.append(f"  `@{author}` in `{repo}` — _{msg}_")
    else:
        lines.append("No new external nWave commits in the last 24 hours.")

    lines.append("")

    # Cumulative adopters table
    ext_users = len(user_repos)
    ext_repos = len(all_repos)
    lines.append(
        f":chart_with_upwards_trend: *Cumulative adopters*: "
        f"{ext_users} external users, {ext_repos} external repos"
    )
    lines.append("")

    if user_repos:
        lines.append("```")
        # Header
        lines.append(f"{'User':<20} {'Repo':<42} {'Type'}")
        lines.append(f"{'-' * 20} {'-' * 42} {'-' * 30}")

        # Sort by user, then repo
        for user in sorted(user_repos):
            repos = sorted(user_repos[user])
            user_type = _user_type(user)
            for i, repo in enumerate(repos):
                desc = _repo_description(repo)
                label = f"{user_type} ({desc})" if desc else user_type
                # Truncate label to fit
                label = label[:30]
                display_user = user if i == 0 else ""
                lines.append(f"{display_user:<20} {repo:<42} {label}")
        lines.append("```")

    lines.append("")
    lines.append(
        "_Note: GitHub commit search indexes the default branch only and may lag "
        "by a few hours. Repos pushing to feature branches will appear after merge._"
    )
    lines.append("_Generated by Claude Code on behalf of the nWave team._")

    return "\n".join(lines)


def post_to_slack(message: str) -> bool:
    """Post message to Slack via incoming webhook."""
    if not SLACK_WEBHOOK_URL:
        print(
            "SLACK_ADOPTION_WEBHOOK_URL not set — printing to stdout instead",
            file=sys.stderr,
        )
        print(message)
        return False

    import requests

    resp = requests.post(
        SLACK_WEBHOOK_URL,
        json={"text": message},
        timeout=10,
    )
    if resp.status_code != 200:
        print(f"Slack post failed: {resp.status_code} {resp.text}", file=sys.stderr)
        return False

    print("Report posted to Slack")
    return True


def main() -> None:
    """Generate and post daily usage report."""
    print("Searching GitHub for nWave attribution commits...")

    # Load the discovered-repos sidecar into the module-global cache so
    # _repo_description() can merge it with KNOWN_REPOS transparently.
    global _DISCOVERED_CACHE
    _DISCOVERED_CACHE = load_discovered_repos()

    recent = search_attribution_commits(hours=24)
    recent_external = filter_external(recent)
    user_repos, all_repos = get_cumulative_data()

    # Auto-register any newly-seen repo with an empty description. Manual
    # enrichment can happen later by editing the sidecar JSON directly.
    new_repos = sorted(
        all_repos - set(KNOWN_REPOS.keys()) - set(_DISCOVERED_CACHE.keys())
    )
    if new_repos:
        for repo in new_repos:
            _DISCOVERED_CACHE[repo] = ""
        save_discovered_repos(_DISCOVERED_CACHE)
        print(f"Auto-registered {len(new_repos)} new repo(s) in sidecar")

    print(f"Found {len(recent)} recent commits ({len(recent_external)} external)")
    print(
        f"Cumulative: {len(user_repos)} external users, {len(all_repos)} external repos"
    )

    report = format_report(recent_external, user_repos, all_repos)
    post_to_slack(report)


if __name__ == "__main__":
    main()
