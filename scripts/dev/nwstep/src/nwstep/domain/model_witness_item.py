"""One formal-model invariant: 'INV id | model invariant name | witness=PATH:SYMBOL'."""

from __future__ import annotations

import re

from nwstep.domain.contract_text import ContractText


class ModelWitnessItem:
    SHAPE = "INV id | model invariant name | witness=PATH:SYMBOL"
    _ID = re.compile(r"INV\d+")
    _SYMBOL = re.compile(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*")

    def __init__(
        self, identifier: str, name: str, witness_path: str, witness_symbol: str
    ) -> None:
        self.identifier = identifier
        self.name = name
        self.witness_path = witness_path
        self.witness_symbol = witness_symbol

    @classmethod
    def parse(cls, item: str) -> ModelWitnessItem:
        identifier, name, witness = ContractText.parts(item, 3, cls.SHAPE)
        if not cls._ID.fullmatch(identifier):
            raise ValueError(f"the id must be INV followed by a number; {cls.SHAPE}")
        value = ContractText.keyed(witness, "witness")
        path, separator, symbol = value.partition(":")
        if (
            not separator
            or not path.strip()
            or not cls._SYMBOL.fullmatch(symbol.strip())
        ):
            raise ValueError("the witness is written 'witness=PATH:SYMBOL'")
        return cls(identifier, name, path.strip(), symbol.strip())
