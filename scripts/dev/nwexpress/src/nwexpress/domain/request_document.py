"""The text of a request: the standing-block template with the card, the title and each section filled in."""

from __future__ import annotations

import string

from nwexpress.domain.request_card import RequestCard
from nwexpress.domain.request_sections import RequestSections


PLACEHOLDERS = frozenset(
    {"card", "title", "scratch", "problem", "deliver", "decisions", "acceptance"}
)


class RequestDocument:
    @staticmethod
    def template_problems(template: str) -> tuple[str, ...]:
        """What makes the template unfit to fill: a placeholder the verb does not fill, or one it leaves out. Empty when it fits."""
        try:
            used = {
                field
                for _, field, _, _ in string.Formatter().parse(template)
                if field is not None
            }
        except ValueError as error:
            return (f"the template is not valid text for filling: {error}",)
        problems: list[str] = []
        unknown = sorted(used - PLACEHOLDERS)
        if unknown:
            problems.append(
                "it names placeholders the verb does not fill: " + ", ".join(unknown)
            )
        unused = sorted(PLACEHOLDERS - used)
        if unused:
            problems.append(
                "it leaves out placeholders the verb fills: " + ", ".join(unused)
            )
        return tuple(problems)

    @staticmethod
    def render(template: str, card: RequestCard, sections: RequestSections) -> str:
        """The request text. Each value is inserted once, so a brace inside a section stays as the caller wrote it."""
        return template.format_map(
            {
                "card": card.text(),
                "title": sections.single_line("title"),
                "scratch": sections.single_line("scratch"),
                "problem": sections.body("problem"),
                "deliver": sections.body("deliver"),
                "decisions": sections.body("decisions"),
                "acceptance": sections.body("acceptance"),
            }
        )
