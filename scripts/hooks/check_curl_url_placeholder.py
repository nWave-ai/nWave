"""Pre-commit hook: enforce {{NWAVE_RAW_URL}} placeholder in curl commands.

Tutorials and guides may include `curl -fsSL .../setup.sh | sh` style bootstrap
commands. These need fully-qualified URLs to work for end users, but the URL
must point at the *published* repo (nWave-ai/nWave), not nwave-dev — and
nwave-dev is private, so hardcoded raw.githubusercontent.com URLs would 404
anyway.

The release pipeline rewrites `{{NWAVE_RAW_URL}}` → the published repo URL
(see .github/workflows/release-prod.yml and release-rc.yml). Source files
must use the placeholder; this hook blocks hardcoded raw URLs.

Allowed:
    sh -c "$(curl -fsSL {{NWAVE_RAW_URL}}/scripts/install/setup.sh)"

Blocked:
    sh -c "$(curl -fsSL https://raw.githubusercontent.com/nWave-ai/nWave/main/scripts/install/setup.sh)"

Scope: scans markdown files under docs/guides/ only. Other docs (research,
reports, internal) may legitimately reference real raw URLs as evidence.

Usage:
    python scripts/hooks/check_curl_url_placeholder.py
    python scripts/hooks/check_curl_url_placeholder.py docs/guides/foo/README.md
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


HARDCODED_RAW_URL = re.compile(r"https?://raw\.githubusercontent\.com/[^\s)\"']+")

# Captures the path-after-branch from a raw.githubusercontent.com URL.
# Handles both legacy (org/repo/branch/path) and refs/heads (org/repo/refs/heads/branch/path) forms.
RAW_URL_PATH = re.compile(
    r"https?://raw\.githubusercontent\.com/"
    r"[^/]+/"  # org
    r"[^/]+/"  # repo
    r"(?:refs/heads/)?"  # optional refs/heads/ prefix
    r"[^/]+/"  # branch
    r"(?P<path>[^\s)\"']+)"  # path
)

SCAN_DIR = "docs/guides"
PLACEHOLDER = "{{NWAVE_RAW_URL}}"


def suggest_replacement(url: str) -> str | None:
    """Convert a hardcoded raw URL into the placeholder form.

    Returns the suggested replacement string, or None if the URL doesn't
    match the expected raw.githubusercontent.com structure.
    """
    match = RAW_URL_PATH.match(url)
    if not match:
        return None
    return f"{PLACEHOLDER}/{match.group('path')}"


def check_files(files: list[Path]) -> list[tuple[Path, int, str, str | None]]:
    """Check files for hardcoded raw.githubusercontent.com URLs.

    Returns list of (file, lineno, found_url, suggested_replacement) tuples.
    Empty list = clean.
    """
    violations: list[tuple[Path, int, str, str | None]] = []
    for file_path in files:
        if not file_path.exists():
            continue
        try:
            content = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for i, line in enumerate(content.splitlines(), 1):
            for match in HARDCODED_RAW_URL.finditer(line):
                found = match.group(0)
                violations.append((file_path, i, found, suggest_replacement(found)))
    return violations


def print_violations(violations: list[tuple[Path, int, str, str | None]]) -> None:
    """Print a per-violation fix instruction."""
    print(
        f"Hardcoded raw.githubusercontent.com URLs detected in {SCAN_DIR}/.\n"
        f"\n"
        f"Why this is blocked:\n"
        f"  - nwave-dev is private; raw URLs to it return 404 for end users.\n"
        f"  - The published repo (nWave-ai/nWave) lives at a different URL.\n"
        f"  - The release pipeline substitutes {PLACEHOLDER} → the correct\n"
        f"    URL per release channel (prod → nwave, rc → nWave-beta).\n"
        f"\n"
        f"How to fix each violation below:\n"
        f"  1. Open the file at the indicated line.\n"
        f"  2. Replace the FOUND string with the FIX string.\n"
        f"  3. Re-stage and commit.\n"
        f"\n"
        f"Violations:\n"
    )
    for file_path, lineno, found, suggested in violations:
        print(f"  {file_path}:{lineno}")
        print(f"    FOUND: {found}")
        if suggested:
            print(f"    FIX:   {suggested}")
        else:
            print(
                f"    FIX:   (could not auto-derive — URL doesn't match the\n"
                f"            org/repo/branch/path structure; rewrite manually\n"
                f"            using {PLACEHOLDER}/<path-from-repo-root>)"
            )
        print()

    print(
        f"Reference example (copy-paste-ready):\n"
        f'  sh -c "$(curl -fsSL {PLACEHOLDER}/scripts/install/setup.sh)"\n'
        f"\n"
        f"Bypass for legitimate research/evidence citations:\n"
        f"  This hook only scans {SCAN_DIR}/. Cite real raw URLs in\n"
        f"  docs/research/ or docs/reports/ instead — those paths are exempt.\n"
    )


def main() -> int:
    """Scan docs/guides/ for hardcoded raw.githubusercontent.com URLs."""
    project_root = Path(__file__).resolve().parent.parent.parent

    if len(sys.argv) > 1:
        files = [Path(f) for f in sys.argv[1:]]
        # Filter to docs/guides/ only when called with explicit files
        files = [f for f in files if SCAN_DIR in f.as_posix() and f.suffix == ".md"]
    else:
        scan_path = project_root / SCAN_DIR
        files = list(scan_path.rglob("*.md")) if scan_path.exists() else []

    violations = check_files(files)
    if violations:
        print_violations(violations)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
