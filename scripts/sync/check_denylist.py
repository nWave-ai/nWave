"""Check a public PR diff against the sensitive-file denylist.

Blocks a pr-mirror/<N> push if any changed path matches a gitignore-style
rule in `denylist.txt` or if any changed file contains a rewritten
`raw.githubusercontent.com/nWave-ai/nWave/main` URL (content rule §7.1).

CLI contract: docs/feature/public-pr-sync/devops/wave-decisions.md §2 + §7.1

    python scripts/sync/check_denylist.py \\
        --base-sha <40-hex-sha> \\
        --head-sha <40-hex-sha> \\
        --denylist <path-to-denylist-file>

    # Alternate form (for unit tests — no git):
    python scripts/sync/check_denylist.py \\
        --diff-file <newline-delimited-paths> \\
        --denylist <path-to-denylist-file>

Exit codes:
    0 = pass (no denylist hits); stdout: {"pass": true, "matched_files": []}
    1 = denylist hit; stdout: {"pass": false, "matched_files": [...]}
    2 = usage error (bad args, invalid SHAs, unreadable denylist, git failure)

Never emits exit code 3 or higher.

Known limitation: deletions (diff-filter D) are excluded. A deleted file
adds no sensitive content, so path-rule evaluation on deleted paths is out
of scope for the PoC. In --diff-file mode, the content rule is skipped
(no git available); path rules still run.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn


SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")
CONTENT_RULE_NAME = "content:rewritten-raw-url"
CONTENT_RULE_RE = re.compile(r"raw\.githubusercontent\.com/nWave-ai/nWave/main")


# ---------------------------------------------------------------------------
# Domain types (pure)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MatchedFile:
    """One (path, rule) pair — a single reason a PR was blocked."""

    path: str
    rule: str

    def as_dict(self) -> dict[str, str]:
        return {"path": self.path, "rule": self.rule}


class UsageError(Exception):
    """Mapped to exit code 2. Carries a human-readable message."""


# ---------------------------------------------------------------------------
# Pure functions (port-to-port testable via CLI driving port)
# ---------------------------------------------------------------------------


def parse_denylist(text: str) -> list[str]:
    """Return trimmed rule lines, skipping blanks and #-comments."""
    rules: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        rules.append(line)
    return rules


def parse_diff_file(text: str) -> list[str]:
    """Return path lines from a --diff-file, skipping blanks and #-comments."""
    # Identical shape to parse_denylist; kept separate for clarity of intent.
    paths: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        paths.append(line)
    return paths


def _rule_matches_path(rule: str, path: str) -> bool:
    """gitignore-style match: support ** recursion and exact/leading-segment matches.

    - ``pyproject.toml`` matches literal ``pyproject.toml`` only (fnmatch).
    - ``.github/**`` matches anything under ``.github/`` at any depth, but NOT
      the bare directory name ``.github``.
    - ``scripts/release/**`` matches ``scripts/release/foo``, ``scripts/release/a/b``.
    """
    if rule.endswith("/**"):
        prefix = rule[: -len("/**")]
        # ``.github/**`` matches ``.github/anything`` — require strict prefix +
        # at least one character beyond the trailing slash.
        return path.startswith(prefix + "/") and len(path) > len(prefix) + 1
    return fnmatch.fnmatchcase(path, rule)


def match_paths(paths: list[str], rules: list[str]) -> list[MatchedFile]:
    """Emit one MatchedFile per (path, rule) hit. No deduplication by path."""
    hits: list[MatchedFile] = []
    for path in paths:
        for rule in rules:
            if _rule_matches_path(rule, path):
                hits.append(MatchedFile(path=path, rule=rule))
    return hits


def content_rule_hits(path: str, content: str) -> MatchedFile | None:
    """Flag if ``content`` contains a rewritten raw-URL for nWave-ai/nWave."""
    if CONTENT_RULE_RE.search(content):
        return MatchedFile(path=path, rule=CONTENT_RULE_NAME)
    return None


def sort_matches(matches: list[MatchedFile]) -> list[MatchedFile]:
    """Deterministic order: (path asc, rule asc)."""
    return sorted(matches, key=lambda m: (m.path, m.rule))


