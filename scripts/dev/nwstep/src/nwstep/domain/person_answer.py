"""A pause the interactive mode asks of the person, and the person's answer to it. An answer answers exactly the
pause after one journal record, and keeps the text and the id of the person who gave it."""

from __future__ import annotations

from typing import Any

from nwstep.domain.refusal import Refusal


class Pause:
    """The question the person must answer before the next step of the delivery is recorded."""

    def __init__(self, after_seq: int, after_step: str, question: str) -> None:
        self.after_seq = after_seq
        self.after_step = after_step
        self.question = question

    @classmethod
    def after(cls, seq: int, step: str, next_step: str | None) -> Pause:
        destination = (
            f"'{next_step}' can start"
            if next_step is not None
            else "the delivery can close"
        )
        return cls(seq, step, f"Accept the result of '{step}' so that {destination}?")


class PersonAnswer:
    """The reply of one person to one pause: the text as given and the id of the person who gave it."""

    def __init__(
        self,
        after_seq: int,
        after_step: str,
        question: str,
        author: str,
        text: str,
    ) -> None:
        self.after_seq = after_seq
        self.after_step = after_step
        self.question = question
        self.author = author
        self.text = text

    @classmethod
    def for_pause(cls, pause: Pause, author: str, text: str) -> PersonAnswer:
        if not author.strip():
            raise Refusal(
                what="the answer names no author",
                why="an answer keeps the id of the person who gave it, so the record says who decided",
                how="give --author with the id of the person who answers",
            )
        if not text.strip():
            raise Refusal(
                what="the answer text is empty",
                why="an answer keeps the words the person gave; an empty answer decides nothing",
                how="give --text with the words of the answer",
            )
        return cls(
            pause.after_seq,
            pause.after_step,
            pause.question,
            author.strip(),
            text.strip(),
        )

    def answers(self, pause: Pause) -> bool:
        return self.after_seq == pause.after_seq

    def to_dict(self) -> dict[str, Any]:
        return {
            "after_seq": self.after_seq,
            "after_step": self.after_step,
            "question": self.question,
            "author": self.author,
            "text": self.text,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PersonAnswer:
        return cls(
            int(data["after_seq"]),
            str(data["after_step"]),
            str(data["question"]),
            str(data["author"]),
            str(data["text"]),
        )
