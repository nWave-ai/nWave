"""One testcase of an open JUnit report, as the report states it.

`name` is the testcase's own name and `classname` the class, module or suite it sits in, when the report gives one.
`kind` and `message` are the failure or error element's own type and message, kept as evidence for the reviewer. They
say why a test failed as the report states it; no tool reads them to decide the verdict.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReportCase:
    name: str
    seconds: float
    status: str
    kind: str = ""
    message: str = ""
    classname: str = ""

    @property
    def full_name(self) -> str:
        """The name a mapping writes in full: the class, module or suite, two colons, then the name."""
        return f"{self.classname}::{self.name}" if self.classname else self.name
