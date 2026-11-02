"""Typed envelope schemas of the roles that answer through the canonical model envelope.

The schemas are frozen in ``role_envelope_schemas.json``: the exact output of the removed live
``_schema_for`` for each covered role and for the floor role. ``schema_for`` serves that text
unchanged, so the envelope a role answers against is byte-identical to the pre-removal installer
output. A role outside the covered set gets the universal outcome floor, never an invented
typed payload.
"""

from __future__ import annotations

import json
from pathlib import Path


_SCHEMA_FILE = Path(__file__).with_name("role_envelope_schemas.json")
_FLOOR_ROLE = "nw-acceptance-designer"

COVERED_ROLES = frozenset(
    {
        "nw-acceptance-designer-reviewer",
        "nw-functional-software-crafter",
        "nw-product-owner",
        "nw-software-crafter",
        "nw-software-crafter-reviewer",
        "nw-solution-architect",
        "nw-user-examiner",
    }
)


def _frozen_schemas() -> dict[str, object]:
    with _SCHEMA_FILE.open(encoding="utf-8") as handle:
        document = json.load(handle)
    if not isinstance(document, dict):
        raise ValueError(f"{_SCHEMA_FILE.name} must hold a JSON object of role schemas")
    return document


_SCHEMAS = _frozen_schemas()


def schema_for(role: str) -> str:
    """Compact JSON text of the envelope schema for ``role``.

    A covered role gets its own frozen schema; any other role gets the floor schema, which is
    the universal outcome envelope (accepted or refused plus a non-empty diagnostic).
    """
    key = role if role in COVERED_ROLES or role == _FLOOR_ROLE else _FLOOR_ROLE
    return json.dumps(_SCHEMAS[key], separators=(",", ":"))
