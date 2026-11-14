"""Which root a delivery may write in, decided from values only.

The clone command marks each clone it makes with MARKER_KEY, whose value is the clone's own toplevel path. A root is
admitted when it carries that marker for its own toplevel, or when it is a git linked worktree: a worktree commits on
its own branch and leaves the primary checkout untouched. Once init has recorded an anchor, the root must also be the
one init ran in. Git reads and writes live in the infrastructure; this module decides.
"""

from __future__ import annotations

from dataclasses import dataclass

from nwstep.domain.refusal import Refusal


MARKER_KEY = "nwstep.delivery-clone"


@dataclass(frozen=True)
class RootFacts:
    """root: the toplevel of the declared root. marked: the clone marker equals that toplevel. linked: the root is a git
    linked worktree rather than the primary working tree. anchor: the toplevel init recorded in the baseline, or None
    when no anchor is known."""

    root: str
    marked: bool
    anchor: str | None
    linked: bool = False


def _where(command: str) -> str:
    """The location flag each delivery command takes: init uses the current directory, prompt requires --root."""
    if command == "init":
        return "from inside <new directory>"
    if command == "prompt":
        return "with --root <new directory>"
    return "from inside <new directory> or with --root <new directory>"


def root_refusal(facts: RootFacts, *, command: str) -> Refusal | None:
    if not facts.marked and not facts.linked:
        return Refusal(
            what=f"the root {facts.root} is neither a delivery clone made by nwstep clone nor a git linked worktree, so it may be your primary checkout",
            why="a delivery edits and commits in its root, so the root must not be the primary checkout the user works in; a linked worktree commits on its own branch and leaves that checkout untouched, a clone the clone command made is known not to be it, and a separate clone without the marker may be it",
            how=f"from your checkout, run 'git worktree add <new directory> -b <branch>' and then run {command} {_where(command)}; or make a delivery clone with 'nwstep clone --source <your checkout> --dest <new directory>' and then run {command} {_where(command)}",
        )
    if facts.anchor is not None and facts.anchor != facts.root:
        return Refusal(
            what=f"the root {facts.root} is not {facts.anchor}, the clone that init took the pre-feature tree from",
            why="the probes judge the change against the tree init recorded; a root swapped after init would judge it against another repository and write records into a clone init never saw",
            how=f"run {command} from {facts.anchor} (or pass --root {facts.anchor} where the command takes it), or start a new workspace by running init inside {facts.root}",
        )
    return None
