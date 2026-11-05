"""The role asks of the design record, parsed and checked against the schema shape.

Pure: the shell reads policy.toml and passes its text here with the shape of the record
members; this module returns a Policy value or the refusal of every construction gap at once.
"""

from __future__ import annotations

import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from functools import partial

from nwdes.contracts import Defect, checked


COVERS = ("target", "design", "slice")
_TABLES = ("member", "role")
_MEMBER_FIELDS = ("cover", "ask", "shape", "example", "minimum")
_TEXT_FIELDS = ("ask", "shape", "example")


@dataclass(frozen=True)
class Member:
    """One record member the policy asks for: its cover, ask sentence, shape line and example."""

    name: str
    cover: str
    ask: str
    shape: str
    example: str
    minimum: int = 0


@dataclass(frozen=True)
class Policy:
    """The members in file order, and the members each role is asked for, in file order."""

    members: Mapping[str, Member]
    asks: Mapping[str, tuple[str, ...]]

    def covering(self, cover: str) -> tuple[Member, ...]:
        return tuple(
            member for member in self.members.values() if member.cover == cover
        )


@dataclass(frozen=True)
class RecordShape:
    """The record shape a policy is checked against: each member's verb and list flags, and the analyses."""

    members: Mapping[str, tuple[bool, bool]]
    analyses: tuple = ()
    slice_members: tuple = ()

    def takes_verb(self, name):
        return self.members[name][0]

    def is_record_array(self, name):
        return self.members[name][1]

    def is_slice_member(self, name):
        return name in self.slice_members


@dataclass(frozen=True)
class _Entry:
    """One named table of policy.toml: its kind (member or role), its name and its contents."""

    kind: str
    name: str
    table: object

    @property
    def path(self):
        return f"{self.kind}.{self.name}"


def _defect(path, why, how):
    # Three facts per defect (where, what, how), the same three that Defect carries.
    return Defect("PartInvalid: policy.toml " + path, why, how)


def _is_text(value):
    return isinstance(value, str) and bool(value.strip())


def _is_name_list(value):
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _unknown_keys(entry, allowed):
    return sorted(set(entry.table) - set(allowed))


def _not_a_member_defect(entry):
    return _defect(
        entry.path,
        f"{entry.name!r} is not a record member of the design shape, so no role can be asked for it.",
        "Name a record member declared in nwdes RECORDS, or remove this table.",
    )


def _no_verb_defect(entry):
    return _defect(
        entry.path,
        f"{entry.name!r} has no recording verb, so a role cannot be asked to supply it.",
        "Remove this table, or ask only for members that have a recording verb.",
    )


def _shape_refusal(entry, shape):
    if entry.name not in shape.members:
        return (_not_a_member_defect(entry),)
    if not shape.takes_verb(entry.name):
        return (_no_verb_defect(entry),)
    return ()


def _cover_value_defect(entry):
    cover = entry.table["cover"]
    return _defect(
        entry.path + ".cover",
        f"cover {cover!r} is not one of {', '.join(COVERS)}.",
        "Set cover to target, design or slice, or remove it.",
    )


def _cover_value_defects(entry):
    return () if entry.table["cover"] in COVERS else (_cover_value_defect(entry),)


def _cover_analysis_defects(entry, shape):
    if entry.name in shape.analyses:
        return ()
    return (
        _defect(
            entry.path + ".cover",
            f"{entry.name!r} is not an analysis of the not-applicable enum, so no reasoned not-applicable can record it.",
            "Declare cover only on an analysis the record shape enumerates.",
        ),
    )


def _holds_records(entry, shape):
    if entry.table.get("cover") == "slice":
        return shape.is_slice_member(entry.name)
    return shape.is_record_array(entry.name)


def _cover_record_defects(entry, shape):
    if _holds_records(entry, shape):
        return ()
    if entry.table.get("cover") == "slice":
        return (
            _defect(
                entry.path + ".cover",
                f"{entry.name!r} is not a record each slice holds once, so no slice can cover it.",
                "Declare cover slice only on a member that a slice holds as one record.",
            ),
        )
    return (
        _defect(
            entry.path + ".cover",
            f"{entry.name!r} is not a list of records, so no row can cover a target or a design.",
            "Declare cover only on a list of records.",
        ),
    )


def _cover_defects(entry, shape):
    if not entry.table.get("cover", ""):
        return ()
    return (
        *_cover_value_defects(entry),
        *_cover_analysis_defects(entry, shape),
        *_cover_record_defects(entry, shape),
    )


def _text_problem(entry, key):
    return _defect(
        f"{entry.path}.{key}",
        "A policy entry states this value as non-empty text.",
        f"Write {key} as a non-empty string in src/nwdes/policy.toml.",
    )


def _text_defects(entry):
    return tuple(
        _text_problem(entry, key)
        for key in _TEXT_FIELDS
        if not _is_text(entry.table.get(key))
    )


