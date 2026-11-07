"""Pure brief rendering, ADR transitions, and compare-before-write plans."""

from __future__ import annotations

import json
import posixpath
import re
import string
from collections import Counter
from collections.abc import Callable, Mapping
from dataclasses import dataclass, fields, is_dataclass, replace
from enum import Enum
from functools import reduce
from html import escape
from itertools import chain, combinations, groupby, product
from types import MappingProxyType

from nwdes import handoff as model
from nwdes.contracts import Built, Defect, Refused, checked, local_path
from nwdes.destinations import DocumentKind
from nwdes.destinations import resolve as resolve_destinations


class OutputKind(str, Enum):
    Handoff = "Handoff"
    Markdown = "Markdown"
    Html = "Html"
    Adr = "Adr"


@dataclass(frozen=True)
class Output:
    kind: OutputKind
    path: str
    data: bytes


@dataclass(frozen=True)
class OutputSet:
    outputs: tuple[Output, ...]

    def __post_init__(self):
        paths = tuple(output.path for output in self.outputs)
        if len(set(paths)) != len(paths) or any(not local_path(path) for path in paths):
            raise ValueError("OutputSet requires distinct repository-relative paths")


@dataclass(frozen=True)
class Write:
    path: str
    data: bytes


@dataclass(frozen=True)
class Unchanged:
    path: str


WritePlan = tuple[Write | Unchanged, ...]


def plan_writes(outputs: OutputSet, existing: Mapping[str, bytes | None]) -> WritePlan:
    return tuple(
        Unchanged(output.path)
        if existing.get(output.path) == output.data
        else Write(output.path, output.data)
        for output in outputs.outputs
    )


def apply_plan(
    existing: Mapping[str, bytes | None], plan: WritePlan
) -> dict[str, bytes | None]:
    return {
        **existing,
        **{step.path: step.data for step in plan if isinstance(step, Write)},
    }


@dataclass(frozen=True)
class Brand:
    css: str
    logo: bytes


