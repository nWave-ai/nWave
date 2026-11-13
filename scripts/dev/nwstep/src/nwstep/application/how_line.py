"""Builds the exact nwstep command lines a refusal tells the executor to run."""

from __future__ import annotations

import shlex
import sys


class HowLine:
    def __init__(self, python: str | None = None) -> None:
        self._python = python or sys.executable

    def command(self, *args: str) -> str:
        return shlex.join([self._python, "-m", "nwstep", *args])
