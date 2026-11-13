"""One command value: exactly one invocation, as the program receives it when no shell reads it.

A command field runs its argument list directly, with no shell. A shell operator outside quotes would therefore reach the
program as an argument and the check would not run as written; a dollar sign or backtick outside single quotes would reach
it as text where a shell would have expanded it. The value is refused here, before anything runs.
Not covered: parentheses, glob patterns, tilde and a leading hash are not operators here; they reach the program as written.
"""

from __future__ import annotations

import shlex
from dataclasses import dataclass


CHAIN_OPERATORS = frozenset("&|;<>\n")
EXPANSION_OPERATORS = frozenset("$`")
TWO_CHARACTER_OPERATORS = frozenset({"&&", "||", ">>", "<<"})


@dataclass(frozen=True)
class Operator:
    """A shell operator found in a value: its text as written and the position where it starts."""

    text: str
    position: int

    @property
    def expands(self) -> bool:
        return self.text in EXPANSION_OPERATORS


class UnquotedOperator(ValueError):
    """Raised by CommandLine.parse for a value that a shell would act on; it names the operator."""

    def __init__(self, operator: Operator) -> None:
        super().__init__(operator.text)
        self.operator = operator


class OperatorScan:
    """Walks one value once, tracking whether the position is inside single or double quotes.

    Inside double quotes a backslash escapes only a double quote or a backslash, as shlex reads it, so an escaped
    dollar sign is still an expansion and is found. With expansions=False a dollar sign or backtick is ordinary text,
    which locates the first chain operator of a value whose expansions are read literally.
    """

    def __init__(self, raw: str, *, expansions: bool = True) -> None:
        self._raw = raw
        self._index = 0
        self._quote: str | None = None
        self._expansions = expansions

    def first(self) -> Operator | None:
        while self._index < len(self._raw):
            found = self._visit()
            if found is not None:
                return found
            self._index += 1
        return None

    def _visit(self) -> Operator | None:
        if self._quote == "'":
            self._close_single()
            return None
        if self._quote == '"':
            return self._inside_double()
        return self._outside()

    def _close_single(self) -> None:
        if self._char() == "'":
            self._quote = None

    def _inside_double(self) -> Operator | None:
        if self._char() == "\\" and self._next() in ('"', "\\"):
            self._index += 1
            return None
        if self._char() == '"':
            self._quote = None
            return None
        if self._expands_here():
            return self._here(self._char())
        return None

    def _outside(self) -> Operator | None:
        if self._char() == "\\":
            self._index += 1
            return None
        if self._char() in "'\"":
            self._quote = self._char()
            return None
        if self._pair() in TWO_CHARACTER_OPERATORS:
            return self._here(self._pair())
        if self._char() in CHAIN_OPERATORS:
            return self._here(self._char())
        if self._expands_here():
            return self._here(self._char())
        return None

    def _expands_here(self) -> bool:
        return self._expansions and self._char() in EXPANSION_OPERATORS

    def _char(self) -> str:
        return self._raw[self._index]

    def _next(self) -> str:
        return self._raw[self._index + 1 : self._index + 2]

    def _pair(self) -> str:
        return self._raw[self._index : self._index + 2]

    def _here(self, text: str) -> Operator:
        return Operator(text, self._index)


@dataclass(frozen=True)
class CommandLine:
    """The argument list of one invocation. Only parse builds it, so a held value has no operator outside quotes."""

    argv: tuple[str, ...]

    @classmethod
    def parse(cls, raw: str) -> CommandLine:
        operator = OperatorScan(raw).first()
        if operator is not None:
            raise UnquotedOperator(operator)
        return cls(tuple(shlex.split(raw)))

    @staticmethod
    def first_invocation(raw: str) -> str | None:
        """A runnable repair line: the words before the first chain operator, each read as the program would receive it.

        A dollar sign or backtick in those words stays text, so the repair line names the value as written and runs.
        None when the value has no word before its first chain operator, or cannot be split at all.
        """
        chain = OperatorScan(raw, expansions=False).first()
        end = len(raw) if chain is None else chain.position
        try:
            words = shlex.split(raw[:end])
        except ValueError:
            return None
        return shlex.join(words) if words else None
