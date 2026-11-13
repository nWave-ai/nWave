"""``nwave-ai tests``: run a test command through the account's queue, select tests.

The only place that reads the process (arguments, environment, working directory)
and writes to its streams. ``run`` hands the work to ``queued_run``; ``select`` reads
the tree once and hands it to the pure ``selection.select_tests``.

Exit codes of ``run``: the command's own when it ended; 2 when the run was refused;
75 when the run left the queue at its declared wait limit and nothing ran
(indeterminate); 124 when the time limit ended the command; 127 when the command
could not start.
Exit codes of ``select``: 0 with a list (also when indeterminate: the widest group
is the list); 2 when refused.
"""

from __future__ import annotations

import json
import os
import signal
import sys
from dataclasses import dataclass
from pathlib import Path

from nwave_ai.testrun import execution, selection_report
from nwave_ai.testrun.declaration_source import load_declaration
from nwave_ai.testrun.dependency_adapters import ADAPTERS
from nwave_ai.testrun.project_tree import read_project
from nwave_ai.testrun.queued_run import (
    NOTICE_PREFIX,
    Command,
    Limits,
    Where,
    queued_run,
)
from nwave_ai.testrun.refusal import Refusal
from nwave_ai.testrun.selection import Project, Unusable, select_tests


EXIT_REFUSED = 2
# The conventional "temporary failure, try again": nothing ran, nothing was judged.
EXIT_INDETERMINATE = 75
EXIT_TIMED_OUT = 124
EXIT_NOT_STARTED = 127
_SIGNAL_BASE = 128

USAGE = """\
usage: nwave-ai tests run [options] NAME [ARG ...]
       nwave-ai tests run [options] -- COMMAND [ARG ...]
       nwave-ai tests select --use NAME [options] [PATH ...]

run: run one test command through the test queue of this account (one queue per
     account: two accounts of one machine do not coordinate).
  NAME [ARG ...]       a command the project declares, with more arguments
  -- COMMAND [ARG ...] any command, as given
  --class NAME         the class of the run; default: the declared command's class,
                       else the last declared class
  --timeout SECONDS    stop the command after this long; the wait in the queue is
                       not counted; default: the declared command's limit, else none
  --receipt FILE       also write the receipt of the run to FILE

select: print the tests a change selects, one per line.
  PATH ...             the changed files, relative to the project root
  --use NAME           the declared use whose depth applies (required)
  --add TEST           also select this test; may be repeated; nothing is removed
  --json               print one JSON document instead of the list

both:
  --root DIR           the project tree; default: the current directory
  --declaration FILE   read the tests declaration from FILE instead of the tests
                       block of .nwave/config.json
  -h, --help           print this text
"""

_RUN_OPTIONS = ("--root", "--declaration", "--class", "--timeout", "--receipt")
_SELECT_OPTIONS = ("--root", "--declaration", "--use", "--add")
_SELECT_FLAGS = ("--json",)


@dataclass(frozen=True)
class _Parsed:
    """The words of a command line: options by name, the rest in order."""

    options: dict[str, list[str]]
    rest: tuple[str, ...]
    after_separator: bool
    help: bool

    def last(self, name: str) -> str | None:
        values = self.options.get(name)
        return values[-1] if values else None


def _say(line: str) -> None:
    print(f"{NOTICE_PREFIX}{line}", file=sys.stderr, flush=True)


def _refuse(refusal: Refusal) -> int:
    for line in refusal.lines():
        print(line, file=sys.stderr, flush=True)
    return EXIT_REFUSED


def _parse(
    words: list[str],
    valued: tuple[str, ...],
    flags: tuple[str, ...],
    *,
    stop_at_word: bool,
) -> _Parsed | Refusal:
    """Split options from the rest; ``--`` ends the options, and so does the first
    plain word when ``stop_at_word`` (what follows belongs to the command)."""
    options: dict[str, list[str]] = {}
    rest: list[str] = []
    position = 0
    while position < len(words):
        word = words[position]
        position += 1
        if word == "--":
            return _Parsed(options, (*rest, *words[position:]), True, False)
        if word in ("-h", "--help"):
            return _Parsed(options, (), False, True)
        if word in flags:
            options.setdefault(word, []).append("")
        elif word in valued:
            if position == len(words):
                return Refusal(
                    what=f"the option {word} was given without a value",
                    why="an option that names nothing cannot be applied",
                    how=f"give a value after {word}; see `nwave-ai tests --help`",
                )
            options.setdefault(word, []).append(words[position])
            position += 1
        elif word.startswith("-"):
            return Refusal(
                what=f"the option {word} is not known",
                why="an option that is not understood must not be ignored",
                how=f"use one of {', '.join((*valued, *flags))}; see "
                "`nwave-ai tests --help`",
            )
        elif stop_at_word:
            return _Parsed(options, (word, *words[position:]), False, False)
        else:
            rest.append(word)
    return _Parsed(options, tuple(rest), False, False)


