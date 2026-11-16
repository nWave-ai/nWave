"""The trunk guard: a reference-transaction hook, installed once in the hook directory every worktree shares.

It guards against ACCIDENTS: a wrong branch -f, update-ref or push made from a delivery worktree. It is NOT a wall: a
process that sets core.hooksPath or skips hooks is not stopped. The real recovery is the reflog of the trunk and the
single-writer rule. The hook's own refusal message says so, and the tests show the documented bypass working.

The hook is a Python script the tool writes with the interpreter that installs it, so it has no shell. It reads the
trunk when it runs: lanes.trunk of the main checkout's repository configuration, then of the global configuration,
default master. A hook file of another author is never overwritten.
"""

from __future__ import annotations

import sys
from enum import Enum
from typing import TYPE_CHECKING

from nwexpress.domain.refusal import Refusal
from nwexpress.infrastructure import commit_hooks_git as git_hooks
from nwexpress.infrastructure.commit_hooks_git import GitHooksError


if TYPE_CHECKING:
    from pathlib import Path


GUARD_NAME = "reference-transaction"
GUARD_MARKER = b"nwexpress trunk guard (reference-transaction)"
# The guard the predecessor tool wrote: its header line on line 2 and its last line. A file with both is that guard and
# is migrated to this one, not refused; any other file under the hook name is foreign and stays untouched.
PREDECESSOR_HEADER = b"# nwstep trunk guard (reference-transaction)"
PREDECESSOR_LAST_LINE = b"    raise SystemExit(main())"
DEFAULT_TRUNK = "master"

