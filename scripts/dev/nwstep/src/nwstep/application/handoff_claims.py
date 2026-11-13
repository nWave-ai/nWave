"""Checks the handoff summary's sentences against the committed change from BASE to HEAD.

A sentence that states a guarantee (every, never, shows, holds, ...) must name a test function of the change: a
guarantee with no named test has no evidence in the diff. A backticked file must be changed from BASE to HEAD and a
backticked symbol must be defined in the change. A sentence that fails either rule is not shown as a claim: it goes
to the 'not backed' list with its reasons. Without a readable change, nothing is checked and the report says so.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from nwstep.domain.baseline import Baseline
from nwstep.domain.definitions import Definitions
from nwstep.infrastructure.git_diff import GitDiff, GitDiffError


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
    NAME = re.compile(r"[A-Za-z_]\w*")
    SYMBOL = re.compile(r"[A-Za-z_][\w.]*\(?\)?")
    SENTENCE_END = re.compile(r"(?<=[.!?])\s+")

    def __init__(self, baseline: Baseline) -> None:
        self._baseline = baseline

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
        tests: set[str] = set()
        symbols: set[str] = set()
        for path in sorted(name for name in changed if name.endswith(".py")):
            source = diff.text(path)
            if source is None:
                continue
            try:
                definitions = Definitions(source)
            except ValueError:
                continue
            symbols |= definitions.names()
            if self._is_test_file(path):
                tests |= {
                    name for name in definitions.functions() if name.startswith("test")
                }
        return frozenset(tests), frozenset(symbols)

    def _reasons(
        self,
        sentence: str,
        changed: frozenset[str],
        tests: frozenset[str],
        symbols: frozenset[str],
    ) -> list[str]:
        reasons: list[str] = []
        for token in self.CODE.findall(sentence):
            if "/" in token or token.endswith(".py"):
                if token.removeprefix("./") not in changed:
                    reasons.append(f"file `{token}` is not changed from BASE to HEAD")
            elif self.SYMBOL.fullmatch(token):
                name = token.rstrip("()").split(".")[-1]
                if name not in symbols and name not in tests:
                    reasons.append(f"symbol `{token}` is not defined in the change")
        if self.GUARANTEE.search(sentence) and not (
            set(self.NAME.findall(sentence)) & tests
        ):
            reasons.append("a guarantee names no test function of the change")
        return reasons

    @staticmethod
    def _is_test_file(path: str) -> bool:
        return (
            path.rsplit("/", 1)[-1].startswith("test_")
            or "tests" in path.split("/")[:-1]
        )
