"""Decides the text of REQUEST.md. Every refusal is decided here, before anything is written, so a refused request writes nothing."""

from __future__ import annotations

from pathlib import Path

from nwexpress.application.how_line import HowLine
from nwexpress.application.request_example import RequestExample
from nwexpress.domain.refusal import Refusal
from nwexpress.domain.request_card import RequestCard
from nwexpress.domain.request_document import RequestDocument
from nwexpress.domain.request_sections import RequestSections


class RequestWriter:
    def __init__(self, how: HowLine) -> None:
        self._how = how

    def plan(  # noqa: PLR0913
        self,
        *,
        card: str | None,
        sections: RequestSections,
        template: str,
        request_path: str,
        request_exists: bool,
        force: bool,
    ) -> str:
        """The text of REQUEST.md, or the refusal that stops it. Pure: it reads and writes nothing."""
        example = RequestExample.command(
            self._how, str(Path(request_path).parent), stdin=None
        )
        missing = (("card",) if card is None else ()) + sections.missing()
        if missing:
            raise Refusal(
                what=f"the request is missing its {', '.join(missing)}",
                why="the board links a delivery to its cards only through the first line of REQUEST.md, and the executor cannot start without the other parts, so the verb writes nothing when one is missing",
                how=example,
            )
        parsed = RequestCard.parse(card or "")
        if parsed is None:
            raise Refusal(
                what=f"--card names {card!r}, which the board does not read",
                why="the board reads a card only when its id is t- followed by four or more digits, and several ids are separated by a comma",
                how=f"write each id as t-NNNN, for example --card t-0556: {example}",
            )
        if not sections.title_is_one_line():
            raise Refusal(
                what="--title holds more than one line",
                why="the title is the heading of the request, and a heading is one line",
                how=f"give the title on one line: {example}",
            )
        problems = RequestDocument.template_problems(template)
        if problems:
            raise Refusal(
                what="the standing-block template does not fit the request: "
                + "; ".join(problems),
                why="the standing rules of every request come from the one template file, and the verb fills only the placeholders it names",
                how="restore templates/request.md in the nwexpress checkout",
            )
        if request_exists and not force:
            raise Refusal(
                what=f"{request_path} already holds a request",
                why="a request is replaced only on purpose, so an earlier request is never lost by accident",
                how=f"add --force to replace it: {example} --force",
            )
        return RequestDocument.render(template, parsed, sections)
