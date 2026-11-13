"""Run a test command of a project through the queue of the account: the use case.

One entry for every caller: the command line, the hooks through it, and the step
recorder of the dynamic executors in-process. It reads what the project declares,
finds the queue of the account and hands a complete request to ``execution``.
Every input is a parameter: the environment and the account home are named by the
caller, never read here.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from nwave_ai.testrun import account_queue, execution
from nwave_ai.testrun.declaration_source import Sourced, load_declaration
from nwave_ai.testrun.refusal import Refusal


if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from pathlib import Path


# What every line the queue says about a run starts with, whoever prints it.
NOTICE_PREFIX = "[nwave tests] "


class ClassChoice(Enum):
    """A class named by its place in the declared order instead of by its name."""

    FIRST = "first"
    LAST = "last"


@dataclass(frozen=True)
class Command:
    """What to run: words given by the caller, or a command the project declares."""

    words: tuple[str, ...]
    declared: bool = False


@dataclass(frozen=True)
class Where:
    """Where the run happens: the tree, its declaration file if named, the account."""

    root: Path
    declaration_file: Path | None
    environment: Mapping[str, str]
    account_home: Path


@dataclass(frozen=True)
class Limits:
    """How the caller bounds the run; ``None`` leaves it to the declaration."""

    run_class: str | ClassChoice | None = None
    time_limit_seconds: float | None = None
    capture_output: bool = False


def _refused(root: Path, command: Command, refusal: Refusal) -> execution.Execution:
    return execution.Execution(
        execution.Receipt(
            run_class="",
            root=str(root.resolve()),
            command=command.words,
            outcome=execution.REFUSED,
            refusal=refusal,
        )
    )


def _resolved(
    command: Command, limits: Limits, sourced: Sourced
) -> tuple[tuple[str, ...], str | None, float | None] | Refusal:
    """The words to run, the class and the limit, after the declaration is applied."""
    declaration = sourced.declaration
    run_class = limits.run_class
    if run_class is ClassChoice.FIRST:
        run_class = declaration.queue.classes[0]
    if run_class is ClassChoice.LAST:
        run_class = None
    if not command.words:
        return Refusal(
            what="no command was given to run",
            why="the queue runs exactly the command it is given; it invents none",
            how=(
                "give a declared command name, or the command after `--`: "
                "nwave-ai tests run --class short -- <command>"
            ),
        )
    if not command.declared:
        return command.words, run_class, limits.time_limit_seconds
    name, *arguments = command.words
    declared = declaration.commands.get(name)
    if declared is None:
        known = ", ".join(declaration.commands) or "none"
        return Refusal(
            what=f"the command '{name}' is not declared in {sourced.source}",
            why="a command run by name is one the project declares",
            how=(
                f"use a declared command ({known}), declare commands.{name}, or "
                "give the command itself after `--`"
            ),
        )
    return (
        (*declared.argv, *arguments),
        run_class or declared.run_class,
        limits.time_limit_seconds or declared.timeout_seconds,
    )


def queued_run(
    command: Command,
    where: Where,
    limits: Limits,
    notify: Callable[[str], None],
) -> execution.Execution:
    """Run ``command`` in ``where.root`` through the queue of the account."""
    sourced = load_declaration(where.root, where.declaration_file)
    if isinstance(sourced, Refusal):
        return _refused(where.root, command, sourced)
    resolved = _resolved(command, limits, sourced)
    if isinstance(resolved, Refusal):
        return _refused(where.root, command, resolved)
    queue = account_queue.queue_directory(where.environment, where.account_home)
    if isinstance(queue, Refusal):
        return _refused(where.root, command, queue)
    argv, run_class, time_limit = resolved
    return execution.execute(
        execution.RunRequest(
            root=where.root,
            argv=argv,
            run_class=run_class,
            time_limit_seconds=time_limit,
            declaration=sourced.declaration,
            queue=queue,
            environment=where.environment,
            capture_output=limits.capture_output,
        ),
        notify,
    )
