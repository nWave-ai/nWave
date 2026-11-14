"""The name a promise maps to a test, and the report cases that name selects.

A runner names a testcase with its module, class or suite before the test (a path, a double colon, a dot) and may add a
parameter suffix in brackets or parentheses. A report case is a candidate for a mapped name when its last segment, with
the parameter suffix removed, is the mapped name's last segment, so the same test is found whichever prefix the runner
uses.

A mapped name may carry a qualifier: the text before its last segment, such as 'french::' or 'tests/test_x.py::'. It
reaches a candidate only when the two qualifiers share a word, a run of letters, digits and underscores, so a path such as
tests/test_x.py shares its words with the dotted module tests.test_x. A candidate of any other qualifier is another test,
and the name does not reach it. A bare name has no qualifier and never narrows its candidates: several are returned, and
the caller refuses them as ambiguous. A qualified name narrows the compatible candidates to the one it writes in full,
when exactly one does; otherwise they are all returned and the caller refuses them as ambiguous.

The name never picks one of several cases. Two qualifiers that share a word are not told apart: 'tests.french' and
'french.english' share 'french', so a mapping of one reaches the other.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from nwstep.domain.report_case import ReportCase

_PARAMETERS = re.compile(r"(\[[^\[\]]*\]|\([^()]*\))\s*$")
_SEGMENT = re.compile(r"::|[./#\s]")
_WORD = re.compile(r"[A-Za-z0-9_]+")


def _bare(text: str) -> str:
    return _PARAMETERS.sub("", text.strip()).strip()


def _last_segment(text: str) -> str:
    bare = _bare(text)
    return _SEGMENT.split(bare)[-1] if bare else ""


def _qualifier_words(text: str) -> frozenset[str]:
    """The words before the last segment of a name, with its parameter suffix removed."""
    bare = _bare(text)
    last = _last_segment(text)
    return frozenset(_WORD.findall(bare[: len(bare) - len(last)] if last else ""))


def _case_words(case: ReportCase) -> frozenset[str]:
    """The words of the class, module or suite a case sits in, and of any qualifier its own name carries."""
    return frozenset(_WORD.findall(case.classname)) | _qualifier_words(case.name)


@dataclass(frozen=True)
class TestName:
    text: str

    @classmethod
    def of(cls, item: str) -> TestName:
        """The test a mapping item names: the text after '=>', or the whole item when it has no arrow."""
        text = item.partition("=>")[2] if "=>" in item else item
        return cls(text.strip())

    @staticmethod
    def key_of(reported: str) -> str:
        """The segment a reported testcase name ends in, with its parameter suffix removed."""
        return _last_segment(reported)

    @property
    def key(self) -> str:
        return self.key_of(self.text)

    @property
    def qualifier(self) -> frozenset[str]:
        return _qualifier_words(self.text)

    def matches(self, reported: str) -> bool:
        return bool(self.key) and self.key_of(reported) == self.key

    def key_matches(self, cases: tuple[ReportCase, ...]) -> tuple[ReportCase, ...]:
        """Every case whose last segment is this name's last segment, whatever its qualifier."""
        return tuple(case for case in cases if self.matches(case.name))

    def select(self, cases: tuple[ReportCase, ...]) -> tuple[ReportCase, ...]:
        """The cases this name means: none when no candidate shares its qualifier, one when exactly one is written in full."""
        candidates = self.key_matches(cases)
        if self.qualifier:
            candidates = tuple(
                case for case in candidates if self.qualifier & _case_words(case)
            )
            if len(candidates) <= 1:
                return candidates
            return self._written(candidates)
        if len(candidates) <= 1 or self.text == self.key:
            return candidates
        if any(_case_words(case) for case in candidates):
            return candidates
        return self._written(candidates)

    def _written(self, candidates: tuple[ReportCase, ...]) -> tuple[ReportCase, ...]:
        written = tuple(
            case for case in candidates if self.text in (case.name, case.full_name)
        )
        return written if len(written) == 1 else candidates