_TEMPLATE = '''#!__PYTHON__
# nwexpress trunk guard (reference-transaction)
#
# Guards against ACCIDENTS: an update of the trunk from a delivery worktree (a wrong branch -f, update-ref or push).
# It is NOT a wall. A process that sets core.hooksPath or skips hooks is not stopped by this file.
# The real recovery is the reflog of the trunk and the single-writer rule: the main checkout writes the trunk.
"""Refuses an update of the trunk made from a worktree other than the main checkout."""

import json
import subprocess
import sys
from pathlib import Path

DEFAULT_TRUNK = "__DEFAULT_TRUNK__"


def git(*arguments):
    completed = subprocess.run(
        ["git", *arguments], capture_output=True, text=True, check=False
    )
    return completed.returncode, completed.stdout.strip()


def configured_trunk(main):
    for path in (main / ".nwave" / "config.json", Path.home() / ".nwave" / "config.json"):
        if not path.is_file():
            continue
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        lanes = document.get("lanes") if isinstance(document, dict) else None
        if isinstance(lanes, dict) and isinstance(lanes.get("trunk"), str):
            return lanes["trunk"]
    return DEFAULT_TRUNK


def main():
    if len(sys.argv) < 2 or sys.argv[1] != "prepared":
        return 0
    updates = [line.split() for line in sys.stdin if line.strip()]
    code, common = git("rev-parse", "--path-format=absolute", "--git-common-dir")
    code_top, top = git("rev-parse", "--show-toplevel")
    if code != 0 or code_top != 0 or not top:
        print("WHAT: the trunk update cannot be checked: git does not name the worktree", file=sys.stderr)
        print("WHY: the guard refuses what it cannot check", file=sys.stderr)
        print("HOW: run the update from the main checkout of the repository", file=sys.stderr)
        return 1
    main_checkout = Path(common).resolve().parent
    if Path(top).resolve() == main_checkout:
        return 0
    trunk = configured_trunk(main_checkout)
    if trunk is None:
        print("WHAT: the trunk update is refused: the configuration of the trunk cannot be read", file=sys.stderr)
        print("WHY: the guard needs lanes.trunk to know which ref is the trunk", file=sys.stderr)
        print("HOW: make the .nwave/config.json of the main checkout a readable JSON object, then retry", file=sys.stderr)
        return 1
    for _, _, ref in updates:
        if ref == "refs/heads/" + trunk:
            print(
                f"WHAT: the update of {ref} from the delivery worktree {top} is refused",
                file=sys.stderr,
            )
            print(
                "WHY: the trunk is written only by the main checkout "
                f"{main_checkout}; this guard stops ACCIDENTS (a wrong branch -f, update-ref or push). "
                "It does NOT stop a process that disables hooks (git -c core.hooksPath=... or a skipped hook): "
                "the real recovery is the reflog of the trunk and the single-writer rule",
                file=sys.stderr,
            )
            print(
                f"HOW: run the update from {main_checkout}, or cherry-pick the commit onto the trunk there; "
                "to bypass this guard on purpose, set core.hooksPath for that one command",
                file=sys.stderr,
            )
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


class GuardOutcome(Enum):
    INSTALLED = "installed"
    MIGRATED = "migrated"
    CURRENT = "current"


class GuardState(Enum):
    ABSENT = "absent"
    STALE = "stale"
    CURRENT = "current"
    PREDECESSOR = "predecessor"
    FOREIGN = "foreign"


def guard_content(python: str = sys.executable, trunk: str = DEFAULT_TRUNK) -> bytes:
    """The bytes of the guard hook for this interpreter; the default trunk is only the fallback the hook reads."""
    return (
        _TEMPLATE.replace("__PYTHON__", python)
        .replace("__DEFAULT_TRUNK__", trunk)
        .encode("utf-8")
    )


def _guard_target(main: Path) -> Path:
    try:
        return git_hooks.hooks_directory(main) / GUARD_NAME
    except GitHooksError as error:
        raise Refusal(
            what=f"the trunk guard cannot be placed for {main}: {error}",
            why="without the hook directory the guard cannot be checked or written, and an unchecked guard is not a guard",
            how=f"make {main} a readable git repository (git -C {main} rev-parse --git-path hooks must succeed), then run the clone command again",
        ) from None


def _is_predecessor_guard(existing: bytes) -> bool:
    """True for the guard the predecessor tool wrote: its header on line 2 and its own last line."""
    lines = existing.splitlines()
    return (
        len(lines) > 2
        and lines[1] == PREDECESSOR_HEADER
        and lines[-1] == PREDECESSOR_LAST_LINE
    )


def _state(target: Path, content: bytes) -> GuardState:
    """Reads the guard file, if any, and says whether it is absent, nwexpress's and current, nwexpress's and stale,
    the predecessor tool's guard to migrate, or foreign."""
    if not target.exists():
        return GuardState.ABSENT
    existing = target.read_bytes()
    if GUARD_MARKER in existing:
        return GuardState.CURRENT if existing == content else GuardState.STALE
    if _is_predecessor_guard(existing):
        return GuardState.PREDECESSOR
    return GuardState.FOREIGN


def _foreign_refusal(target: Path, main: Path) -> Refusal:
    return Refusal(
        what=f"the reference-transaction hook {target} is not written by nwexpress, so the trunk guard is not installed",
        why="the project's own reference-transaction hook may enforce rules of its own, and replacing it would lose them",
        how=f"move {target} aside by hand if its rules are not needed, or keep it and enforce the trunk rule there; then run the clone command again",
    )


def check_trunk_guard(main: Path) -> None:
    """Reads the guard's place and refuses a foreign hook there. Writes nothing, so it can run before any write."""
    target = _guard_target(main)
    if _state(target, guard_content()) is GuardState.FOREIGN:
        raise _foreign_refusal(target, main)


def install_trunk_guard(main: Path) -> GuardOutcome:
    """Writes the guard into the hook directory of main, or refuses when a hook of that name is neither nwexpress's
    nor the predecessor tool's guard. The predecessor guard is replaced by this one, so the trunk rule stays in force.

    The write is atomic: the content goes to a partial file that replaces the guard only when it is complete, and the
    partial file is removed when the write fails.
    """
    target = _guard_target(main)
    content = guard_content()
    state = _state(target, content)
    if state is GuardState.FOREIGN:
        raise _foreign_refusal(target, main)
    if state is GuardState.CURRENT:
        return GuardOutcome.CURRENT
    temporary = target.with_name(GUARD_NAME + ".nwexpress-partial")
    try:
        temporary.write_bytes(content)
        temporary.chmod(0o755)
        temporary.replace(target)
    except OSError as error:
        temporary.unlink(missing_ok=True)
        raise Refusal(
            what=f"the trunk guard cannot be written in the hook directory of {main}: {error.strerror or error}",
            why="without the guard an accidental trunk update from a delivery worktree is not refused",
            how=f"make the hook directory of {main} writable, then run the clone command again",
        ) from None
    if state is GuardState.PREDECESSOR:
        return GuardOutcome.MIGRATED
    return GuardOutcome.INSTALLED
