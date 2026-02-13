"""Check all tracked files for merge conflict markers.

Detects actual merge conflicts by requiring both opening (<<<<<<< ) and closing
(>>>>>>>) markers in the same file. Lone ======= lines are ignored since they
appear in documentation, test output, and code separators.

Used by both pre-commit hook and CI security-checks job.
"""

import re
import subprocess
import sys


CONFLICT_OPEN = re.compile(r"^<<<<<<<\s", re.MULTILINE)
CONFLICT_CLOSE = re.compile(r"^>>>>>>>\s", re.MULTILINE)


def main() -> int:
    result = subprocess.run(
        ["git", "ls-files"], capture_output=True, text=True, check=False
    )
    files = result.stdout.splitlines()

    bad = []
    for filepath in files:
        if not filepath:
            continue
        try:
            with open(filepath, errors="ignore") as fh:
                content = fh.read()
            if CONFLICT_OPEN.search(content) and CONFLICT_CLOSE.search(content):
                bad.append(filepath)
        except OSError:
            continue

    if bad:
        for b in bad:
            print(f"Merge conflict markers found: {b}")
        return 1

    print("No merge conflict markers found")
    return 0


if __name__ == "__main__":
    sys.exit(main())
