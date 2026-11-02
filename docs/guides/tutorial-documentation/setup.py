#!/usr/bin/env python3
"""Setup for Tutorial 15: Creating Quality Documentation.

Creates a small string-utils module with three functions ready to be
documented by /nw-document. No tests, no venv — this tutorial focuses
on documentation generation, not Python tooling.

Run from outside the nWave repo (e.g. ``cd $(mktemp -d)`` first).
See manual-setup.md for the same steps written as prose.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path


PROJECT_DIR = Path("string-utils")

STRING_UTILS_PY = '''\
"""String utility functions for common text transformations."""


def slugify(text: str) -> str:
    """Convert text to a URL-friendly slug.

    Lowercases the text, replaces spaces with hyphens,
    and removes non-alphanumeric characters (except hyphens).

    Args:
        text: The input string to slugify.

    Returns:
        A lowercase, hyphen-separated string safe for URLs.
    """
    import re
    text = text.lower().strip()
    text = re.sub(r"[^\\w\\s-]", "", text)
    text = re.sub(r"[\\s_]+", "-", text)
    return text.strip("-")


def truncate(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to a maximum length, adding a suffix if truncated.

    If the text is shorter than max_length, it is returned unchanged.
    Otherwise, it is cut at max_length minus the suffix length, and
    the suffix is appended.

    Args:
        text: The input string to truncate.
        max_length: Maximum allowed length (default 100).
        suffix: String to append when truncating (default "...").

    Returns:
        The original or truncated string.
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def word_count(text: str) -> int:
    """Count the number of words in a string.

    Words are separated by whitespace. Empty strings return 0.

    Args:
        text: The input string.

    Returns:
        The number of words.
    """
    return len(text.split()) if text.strip() else 0
'''


def main() -> int:
    force = "--force" in sys.argv[1:]

    if force and PROJECT_DIR.exists():
        shutil.rmtree(PROJECT_DIR)

    if PROJECT_DIR.exists():
        print(f"{PROJECT_DIR} already exists. Run with --force to recreate.")
        return 0

    PROJECT_DIR.mkdir()
    (PROJECT_DIR / "string_utils.py").write_text(STRING_UTILS_PY)

    print(
        f"\nSetup complete. {PROJECT_DIR} ready.\n\n"
        f"Next steps:\n"
        f"  cd {PROJECT_DIR}\n"
        f"  Open Claude Code in this directory and run /nw-document\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
