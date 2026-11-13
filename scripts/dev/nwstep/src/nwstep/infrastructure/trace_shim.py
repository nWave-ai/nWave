"""Observes which lines a candidate run executes, with the stdlib trace module.

A sitecustomize.py placed first on PYTHONPATH starts trace.Trace in every Python process that also
has NWSTEP_TRACE_DIR set, and writes the executed-line counts per file to that directory when the
process exits. The shim only observes: it does not change what the command computes. Processes
that do not import it write nothing, which is reported as could-not-verify, never as executed.
"""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Mapping
from pathlib import Path
from types import TracebackType

SITE_CUSTOMIZE = """
import atexit
import json
import os
import sys
import tempfile
import trace

_directory = os.environ.get("NWSTEP_TRACE_DIR")
if _directory:
    _tracer = trace.Trace(
        count=1, trace=0, ignoredirs=[sys.prefix, sys.base_prefix, sys.exec_prefix]
    )

    def _finish():
        sys.settrace(None)
        lines = {}
        for (filename, _line), _count in _tracer.results().counts.items():
            key = os.path.realpath(filename)
            lines[key] = lines.get(key, 0) + 1
        handle, target = tempfile.mkstemp(dir=_directory, suffix=".json")
        with os.fdopen(handle, "w", encoding="utf-8") as output:
            json.dump(lines, output)

    sys.settrace(_tracer.globaltrace_lt)
    atexit.register(_finish)
"""


class TraceShim:
    def __init__(self) -> None:
        self._scratch = tempfile.TemporaryDirectory(prefix="nwstep-trace-")
        self._shim_directory = Path(self._scratch.name) / "shim"
        self._trace_directory = Path(self._scratch.name) / "traces"

    def __enter__(self) -> TraceShim:
        self._shim_directory.mkdir()
        self._trace_directory.mkdir()
        (self._shim_directory / "sitecustomize.py").write_text(
            SITE_CUSTOMIZE, encoding="utf-8"
        )
        return self

    def __exit__(
        self,
        error_type: type[BaseException] | None,
        error: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._scratch.cleanup()

    def new_trace_directory(self) -> Path:
        directory = Path(tempfile.mkdtemp(dir=self._trace_directory))
        return directory

    def environment(
        self, base: Mapping[str, str], trace_directory: Path
    ) -> dict[str, str]:
        environment = dict(base)
        existing = environment.get("PYTHONPATH")
        paths = (
            [str(self._shim_directory), existing]
            if existing
            else [str(self._shim_directory)]
        )
        environment["PYTHONPATH"] = os.pathsep.join(paths)
        environment["NWSTEP_TRACE_DIR"] = str(trace_directory)
        return environment

    @staticmethod
    def executed_lines(trace_directory: Path, file: Path) -> int | None:
        """Lines of the file that ran, summed over the processes that wrote a trace; None when no Python process wrote one."""
        records = sorted(trace_directory.glob("*.json"))
        if not records:
            return None
        key = os.path.realpath(file)
        total = 0
        for record in records:
            counts = json.loads(record.read_text(encoding="utf-8"))
            total += int(counts.get(key, 0))
        return total
