"""Generate release notes from conventional commits between git tags.

CLI interface:
    python generate_changelog.py --stage dev|rc|stable --version VERSION
        [--source-tag SOURCE_TAG] [--repo GITHUB_REPOSITORY]
        --output OUTPUT_PATH

Stages:
    dev    -> Dev snapshot notes (no install section)
    rc     -> Release candidate notes with --pre install flag
    stable -> Stable release notes with standard install

Output: Markdown release notes written to --output AND printed to stdout.

Exit codes:
    0 = success
    1 = error
"""

from __future__ import annotations

import argparse
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate release notes from conventional commits."
    )
    parser.add_argument(
        "--stage",
        required=True,
        choices=("dev", "rc", "stable"),
        help="Release stage: dev, rc, or stable",
    )
    parser.add_argument(
        "--version",
        required=True,
        help="Version string without v prefix (e.g. 1.1.23rc1 or 1.1.23)",
    )
    parser.add_argument(
        "--source-tag",
        default="",
        help="Source tag for 'Promoted from' line (e.g. v1.1.23.dev1)",
    )
    parser.add_argument(
        "--repo",
        default="",
        help="GitHub repository (e.g. nwave-ai/nwave-dev) for compare links",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output file path for release notes",
    )
    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
# Git interaction (impure functions, isolated for testability)
# ---------------------------------------------------------------------------


