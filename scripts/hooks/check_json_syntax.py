"""Check all JSON files for valid syntax.

Mirrors CI file-quality job: scans all JSON files in the repo, not just staged ones.
Excludes .git/, dist/, and node_modules/ directories.
"""

import json
import sys
from pathlib import Path


def main() -> int:
    errors = []
    for json_file in Path().rglob("*.json"):
        path_str = str(json_file)
        if ".git" in path_str or "dist" in path_str or "node_modules" in path_str:
            continue
        try:
            with open(json_file) as fh:
                json.load(fh)
        except json.JSONDecodeError as e:
            errors.append(f"{json_file}: {e}")

    if errors:
        for e in errors:
            print(f"JSON error: {e}")
        return 1

    print("All JSON files have valid syntax")
    return 0


if __name__ == "__main__":
    sys.exit(main())