def _seconds(text: str | None) -> float | Refusal | None:
    if text is None:
        return None
    try:
        seconds = float(text)
    except ValueError:
        seconds = -1.0
    if seconds > 0 and seconds != float("inf"):
        return seconds
    return Refusal(
        what=f"the time limit '{text}' is not a positive number",
        why="the limit bounds how long the command may run",
        how="give --timeout as a number of seconds greater than 0, for example 300",
    )


def _path(text: str | None) -> Path | None:
    return None if text is None else Path(text)


def _write_receipt(receipt: execution.Receipt, file: str | None) -> None:
    document = json.dumps(receipt.as_document(), sort_keys=True)
    _say(f"receipt: {document}")
    if file is not None:
        target = Path(file)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(document + "\n", encoding="utf-8")


def _exit_of(receipt: execution.Receipt) -> int:
    if receipt.outcome == execution.REFUSED:
        return EXIT_REFUSED
    if receipt.outcome == execution.INDETERMINATE:
        return EXIT_INDETERMINATE
    if receipt.outcome == execution.TIMED_OUT:
        return EXIT_TIMED_OUT
    if receipt.outcome == execution.NOT_STARTED or receipt.exit is None:
        return EXIT_NOT_STARTED
    # A command ended by a signal has a negative exit: report it as shells do.
    return receipt.exit if receipt.exit >= 0 else _SIGNAL_BASE - receipt.exit


def _run(words: list[str]) -> int:
    parsed = _parse(words, _RUN_OPTIONS, (), stop_at_word=True)
    if isinstance(parsed, Refusal):
        return _refuse(parsed)
    if parsed.help:
        print(USAGE, end="")
        return 0
    limit = _seconds(parsed.last("--timeout"))
    if isinstance(limit, Refusal):
        return _refuse(limit)
    done = queued_run(
        Command(parsed.rest, declared=not parsed.after_separator),
        Where(
            root=Path(parsed.last("--root") or Path.cwd()),
            declaration_file=_path(parsed.last("--declaration")),
            environment=dict(os.environ),
            account_home=Path.home(),
        ),
        Limits(run_class=parsed.last("--class"), time_limit_seconds=limit),
        _say,
    )
    receipt = done.receipt
    if receipt.outcome == execution.INDETERMINATE:
        print(
            "INDETERMINATE: this run is neither a pass nor a failure",
            file=sys.stderr,
            flush=True,
        )
    if receipt.refusal is not None:
        _refuse(receipt.refusal)
    if receipt.outcome == execution.TIMED_OUT:
        _say(
            f"the command was stopped at its time limit of "
            f"{receipt.time_limit_seconds:g} s"
        )
    _write_receipt(receipt, parsed.last("--receipt"))
    return _exit_of(receipt)


def _select(words: list[str]) -> int:
    parsed = _parse(words, _SELECT_OPTIONS, _SELECT_FLAGS, stop_at_word=False)
    if isinstance(parsed, Refusal):
        return _refuse(parsed)
    if parsed.help:
        print(USAGE, end="")
        return 0
    root = Path(parsed.last("--root") or Path.cwd())
    sourced = load_declaration(root, _path(parsed.last("--declaration")))
    if isinstance(sourced, Refusal):
        return _refuse(sourced)
    rules = sourced.declaration.selection
    if rules is None:
        return _refuse(selection_report.no_selection_refusal(sourced.source))
    use = selection_report.declared_use(rules, parsed.last("--use"))
    if isinstance(use, Refusal):
        return _refuse(use)
    result = select_tests(
        parsed.rest,
        parsed.options.get("--add", []),
        use.depth,
        Project(rules, read_project(root, rules), ADAPTERS),
    )
    if isinstance(result, Unusable):
        return _refuse(result.refusal())
    report = selection_report.report(result, use, rules.local_ceiling)
    if isinstance(report, Refusal):
        return _refuse(report)
    for note in report.notes:
        print(note, file=sys.stderr)
    if "--json" in parsed.options:
        print(json.dumps(report.document, sort_keys=True, indent=2))
        return 0
    for test in report.tests:
        print(test)
    return 0


def _stop_on_termination() -> None:
    """Turn a termination request into an ordinary exit, so that the run leaves the
    queue and stops its command on the way out."""

    def stop(signum: int, _frame: object) -> None:
        raise SystemExit(_SIGNAL_BASE + signum)

    try:
        signal.signal(signal.SIGTERM, stop)
    except ValueError:
        # Not the main thread of the process: the caller owns the signals.
        return


def main(argv: list[str]) -> int:
    """Run ``nwave-ai tests ARGV``; return the exit code."""
    verb, words = (argv[0], argv[1:]) if argv else (None, [])
    if verb in (None, "-h", "--help", "help"):
        print(USAGE, end="")
        return 0
    if verb == "run":
        _stop_on_termination()
        return _run(words)
    if verb == "select":
        return _select(words)
    return _refuse(
        Refusal(
            what=f"'{verb}' is not a verb of `nwave-ai tests`",
            why="the command runs tests through the queue or selects them; "
            "it does nothing else",
            how="use `nwave-ai tests run` or `nwave-ai tests select`; see "
            "`nwave-ai tests --help`",
        )
    )
