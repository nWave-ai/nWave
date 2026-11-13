"""A text template bound in one pass: every placeholder is declared, has a value and a known filter, or the render is refused."""

from __future__ import annotations

import re
from collections.abc import Mapping

from nwstep.domain.refusal import Refusal

Value = str | tuple[str, ...] | None


class Template:
    CSV = "csv"
    FILTERS = (CSV,)
    CSV_SEPARATOR = ", "
    _TOKEN = re.compile(r"\{\{(.*?)\}\}", re.DOTALL)
    _GRAMMAR = re.compile(r"\s*([A-Za-z_]\w*)\s*(?:\|\s*([A-Za-z_]\w*)\s*)?")

    def __init__(self, text: str) -> None:
        self._text = text

    def render(
        self, values: Mapping[str, Value], declared: frozenset[str], how: str
    ) -> str:
        """Fill every placeholder from values once. A filled value is never read again for placeholders."""
        pieces: list[str] = []
        cursor = 0
        for token in self._TOKEN.finditer(self._text):
            literal = self._text[cursor : token.start()]
            self._refuse_stray_delimiters(literal, how)
            pieces.append(literal)
            pieces.append(
                self._fill(token.group(0), token.group(1), values, declared, how)
            )
            cursor = token.end()
        tail = self._text[cursor:]
        self._refuse_stray_delimiters(tail, how)
        pieces.append(tail)
        return "".join(pieces)

    def _fill(
        self,
        token: str,
        inner: str,
        values: Mapping[str, Value],
        declared: frozenset[str],
        how: str,
    ) -> str:
        grammar = self._GRAMMAR.fullmatch(inner)
        if grammar is None:
            raise self._refusal(
                f"unknown placeholder '{token}'",
                "a placeholder is one declared name, optionally followed by '|' and a filter",
                how,
            )
        name, filter_name = grammar.group(1), grammar.group(2)
        if name not in declared:
            raise self._refusal(
                f"unknown placeholder '{name}'",
                f"the prompt binds only: {', '.join(sorted(declared))}",
                how,
            )
        if filter_name is not None and filter_name not in self.FILTERS:
            raise self._refusal(
                f"unknown filter '{filter_name}' on '{name}'",
                f"the known filters are: {', '.join(self.FILTERS)}",
                how,
            )
        value = values.get(name)
        if value is None:
            raise self._refusal(
                f"placeholder '{name}' is declared but has no value",
                "every declared placeholder is bound before the template is filled",
                how,
            )
        if isinstance(value, tuple):
            if filter_name != self.CSV:
                raise self._refusal(
                    f"'{name}' is a list; write {{{{{name}|csv}}}}",
                    "a list placeholder needs a filter that turns it into text",
                    how,
                )
            return self.CSV_SEPARATOR.join(value)
        if filter_name == self.CSV:
            raise self._refusal(
                f"filter 'csv' applies to a list; '{name}' is text",
                "csv turns a list of items into text and text has no items",
                how,
            )
        return value

    def _refuse_stray_delimiters(self, literal: str, how: str) -> None:
        if "}}" in literal:
            raise self._refusal(
                "stray '}}' in the template",
                "a closing delimiter without an opening one would be printed as text",
                how,
            )
        if "{{" in literal:
            raise self._refusal(
                "unclosed placeholder '{{' in the template",
                "every '{{' must close with '}}' on the same placeholder",
                how,
            )

    @staticmethod
    def _refusal(what: str, why: str, how: str) -> Refusal:
        return Refusal(what=what, why=why, how=how)
