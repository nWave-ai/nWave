"""The report a command writes at its declared path: removed before the command runs, read after it.

Removing the file first means that a report from an earlier run can never answer for this one; a command that
stops before it writes is seen as having written no report. This adapter is the only reader of a report file.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from nwexpress.domain.declared_path import DeclaredPath
from nwexpress.domain.report_outcome import (
    NoReport,
    ReportOutcome,
    UnreadableReport,
    parse_report,
)


class ReportFile:
    @staticmethod
    def remove(root: Path, declared: str) -> None:
        target = root / DeclaredPath.parse(declared).text
        if target.is_file():
            target.unlink()

    @staticmethod
    def read(root: Path, declared: str) -> ReportOutcome:
        target = root / DeclaredPath.parse(declared).text
        if not target.is_file():
            return NoReport()
        try:
            text = target.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            return UnreadableReport(f"the file cannot be read as text: {error}")
        return parse_report(text)

    @staticmethod
    def bytes_of(root: Path, declared: str) -> bytes | None:
        """The file's bytes, or None when no file is there; an unreadable file raises OSError for the caller to name."""
        target = root / DeclaredPath.parse(declared).text
        if not target.is_file():
            return None
        return target.read_bytes()

    @staticmethod
    def keep(root: Path, declared: str, directory: Path, name: str) -> Path:
        """Copies the report at the declared path into the directory under the given name, and returns the copy's path."""
        source = root / DeclaredPath.parse(declared).text
        directory.mkdir(parents=True, exist_ok=True)
        kept = directory / name
        shutil.copyfile(source, kept)
        return kept
