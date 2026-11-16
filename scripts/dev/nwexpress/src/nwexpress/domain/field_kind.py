"""The closed set of input kinds a schema field may declare."""

from __future__ import annotations

from enum import Enum


class FieldKind(Enum):
    TEXT = "text"
    LIST = "list"
    ENUM = "enum"
    INT = "int"
    BOOL = "bool"
    PATHS = "paths"
    COMMAND = "command"
    CASES = "cases"
    SCENARIOS = "scenarios"
    CONFLICTS = "conflicts"
    TYPESAFE = "typesafe"

    @property
    def is_multi(self) -> bool:
        """Multi-valued kinds are given with repeated --item NAME=VALUE."""
        return self in (
            FieldKind.LIST,
            FieldKind.PATHS,
            FieldKind.CASES,
            FieldKind.SCENARIOS,
            FieldKind.CONFLICTS,
        )
