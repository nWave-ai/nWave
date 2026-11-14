"""A test a mapping names must occur, as a whole word, in one of the test files the same oracle record declares.

The check reads no test grammar: a name written in a shell script, a C file or a Python module is found alike. A name
in a file the oracle does not declare is not searched, so a misspelt name or a test in an undeclared file is refused at
record time instead of after the whole delivery.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from nwstep.domain.declared_path import DeclaredPath
from nwstep.domain.symbol_text import SymbolText
from nwstep.domain.test_name import TestName


class DeclaredTestNames:
    @staticmethod
    def absent(
        root: Path, declared: Iterable[str], items: Iterable[str]
    ) -> tuple[str, ...]:
        """The names the items map that no declared file mentions, in the order of the items."""
        texts = [
            (root / DeclaredPath.parse(path).text).read_text(encoding="utf-8")
            for path in declared
        ]
        return tuple(
            name.text
            for name in (TestName.of(item) for item in items)
            if not any(SymbolText.mentions(text, name.key) for text in texts)
        )
