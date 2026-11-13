"""One message of an edge matrix: 'MSG id | input | what | why | how | test=TEST_ID', or 'MSG0 | none: reason'."""

from __future__ import annotations

import re

from nwstep.domain.contract_text import ContractText


class MessageItem:
    SHAPE = "MSG id | input | what | why | how | test=TEST_ID"
    NONE_ID = "MSG0"
    _ID = re.compile(r"MSG\d+")
    _TEST = re.compile(r"[A-Za-z_]\w*")

    def __init__(
        self, identifier: str, test: str | None, none_reason: str | None
    ) -> None:
        self.identifier = identifier
        self.test = test
        self.none_reason = none_reason

    @classmethod
    def parse(cls, item: str) -> MessageItem:
        reason = ContractText.none_reason(item, cls.NONE_ID)
        if reason is not None:
            return cls(cls.NONE_ID, None, reason)
        identifier = item.split("|", 1)[0].strip()
        if not cls._ID.fullmatch(identifier):
            raise ValueError(f"the id must be MSG followed by a number; {cls.SHAPE}")
        parts = ContractText.parts(item, 6, cls.SHAPE)
        test = ContractText.keyed(parts[5], "test")
        if not cls._TEST.fullmatch(test):
            raise ValueError("the test is a test function name, written 'test=TEST_ID'")
        return cls(parts[0], test, None)
