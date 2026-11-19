"""The process effect a slice's declared verification commands need.

Each declared command is run as the argv that its shell-word split gives: no shell, no program
name written here, in the directory the caller names, under a timeout. The caller names a copy
of the user's checkout or of the candidate, never the checkout itself. Nothing else is started
in this module; the architecture rule that names it (tests/nwdes/architecture/test_git_only.py)
checks exactly that.
"""

from __future__ import annotations

import shlex
import subprocess


VERIFY_TIMEOUT_S = 120


def run_declared(commands, cwd) -> bool:
    """Run each declared command in order in cwd; True when every one started and finished within
    the timeout. A command that cannot be split, cannot start or times out returns False, and the
    caller then treats the declared report as not written. A non-zero exit is not a failure here:
    a failing identity is read from the report."""
    for command in commands:
        try:
            argv = shlex.split(command)
        except ValueError:
            return False
        if not argv:
            return False
        try:
            subprocess.run(
                argv,
                cwd=cwd,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                timeout=VERIFY_TIMEOUT_S,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return False
    return True
