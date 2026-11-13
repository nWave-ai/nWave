"""The command prefix a user runs nwstep with: the source on PYTHONPATH and this interpreter, both absolute."""

from __future__ import annotations

import os
import shlex
import sys
from pathlib import Path

from nwstep.infrastructure.package_paths import PackagePaths


class InvocationLine:
    def __init__(self, python: str | None = None, source: Path | None = None) -> None:
        self._python = python or sys.executable
        self._source = source or PackagePaths.SOURCE

    def text(self) -> str:
        module = shlex.join([self._python, "-m", "nwstep"])
        override = os.environ.get("NWSTEP_SKILLS_ROOT")
        prefix = f"NWSTEP_SKILLS_ROOT={shlex.quote(override)} " if override else ""
        return f"{prefix}PYTHONPATH={shlex.quote(str(self._source))} {module}"