def _minimum_defect(entry):
    return _defect(
        entry.path + ".minimum",
        "minimum is a whole number of items, zero or more.",
        "Write minimum = 1 for an item the record must hold, or remove it.",
    )


def _minimum_defects(entry):
    minimum = entry.table.get("minimum", 0)
    valid = type(minimum) is int and minimum >= 0
    return () if valid else (_minimum_defect(entry),)


def _unknown_member_defects(entry):
    return tuple(
        _defect(
            f"{entry.path}.{key}",
            "The policy holds only cover, ask, shape, example and minimum for a member.",
            "Remove the key from src/nwdes/policy.toml.",
        )
        for key in _unknown_keys(entry, _MEMBER_FIELDS)
    )


def _built_member(entry):
    table = entry.table
    return Member(
        entry.name,
        table.get("cover", ""),
        table["ask"],
        table["shape"],
        table["example"],
        table.get("minimum", 0),
    )


def _field_defects(entry, shape):
    return (
        *_cover_defects(entry, shape),
        *_text_defects(entry),
        *_minimum_defects(entry),
        *_unknown_member_defects(entry),
    )


def _member(entry, shape):
    """One [member] table: the record shape gates it, then each field is checked in turn."""
    refusal = _shape_refusal(entry, shape)
    if refusal:
        return None, refusal
    defects = _field_defects(entry, shape)
    if defects:
        return None, defects
    return _built_member(entry), ()


def _duplicate_ask_defects(entry):
    asks = entry.table["asks"]
    return tuple(
        _defect(
            entry.path + ".asks",
            f"{item!r} is listed twice for this role.",
            "List each asked member once.",
        )
        for item in sorted({item for item in asks if asks.count(item) > 1})
    )


def _undeclared_ask_defects(entry, members):
    return tuple(
        _defect(
            entry.path + ".asks",
            f"{item!r} is not a member declared in this file.",
            "Declare the member under [member.NAME] or remove it from asks.",
        )
        for item in entry.table["asks"]
        if item not in members
    )


def _unknown_role_defects(entry):
    return tuple(
        _defect(
            f"{entry.path}.{key}",
            "A role table holds only asks.",
            "Remove the key from src/nwdes/policy.toml.",
        )
        for key in _unknown_keys(entry, ("asks",))
    )


def _asks_not_list_defect(entry):
    return _defect(
        entry.path + ".asks",
        "asks is a list of member names.",
        'Write asks = ["member", ...] naming members declared in this file.',
    )


def _ask_defects(entry, members):
    return (
        *_duplicate_ask_defects(entry),
        *_undeclared_ask_defects(entry, members),
        *_unknown_role_defects(entry),
    )


def _role(entry, members):
    """One [role] table: its asks name declared members, each once, and nothing else."""
    if not _is_name_list(entry.table.get("asks")):
        return None, (_asks_not_list_defect(entry),)
    defects = _ask_defects(entry, members)
    if defects:
        return None, defects
    return tuple(entry.table["asks"]), ()


def _table_defects(data):
    return tuple(
        _defect(
            key,
            "Only [member.*] and [role.*] tables are declared.",
            "Remove the table.",
        )
        for key in sorted(set(data) - set(_TABLES))
    )


def _entries(kind, data):
    return [_Entry(kind, name, table) for name, table in (data.get(kind) or {}).items()]


def _check_table(entry, check):
    if isinstance(entry.table, Mapping):
        return check(entry)
    return None, (
        _defect(
            entry.path, f"A {entry.kind} is a table.", f"Write [{entry.kind}.NAME]."
        ),
    )


def _check_tables(entries, check):
    """Each named table in file order: the checked values by name, and every defect in order."""
    values, defects = {}, []
    for entry in entries:
        value, problems = _check_table(entry, check)
        defects.extend(problems)
        if value is not None:
            values[entry.name] = value
    return values, defects


def _not_toml_defect(error):
    return Defect(
        "PartInvalid: policy.toml",
        "The file is not valid TOML: " + str(error),
        "Fix the syntax of src/nwdes/policy.toml.",
    )


def _checked_policy(data, shape):
    members, member_defects = _check_tables(
        _entries("member", data), partial(_member, shape=shape)
    )
    roles, role_defects = _check_tables(
        _entries("role", data), partial(_role, members=members)
    )
    defects = (*_table_defects(data), *member_defects, *role_defects)
    return Policy(members, roles), defects


def parse(
    text: str, shape: Mapping[str, tuple[bool, bool]], analyses=(), slice_members=()
):
    """Parse policy.toml against the shape {member: (has a verb, is a list of records)}."""
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        return checked(None, (_not_toml_defect(error),))
    policy, defects = _checked_policy(
        data, RecordShape(shape, analyses, tuple(slice_members))
    )
    return checked(policy, defects)
