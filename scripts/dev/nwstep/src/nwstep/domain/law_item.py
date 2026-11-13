"""One oracle law: 'LAW id | law text | generator=TEST_ID | observation=TEXT | mutant=TEXT', or 'LAW0 | none: reason'.

A generator written as a pytest node id ('tests/test_x.py::test_y') is read as its test name: the name is what the
tool checks against the change, so the path form is accepted rather than refused.
"""

from __future__ import annotations

import re

from nwstep.domain.contract_text import ContractText


class LawItem:
    SHAPE = "LAW id | law text | generator=TEST_ID | observation=TEXT | mutant=TEXT"
    NONE_ID = "LAW0"
    _ID = re.compile(r"LAW\d+")
    _TEST = re.compile(r"[A-Za-z_]\w*")

    def __init__(
        self,
        identifier: str,
        generator: str | None,
        none_reason: str | None,
    ) -> None:
        self.identifier = identifier
        self.generator = generator
        self.none_reason = none_reason

    @classmethod
    def parse(cls, item: str) -> LawItem:
        reason = ContractText.none_reason(item, cls.NONE_ID)
        if reason is not None:
            return cls(cls.NONE_ID, None, reason)
        identifier = item.split("|", 1)[0].strip()
        if not cls._ID.fullmatch(identifier):
            raise ValueError(f"the id must be LAW followed by a number; {cls.SHAPE}")
        identifier, _text, generator, observation, mutant = ContractText.parts(
            item, 5, cls.SHAPE
        )
        ContractText.keyed(observation, "observation")
        ContractText.keyed(mutant, "mutant")
        test = ContractText.keyed(generator, "generator").rsplit("::", 1)[-1].strip()
        if not cls._TEST.fullmatch(test):
            raise ValueError(
                "the generator is a test function name, written 'generator=TEST_ID'"
            )
        return cls(identifier, test, None)
