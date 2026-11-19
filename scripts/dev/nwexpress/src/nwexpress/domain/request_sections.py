"""The sections of a request: the title, the problem, what to deliver, the owner decisions, the acceptance and the scratch folder."""

from __future__ import annotations

from dataclasses import dataclass


NOT_GIVEN = "Not given in this request."
REQUIRED_PARTS = ("title", "problem", "acceptance", "scratch")


def _given(value: str | None) -> bool:
    return value is not None and value.strip() != ""


@dataclass(frozen=True)
class RequestSections:
    title: str | None
    problem: str | None
    deliver: str | None
    decisions: str | None
    acceptance: str | None
    scratch: str | None

    def missing(self) -> tuple[str, ...]:
        """The required parts that are absent or blank, in their declared order."""
        return tuple(name for name in REQUIRED_PARTS if not _given(getattr(self, name)))

    def single_line(self, name: str) -> str:
        """A one-line part without its surrounding spaces."""
        return (getattr(self, name) or "").strip()

    def title_is_one_line(self) -> bool:
        return "\n" not in self.single_line("title")

    def body(self, name: str) -> str:
        """A section as the request holds it: its text without the line breaks around it, or NOT_GIVEN when it is blank."""
        value = getattr(self, name)
        if not _given(value):
            return NOT_GIVEN
        return value.strip("\r\n")