def normalize(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n").rstrip("\n")


_ESCAPED_PUNCTUATION = str.maketrans(
    {character: "\\" + character for character in string.punctuation}
)
_UNESCAPED_PUNCTUATION = re.compile(r"\\([" + re.escape(string.punctuation) + r"])")
_HTML_TOKENS = re.compile(
    r"^(?P<fence>`{3,})[^`\n]*\n(?P<content>[\s\S]*?)(?P=fence)$|^(?P<line>.*)$",
    re.MULTILINE,
)
_HTML_HEADING = re.compile(r"(#{1,6}) (.*)")


def escaped(text: str) -> str:
    return text if text.isalnum() else text.translate(_ESCAPED_PUNCTUATION)


def unescape(text: str) -> str:
    return _UNESCAPED_PUNCTUATION.sub(r"\1", text) if "\\" in text else text


def inline(text: str) -> str:
    if text.isalnum() or re.fullmatch(r"[A-Za-z0-9/.][A-Za-z0-9_./:-]*", text):
        return text
    marker = "`" * (
        1 + max((len(run[0]) for run in re.finditer(r"`+", text)), default=0)
    )
    padding = (
        " "
        if text.strip(" ")
        and (text.startswith(("`", " ")) or text.endswith(("`", " ")))
        else ""
    )
    return marker + padding + text + padding + marker


def _fence_marker(content):
    return (
        "`" * (1 + max(len(match[0]) for match in re.finditer(r"`+", content)))
        if "```" in content
        else "```"
    )


@dataclass(frozen=True)
class FactReference:
    identity: str
    marker: str


def fenced_exact(text: str, *, language="text") -> str:
    fence = _fence_marker(text)
    return f"{fence}{language}\n{text}\n{fence}\n"


def fenced(text: str | FactReference, *, language="text") -> str:
    """Fence free text using the canonical TEXT line-end rule."""
    if isinstance(text, FactReference):
        return text.marker + text.identity + text.marker + "\n"
    return fenced_exact(normalize(text), language=language)


def fenced_diff(text: str) -> str:
    """Retain supplied diff bytes apart from the required final line feed."""
    content = text if text.endswith("\n") else text + "\n"
    fence = _fence_marker(content)
    return f"{fence}diff\n{content}{fence}\n"


def _literal_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for key, child in value.items():
            yield key
            yield from _literal_strings(child)
    elif isinstance(value, (tuple, list)):
        for child in value:
            yield from _literal_strings(child)
    elif is_dataclass(value):
        for field in fields(value):
            yield from _literal_strings(getattr(value, field.name))


@dataclass(frozen=True)
class FactReferences:
    facts: model.Record
    marker: str

    def project(self, handoff):
        return replace(
            handoff,
            facts=model.Record(
                (identity, FactReference(identity, self.marker))
                for identity in self.facts
            ),
        )

    def expand(self, text):
        pattern = re.compile(
            re.escape(self.marker) + r"(F[1-9][0-9]*)" + re.escape(self.marker)
        )
        matches = tuple(pattern.finditer(text))
        repeated = frozenset(
            identity
            for identity, count in Counter(match[1] for match in matches).items()
            if count > 1
        )

        def append(state, match):
            parts, end, seen = state
            identity = match[1]
            printed = (
                f"[{identity}] (above)"
                if identity in seen
                else (f"[{identity}]\n" if identity in repeated else "")
                + fenced(self.facts[identity], language="").rstrip("\n")
            )
            return (
                (*parts, text[end : match.start()], printed),
                match.end(),
                seen | {identity},
            )

        parts, end, _ = reduce(append, matches, ((), 0, frozenset()))
        return "".join((*parts, text[end:]))


def fact_references(handoff, literals=()):
    """Mark only typed TEXT slots; keep literal fields and supplied evidence verbatim."""
    if any(isinstance(text, FactReference) for text in handoff.facts.values()):
        return None
    longest = max(
        (
            len(run[0])
            for text in _literal_strings((handoff, literals))
            for run in re.finditer(r"~+", text)
        ),
        default=0,
    )
    return FactReferences(handoff.facts, "~" * (longest + 2))


@dataclass(frozen=True, order=True)
class AdrKey:
    prefix: str
    number: int

    @property
    def text(self):
        return f"{self.prefix + '-' if self.prefix else ''}{self.number:03d}"


@dataclass(frozen=True)
class AdrEntry:
    key: AdrKey
    path: str
    data: bytes
    body: tuple[str, str, str, str, str] | None
    status: str
    missing: str = ""


Register = tuple[AdrEntry, ...]


@dataclass(frozen=True)
class AdrResult:
    files: Mapping[str, bytes]
    snapshot: tuple[Mapping[str, str], ...]
    register: Register


_PREFIX = model.ADR_PREFIX_PATTERN
_ADR_SECTIONS = ("Context", "Decision", "Alternatives", "Consequences")


def adr_filename(key: AdrKey) -> str:
    return f"ADR-{key.text}.md"


def parse_adr_filename(name: str) -> AdrKey | None:
    match = re.fullmatch(
        r"ADR-(?:(" + _PREFIX + r")-)?([0-9]{3,})(?:-[a-z0-9][a-z0-9-]*)?\.md", name
    )
    return (
        AdrKey(match[1] or "", int(match[2])) if match and int(match[2]) > 0 else None
    )


def _read_entry(key, path, data):
    try:
        text = data.decode("utf-8")
    except UnicodeError:
        return AdrEntry(key, path, data, None, "", "# " + key.text)
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    title = re.fullmatch(r"# (\S+) (.+)", lines[0])
    if title is None or unescape(title[1]) != key.text:
        return AdrEntry(key, path, data, None, "", "# " + key.text)
    if len(lines) < 2 or not re.fullmatch(
        rf"Status: ({model.ADR_STATUS_PATTERN})", lines[1]
    ):
        return AdrEntry(key, path, data, None, "", "Status:")
    status = lines[1][8:]

    def sections(index, names):
        if not names:
            return (
                () if not any(line.strip() for line in lines[index:]) else "end of file"
            )
        start = next(
            (
                position
                for position in range(index, len(lines))
                if lines[position].strip()
            ),
            len(lines),
        )
        heading = "## " + names[0]
        if start >= len(lines) or lines[start] != heading:
            return heading
        opening = next(
            (
                position
                for position in range(start + 1, len(lines))
                if lines[position].strip()
            ),
            len(lines),
        )
        fence = (
            re.fullmatch(r"(`{3,})text", lines[opening])
            if opening < len(lines)
            else None
        )
        if not fence or fence[1] not in lines[opening + 1 :]:
            return heading
        end = lines.index(fence[1], opening + 1)
        rest = sections(end + 1, names[1:])
        return (
            rest
            if isinstance(rest, str)
            else (normalize("\n".join(lines[opening + 1 : end])), *rest)
        )

    body = sections(2, _ADR_SECTIONS)
    return AdrEntry(
        key,
        path,
        data,
        None if isinstance(body, str) else (unescape(title[2]), *body),
        status,
        body if isinstance(body, str) else "",
    )


def read_adr(files: Mapping[str, bytes]):
    entries = tuple(
        _read_entry(key, path, data)
        for path, data in files.items()
        for key in (parse_adr_filename(path),)
        if key is not None
    )
    keys = tuple(dict.fromkeys(entry.key for entry in entries))
    return checked(
        entries,
        (
            Defect(
                f"AdrKeyClash: {key.text}",
                ", ".join(entry.path for entry in entries if entry.key == key),
                "Keep exactly one file for this ADR key.",
            )
            for key in keys
            if sum(entry.key == key for entry in entries) > 1
        ),
    )


def next_number(register: Register | tuple[AdrKey, ...], prefix: str) -> int:
    keys = (entry if isinstance(entry, AdrKey) else entry.key for entry in register)
    return 1 + max((key.number for key in keys if key.prefix == prefix), default=0)


def _adr_defect(kind, field, why, how):
    return Defect(f"{kind}: {field}", why, how)


def _row_defects(row, index):
    return model.check_adr_row(row, f"design.adrs[{index}]")


def _body_units(row, index):
    units = model.adr_body_units(row, f"design.adrs[{index}]")
    return tuple(
        value
        if name == "title" or isinstance(value, model.UnavailableInput)
        else normalize(value)
        for name, value in units.items()
    )


class BodyRelation(Enum):
    Equal = "equal"
    Different = "different"
    Unavailable = "unavailable"


def _body_relation(left, right):
    if left is None or right is None:
        return BodyRelation.Different
    pairs = tuple(zip(left, right, strict=True))
    known = tuple(
        (before, after)
        for before, after in pairs
        if not isinstance(before, model.UnavailableInput)
        and not isinstance(after, model.UnavailableInput)
    )
    if any(before != after for before, after in known):
        return BodyRelation.Different
    return BodyRelation.Equal if len(known) == len(pairs) else BodyRelation.Unavailable


def _render_adr(key, row):
    return (
        f"# {escaped(key.text)} {escaped(row['title'])}\nStatus: {row['status']}\n\n"
        + "\n".join(
            f"## {name}\n\n{fenced(row[name.lower()])}" for name in _ADR_SECTIONS
        )
    ).encode("utf-8")


def _with_status(entry, status):
    text = entry.data.decode("utf-8")
    rewritten = re.sub(
        r"(^[^\r\n]*(?:\r\n|\r|\n))Status: [^\r\n]*",
        lambda match: match[1] + "Status: " + status,
        text,
        count=1,
    )
    return replace(entry, data=rewritten.encode("utf-8"), status=status)


def _foreign(entry):
    return checked(
        None,
        (
            _adr_defect(
                "AdrForeignLayout",
                entry.path,
                f"Missing layout line or fenced section: {entry.missing}",
                "add a new ADR or migrate the file by hand",
            ),
        ),
    )


@dataclass(frozen=True)
class PendingAdr:
    """An operation's record, without a number or rendered representation."""

    position: int
    prefix: str | model.UnavailableInput


@dataclass(frozen=True)
class Superseded:
    successor: AdrKey | PendingAdr | str


@dataclass(frozen=True)
class AdrDescription:
    identity: AdrKey | PendingAdr
    body: tuple[str | model.UnavailableInput, ...] | None
    status: str | Superseded
    original: AdrEntry | None


@dataclass(frozen=True)
class AdrAdd:
    pass


@dataclass(frozen=True)
class AdrNamed:
    selector: str
    entry: AdrDescription


@dataclass(frozen=True)
class AdrSelectionUnavailable:
    pass


@dataclass(frozen=True)
class AdrMatchUnavailable:
    pass


def _decode_status(status: str) -> str | Superseded:
    return (
        Superseded(status.removeprefix("Superseded by "))
        if status.startswith("Superseded by ")
        else status
    )


def _describe(entry):
    return AdrDescription(
        entry.key,
        entry.body,
        _decode_status(entry.status),
        entry,
    )


def _select_adr(register, row):
    """Read only the selector scalar and its current resolved record unit."""
    if not isinstance(row, Mapping):
        return Built(AdrSelectionUnavailable())
    selectors = tuple(name for name in ("key", "supersedes") if name in row)
    if len(selectors) > 1:
        return Built(AdrSelectionUnavailable())
    if not selectors:
        return Built(AdrAdd())
    selector = selectors[0]
    if model.check_adr_selector(row[selector], selector):
        return Built(AdrSelectionUnavailable())
    entry = next(
        (
            entry
            for entry in register
            if isinstance(entry.identity, AdrKey)
            and entry.identity.text == row[selector]
        ),
        None,
    )
    if entry is None:
        return checked(
            None,
            (
                _adr_defect(
                    "DanglingReference",
                    row[selector],
                    "No ADR has this key.",
                    "Use an existing key or add a row without a key.",
                ),
            ),
        )
    if entry.body is None:
        return _foreign(entry.original)
    return Built(AdrNamed(selector, entry))


def _transition_defects(selection, status, index):
    decoded = _decode_status(status)
    if isinstance(decoded, Superseded):
        if (
            isinstance(selection, AdrNamed)
            and selection.selector == "key"
            and selection.entry.status == decoded
        ):
            return ()
        return (
            _adr_defect(
                "AdrTransitionInvalid",
                selection.entry.identity.text
                if isinstance(selection, AdrNamed)
                else f"design.adrs[{index}].status",
                "A superseded status can only repeat the successor already recorded by the selected ADR.",
                "Use nwdes design open --from-current to retain the recorded status, or add an accepted successor with nwdes design adr add --supersedes.",
            ),
        )
    if not isinstance(selection, AdrNamed) or selection.selector != "supersedes":
        return ()
    if (
        selection.entry.status == "Accepted"
        or isinstance(selection.entry.status, Superseded)
    ) and status == "Accepted":
        return ()
    return (
        _adr_defect(
            "AdrTransitionInvalid",
            selection.entry.identity.text,
            "Only an accepted ADR can be superseded by an accepted successor.",
            "Accept the predecessor and successor or add an independent ADR.",
        ),
    )


def _immutable_body_defects(selection, body):
    if not isinstance(selection, AdrNamed) or selection.selector != "key":
        return ()
    if (
        selection.entry.status == "Proposed"
        or _body_relation(selection.entry.body, body) != BodyRelation.Different
    ):
        return ()
    return (
        _adr_defect(
            "AdrAcceptedImmutable",
            selection.entry.identity.text,
            "An accepted or superseded ADR body cannot change.",
            "Add a new accepted successor with supersedes instead.",
        ),
    )


def _adr_rank(entry):
    identity = entry.identity
    return (
        (1, identity.position)
        if isinstance(identity, PendingAdr)
        else (0, identity.number)
    )


def _equal_adr(register, prefix, body, predecessor, unavailable):
    def relation(candidate):
        if isinstance(prefix, model.UnavailableInput) or isinstance(
            candidate.identity.prefix, model.UnavailableInput
        ):
            return BodyRelation.Unavailable
        if candidate.identity.prefix != prefix:
            return BodyRelation.Different
        if candidate.identity in unavailable:
            return BodyRelation.Unavailable
        if predecessor is not None and candidate.status != "Accepted":
            return BodyRelation.Different
        return _body_relation(candidate.body, body)

    matches = (
        (candidate, relation(candidate))
        for candidate in sorted(register, key=_adr_rank, reverse=True)
        if predecessor is None or candidate.identity != predecessor.identity
    )
    match = next(
        (
            (candidate, result)
            for candidate, result in matches
            if result != BodyRelation.Different
        ),
        (None, BodyRelation.Equal),
    )
    return (
        AdrMatchUnavailable()
        if match[1] == BodyRelation.Unavailable
        else Built(match[0])
    )


def _recorded_adr(register, predecessor):
    recorded = predecessor.status.successor
    return next(
        (
            entry
            for entry in register
            if entry.identity == recorded
            or (isinstance(entry.identity, AdrKey) and entry.identity.text == recorded)
        ),
        None,
    )


def _successor_defects(selection, successor):
    if not isinstance(selection.entry.status, Superseded):
        return ()
    recorded = selection.entry.status.successor
    if successor is not None and (
        recorded == successor.identity
        or (
            isinstance(successor.identity, AdrKey)
            and recorded == successor.identity.text
        )
    ):
        return ()
    return (
        _adr_defect(
            "AdrTransitionInvalid",
            selection.entry.identity.text,
            "A superseded ADR already names its immutable successor.",
            "Replay the recorded successor unchanged, or supersede that accepted successor.",
        ),
    )


@dataclass(frozen=True)
class PreparedAdr:
    build: Callable[[], Built[AdrResult]]


@dataclass(frozen=True)
class AdrPlan:
    entries: tuple[AdrDescription, ...]
    declared: tuple[AdrKey | PendingAdr, ...]


@dataclass(frozen=True)
class AdrOperationUnits:
    selection: AdrAdd | AdrNamed
    body: tuple[str | model.UnavailableInput, ...]
    status: str
    prefix: str | model.UnavailableInput
    position: int
    equal: AdrDescription | None


def _planned_operation(register, operation: AdrOperationUnits):
    """Evolve selector/status/register units while carrying body availability."""
    selection, body, status, prefix, position, equal = (
        operation.selection,
        operation.body,
        operation.status,
        operation.prefix,
        operation.position,
        operation.equal,
    )
    if isinstance(selection, AdrNamed):
        entry = selection.entry
        if selection.selector == "supersedes":
            successor = equal or AdrDescription(
                PendingAdr(position, prefix), body, status, None
            )
            predecessor = replace(entry, status=Superseded(successor.identity))
            return (
                *(
                    candidate
                    for candidate in register
                    if candidate.identity not in (entry.identity, successor.identity)
                ),
                successor,
                predecessor,
            ), successor.identity
        updated = replace(
            entry,
            body=body if entry.status == "Proposed" else entry.body,
            status=status if entry.status == "Proposed" else entry.status,
        )
        return (
            tuple(
                updated if candidate.identity == entry.identity else candidate
                for candidate in register
            ),
            entry.identity,
        )
    if equal is not None:
        return register, equal.identity
    created = AdrDescription(PendingAdr(position, prefix), body, status, None)
    return (*register, created), created.identity


def _selector_required_defects(register, selection, prefix, body, index):
    if not isinstance(selection, AdrAdd):
        return ()
    matches = tuple(
        entry.identity.text
        for entry in sorted(register, key=_adr_rank)
        if entry.status == "Accepted"
        and entry.identity.prefix == prefix
        and entry.body is not None
        and entry.body[0] == body[0]
        and _body_relation(entry.body, body) == BodyRelation.Different
    )
    if not matches:
        return ()
    keys = ", ".join(matches)
    if len(matches) == 1:
        key = matches[0]
        repair = f'To retain the decision, use key: "{key}" with its unchanged body. To replace it, use supersedes: "{key}" with an Accepted successor. For an independent decision, use a distinct title.'
    else:
        retention = " or ".join(f'key: "{key}"' for key in matches)
        replacement = " or ".join(f'supersedes: "{key}"' for key in matches)
        repair = (
            "Choose the intended existing identity explicitly. "
            f"To retain the decision, use {retention} with its unchanged body. "
            f"To replace it, use {replacement} with an Accepted successor. "
            "For an independent decision, use a distinct title."
        )
    return (
        _adr_defect(
            "AdrSelectorRequired",
            f"design.adrs[{index}]",
            f"This selectorless row repeats the title of accepted ADR {keys} but has a different body; a title does not establish identity or supersession.",
            repair,
        ),
    )


def _prepare_adr_row(state, indexed):
    register, declared, unavailable, defects, identities = state
    index, row = indexed
    shape = _row_defects(row, index)
    # A refused operation cannot erase the immutable reg:K lookup units.
    selected = _select_adr(identities, row)
    problems = (*shape, *(selected.defects if isinstance(selected, Refused) else ()))
    if isinstance(selected, Refused) or isinstance(
        selected.value, AdrSelectionUnavailable
    ):
        return register, declared, unavailable, (*defects, *problems), identities
    selection = selected.value
    if isinstance(selection, AdrNamed):
        if selection.entry.identity in unavailable:
            return register, declared, unavailable, (*defects, *problems), identities
        selection = AdrNamed(
            selection.selector,
            next(
                entry
                for entry in register
                if entry.identity == selection.entry.identity
            ),
        )
    body = _body_units(row, index)
    status = model.adr_status_input(row)
    prefix_input = model.adr_prefix_input(row)
    prefix = (
        prefix_input.value
        if isinstance(prefix_input, Built)
        else model.UnavailableInput(prefix_input.defects[0])
    )
    transition = (
        _transition_defects(selection, status.value, index)
        if isinstance(status, Built)
        else ()
    )
    immutable = _immutable_body_defects(selection, body)
    superseding = isinstance(selection, AdrNamed) and selection.selector == "supersedes"
    equal = (
        _equal_adr(
            register,
            prefix,
            body,
            selection.entry if superseding else None,
            unavailable,
        )
        if isinstance(selection, AdrAdd) or superseding
        else Built(None)
    )
    recorded = (
        _recorded_adr(register, selection.entry)
        if superseding and isinstance(selection.entry.status, Superseded)
        else None
    )
    successor = (
        _successor_defects(
            selection, equal.value if isinstance(equal, Built) else recorded
        )
        if superseding and isinstance(status, Built) and status.value == "Accepted"
        else ()
    )
    selector_required = _selector_required_defects(
        identities, selection, prefix, body, index
    )
    problems = (*problems, *transition, *immutable, *successor, *selector_required)
    if (
        not isinstance(status, Built)
        or transition
        or immutable
        or successor
        or selector_required
    ):
        blocked = (
            unavailable | {selection.entry.identity}
            if isinstance(selection, AdrNamed)
            else unavailable
        )
        return register, declared, blocked, (*defects, *problems), identities
    # With an unproduced body, every admissible replay keeps its recorded successor.
    matched = equal.value if isinstance(equal, Built) else recorded
    current, identity = _planned_operation(
        register,
        AdrOperationUnits(selection, body, status.value, prefix, index, matched),
    )
    return (
        current,
        (*declared, identity),
        unavailable,
        (*defects, *problems),
        identities,
    )


def apply_adr(register: Register, rows):
    prepared = prepare_adr(register, rows)
    return prepared if isinstance(prepared, Refused) else prepared.value.build()


@dataclass(frozen=True)
class _AdrBodySlot:
    row: int
    field: str
    wording: str
    changed: bool
    key: AdrKey | None = None

    @property
    def identity(self):
        return (self.key if self.key is not None else self.row, self.field)


def _adr_body_changed(selected, body, status):
    match selected:
        case Built(value=AdrAdd()) | Built(value=AdrNamed(selector="supersedes")):
            return True
        case Built(value=AdrNamed(selector="key", entry=entry)):
            return _body_relation(entry.body, body) == BodyRelation.Different or (
                entry.status == "Proposed" and status == "Accepted"
            )
        case _:
            return False


def _adr_body_slots(register, row, index):
    if not isinstance(row, Mapping):
        return ()
    body = _body_units(row, index)
    selected = _select_adr(register, row)
    key = (
        selected.value.entry.identity
        if isinstance(selected, Built)
        and isinstance(selected.value, AdrNamed)
        and selected.value.selector == "key"
        else None
    )
    changed = _adr_body_changed(selected, body, row.get("status"))
    return tuple(
        _AdrBodySlot(index, name, " ".join(value.split()), changed, key)
        for name, value in zip(model.ADR_BODY_FIELDS[1:], body[1:], strict=True)
        if not isinstance(value, model.UnavailableInput)
    )


def _changed_body_pairs(slots):
    slots = tuple(slots)
    changed = tuple(slot for slot in slots if slot.changed)
    others = tuple(slot for slot in slots if not slot.changed)
    return chain(combinations(changed, 2), product(changed, others))


def _duplicate_adr_body_defects(register, rows):
    slots = (
        slot
        for index, row in enumerate(rows)
        for slot in _adr_body_slots(register, row, index)
    )
    return tuple(
        _adr_defect(
            "InconsistentFacts",
            f"design.adrs[{left.row}].{left.field}, design.adrs[{right.row}].{right.field}",
            "These ADR body slots repeat the same wording up to whitespace, and at least one row is new or changed.",
            "Return this refusal to the architect to record distinct ADR wording with nwdes design adr add, then retry nwdes design close.",
        )
        for _, group in groupby(
            sorted(slots, key=lambda slot: slot.wording), key=lambda slot: slot.wording
        )
        for left, right in _changed_body_pairs(group)
        if left.identity != right.identity
    )


def prepare_adr(register: Register, rows, prior_declarations=()):
    rows = model.normalize_input(model.array(model.ADR_ROW), rows, "design.adrs").value
    if rows is None:
        rows = []
    if not isinstance(rows, (tuple, list)):
        return checked(
            None,
            (
                _adr_defect(
                    "PartInvalid",
                    "design.adrs",
                    "Expected an array.",
                    "Record ADR values with nwdes design adr add, then nwdes design close.",
                ),
            ),
        )
    identities = tuple(map(_describe, register))
    entries, declared, _, defects, _ = reduce(
        _prepare_adr_row,
        enumerate(rows),
        (identities, (), frozenset(), (), identities),
    )
    retained = frozenset(
        selected.value.entry.identity
        for row in rows
        if isinstance((selected := _select_adr(identities, row)), Built)
        and isinstance(selected.value, AdrNamed)
        and selected.value.selector == "key"
    ) | frozenset(declared)
    previous_keys = frozenset(row["key"] for row in prior_declarations)
    dropped = tuple(
        _adr_defect(
            "AdrDeclarationDropped",
            entry.identity.text,
            "The candidate removes this feature's accepted ADR from design.adrs without an explicit accepted successor.",
            f'Retain the unchanged ADR with key: "{entry.identity.text}", or declare its accepted replacement with supersedes: "{entry.identity.text}"; do not remove the declaration implicitly.',
        )
        for entry in sorted(identities, key=_adr_rank)
        if entry.identity.text in previous_keys
        and entry.status == "Accepted"
        and entry.identity not in retained
        and not any(
            current.identity == entry.identity
            and isinstance(current.status, Superseded)
            for current in entries
        )
    )
    return checked(
        PreparedAdr(lambda: _materialize_adrs(AdrPlan(entries, declared))),
        (*dropped, *defects, *_duplicate_adr_body_defects(identities, rows)),
    )


def _materialize_adrs(plan):
    """Number and render a fully admitted plan; no semantic refusals remain."""
    existing = tuple(
        entry.identity for entry in plan.entries if isinstance(entry.identity, AdrKey)
    )
    pending = sorted(
        (
            entry.identity
            for entry in plan.entries
            if isinstance(entry.identity, PendingAdr)
        ),
        key=lambda identity: identity.position,
    )

    def number(keys, identity):
        key = AdrKey(
            identity.prefix, next_number((*existing, *keys.values()), identity.prefix)
        )
        return {**keys, identity: key}

    numbered = reduce(number, pending, {})

    def key(identity):
        return numbered[identity] if isinstance(identity, PendingAdr) else identity

    def materialize(entry):
        status = entry.status
        if isinstance(status, Superseded):
            target = status.successor
            status = "Superseded by " + (
                target if isinstance(target, str) else key(target).text
            )
        original = entry.original
        if original is not None and entry.body == original.body:
            return (
                original
                if status == original.status
                else _with_status(original, status)
            )
        assigned = key(entry.identity)
        path = original.path if original is not None else adr_filename(assigned)
        row = {
            "title": entry.body[0],
            "status": status,
            **dict(
                zip(
                    (name.lower() for name in _ADR_SECTIONS),
                    entry.body[1:],
                    strict=True,
                )
            ),
        }
        return AdrEntry(assigned, path, _render_adr(assigned, row), entry.body, status)

    current = tuple(map(materialize, plan.entries))
    declared = tuple(dict.fromkeys(key(identity) for identity in plan.declared))
    return Built(
        AdrResult(
            MappingProxyType({entry.path: entry.data for entry in current}),
            tuple(
                MappingProxyType(
                    {
                        "key": entry.key.text,
                        "title": entry.body[0],
                        "status": entry.status,
                    }
                )
                for identity in declared
                for entry in current
                if entry.key == identity
            ),
            current,
        )
    )


@dataclass(frozen=True)
class ProductSection:
    identity: str
    product: str
    architecture: str
    acceptance: str


@dataclass(frozen=True)
class ProductHandoff:
    sections: tuple[ProductSection, ...] = ()


def render_html(markdown: str, brand: Brand) -> str:
    def block(match):
        if match["fence"] is not None:
            return (
                "<pre><code>" + escape(match["content"], quote=True) + "</code></pre>"
            )
        line = match["line"]
        heading = _HTML_HEADING.fullmatch(line) if line.startswith("#") else None
        if heading:
            level = len(heading[1])
            return f"<h{level}>{escape(unescape(heading[2]), quote=True)}</h{level}>"
        return "<p>" + escape(unescape(line), quote=True) + "</p>" if line else ""

    tokens = _HTML_TOKENS.finditer(markdown)
    return (
        '<!doctype html>\n<html><head><meta charset="utf-8"><style>'
        + brand.css
        + "</style></head><body>"
        + brand.logo.decode("utf-8")
        + "\n"
        + "\n".join(map(block, tokens))
        + "\n</body></html>\n"
    )


def render_field(spec, value, facts, level=3, *, compact=False):
    """Reuse the field print classes across documents and role projections."""
    return _render_field(
        lambda identity: fenced(facts[identity], language="" if compact else "text"),
        spec,
        value,
        level,
        compact,
    )


def render_resolved_field(spec, value, level=3, *, compact=False):
    """Print a projected schema value whose TEXT slots already hold authored text."""
    return _render_field(
        lambda text: fenced(text, language="" if compact else "text"),
        spec,
        value,
        level,
        compact,
    )


def _field_heading(label, level, compact):
    return (
        escaped(label) + ":\n"
        if compact
        else "#" * level + " " + escaped(label) + "\n\n"
    )


def _render_field(print_text, spec, value, level, compact):
    if value in (None, (), model.EMPTY):
        return "None.\n"
    if spec.kind == "text":
        return print_text(value)
    if spec.kind == "command":
        return fenced(value, language="" if compact else "text")
    if compact and spec.kind == "line":
        return inline(value) + "\n"
    if spec.kind in ("line", "string", "reference"):
        return escaped(value) + "\n"
    if spec.kind in ("enum", "adr_status"):
        return value + "\n"
    if spec is model.SHARED_DECISION or spec is model.SHARED_CONSTRAINT:
        slices = value.get("slices", ())
        return print_text(value["text"]) + (
            ("Slices: " if compact else "Governed slices: ")
            + ", ".join(map(escaped, slices))
            + "\n"
            if slices
            else ""
        )
    if spec.kind == "choice":
        return (
            value[spec.discriminator]
            + ("\n" if compact else "\n\n")
            + _render_field(
                print_text,
                spec.index[value[spec.discriminator]],
                value,
                level,
                compact,
            )
        )
    if spec.kind == "array":
        if spec.members[0].kind == "command":
            return fenced(
                "\n".join(dict.fromkeys(value)), language="" if compact else "text"
            )
        return ("" if compact else "\n").join(
            (
                _field_heading(child["id"], level, compact)
                if isinstance(child, Mapping) and "id" in child
                else ""
            )
            + _render_field(print_text, spec.members[0], child, level + 1, compact)
            for child in value
        )
    if spec.kind == "table":
        return ("" if compact else "\n").join(
            _field_heading(identity, level, compact)
            + _render_field(
                print_text, spec.members[0], value[identity], level + 1, compact
            )
            for identity in sorted(value, key=model.id_order)
        )
    return ("" if compact else "\n").join(
        (
            _field_heading(
                "Slice work"
                if field == "work"
                else field.replace("_", " ").capitalize(),
                min(level, 6),
                compact,
            )
            if child_spec.kind in ("array", "record", "table", "choice")
            else ""
        )
        + _render_field(print_text, child_spec, value.get(field), level + 1, compact)
        for field, child_spec in spec.members
        if not compact or value.get(field) not in (None, (), model.EMPTY)
    )


def render_adrs(rows):
    return (
        "".join(
            f"- {escaped(row['key'])} {escaped(row['title'])} — {row['status']}\n"
            for row in rows
        )
        or "None.\n"
    )


def _brief_document(scope, document_kind, handoff_argument):
    default = next(
        path
        for kind, path in resolve_destinations((), scope).value.briefs
        if kind is document_kind
    )
    return (
        posixpath.join(posixpath.dirname(handoff_argument), posixpath.basename(default))
        if handoff_argument is not None
        else default
    )


def acceptance_document(scope, handoff_argument=None):
    return _brief_document(scope, DocumentKind.Acceptance, handoff_argument)


def architecture_document(scope, handoff_argument=None):
    return _brief_document(scope, DocumentKind.Architecture, handoff_argument)


def _path_prefix(row):
    prefix, separator, _ = row[1].rpartition("/")
    return prefix + separator


def _path_group(prefix, rows):
    full = "".join(label + " " + inline(path) + "\n" for label, path in rows)
    if prefix and len(rows) > 1:
        scoped = (
            "Path prefix "
            + inline(prefix)
            + ":\n"
            + "".join(
                "  " + label + " " + inline(path[len(prefix) :]) + "\n"
                for label, path in rows
            )
        )
        return (
            scoped if len(scoped.encode("utf-8")) < len(full.encode("utf-8")) else full
        )
    return full


def path_index(rows):
    """Factor exact path prefixes; no normalization of stored path values."""
    return (
        "".join(
            _path_group(prefix, tuple(group))
            for prefix, group in groupby(sorted(rows, key=_path_prefix), _path_prefix)
        )
        or "None.\n"
    )


def _acceptance_row(row, test=None):
    disposition = row["disposition"]
    return (
        (
            inline(disposition["test"] if test is None else test)
            if disposition["kind"] == "Tested"
            else "NotTested owner " + inline(disposition["owner"])
        )
        + " "
        + (",".join(map(escaped, row.get("covers", ()))) or "None.")
        + (
            " obligations " + ",".join(map(escaped, disposition["obligations"]))
            if disposition.get("obligations")
            else ""
        )
        + "\n"
    )


def _test_prefix(row):
    disposition = row["disposition"]
    if disposition["kind"] != "Tested":
        return None
    prefix, separator, suffix = disposition["test"].rpartition("::")
    return prefix + separator if separator and suffix else None


def _acceptance_group(prefix, rows):
    if prefix is None or len(rows) == 1:
        return "".join(map(_acceptance_row, rows))
    common = posixpath.commonprefix(tuple(row["disposition"]["test"] for row in rows))
    candidate = common[: max(len(prefix), common.rfind("_") + 1)]
    prefix = (
        prefix
        if any(row["disposition"]["test"] == candidate for row in rows)
        else candidate
    )
    return (
        "Test prefix "
        + inline(prefix)
        + ":\n"
        + "".join(
            "  " + _acceptance_row(row, row["disposition"]["test"][len(prefix) :])
            for row in rows
        )
    )


def acceptance_rows(rows):
    """Print locator/owner and covers only; narrative stays in the acceptance document."""
    return (
        "".join(
            _acceptance_group(prefix, tuple(group))
            for prefix, group in groupby(rows, _test_prefix)
        )
        if rows
        else "Rows: None.\n"
    )


def acceptance_index(scope, identity, rows, *, handoff_argument=None):
    document = acceptance_document(scope, handoff_argument)
    return (
        "Acceptance: "
        + inline(document)
        + " ### "
        + identity
        + "; read via file tool. Rows: locator/owner, covers, obligations.\n"
        + acceptance_rows(rows)
    )


def charter_sections(charter):
    """Shared sections over the feature charter's resolved public-authored text."""
    return (
        (
            "Intent",
            fenced(charter["intent"]),
        ),
        ("Charter", fenced(charter["exploration"])),
        (
            "Expected observations (oracle)",
            "".join("- Positive:\n" + fenced(text) for text in charter["positive"])
            + "- Negative:\n"
            + fenced(charter["negative"]),
        ),
    )


def _render_charter(handoff):
    charter = handoff.charter
    if charter is None:
        return "None.\n"

    def sections(value, prefix):
        return "".join(
            prefix + name + "\n\n" + body
            for name, body in charter_sections(
                model.expanded(model.CHARTER, value, handoff.facts)
            )
        )

    if charter["kind"] == "LegacySlices":
        return "".join(
            "### Legacy " + escaped(identity) + "\n\n" + sections(value, "#### ")
            for identity, value in charter["slices"].items()
        )
    return (
        sections(charter, "### ")
        + "### Session log (append-only)\n\n"
        + "| Observation | Result |\n| --- | --- |\n"
    )


def brief_sections(handoff, kind):
    facts = handoff.facts
    if kind is DocumentKind.Product:
        product = handoff.product or model.EMPTY
        specs = model.PRODUCT.index
        return (
            ("Request", fenced(facts[handoff.request])),
            ("Work", render_field(model.WORK, handoff.work, facts)),
            (
                "Promises",
                render_field(specs["promises"], product.get("promises"), facts),
            ),
            (
                "Scope",
                (
                    render_field(specs["scope_in"], product.get("scope_in"), facts)
                    + "\n"
                    + render_field(specs["scope_out"], product.get("scope_out"), facts)
                )
                if product.get("scope_in") or product.get("scope_out")
                else "None.\n",
            ),
            (
                "Decisions",
                render_field(specs["decisions"], product.get("decisions"), facts),
            ),
            ("Journey", render_field(specs["journey"], product.get("journey"), facts)),
            ("Slices", render_field(specs["slices"], product.get("slices"), facts)),
        )
    if kind is DocumentKind.Architecture:
        design = handoff.design or model.EMPTY
        return (
            ("Paradigm", design.get("paradigm", "None.") + "\n"),
            (
                "Shared records",
                render_field(model.SHARED_RECORDS, design.get("shared"), facts),
            ),
            (
                "Slices",
                render_field(model.DESIGN.index["slices"], design.get("slices"), facts),
            ),
            ("ADRs", render_adrs(design.get("adrs", ()))),
        )
    return (
        (
            "Slices",
            render_field(
                model.CANONICAL_SCHEMAS["acceptance"],
                handoff.acceptance,
                facts,
            ),
        ),
        ("Expectations", render_field(model.EXPECTATIONS, handoff.expectations, facts)),
        (
            "Charter",
            _render_charter(handoff),
        ),
        (
            "Examination",
            _render_field(
                lambda identity: fenced_exact(facts[identity]),
                model.CANONICAL_SCHEMAS["examination"],
                handoff.examination,
                level=3,
                compact=False,
            ),
        ),
    )


def render_markdown(handoff, kind, register=()):
    identity = getattr(handoff.scope, "id", "project")
    return f"# {kind.value} brief: {escaped(identity)}\n\n" + "\n".join(
        f"## {name}\n\n{content}" for name, content in brief_sections(handoff, kind)
    )


def feature_outputs(handoff, destinations, brand, adr_files=()):
    briefs = tuple(
        Output(
            OutputKind.Markdown, path, render_markdown(handoff, kind).encode("utf-8")
        )
        for kind, path in destinations.briefs
    )
    pages = tuple(
        Output(
            OutputKind.Html,
            output.path[:-3] + ".html",
            render_html(output.data.decode("utf-8"), brand).encode("utf-8"),
        )
        for output in briefs
    )
    return OutputSet(
        (
            *adr_files,
            *briefs,
            *pages,
            Output(OutputKind.Handoff, destinations.handoff, model.serialize(handoff)),
        )
    )


def _deepen(markdown):
    tokens = _HTML_TOKENS.finditer(markdown)
    return "\n".join(
        match[0]
        if match["fence"] is not None
        else "#" + match[0]
        if match[0].startswith("#") and re.match(r"#{1,5} ", match[0])
        else match[0]
        for match in tokens
    )


def rebuild_section(product: ProductHandoff, handoffs) -> ProductHandoff:
    """Rebuild structured sections rather than patching rendered Markdown."""
    sections = {section.identity: section for section in product.sections}
    updates = {
        getattr(handoff.scope, "id", "project"): ProductSection(
            getattr(handoff.scope, "id", "project"),
            *(
                "".join(
                    f"### {name}\n\n{_deepen(content)}"
                    for name, content in brief_sections(handoff, kind)
                )
                for kind in DocumentKind
            ),
        )
        for handoff in handoffs
    }
    return ProductHandoff(
        tuple(value for _, value in sorted({**sections, **updates}.items()))
    )


def project_outputs(previous, handoffs, destinations, brand):
    product = rebuild_section(previous, handoffs)
    briefs = tuple(
        Output(
            OutputKind.Markdown,
            path,
            (
                f"# {kind.value} brief: project\n\n"
                + "".join(
                    f"## {escaped(section.identity)}\n\n"
                    + getattr(section, kind.value.lower())
                    for section in product.sections
                )
            ).encode("utf-8"),
        )
        for kind, path in destinations.briefs
    )
    pages = tuple(
        Output(
            OutputKind.Html,
            output.path[:-3] + ".html",
            render_html(output.data.decode("utf-8"), brand).encode("utf-8"),
        )
        for output in briefs
    )
    data = {
        "sections": [
            {
                "identity": section.identity,
                "product": section.product,
                "architecture": section.architecture,
                "acceptance": section.acceptance,
            }
            for section in product.sections
        ]
    }
    canonical = (
        json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    ).encode("utf-8")
    return OutputSet(
        (*briefs, *pages, Output(OutputKind.Handoff, destinations.handoff, canonical))
    )


def parse_product(data):
    parsed = model.parse_json(data, "project handoff", "HandoffInvalid")
    if isinstance(parsed, Refused):
        return parsed
    raw = parsed.value
    names = ("identity", "product", "architecture", "acceptance")
    if (
        not isinstance(raw, model.Record)
        or set(raw) != {"sections"}
        or not isinstance(raw["sections"], tuple)
        or any(
            not isinstance(row, model.Record)
            or set(row) != set(names)
            or any(not isinstance(row[name], str) for name in names)
            for row in raw["sections"]
        )
    ):
        return checked(
            None,
            (
                Defect(
                    "HandoffInvalid: project sections",
                    "Expected per-feature sections.",
                    "Supply the project handoff nwdes built.",
                ),
            ),
        )
    return Built(
        ProductHandoff(tuple(ProductSection(**row) for row in raw["sections"]))
    )


def adr_outputs(register, directory, snapshot, predecessors=()):
    selected = {row["key"] for row in snapshot} | set(predecessors)
    return tuple(
        Output(OutputKind.Adr, directory + "/" + entry.path, entry.data)
        for entry in register
        if entry.key.text in selected
    )


def declaration_snapshot(design, register):
    """Inspect each produced declaration key, independent of other prior parts."""
    if not isinstance(design, Mapping):
        return Built(())
    rows = design.get("adrs", ())
    keys = tuple(
        row["key"]
        for row in (rows if isinstance(rows, (tuple, list)) else ())
        if isinstance(row, Mapping)
        and isinstance(row.get("key"), str)
        and not model.check_adr_selector(row["key"], "design.adrs.key")
    )
    entries = {entry.key.text: entry for entry in register}
    missing = tuple(
        Defect(
            f"DanglingReference: {key}",
            "The declared ADR file is absent.",
            "Restore the ADR file or apply a design without this declaration.",
        )
        for key in keys
        if key not in entries
    )
    foreign = tuple(
        defect
        for key in keys
        if key in entries and entries[key].body is None
        for defect in _foreign(entries[key]).defects
    )
    snapshot = tuple(
        MappingProxyType(
            {"key": key, "title": entries[key].body[0], "status": entries[key].status}
        )
        for key in keys
        if key in entries and entries[key].body is not None
    )
    return checked(snapshot, (*missing, *foreign))


def added_adrs(base, side):
    """Project newly added ADR keys to their retained source bytes."""
    return {
        key.text: data
        for path, data in side.items()
        if path not in base
        for key in (parse_adr_filename(path.rsplit("/", 1)[-1]),)
        if key is not None
    }


def adr_body_equal(key: str, left: bytes, right: bytes):
    """Compare ADR meaning while leaving each side's source bytes untouched."""
    parsed_key = parse_adr_filename("ADR-" + key + ".md")

    def body(data):
        entry = _read_entry(parsed_key, "", data) if parsed_key is not None else None
        return entry.body if entry is not None and entry.body is not None else data

    return body(left) == body(right)


@dataclass(frozen=True)
class RekeyRegisters:
    lane: Register
    trunk: Register

    def successor(self, original: AdrEntry) -> AdrEntry | None:
        trunk_keys = frozenset(entry.key for entry in self.trunk)
        return min(
            (
                entry
                for entry in self.lane
                if entry.key != original.key
                and entry.key.prefix == original.key.prefix
                and entry.body == original.body
                and entry.key not in trunk_keys
            ),
            key=lambda entry: entry.key.number,
            default=None,
        )


def rekey_adr(current, registers: RekeyRegisters, key, destinations, brand):
    """Materialize an admitted rekey, preserving every non-key source region."""
    register = registers.lane
    original = next(entry for entry in register if entry.key.text == key)
    successor = registers.successor(original)
    if successor is None:
        assigned = AdrKey(
            original.key.prefix,
            next_number((*register, *registers.trunk), original.key.prefix),
        )
        text = original.data.decode("utf-8")
        renamed = replace(
            original,
            key=assigned,
            path=adr_filename(assigned),
            data=re.sub(
                r"^# \S+ ",
                lambda match: "# " + escaped(assigned.text) + " ",
                text,
                count=1,
            ).encode("utf-8"),
        )
    else:
        renamed = successor
        assigned = successor.key
    updated = (
        renamed,
        *(
            _with_status(entry, "Superseded by " + assigned.text)
            if entry.status == "Superseded by " + key
            else entry
            for entry in register
            if entry.key not in (original.key, assigned)
        ),
    )
    snapshot = tuple(
        {
            **row,
            "key": assigned.text if row["key"] == key else row["key"],
            "status": "Superseded by " + assigned.text
            if row["status"] == "Superseded by " + key
            else row["status"],
        }
        for row in (current.design or {}).get("adrs", ())
    )
    current = model.snapshot_adrs(current, snapshot)
    changed = (
        entry
        for entry in updated
        if entry is renamed or entry.status == "Superseded by " + assigned.text
    )
    outputs = tuple(
        Output(
            OutputKind.Adr, destinations.adr_directory + "/" + entry.path, entry.data
        )
        for entry in changed
    )
    return feature_outputs(current, destinations, brand, outputs)
