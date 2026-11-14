"""The commit hooks a source repository runs, and which of them a clone takes over: values only.

A hook is a file in the effective hook directory of a repository, which git reads from core.hooksPath when that is set.
A file runs only when it is executable and its name does not end in .sample, the suffix of the examples git's templates
ship. The effects that read and write those files live in the infrastructure module that calls these functions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from nwstep.domain.commit_hooks import HookOutcome


EXECUTABLE_BITS = 0o111
SAMPLE_SUFFIX = ".sample"


@dataclass(frozen=True)
class SourceHook:
    """name: the file name in the hook directory. mode: its permission bits. content: its bytes."""

    name: str
    mode: int
    content: bytes


@dataclass(frozen=True)
class CloneHooks:
    """outcome: what the clone command did about the commit hooks. copied: the names it copied from the source, in order."""

    outcome: HookOutcome
    copied: tuple[str, ...] = ()


def runnable(hooks: tuple[SourceHook, ...]) -> tuple[SourceHook, ...]:
    """The hooks git would run: executable, not a .sample example, in name order."""
    selected = (
        hook
        for hook in hooks
        if hook.mode & EXECUTABLE_BITS and not hook.name.endswith(SAMPLE_SUFFIX)
    )
    return tuple(sorted(selected, key=lambda hook: hook.name))