# ---------------------------------------------------------------------------
# Git adapter (thin wrapper; only used in git mode)
# ---------------------------------------------------------------------------


def _git(*args: str, cwd: Path | None = None) -> str:
    """Run git, return stdout. Raise UsageError with stderr on non-zero exit."""
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError as exc:
        raise UsageError("git executable not found on PATH") from exc
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        raise UsageError(
            f"git {' '.join(args)} failed: {stderr or 'unknown error'}"
        ) from exc
    return result.stdout


def git_diff_names(base_sha: str, head_sha: str) -> list[str]:
    """Return added/copied/modified/renamed paths between base and head.

    Deletions excluded (diff-filter ACMR) — a deleted file adds no sensitive
    content. Reference: wave-decisions.md §2 "Reference behaviour".
    """
    out = _git(
        "diff",
        "--name-only",
        "--diff-filter=ACMR",
        f"{base_sha}..{head_sha}",
    )
    return [line for line in out.splitlines() if line]


def git_show_blob(sha: str, path: str) -> str:
    """Return file content at `<sha>:<path>`. Empty string if not readable as text."""
    try:
        result = subprocess.run(
            ["git", "show", f"{sha}:{path}"],
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError:
        # File may not exist at that SHA (e.g. pure rename edge case) — skip.
        return ""
    # Best-effort decode; binary files yield no useful content for the text rule.
    try:
        return result.stdout.decode("utf-8")
    except UnicodeDecodeError:
        return ""


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _die(message: str) -> NoReturn:
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(2)


def _validate_sha(label: str, value: str) -> str:
    if not SHA_RE.fullmatch(value):
        raise UsageError(f"--{label} must be a 40-character hex SHA, got {value!r}")
    return value


def _read_denylist(path: str) -> list[str]:
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise UsageError(
            f"cannot read denylist file {path!r}: {exc.strerror or exc}"
        ) from exc
    return parse_denylist(text)


def _read_diff_file(path: str) -> list[str]:
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise UsageError(
            f"cannot read diff file {path!r}: {exc.strerror or exc}"
        ) from exc
    return parse_diff_file(text)


def _emit_result(matches: list[MatchedFile]) -> int:
    matches = sort_matches(matches)
    payload: dict[str, object] = {
        "pass": len(matches) == 0,
        "matched_files": [m.as_dict() for m in matches],
    }
    sys.stdout.write(json.dumps(payload))
    return 0 if not matches else 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check a public PR diff against the sensitive-file denylist.",
        add_help=True,
    )
    parser.add_argument(
        "--denylist",
        required=True,
        help="Path to the denylist file (gitignore-style rules, one per line).",
    )
    parser.add_argument(
        "--base-sha",
        help="Base SHA (git mode). 40 hex chars. Ignored if --diff-file given.",
    )
    parser.add_argument(
        "--head-sha",
        help="Head SHA (git mode). 40 hex chars. Ignored if --diff-file given.",
    )
    parser.add_argument(
        "--diff-file",
        help=(
            "Newline-delimited paths (diff-file mode). Takes precedence over "
            "--base-sha/--head-sha. Content rule is skipped in this mode."
        ),
    )
    return parser


def _run(args: argparse.Namespace) -> int:
    rules = _read_denylist(args.denylist)

    if args.diff_file is not None:
        paths = _read_diff_file(args.diff_file)
        # Content rule requires git; skip in diff-file mode (documented).
        matches = match_paths(paths, rules)
        return _emit_result(matches)

    # git mode — both SHAs required and valid.
    if not args.base_sha:
        raise UsageError("--base-sha is required in git mode")
    if not args.head_sha:
        raise UsageError("--head-sha is required in git mode")
    base = _validate_sha("base-sha", args.base_sha)
    head = _validate_sha("head-sha", args.head_sha)

    paths = git_diff_names(base, head)
    matches = match_paths(paths, rules)
    for path in paths:
        content = git_show_blob(head, path)
        hit = content_rule_hits(path, content)
        if hit is not None:
            matches.append(hit)
    return _emit_result(matches)


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        exit_code = _run(args)
    except UsageError as exc:
        _die(str(exc))
    except Exception as exc:
        # Exit-code invariant: any unhandled exception maps to 2, never 3+.
        _die(f"unexpected error: {exc}")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
