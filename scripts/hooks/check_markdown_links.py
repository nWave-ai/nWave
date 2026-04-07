"""Pre-commit hook: validate relative markdown links.

Catches broken file/folder references inside markdown files. Specifically:
- Relative file links pointing at non-existent files
- Relative folder links pointing at folders without a README.md
- Stale paths after refactoring/restructuring (the recurring class of bug)

Encodes the nWave convention: a link to a folder under `docs/guides/`
must resolve to a folder containing a `README.md`. This matches the
guides layout where every doc lives in `<name>/README.md`. Folder
links elsewhere (e.g. `../../tests/`, `../../architecture/`) just need
to exist — they are browse-the-folder links, not document references.

Skipped:
- Absolute URLs (http, https, mailto, ftp, ftps, tel, data) — out of scope
- Pure anchor links (#section) — anchor validation not implemented in v1
- Files inside fenced code blocks (``` ... ```)
- Files under EXCLUDED_DIRS (audit reports, research evidence, archive)

Special handling:
- {{NWAVE_RAW_URL}}/<path> links: the placeholder is rewritten at release
  time to https://raw.githubusercontent.com/nwave-ai/nwave/main/, so the
  path component is validated against the project root. A tutorial that
  points at a missing script gets caught here, not by end users hitting 404.

Usage:
    python scripts/hooks/check_markdown_links.py
    python scripts/hooks/check_markdown_links.py docs/guides/foo/README.md
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


# Markdown link/image: [text](url) and ![alt](url).
# Captures the URL portion, optionally followed by a "title" we ignore.
LINK_PATTERN = re.compile(r"!?\[[^\]]*\]\((?P<url>[^)\s]+)(?:\s+\"[^\"]*\")?\)")

# URL schemes we don't validate (external).
ABSOLUTE_SCHEMES = (
    "http://",
    "https://",
    "mailto:",
    "ftp://",
    "ftps://",
    "tel:",
    "data:",
)

# Release-time substitution sentinel. The path AFTER this prefix is
# validated against the project root (the placeholder expands to a raw
# URL that mirrors the repo tree).
RAW_URL_PLACEHOLDER = "{{NWAVE_RAW_URL}}"

# Folders under this prefix follow the "every doc is folder/README.md"
# convention and must contain a README.md if linked to.
GUIDES_README_REQUIRED_PREFIX = "docs/guides"

# Default scan paths (relative to project root).
SCAN_PATHS = (
    "docs",
    "nWave/skills",
    "README.md",
    "nWave/README.md",
    "CONTRIBUTING.md",
)

# Directories to skip even when scanning recursively.
# These contain intentional historical references or external evidence URLs.
EXCLUDED_DIRS = (
    "docs/reports/analysis/divio-audit",
    "docs/research",
    "docs/archive",
    "docs/feature",
    "docs/evolution",
)


def is_excluded(path: Path, project_root: Path) -> bool:
    """Return True if path lives under an excluded directory."""
    try:
        rel = path.resolve().relative_to(project_root)
    except ValueError:
        return False
    rel_str = rel.as_posix()
    return any(rel_str == ex or rel_str.startswith(ex + "/") for ex in EXCLUDED_DIRS)


def is_external(url: str) -> bool:
    """Return True if URL uses an absolute external scheme."""
    return url.startswith(ABSOLUTE_SCHEMES)


def validate_placeholder_link(url: str, project_root: Path) -> str | None:
    """Validate a {{NWAVE_RAW_URL}}/<path> link against the project root.

    Returns None if the link is valid (or not a placeholder link),
    or an error message describing the problem.
    """
    if not url.startswith(RAW_URL_PLACEHOLDER):
        return None
    remainder = url[len(RAW_URL_PLACEHOLDER) :]
    if not remainder:
        # Bare {{NWAVE_RAW_URL}} with no path — meaningless but not broken.
        return None
    if not remainder.startswith("/"):
        # Malformed: should be {{NWAVE_RAW_URL}}/path, not {{NWAVE_RAW_URL}}path.
        return "placeholder link missing leading slash before path"
    # Strip query and anchor before resolving
    path_part = remainder.lstrip("/")
    if "?" in path_part:
        path_part = path_part.split("?", 1)[0]
    if "#" in path_part:
        path_part = path_part.split("#", 1)[0]
    if not path_part:
        return None
    target = (project_root / path_part).resolve()
    if not target.exists():
        return f"placeholder path does not exist at repo root: {path_part}"
    return None


def resolve_target(source_file: Path, url: str) -> Path:
    """Resolve a relative URL against the source file's directory.

    Strips query string and anchor before resolving. Returns the
    resolved absolute path (which may not exist).
    """
    # Strip query string
    if "?" in url:
        url = url.split("?", 1)[0]
    # Strip anchor
    if "#" in url:
        url = url.split("#", 1)[0]
    if not url:
        # Pure anchor link → target is the source file itself
        return source_file
    return (source_file.parent / url).resolve()


def validate_target(target: Path, project_root: Path) -> str | None:
    """Check that target exists and conforms to the folder/README.md rule.

    Returns None if valid, or an error message describing the problem.

    A folder target under docs/guides/ must contain a README.md (the
    "every doc lives in folder/README.md" convention). Folder targets
    elsewhere just need to exist.
    """
    if target.is_file():
        return None
    if target.is_dir():
        try:
            rel = target.resolve().relative_to(project_root).as_posix()
        except ValueError:
            return None  # outside project — can't enforce convention
        if (
            rel.startswith(GUIDES_README_REQUIRED_PREFIX + "/")
            or rel == GUIDES_README_REQUIRED_PREFIX
        ):
            if not (target / "README.md").is_file():
                return "guide folder exists but contains no README.md"
        return None
    return "target does not exist"


def iter_link_lines(content: str):
    """Yield (lineno, url) for each markdown link outside fenced code blocks."""
    in_code_block = False
    for lineno, line in enumerate(content.splitlines(), 1):
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        for match in LINK_PATTERN.finditer(line):
            yield lineno, match.group("url")


def check_file(file_path: Path, project_root: Path) -> list[str]:
    """Check all links in a single markdown file. Returns violation strings."""
    violations: list[str] = []
    try:
        content = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return violations

    rel = (
        file_path.relative_to(project_root)
        if file_path.is_absolute() and project_root in file_path.parents
        else file_path
    )

    for lineno, url in iter_link_lines(content):
        # {{NWAVE_RAW_URL}}/<path> — validate path against project root
        if url.startswith(RAW_URL_PLACEHOLDER):
            error = validate_placeholder_link(url, project_root)
            if error:
                violations.append(f"{rel}:{lineno}: {error}\n    link:    {url}")
            continue

        if is_external(url):
            continue
        if url.startswith("#"):
            # Pure anchor — v1 does not validate anchors.
            continue

        target = resolve_target(file_path, url)
        error = validate_target(target, project_root)
        if error:
            try:
                rel_target = target.relative_to(project_root)
                target_display = rel_target.as_posix()
            except ValueError:
                target_display = str(target)
            violations.append(
                f"{rel}:{lineno}: {error}\n"
                f"    link:    {url}\n"
                f"    resolves to: {target_display}"
            )
    return violations


def collect_files(project_root: Path) -> list[Path]:
    """Collect all .md files under SCAN_PATHS, honoring EXCLUDED_DIRS."""
    files: list[Path] = []
    for sp in SCAN_PATHS:
        path = project_root / sp
        if not path.exists():
            continue
        if path.is_file() and path.suffix == ".md":
            files.append(path)
        elif path.is_dir():
            for md in path.rglob("*.md"):
                if not is_excluded(md, project_root):
                    files.append(md)
    return sorted(files)


def main() -> int:
    project_root = Path(__file__).resolve().parent.parent.parent

    if len(sys.argv) > 1:
        # Pre-commit passes specific files; filter to relevant ones.
        files = []
        for arg in sys.argv[1:]:
            p = Path(arg).resolve()
            if p.suffix == ".md" and not is_excluded(p, project_root):
                files.append(p)
    else:
        files = collect_files(project_root)

    all_violations: list[str] = []
    for f in files:
        all_violations.extend(check_file(f, project_root))

    if all_violations:
        print(
            f"Broken markdown links detected ({len(all_violations)} total).\n"
            f"\n"
            f"How to fix:\n"
            f"  - 'target does not exist': verify the file/folder you linked to actually\n"
            f"    exists at the resolved path. After moves and restructures, relative\n"
            f"    paths often need an extra ../ or fewer ../.\n"
            f"  - 'guide folder exists but contains no README.md': in nWave's convention,\n"
            f"    every folder linked from a guide must have a README.md inside. Either\n"
            f"    point at a specific file or add a README.md to the folder.\n"
            f"  - 'placeholder path does not exist at repo root': {RAW_URL_PLACEHOLDER}/<path>\n"
            f"    expands at release time to a raw URL mirroring the repo tree, so <path>\n"
            f"    must exist relative to the project root. Verify the script/file exists\n"
            f"    at the path you wrote, or fix the path.\n"
            f"\n"
            f"Excluded from scanning: {', '.join(EXCLUDED_DIRS)}\n"
            f"(audit/research/archive paths may legitimately reference moved content)\n"
            f"\n"
            f"Violations:\n"
        )
        for v in all_violations:
            print(f"  {v}\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
