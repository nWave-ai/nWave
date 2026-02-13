"""Check all tracked files end with a newline.

Mirrors CI file-quality job: scans all git-tracked files, not just staged ones.
Excludes dist/ and .git/ directories.
"""

import subprocess
import sys
from pathlib import Path


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
        p = Path(filepath)
        if not p.is_file() or p.stat().st_size == 0:
            continue
        try:
            with open(filepath, "rb") as fh:
                fh.seek(-1, 2)
                if fh.read(1) != b"\n":
                    bad.append(filepath)
        except OSError:
            continue

    if bad:
        for b in bad[:20]:
            print(f"Missing newline at end of file: {b}")
        if len(bad) > 20:
            print(f"... and {len(bad) - 20} more")
        return 1

    print("All files have proper end-of-file newlines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
