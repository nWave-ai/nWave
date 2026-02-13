"""Detect private keys in all tracked files.

Mirrors CI security-checks job: scans all git-tracked files, not just staged ones.
"""

import re
import subprocess
import sys


KEY_PATTERN = re.compile(r"-----BEGIN (RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----")


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
            if KEY_PATTERN.search(content):
                bad.append(filepath)
        except OSError:
            continue

    if bad:
        for b in bad:
            print(f"Private key detected: {b}")
        return 1

    print("No private keys detected")
    return 0


if __name__ == "__main__":
    sys.exit(main())
