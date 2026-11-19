"""Reads the text sections of a request: a path names a text file, and - names standard input, which one section at most may read."""

from __future__ import annotations

import sys
from pathlib import Path

from nwexpress.application.how_line import HowLine
from nwexpress.application.request_example import RequestExample
from nwexpress.domain.refusal import Refusal


STDIN = "-"
FLAGS = {
    "problem": "--problem",
    "deliver": "--deliver",
    "decisions": "--decisions",
    "acceptance": "--acceptance",
}


class SectionReader:
    def __init__(self, how: HowLine, workspace: str) -> None:
        self._how = how
        self._workspace = workspace

    def read(self, paths: dict[str, str | None]) -> dict[str, str | None]:
        """The text of each section given, or None for a section left out. Refuses when two sections read stdin."""
        given = {name: value for name, value in paths.items() if value is not None}
        from_stdin = [FLAGS[name] for name, value in given.items() if value == STDIN]
        if len(from_stdin) > 1:
            raise Refusal(
                what=f"{' and '.join(from_stdin)} both read stdin",
                why="standard input can be read once in a run, so only one section can come from it",
                how=RequestExample.command(self._how, self._workspace, from_stdin[0]),
            )
        return {
            name: self._read_one(FLAGS[name], value) if value is not None else None
            for name, value in paths.items()
        }

    def _read_one(self, flag: str, value: str) -> str:
        if value == STDIN:
            return sys.stdin.read()
        try:
            return Path(value).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            raise Refusal(
                what=f"{flag} names {value}, which cannot be read as text: {error}",
                why="a section is written into the request only from text the verb can read",
                how=f"give the path of a readable UTF-8 text file, or - to read the section from stdin: {flag} <file>",
            ) from None
