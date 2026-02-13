"""Check all tracked files for trailing whitespace.

Mirrors CI file-quality job: scans all git-tracked files, not just staged ones.
Excludes dist/ and .git/ directories.
"""

import subprocess
import sys


def main() -> int:
    result = subprocess.run(
        ["git", "ls-files"], capture_output=True, text=True, check=False
    )
    files = [
        f
        for f in result.stdout.splitlines()
        if f and not f.startswith(("dist/", ".git/"))
    ]

    bad = []
    for filepath in files:
        try:
            with open(filepath, errors="ignore") as fh:
                for i, line in enumerate(fh, 1):
                    stripped = line.rstrip("\n\r")
                    if stripped != stripped.rstrip(" \t"):
                        bad.append(f"{filepath}:{i}")
        except (OSError, UnicodeDecodeError):
            continue

    if bad:
        for b in bad[:20]:
            print(f"Trailing whitespace: {b}")
        if len(bad) > 20:
            print(f"... and {len(bad) - 20} more")
        return 1

    print("No trailing whitespace found")
    return 0


if __name__ == "__main__":
    sys.exit(main())
