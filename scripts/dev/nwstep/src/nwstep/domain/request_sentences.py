"""A request split into numbered sentences: headings are skipped, and a sentence ends at its punctuation or its line."""

from __future__ import annotations

import re

from nwstep.domain.sentence import Sentence


class RequestSentences:
    KEY = "request_sentences"
    _BOUNDARY = re.compile(r"(?<=[.?!])\s+")

    def __init__(self, sentences: tuple[Sentence, ...]) -> None:
        self.sentences = sentences

    @classmethod
    def from_text(cls, text: str) -> RequestSentences:
        pieces: list[str] = []
        for line in text.splitlines():
            if line.lstrip().startswith("#"):
                continue
            pieces += [piece.strip() for piece in cls._BOUNDARY.split(line)]
        numbered = tuple(
            Sentence(f"S{number}", piece)
            for number, piece in enumerate((p for p in pieces if p), start=1)
        )
        return cls(numbered)

    def find(self, identifier: str) -> Sentence | None:
        return next(
            (
                sentence
                for sentence in self.sentences
                if sentence.identifier == identifier
            ),
            None,
        )

    def to_values(self) -> list[str]:
        return [sentence.line() for sentence in self.sentences]
