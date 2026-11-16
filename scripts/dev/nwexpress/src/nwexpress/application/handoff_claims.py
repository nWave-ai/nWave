"""Checks the handoff summary's sentences against the committed change from BASE to HEAD.

A sentence that states a guarantee (every, never, shows, holds, ...) must name a test of the change: a test the oracle
mapped to a promise and whose name occurs as a whole word in a declared test file the change contains. A backticked
file must be changed from BASE to HEAD, and a backticked symbol must occur as a whole word in the text of a changed
file. A sentence that fails either rule is not shown as a claim: it goes to the 'not backed' list with its reasons.
Without a readable change, nothing is checked and the report says so.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from nwexpress.domain.baseline import Baseline
from nwexpress.domain.symbol_text import SymbolText
from nwexpress.domain.test_name import TestName
from nwexpress.infrastructure.git_diff import GitDiff, GitDiffError


@dataclass(frozen=True)
class ClaimsReport:
    verified: bool
    reason: str | None
    backed: tuple[str, ...]
    not_backed: tuple[tuple[str, str], ...]


class HandoffClaims:
    GUARANTEE = re.compile(
        r"\b(all|every|each|none|never|always|only|must|holds?|guarantees?|shows?|keeps?|refuses?|rejects?|exactly|no)\b",
        re.IGNORECASE,
    )
    CODE = re.compile(r"`([^`]+)`")
    SYMBOL = re.compile(r"[A-Za-z_][\w.]*\(?\)?")
    SENTENCE_END = re.compile(r"(?<=[.!?])\s+")

    def __init__(
        self,
        baseline: Baseline,
        mapped: Iterable[str] = (),
        declared: Iterable[str] = (),
    ) -> None:
        self._baseline = baseline
        self._mapped = tuple(dict.fromkeys(TestName.of(item).key for item in mapped))
        self._declared = tuple(declared)

    def judge(self, text: str) -> ClaimsReport:
        sentences = self.split(text)
        if not self._baseline.is_available or self._baseline.top is None:
            return ClaimsReport(False, self._baseline.reason or "no baseline", (), ())
        try:
            diff = GitDiff(
                str(self._baseline.top), str(self._baseline.sha), working=False
            )
            changed = diff.names()
            tests, symbols = self._facts(diff, changed)
        except GitDiffError as error:
            return ClaimsReport(False, str(error), (), ())
        backed: list[str] = []
        not_backed: list[tuple[str, str]] = []
        for sentence in sentences:
            reasons = self._reasons(sentence, changed, tests, symbols)
            if reasons:
                not_backed.append((sentence, "; ".join(reasons)))
            else:
                backed.append(sentence)
        return ClaimsReport(True, None, tuple(backed), tuple(not_backed))

    def split(self, text: str) -> list[str]:
        return [
            part.strip()
            for part in self.SENTENCE_END.split(text.strip())
            if part.strip()
        ]

    def _facts(
        self, diff: GitDiff, changed: frozenset[str]
    ) -> tuple[frozenset[str], frozenset[str]]:
        """The tests of the change (mapped names found in the declared files) and the words the changed files hold."""
        declared_texts = [
            text
            for path in self._declared
            if path in changed and (text := diff.text(path)) is not None
        ]
        tests = frozenset(
            name
            for name in self._mapped
            if any(SymbolText.mentions(text, name) for text in declared_texts)
        )
        symbols: set[str] = set()
        for path in sorted(changed):
            source = diff.text(path)
            if source is not None:
                symbols |= SymbolText.identifiers(source)
        return tests, frozenset(symbols)

    def _reasons(
        self,
        sentence: str,
        changed: frozenset[str],
        tests: frozenset[str],
        symbols: frozenset[str],
    ) -> list[str]:
        reasons: list[str] = []
        for token in self.CODE.findall(sentence):
            if "/" in token:
                if token.removeprefix("./") not in changed:
                    reasons.append(f"file `{token}` is not changed from BASE to HEAD")
            elif self.SYMBOL.fullmatch(token):
                name = token.rstrip("()").split(".")[-1]
                if name not in symbols and name not in tests:
                    reasons.append(f"symbol `{token}` is not defined in the change")
        if self.GUARANTEE.search(sentence) and not any(
            SymbolText.mentions(sentence, name) for name in tests
        ):
            reasons.append("a guarantee names no test of the change")
        return reasons