def _find_previous_tag(stage: str, current_version: str) -> str:
    """Find previous tag for changelog comparison.

    For dev: nearest tag of ANY type via ``git describe``.
    For rc/stable: most recent tag of the same type merged into HEAD.
    """
    if stage == "dev":
        try:
            result = subprocess.run(
                ["git", "describe", "--tags", "--abbrev=0", "HEAD^"],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                return ""
            return result.stdout.strip()
        except OSError:
            return ""

    try:
        result = subprocess.run(
            ["git", "tag", "--sort=-v:refname", "--merged", "HEAD"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return ""
        all_tags = result.stdout.strip().splitlines()
    except OSError:
        return ""

    if stage == "rc":
        tag_re = re.compile(r"^v\d+\.\d+\.\d+rc\d+$")
    else:
        tag_re = re.compile(r"^v\d+\.\d+\.\d+$")

    current_tag = f"v{current_version}"
    return next(
        (
            t.strip()
            for t in all_tags
            if tag_re.match(t.strip()) and t.strip() != current_tag
        ),
        "",
    )


def _fetch_commits(prev_tag: str) -> str:
    """Fetch commit log between prev_tag and HEAD (or all commits if no prev_tag)."""
    record_end = "<<--EOR-->>"
    fmt = f"%s%x00%b%x00%h{record_end}"
    cmd = ["git", "log", "--no-merges", f"--pretty=format:{fmt}"]
    if prev_tag:
        cmd.insert(2, f"{prev_tag}..HEAD")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return ""
        return result.stdout
    except OSError:
        return ""


# ---------------------------------------------------------------------------
# Pure functions (no I/O, no subprocess)
# ---------------------------------------------------------------------------

_CONVENTIONAL_RE = re.compile(
    r"^(?P<type>[a-z]+)(?:\((?P<scope>[^)]*)\))?(?P<bang>!)?:\s*(?P<desc>.+)$"
)


def _parse_conventional_commit(subject: str) -> dict[str, str | bool] | None:
    """Parse a conventional commit subject line.

    Returns dict with keys: type, scope, bang, desc -- or None if not conventional.
    """
    m = _CONVENTIONAL_RE.match(subject)
    if not m:
        return None
    return {
        "type": m.group("type"),
        "scope": m.group("scope") or "",
        "bang": bool(m.group("bang")),
        "desc": m.group("desc"),
    }


def _categorize_commits(raw_log: str) -> dict[str, list[str]]:
    """Parse raw git log output and categorize into breaking/features/fixes/other.

    Returns dict with keys: breaking, features, fixes, other (each a list of strings).
    """
    record_end = "<<--EOR-->>"
    breaking: list[str] = []
    features: list[str] = []
    fixes: list[str] = []
    other: list[str] = []

    for record in raw_log.split(record_end):
        record = record.strip()
        if not record:
            continue
        parts = record.split("\x00")
        if len(parts) < 3:
            continue
        subject = parts[0].strip()
        body = parts[1].strip()
        sha = parts[2].strip()
        if not subject or not sha:
            continue
        if "chore(release):" in subject or "[skip ci]" in subject:
            continue

        parsed = _parse_conventional_commit(subject)
        is_breaking = (parsed and parsed["bang"]) or "BREAKING CHANGE:" in body
        line = f"- {subject} (`{sha}`)"

        if is_breaking:
            breaking.append(line)
        elif parsed:
            ctype = parsed["type"]
            if ctype == "feat":
                features.append(line)
            elif ctype == "fix":
                fixes.append(line)
            else:
                other.append(line)
        else:
            other.append(line)

    return {
        "breaking": breaking,
        "features": features,
        "fixes": fixes,
        "other": other,
    }


def _render_markdown(
    stage: str,
    version: str,
    source_tag: str,
    repo: str,
    prev_tag: str,
    categories: dict[str, list[str]],
    release_date: str,
) -> str:
    """Render categorized commits into markdown release notes."""
    sections: list[str] = []

    if stage == "dev":
        sections.append(f"**Dev snapshot** `{version}` ({release_date})\n")
        if prev_tag and repo:
            sections.append(
                f"**Changes since**: [{prev_tag}]"
                f"(https://github.com/{repo}/compare/{prev_tag}...v{version})\n"
            )
        empty_message = "No notable changes (internal improvements)\n"
    elif stage == "rc":
        sections.append(f"**Release candidate** `{version}` ({release_date})\n")
        if source_tag:
            sections.append(f"**Promoted from**: `{source_tag}`\n")
        if prev_tag and repo:
            sections.append(
                f"**Changes since**: [{prev_tag}]"
                f"(https://github.com/{repo}/compare/{prev_tag}...v{version})\n"
            )
        sections.append(
            "## Install\n"
            "uv (recommended):\n```bash\n"
            f"UV_PRERELEASE=allow uv tool install "
            f"--index https://test.pypi.org/simple/ "
            f"--index https://pypi.org/simple/ "
            f"--index-strategy unsafe-best-match "
            f"nwave-ai=={version}\n"
            "```\n"
            "pipx (fallback):\n```bash\n"
            f'pipx install nwave-ai=={version} --pip-args="--pre"\n'
            "```\n"
        )
        empty_message = "No notable changes (internal improvements)\n"
    else:
        sections.append(f"# nWave Framework v{version}\n")
        sections.append(f"**Release Date**: {release_date}\n")
        if source_tag:
            sections.append(f"**Promoted from**: `{source_tag}`\n")
        if prev_tag and repo:
            sections.append(
                f"**Full Changelog**: [{prev_tag}...v{version}]"
                f"(https://github.com/{repo}/compare/{prev_tag}...v{version})\n"
            )
        sections.append(
            "## Installation\n"
            "uv (recommended):\n```bash\nuv tool install nwave-ai\n```\n"
            "pipx (fallback):\n```bash\npipx install nwave-ai\n```\n"
        )
        empty_message = "Patch release (internal improvements)\n"

    breaking = categories.get("breaking", [])
    features = categories.get("features", [])
    fixes = categories.get("fixes", [])
    other_items = categories.get("other", [])

    if breaking:
        sections.extend(["## Breaking Changes\n", "\n".join(breaking) + "\n"])
    if features:
        sections.extend(["## Features\n", "\n".join(features) + "\n"])
    if fixes:
        sections.extend(["## Bug Fixes\n", "\n".join(fixes) + "\n"])
    if other_items:
        sections.extend(["## Other Changes\n", "\n".join(other_items) + "\n"])
    if not any([breaking, features, fixes, other_items]):
        sections.append(empty_message)

    return "\n".join(sections)


# ---------------------------------------------------------------------------
# Main (I/O orchestration)
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    release_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    prev_tag = _find_previous_tag(args.stage, args.version)
    raw_log = _fetch_commits(prev_tag)
    categories = _categorize_commits(raw_log)

    notes = _render_markdown(
        stage=args.stage,
        version=args.version,
        source_tag=args.source_tag,
        repo=args.repo,
        prev_tag=prev_tag,
        categories=categories,
        release_date=release_date,
    )

    output_path = Path(args.output)
    if output_path.parent != Path():
        output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(notes)
    print(notes)


if __name__ == "__main__":
    main()
