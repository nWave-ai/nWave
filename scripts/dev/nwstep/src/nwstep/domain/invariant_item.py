"""One design invariant: 'INV id | text | witness=PATH:SYMBOL | bypass=text or none', or 'INV0 | none: reason'."""

from __future__ import annotations

import re

from nwstep.domain.contract_text import ContractText


class InvariantItem:
    SHAPE = "INV id | invariant text | witness=PATH:SYMBOL | bypass=text or none"
    NONE_ID = "INV0"
    _ID = re.compile(r"INV\d+")
    _SYMBOL = re.compile(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*")

    def __init__(
        self,
        identifier: str,
        text: str | None,
        witness_path: str | None,
        witness_symbol: str | None,
        bypass: str | None,
        none_reason: str | None,
    ) -> None:
        self.identifier = identifier
        self.text = text
        self.witness_path = witness_path
        self.witness_symbol = witness_symbol
        self.bypass = bypass
        self.none_reason = none_reason

    @classmethod
    def parse(cls, item: str) -> InvariantItem:
        reason = ContractText.none_reason(item, cls.NONE_ID)
        if reason is not None:
            return cls(cls.NONE_ID, None, None, None, None, reason)
        identifier = item.split("|", 1)[0].strip()
        if not cls._ID.fullmatch(identifier):
            raise ValueError(f"the id must be INV followed by a number; {cls.SHAPE}")
        identifier, text, witness, bypass = ContractText.parts(item, 4, cls.SHAPE)
        value = ContractText.keyed(witness, "witness")
        path, separator, symbol = value.partition(":")
        if (
            not separator
            or not path.strip()
            or not cls._SYMBOL.fullmatch(symbol.strip())
        ):
            raise ValueError("the witness is written 'witness=PATH:SYMBOL'")
        return cls(
            identifier,
            text,
            path.strip(),
            symbol.strip(),
            ContractText.keyed(bypass, "bypass"),
            None,
        )
