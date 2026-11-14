"""The declared dependents command, run as a process: the selector's one outside call.

The command runs from the project root, is not given a shell, and gets one JSON object
on standard input: ``{"files": [...], "targets": [...]}``, the tree-relative paths of
the project and the files it must answer for. Its answer is one line per direct
dependency, ``TARGET<TAB>DEPENDENT``, with TARGET among the targets. An answer naming
anything else is refused, and so is any status other than 0 or a program that cannot
start.

A call still running at its bound is killed, with the whole process group it started
(the shell and whatever it runs), and gives no answer: that is a refusal that says it
was a TIMEOUT, not a failure of the command's answer.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING

from nwave_ai.testrun.dependents.edge import DependencyEdge
from nwave_ai.testrun.refusal import Refusal


if TYPE_CHECKING:
    from pathlib import Path

    from nwave_ai.testrun.dependents.declared import DeclaredDependents


_POSIX = os.name == "posix"


@dataclass(frozen=True)
class DependentsCommand:
    """Calling it with targets runs the declared command once, bounded, and returns its edges."""

    declared: DeclaredDependents
    root: Path
    files: frozenset[str]

    def __call__(self, targets: frozenset[str]) -> frozenset[DependencyEdge] | Refusal:
        request = json.dumps({"files": sorted(self.files), "targets": sorted(targets)})
        try:
            process = subprocess.Popen(
                list(self.declared.argv),
                cwd=self.root,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                start_new_session=_POSIX,
            )
        except OSError as error:
            return self._refused(f"it could not be started ({error.strerror or error})")
        try:
            answer, said = process.communicate(
                request, timeout=self.declared.timeout_seconds
            )
        except subprocess.TimeoutExpired:
            _kill(process)
            process.communicate()
            return self._timed_out()
        if process.returncode != 0:
            words = " ".join(said.split()) or "no message on standard error"
            return self._refused(f"it exited with status {process.returncode}: {words}")
        return self._edges(answer, targets)

    def _edges(
        self, answer: str, targets: frozenset[str]
    ) -> frozenset[DependencyEdge] | Refusal:
        edges: set[DependencyEdge] = set()
        for number, line in enumerate(answer.splitlines(), start=1):
            if not line:
                continue
            target, separator, dependent = line.partition("\t")
            if not separator or not target or not dependent or "\t" in dependent:
                return self._refused(
                    f"line {number} of its answer is not TARGET, a tab and DEPENDENT: "
                    f"{line!r}"
                )
            if target not in targets or dependent not in self.files:
                return self._refused(
                    f"line {number} of its answer names a file outside the request: "
                    f"{line!r}"
                )
            edges.add(DependencyEdge(target, dependent))
        return frozenset(edges)

    def _refused(self, detail: str) -> Refusal:
        command = " ".join(self.declared.argv)
        return Refusal(
            what=f"the declared dependents command '{command}' gave no usable answer: "
            f"{detail}",
            why="which files depend on a change is answered by the command the project "
            "declares; without that answer the selector cannot tell which tests to run",
            how="repair the command so that it exits 0 and prints one TARGET, a tab and "
            "DEPENDENT line per dependency, or correct selection.dependents in the "
            "declaration; then run nwave-ai tests select --use commit <a changed path>",
        )

    def _timed_out(self) -> Refusal:
        command = " ".join(self.declared.argv)
        bound = self.declared.timeout_seconds
        return Refusal(
            what=f"TIMEOUT: the declared dependents command '{command}' did not answer "
            f"within its bound of {bound:g} seconds and was killed; this is a timeout, "
            "not a failure of the command's answer",
            why="a command killed at its bound has given no answer, so the files it "
            "would answer for are unknown and the selector cannot narrow the tests",
            how="make the command answer within selection.dependents.timeout_seconds "
            f"(now {bound:g} seconds, at most 600), or declare a larger bound up to that "
            "ceiling; then run nwave-ai tests select --use commit <a changed path>",
        )


def _kill(process: subprocess.Popen[str]) -> None:
    """Kill the command and everything it started, so that its output pipes close."""
    if hasattr(os, "killpg"):
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        return
    process.kill()
