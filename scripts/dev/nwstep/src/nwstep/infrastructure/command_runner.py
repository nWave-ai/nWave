"""Runs an argv without a shell, in the root, through the account's test queue, within a time limit. Output is kept whole and as a tail.

The queue is the one of `nwave-ai tests run` (nwave_ai.testrun, in the repository that
ships this nwstep): the hooks and the executors wait in the same line. The time limit
bounds the command only; the wait for a place is not counted in it, nor in the duration.
A run stopped at its limit says so in its outcome, with the limit it was stopped at.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from nwstep.domain.command_bound import CommandBound
from nwstep.domain.command_outcome import CommandOutcome
from nwstep.infrastructure.package_paths import PackagePaths


if TYPE_CHECKING:
    from collections.abc import Mapping


class CommandRunner:
    TIMEOUT_S = CommandBound.DEFAULT_SECONDS
    TAIL_LINES = 40

    def __init__(self, timeout_s: int = TIMEOUT_S) -> None:
        """A command runs within TIMEOUT_S unless the caller states its own bound for the run. No run is unbounded."""
        self._timeout_s = timeout_s

    def run(
        self,
        argv: list[str],
        cwd: Path,
        environment: Mapping[str, str] | None = None,
        timeout_s: int | None = None,
    ) -> CommandOutcome:
        bound = self._timeout_s if timeout_s is None else timeout_s
        try:
            queued_run = self._queue()
        except ImportError as error:
            return self._outcome(
                argv,
                0.0,
                None,
                b"",
                f"could not start {argv[0]}: the account's test queue cannot be loaded "
                f"from {PackagePaths.REPOSITORY}: {error}",
            )
        done = queued_run.queued_run(
            queued_run.Command(tuple(argv)),
            queued_run.Where(
                root=cwd,
                declaration_file=None,
                environment=dict(os.environ if environment is None else environment),
                account_home=Path.home(),
            ),
            self._limits(queued_run, bound),
            lambda line: print(
                f"{queued_run.NOTICE_PREFIX}{line}", file=sys.stderr, flush=True
            ),
        )
        receipt = done.receipt
        stopped = receipt.outcome == queued_run.execution.TIMED_OUT
        return self._outcome(
            argv,
            receipt.duration_seconds,
            receipt.exit,
            done.output or b"",
            self._problem(queued_run, receipt, bound),
            timed_out_after=bound if stopped else None,
        )

    def _limits(self, queued_run, bound: int):
        """The class and the bound of one command.

        A command within TIMEOUT_S belongs to the class the project declares first, the one that goes first. A longer
        bound belongs to the class declared last.
        """
        short = bound <= self.TIMEOUT_S
        choice = queued_run.ClassChoice
        return queued_run.Limits(
            run_class=choice.FIRST if short else choice.LAST,
            time_limit_seconds=bound,
            capture_output=True,
        )

    @staticmethod
    def _problem(queued_run, receipt, bound: int) -> str | None:
        """What stopped the command from giving an exit of its own, if anything did."""
        if receipt.outcome == queued_run.execution.TIMED_OUT:
            return f"timed out after {bound}s"
        if receipt.refusal is None:
            return None
        if receipt.outcome == queued_run.execution.NOT_STARTED:
            return receipt.refusal.what
        return " ".join(receipt.refusal.lines())

    @staticmethod
    def _queue():
        """The queue's entry, imported from the repository that ships this nwstep."""
        repository = str(PackagePaths.REPOSITORY)
        if repository not in sys.path:
            sys.path.insert(0, repository)
        from nwave_ai.testrun import queued_run

        return queued_run

    def _outcome(
        self,
        argv: list[str],
        duration_s: float,
        exit_code: int | None,
        output: bytes,
        problem: str | None,
        timed_out_after: int | None = None,
    ) -> CommandOutcome:
        text = output.decode("utf-8", errors="replace")
        lines = text.splitlines()
        return CommandOutcome(
            argv=tuple(argv),
            exit_code=exit_code,
            duration_s=duration_s,
            output_tail=tuple(lines[-self.TAIL_LINES :]),
            problem=problem,
            output=text,
            timed_out_after=timed_out_after,
        )
