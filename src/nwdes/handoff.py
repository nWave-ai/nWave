"""Canonical handoffs: immutable values, generated schemas and total transitions."""

from __future__ import annotations

import json
import posixpath
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, fields, replace
from enum import Enum
from functools import cache, cached_property, reduce
from types import MappingProxyType

from nwdes import policy as role_policy
from nwdes import prose
from nwdes.contracts import Built, Defect, Refused, checked


@dataclass(frozen=True, init=False)
class Record(Mapping):
    _index: Mapping

    def __init__(self, entries=()):
        object.__setattr__(self, "_index", MappingProxyType(dict(entries)))

    def __getitem__(self, key):
        return self._index[key]

    def __iter__(self):
        return iter(self._index)

    def __len__(self):
        return len(self._index)

    def __contains__(self, key):
        return key in self._index

    def get(self, key, default=None):
        return self._index.get(key, default)

    def items(self):
        return self._index.items()

    def values(self):
        return self._index.values()

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError as error:
            raise AttributeError(key) from error


EMPTY = Record()
ProgramResolution = Mapping[str, bool]
_MAPPINGS = (dict, Record, Mapping)


def freeze(value):
    if value is None or isinstance(value, (str, int)):
        return value
    if isinstance(value, Record):
        return value
    if isinstance(value, Mapping):
        return Record((name, freeze(child)) for name, child in value.items())
    if isinstance(value, (list, tuple)):
        return tuple(map(freeze, value))
    return value


def _document_value(value):
    if isinstance(value, Mapping):
        return value
    if isinstance(value, Handoff):
        return {
            "schema": "nwdes.handoff",
            "version": 4,
            **{
                field.name: getattr(value, field.name)
                for field in fields(value)
                if field.init and field.name != "withdrawals"
            },
        }
    if isinstance(value, (Feature, Epic)):
        return {"kind": value.kind, "id": value.id}
    if isinstance(value, Project):
        return {"kind": "Project"}
    return value


def _present_field(name, child, parent):
    if child not in (None, (), EMPTY):
        return True
    if name == "rows" and child == ():
        return True
    expectations = parent.get("expectations")
    return (
        name == "examination"
        and isinstance(expectations, Mapping)
        and expectations.get("rows") == ()
    )


def to_data(value):
    if value is None or isinstance(value, (str, int)):
        return value
    value = _document_value(value)
    if isinstance(value, Mapping):
        return {
            name: to_data(child)
            for name, child in value.items()
            if _present_field(name, child, value)
        }
    if isinstance(value, (tuple, list)):
        return [to_data(child) for child in value]
    return value


def _json_text(value, indent):
    """Emit the fixed pretty layout directly; the stdlib still escapes strings."""
    if isinstance(value, str):
        return json.encoder.encode_basestring(value)
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, int):
        return str(value)
    nested = indent + "  "
    if isinstance(value, (tuple, list)):
        if not value:
            return "[]"
        return (
            "[\n"
            + ",\n".join(nested + _json_text(child, nested) for child in value)
            + "\n"
            + indent
            + "]"
        )
    if not isinstance(value, _MAPPINGS):
        value = _document_value(value)
    if isinstance(value, _MAPPINGS):
        entries = sorted(value.items())
        if not entries:
            return "{}"
        return (
            "{\n"
            + ",\n".join(
                nested
                + json.encoder.encode_basestring(name)
                + ": "
                + _json_text(child, nested)
                for name, child in entries
            )
            + "\n"
            + indent
            + "}"
        )
    return json.dumps(value, ensure_ascii=False)


def json_text(value):
    """Encode schemas compactly and other JSON in the canonical readable layout."""
    if isinstance(value, Mapping) and "$defs" in value:
        return json.dumps(
            value, ensure_ascii=False, separators=(",", ":"), sort_keys=True
        )
    return _json_text(value, "")


def serialize(value) -> bytes:
    return (
        json.dumps(to_data(value), sort_keys=True, indent=0, ensure_ascii=False) + "\n"
    ).encode("utf-8")


@dataclass(frozen=True)
class Project:
    kind: str = "Project"


@dataclass(frozen=True)
class Feature:
    id: str
    kind: str = "Feature"


@dataclass(frozen=True)
class Epic:
    id: str
    kind: str = "Epic"


Scope = Project | Feature | Epic


@dataclass(frozen=True)
class Handoff:
    request: str
    scope: Scope
    work: Record
    counters: Record = EMPTY
    facts: Record = EMPTY
    product: Record | None = None
    design: Record | None = None
    acceptance: Record = EMPTY
    expectations: Record | None = None
    charter: Record | None = None
    examination: Record = EMPTY
    withdrawals: tuple[str, ...] = field(default=(), compare=False, repr=False)

    @cached_property
    def _references(self) -> _ReferenceTargets:
        return _ReferenceTargets(frozenset(_record_ids(self)), slice_ids(self))

    def scoped_records(self, slice=None):
        """Shared records, then the named slice's records or every slice's records."""
        design = self.design or EMPTY
        slices = design.get("slices") or EMPTY
        scoped = (slices.get(slice) or EMPTY,) if slice is not None else slices.values()
        return tuple(
            part
            for part in (
                design.get("shared"),
                *(own.get("records") for own in scoped),
            )
            if part
        )


@dataclass(frozen=True)
class PreparedHandoff:
    """Defer identity allocation until all independent boundary inspections finish."""

    build: Callable[[], Built[Handoff] | Refused]
    output: RoleInput | None = None


def finish(prepared):
    return prepared if isinstance(prepared, Refused) else prepared.value.build()


class RequiredError(Enum):
    MissingFact = "MissingFact"
    PartInvalid = "PartInvalid"


@dataclass(frozen=True)
class Spec:
    kind: str
    members: tuple = ()
    required: tuple[str, ...] = ()
    identity: str = ""
    minimum: int = 0
    exclusive: tuple[str, ...] = ()
    key_reference: str = ""
    key_shape: str = ""
    discriminator: str = "kind"
    required_error: RequiredError = RequiredError.MissingFact
    total: bool = False
    index: Mapping = field(init=False, compare=False, repr=False)
    allowed: frozenset[str] = field(init=False, compare=False, repr=False)
    has_ids: bool = field(init=False, compare=False, repr=False)
    id_children: tuple = field(init=False, compare=False, repr=False)
    has_references: bool = field(init=False, compare=False, repr=False)
    reference_fields: tuple[str, ...] = field(init=False, compare=False, repr=False)
    reference_children: tuple = field(init=False, compare=False, repr=False)
    required_fields: tuple[str, ...] = field(init=False, compare=False, repr=False)
    has_table_references: bool = field(init=False, compare=False, repr=False)
    id_kinds: tuple[str, ...] = field(init=False, compare=False, repr=False)
    has_text: bool = field(init=False, compare=False, repr=False)
    text_children: tuple = field(init=False, compare=False, repr=False)

    def __post_init__(self):
        index = dict(self.members) if self.kind in ("record", "choice") else {}
        object.__setattr__(self, "index", MappingProxyType(index))
        object.__setattr__(
            self,
            "required_fields",
            tuple(
                name
                for name in self.required
                if index[name].kind != "array" or index[name].minimum
            ),
        )
        object.__setattr__(
            self, "allowed", frozenset((*index, *(("id",) if self.identity else ())))
        )
        children = (
            tuple(index.values())
            if index
            else self.members
            if self.kind in ("array", "table")
            else ()
        )
        object.__setattr__(
            self,
            "has_text",
            self.kind == "text" or any(child.has_text for child in children),
        )
        object.__setattr__(
            self,
            "text_children",
            tuple((name, child) for name, child in index.items() if child.has_text),
        )
        object.__setattr__(
            self,
            "id_kinds",
            tuple(
                dict.fromkeys(
                    (
                        *((self.identity,) if self.identity else ()),
                        *(kind for child in children for kind in child.id_kinds),
                    )
                )
            ),
        )
        identities = tuple(
            (name, child) for name, child in index.items() if child.has_ids
        )
        links = tuple(
            name
            for name, child in index.items()
            if self.kind == "record"
            and name in ("covers", "promises", "depends_on", "slices")
            and child.kind == "array"
            and child.members[0].kind in ("reference", "string")
        )
        references = tuple(
            (name, child) for name, child in index.items() if child.has_references
        )
        object.__setattr__(
            self,
            "has_ids",
            bool(self.identity) or any(child.has_ids for child in children),
        )
        object.__setattr__(self, "id_children", identities)
        object.__setattr__(
            self,
            "has_references",
            bool(self.key_reference)
            or bool(links)
            or any(child.has_references for child in children),
        )
        object.__setattr__(self, "reference_fields", links)
        object.__setattr__(self, "reference_children", references)
        object.__setattr__(
            self,
            "has_table_references",
            self.kind == "table"
            or any(child.has_table_references for child in children),
        )


TEXT = Spec("text")
LINE = Spec("line")
IDENTITY = Spec("identity")
STRING = Spec("string")
REFERENCE = Spec("reference")
COMMAND = Spec("command")
PROMISE_REFERENCE = Spec("reference", ("P",))
OBLIGATION = Spec("obligation")
_OBLIGATION_KEY = re.compile(r"[LT][1-9][0-9]*(?:/F[1-9][0-9]*)?")
ADR_PREFIX_PATTERN = r"[A-Z][A-Z0-9]*(?:-[A-Z][A-Z0-9]*)*"
PREFIX = Spec("prefix")
ADR_STATUS_PATTERN = r"Proposed|Accepted|Superseded by [A-Z0-9-]+"
ADR_STATUS = Spec("adr_status", ("Proposed", "Accepted"))


def enum(*values):
    return Spec("enum", values)


def array(item, minimum=0):
    return Spec(
        "array", (item,), minimum=minimum, required_error=RequiredError.PartInvalid
    )


def _missing_kind(parent, child):
    """Whether an absent required member is a MissingFact: a list reports by its own error, any other member by its record's."""
    error = child.required_error if child.kind == "array" else parent.required_error
    return error is RequiredError.MissingFact


def record(
    required=(), identity="", *, required_error=RequiredError.MissingFact, **members
):
    return Spec(
        "record",
        tuple(members.items()),
        tuple(required),
        identity,
        required_error=required_error,
    )


def choice(*, discriminator="kind", **alternatives):
    return Spec("choice", tuple(alternatives.items()), discriminator=discriminator)


def table(item, key="S", *, total=False, key_shape=""):
    return Spec("table", (item,), key_reference=key, key_shape=key_shape, total=total)


REWORK = record(("delta", "reason"), delta=TEXT, reason=TEXT)
WORK = record(("size", "value"), size=enum("S", "M", "L"), value=TEXT, rework=REWORK)
WORK_PATCH = replace(WORK, required=())
PROMISE = choice(
    Outcome=record(("text",), identity="P", text=TEXT),
    Scenario=record(
        ("title", "given", "when", "then"),
        identity="P",
        title=TEXT,
        given=TEXT,
        when=TEXT,
        then=TEXT,
    ),
)
SLICE = record(
    ("observation",),
    identity="S",
    observation=TEXT,
    promises=array(PROMISE_REFERENCE),
    depends_on=array(STRING),
    work=WORK,
)
PRODUCT = record(
    ("slices",),
    promises=array(PROMISE),
    scope_in=array(TEXT),
    scope_out=array(TEXT),
    decisions=array(
        record(
            ("text", "status"),
            text=TEXT,
            status=choice(
                Proposed=record(),
                Confirmed=record(),
                Open=record(("owner",), owner=enum("Product", "Design", "Acceptance")),
            ),
        )
    ),
    journey=array(record(("step", "emotion"), step=TEXT, emotion=TEXT)),
    slices=array(SLICE, 1),
)
TARGET = record(
    ("path", "change"), path=LINE, change=enum("Create", "Extend"), reason=TEXT
)
PUBLIC_ORACLE = record(
    ("stimulus", "expected", "falsifier"),
    stimulus=TEXT,
    expected=TEXT,
    falsifier=TEXT,
    promises=array(PROMISE_REFERENCE),
)
PREFACTORING = record(
    ("move", "preserved", "existing_oracle", "verification"),
    move=TEXT,
    preserved=TEXT,
    existing_oracle=LINE,
    verification=array(COMMAND, 1),
)
GENERATOR = record(
    ("domain", "size_bound", "seed_policy", "must_include", "shrinking"),
    domain=TEXT,
    size_bound=LINE,
    seed_policy=LINE,
    must_include=array(TEXT),
    depth_bound=LINE,
    shrinking=TEXT,
)
TREATMENT = choice(
    Broad=record(
        ("generator", "independent_observation", "falsifier"),
        generator=GENERATOR,
        independent_observation=TEXT,
        falsifier=TEXT,
    ),
    Finite=record(("cases", "reason"), cases=array(TEXT), reason=TEXT),
    NoTest=record(("reason",), reason=TEXT),
)
FAILURE = record(
    ("condition", "outcome", "observation"),
    identity="B",
    condition=TEXT,
    outcome=enum("Refusal", "Retry", "Indeterminate"),
    observation=TEXT,
)
BOUNDARIES = record(
    ("driving_port", "dependency_direction"),
    driving_port=TEXT,
    driven_ports=array(TEXT),
    dependency_direction=TEXT,
    failures=array(FAILURE),
)
LAW = record(
    ("statement", "kind", "layer", "owner", "treatment"),
    identity="L",
    statement=TEXT,
    kind=enum("Algebraic", "Invariant", "RoundTrip", "Refinement", "Temporal"),
    layer=enum("Domain", "Application", "Adapter", "Infrastructure"),
    owner=LINE,
    treatment=TREATMENT,
    evidence=array(LINE),
)
CLAIM = record(
    (
        "proposition",
        "harm",
        "owner",
        "admitted_input",
        "constructor",
        "consumer",
        "public_observation",
        "bypass",
    ),
    identity="C",
    proposition=TEXT,
    harm=TEXT,
    owner=LINE,
    admitted_input=TEXT,
    constructor=LINE,
    consumer=LINE,
    public_observation=TEXT,
    bypass=TEXT,
)
MODEL = record(
    ("language", "path"),
    language=enum("Quint", "TlaPlus", "Agda"),
    path=LINE,
    properties=array(
        record(
            ("name", "kind", "statement", "symbol", "site"),
            name=LINE,
            kind=enum("Invariant", "Temporal", "Theorem"),
            statement=TEXT,
            symbol=LINE,
            site=LINE,
        )
    ),
    atoms=array(
        record(
            ("kind", "name", "symbol", "site"),
            kind=enum("State", "Action", "Constant"),
            name=LINE,
            symbol=LINE,
            site=LINE,
            atomicity=TEXT,
        )
    ),
    assumptions=array(TEXT),
    mutants=array(
        record(("description",), identity="N", description=TEXT, kills=array(LINE))
    ),
)
RECORDS = record(
    decisions=array(TEXT),
    constraints=array(TEXT),
    reuse=array(
        record(
            ("symbol", "locator", "decision", "reason"),
            symbol=LINE,
            locator=LINE,
            decision=enum("Reuse", "Extend", "Replace", "CreateNew"),
            reason=TEXT,
        )
    ),
    impact=array(
        record(
            ("kind", "locator", "decision", "reason"),
            kind=LINE,
            locator=LINE,
            decision=enum("Changed", "Migrated", "UnchangedCompatible"),
            reason=TEXT,
        )
    ),
    agreement=array(
        record(
            ("contract", "locator", "party", "decision", "reason"),
            contract=LINE,
            locator=LINE,
            party=enum("Producer", "Consumer"),
            decision=enum("Migrated", "UnchangedCompatible", "Incompatible"),
            reason=TEXT,
        )
    ),
    not_applicable=array(
        record(
            ("analysis", "reason"),
            analysis=enum(
                "reuse",
                "impact",
                "agreement",
                "architectural_tests",
                "contract_tests",
                "prefactoring",
            ),
            reason=TEXT,
        )
    ),
    boundaries=BOUNDARIES,
    observations=array(
        record(
            ("description", "result_type", "cannot_distinguish"),
            description=TEXT,
            result_type=LINE,
            cannot_distinguish=TEXT,
        )
    ),
    equality=array(record(("under", "definition"), under=LINE, definition=TEXT)),
    constructors=array(record(("name", "signature"), name=LINE, signature=LINE)),
    laws=array(LAW),
    refuted=array(
        record(
            ("statement", "cause", "counterexample"),
            statement=TEXT,
            cause=TEXT,
            counterexample=TEXT,
        )
    ),
    claims=array(CLAIM),
    states=array(
        record(
            ("kind", "state"),
            kind=enum("Admitted", "Excluded", "Unknown"),
            state=TEXT,
            owner=LINE,
        )
    ),
    models=array(MODEL),
    closure=array(
        record(
            ("subject", "axis", "design", "runtime", "basis"),
            subject=TEXT,
            axis=enum("Safety", "Inhabitation", "PublicReachability", "Liveness"),
            design=enum("Pass", "Blocked"),
            runtime=enum("Observed", "DesignedNotBuilt", "Indeterminate"),
            basis=TEXT,
            evidence=array(LINE),
        )
    ),
    risks=array(
        record(
            ("kind", "source", "preserved", "allowed", "forbidden", "residue", "owner"),
            identity="Y",
            kind=enum("Stressor", "SinglePointOfFailure", "Bypass"),
            source=TEXT,
            preserved=TEXT,
            allowed=TEXT,
            forbidden=TEXT,
            residue=TEXT,
            owner=LINE,
        )
    ),
    architectural_tests=array(
        record(
            ("obligation", "oracle", "command"),
            identity="T",
            obligation=TEXT,
            oracle=LINE,
            command=COMMAND,
        )
    ),
    contract_tests=array(
        record(
            (
                "obligation",
                "contract",
                "producer",
                "consumer",
                "observation",
                "oracle",
                "command",
            ),
            identity="T",
            obligation=TEXT,
            contract=LINE,
            producer=LINE,
            consumer=LINE,
            observation=TEXT,
            oracle=LINE,
            command=COMMAND,
        )
    ),
)
SHARED_DECISION = record(
    ("text", "slices"), identity="D", text=TEXT, slices=array(Spec("reference", ("S",)))
)
SHARED_CONSTRAINT = replace(SHARED_DECISION, identity="K")
SHARED_RECORDS = replace(
    RECORDS,
    members=tuple(
        (
            name,
            array(SHARED_DECISION)
            if name == "decisions"
            else array(SHARED_CONSTRAINT)
            if name == "constraints"
            else spec,
        )
        for name, spec in RECORDS.members
    ),
)

SLICE_DESIGN = record(
    ("oracle", "verification"),
    targets=array(TARGET),
    oracle=LINE,
    verification=array(COMMAND, 1),
    supports=array(LINE),
    public_oracle=PUBLIC_ORACLE,
    prefactoring=PREFACTORING,
    records=RECORDS,
)
SLICE_PATCH = replace(
    SLICE_DESIGN,
    required=(),
    members=tuple(
        (name, replace(spec, required=()) if name == "public_oracle" else spec)
        for name, spec in SLICE_DESIGN.members
    ),
)

# The slice members a policy may ask for by name: each is one record a slice holds once.
SLICE_MEMBERS = MappingProxyType({"prefactoring": PREFACTORING})

ADR_ROW = record(
    ("title", "status", "context", "decision", "alternatives", "consequences"),
    prefix=PREFIX,
    title=LINE,
    status=ADR_STATUS,
    context=TEXT,
    decision=TEXT,
    alternatives=TEXT,
    consequences=TEXT,
    key=LINE,
    supersedes=LINE,
)
ADR_ROW = replace(ADR_ROW, exclusive=("key", "supersedes"))
ADR_BODY_FIELDS = ("title", "context", "decision", "alternatives", "consequences")
ADR_BODY = record(
    ADR_BODY_FIELDS, **{name: ADR_ROW.index[name] for name in ADR_BODY_FIELDS}
)
ADR_SNAPSHOT = record(("key", "title", "status"), key=LINE, title=LINE, status=LINE)
DESIGN = record(
    ("paradigm",),
    paradigm=enum("functional", "object_oriented", "procedural"),
    shared=SHARED_RECORDS,
    slices=table(SLICE_DESIGN),
    adrs=array(ADR_ROW),
)
ACCEPTANCE_ROW = record(
    ("stimulus", "expected", "user_result", "disposition"),
    covers=array(REFERENCE),
    stimulus=TEXT,
    expected=TEXT,
    user_result=TEXT,
    disposition=choice(
        Tested=record(
            ("test",),
            test=LINE,
            still_passes_if=TEXT,
            obligations=array(OBLIGATION),
        ),
        NotTested=record(("reason", "owner"), reason=TEXT, owner=LINE),
    ),
)


def _slices_shape(spec):
    """The same record with each slice checked for shape only; its requirements are checked per slice."""
    return replace(
        spec,
        members=tuple(
            (name, table(SLICE_PATCH) if name == "slices" else child)
            for name, child in spec.members
        ),
    )


DESIGN_SHAPE = _slices_shape(DESIGN)
# A stimulus is absent only on the NotTested row of a prose-only slice; the requirement is
# checked where the slice is known (see _acceptance_requirements), never by the shape.
ACCEPTANCE_SHAPE = replace(
    ACCEPTANCE_ROW, required=("expected", "user_result", "disposition")
)

EXPECTATIONS = record(
    rows=array(
        record(("text",), identity="E", promises=array(PROMISE_REFERENCE), text=TEXT)
    )
)
CHARTER = record(
    ("intent", "exploration", "positive", "negative"),
    required_error=RequiredError.PartInvalid,
    intent=TEXT,
    exploration=TEXT,
    positive=array(TEXT, 1),
    negative=TEXT,
)
LEGACY_CHARTERS = table(CHARTER, key="", key_shape="S")
CHARTER_PART = choice(
    Feature=CHARTER,
    LegacySlices=record(("slices",), slices=LEGACY_CHARTERS),
)
VERDICT = choice(
    discriminator="verdict",
    met=record(observations=array(TEXT)),
    unmet=record(
        ("class",),
        required_error=RequiredError.PartInvalid,
        observations=array(TEXT),
        **{
            "class": enum(
                "oracle_gap",
                "product_violation",
                "expectation_defect",
                "observation_gap",
            )
        },
    ),
)
OBSERVATION_REFERENCE = Spec("draft_reference", ("O",))
EXAMINATION_OBSERVATION = record(("id", "text"), id=OBSERVATION_REFERENCE, text=TEXT)
EXAMINATION_VERDICT = replace(
    VERDICT,
    members=tuple(
        (
            name,
            replace(
                spec,
                members=tuple(
                    (
                        field,
                        array(OBSERVATION_REFERENCE)
                        if field == "observations"
                        else child,
                    )
                    for field, child in spec.members
                ),
            ),
        )
        for name, spec in VERDICT.members
    ),
)
EXAMINATION_INPUT = record(
    ("observations", "verdicts"),
    observations=array(EXAMINATION_OBSERVATION),
    verdicts=table(EXAMINATION_VERDICT, key="E", total=True),
)
ROLE_SCHEMAS = {
    "product": PRODUCT,
    "design": DESIGN,
    "acceptance": array(ACCEPTANCE_ROW),
    "expectations": EXPECTATIONS,
    "charter": CHARTER,
    "examine": EXAMINATION_INPUT,
}


CANONICAL_PARTS = (
    ("request", TEXT),
    ("work", WORK),
    ("product", PRODUCT),
    (
        "design",
        replace(
            DESIGN,
            members=tuple(
                (name, array(ADR_SNAPSHOT) if name == "adrs" else spec)
                for name, spec in DESIGN.members
            ),
        ),
    ),
    ("acceptance", table(array(ACCEPTANCE_ROW))),
    ("expectations", EXPECTATIONS),
    ("charter", CHARTER_PART),
    ("examination", table(VERDICT, key="E")),
)

# Shape checks of stored and produced parts. They read the same schemas with each slice's
# requirements removed, so printing keeps the declared specs; requirements are checked per slice.
ROLE_CHECKS = MappingProxyType({**ROLE_SCHEMAS, "design": DESIGN_SHAPE})
CHECKED_PARTS = tuple(
    (
        name,
        _slices_shape(spec)
        if name == "design"
        else table(array(ACCEPTANCE_SHAPE))
        if name == "acceptance"
        else spec,
    )
    for name, spec in CANONICAL_PARTS
)
CANONICAL_SCHEMAS = MappingProxyType(dict(CANONICAL_PARTS))
HANDOFF_INPUT = record(
    schema=STRING,
    version=Spec("raw"),
    scope=choice(
        Project=record(),
        Feature=record(("id",), id=LINE),
        Epic=record(("id",), id=LINE),
    ),
    facts=Spec("raw"),
    counters=Spec("raw"),
    **dict(CANONICAL_PARTS),
)


def _schema_paths(spec, path=""):
    own = (path,) if path else ()
    if spec.kind == "array":
        return (*own, *_schema_paths(spec.members[0], path + "[]"))
    if spec.kind == "table":
        return (
            *own,
            *_schema_paths(
                spec.members[0], path + "." + (spec.key_reference or spec.key_shape)
            ),
        )
    if spec.kind == "choice":
        return (
            *own,
            path + "." + spec.discriminator,
            *(
                child_path
                for _, alternative in spec.members
                for child_path in _schema_paths(alternative, path)
            ),
        )
    if spec.kind == "record":
        return (
            *own,
            *((path + ".id",) if spec.identity else ()),
            *(
                child_path
                for name, child in spec.members
                for child_path in _schema_paths(child, (path + "." + name).lstrip("."))
            ),
        )
    return own


SCHEMA_PATHS = tuple(dict.fromkeys(_schema_paths(HANDOFF_INPUT)))

_INVALID_TEXT = re.compile("[\\x00\\ud800-\\udfff]")
_LINE_BOUNDARY = re.compile("[\\n\\r\\v\\f\\x1c\\x1d\\x1e\\x85\\u2028\\u2029]")
_IDENTITY = re.compile(r"([FPSBLNCYTEDK])[1-9][0-9]*")
_FACT_ID = re.compile(r"F[1-9][0-9]*")
_SCOPE_ID = re.compile(r"[a-z0-9][a-z0-9-]*")
_ADR_PREFIX = re.compile(ADR_PREFIX_PATTERN)
_EMPTY_JSON_ARRAY = re.compile(rb"\[[ \t\r\n]*\]")


class _DuplicateKey(ValueError):
    pass


def _pairs(pairs):
    value = Record((name, freeze(child)) for name, child in pairs)
    if len(value) != len(pairs):
        raise _DuplicateKey("Duplicate JSON key")
    return value


def parse_json(data: bytes, path="input", error_kind="PartInvalid"):
    """Decode strict JSON into immutable mappings and sequences at their boundary."""
    try:
        text = data.decode("utf-8")
        value = json.loads(
            text,
            object_pairs_hook=_pairs,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError("Non-JSON constant " + value)
            ),
        )
        return Built(freeze(value))
    except RecursionError:
        return checked(
            None,
            (
                Defect(
                    f"{error_kind}: {path}",
                    "The JSON document is nested too deeply to decode into immutable values.",
                    "Reduce nested arrays and objects to the structure declared by nwdes schema.",
                ),
            ),
        )
    except (ValueError, UnicodeError, AttributeError) as error:
        return checked(
            None,
            (
                Defect(
                    f"{error_kind}: {path}",
                    str(error),
                    "Supply only the complete original JSON, allowing JSON whitespace but no "
                    "status lines, prose or Markdown fences before or after it. Use strict "
                    "UTF-8 without a BOM or duplicate keys. Use nwdes role verbs to record "
                    "role values; nwdes constructs and serializes their records. Never "
                    "repair JSON in the host or weaken validation.",
                ),
            ),
        )


@dataclass(frozen=True)
class _ValueProblem(Defect):
    path: str
    id_kinds: tuple[str, ...] = ()


def _invalid(
    path,
    why,
    missing=False,
    id_kinds=(),
    *,
    how="Record the value with the role verb's typed flags and declared choices; use its --help or the generated prompt's verb reference.",
):
    return _ValueProblem(
        f"{'MissingFact' if missing else 'PartInvalid'}: {path}",
        why,
        how,
        path,
        id_kinds,
    )


@dataclass(frozen=True)
class UnavailableInput:
    """A failed producer, not an absent or malformed downstream value."""

    defect: Defect


def missing_flag(name):
    flag = "--" + name.replace("_", "-")
    return Defect(
        "MissingFact: " + flag,
        "Required invocation value is absent.",
        "Supply " + flag + ".",
    )


def _missing_work(slice=None):
    path = "product.slices." + slice + ".work" if slice is not None else "work"
    command = (
        "nwdes work set ROOTS SCOPE"
        + (" --slice " + slice if slice is not None else "")
        + " --size S|M|L --value TEXT"
    )
    return _ValueProblem(
        "MissingFact: " + path,
        "The target has no work.",
        "Create the target work with " + command + ".",
        path,
    )


def _absent(value):
    return value is None or (isinstance(value, (list, tuple)) and not value)


PROSE_REASON = "prose, verified by EXAMINE"
PROSE_OWNER = "EXAMINE"
# Design fields that only an oracle can use: a prose-only slice must not carry them.
_PROSE_FORBIDDEN = ("oracle", "verification", "supports", "prefactoring")
_PROSE_PUBLIC_FORBIDDEN = ("stimulus", "expected", "falsifier")
# The command-line flag that supplies each forbidden field, where one exists.
_PROSE_FLAGS = MappingProxyType(
    {
        "oracle": "--oracle",
        "verification": "--command",
        "supports": "--support",
        "public_oracle.stimulus": "--stimulus",
        "public_oracle.expected": "--expected",
        "public_oracle.falsifier": "--falsifier",
    }
)


def is_prose_only(design):
    """Derived, never stored: the slice has targets and every target is a prose asset."""
    rows = design.get("targets") if isinstance(design, Mapping) else None
    return prose.prose_only(
        row.get("path") if isinstance(row, Mapping) else None
        for row in (rows if isinstance(rows, (tuple, list)) else ())
    )


def _supplied_oracle_fields(design):
    """The forbidden fields a design record supplies, in declaration order."""
    fields = design if isinstance(design, Mapping) else EMPTY
    public = fields.get("public_oracle")
    public = public if isinstance(public, Mapping) else EMPTY
    return (
        *(name for name in _PROSE_FORBIDDEN if not _absent(fields.get(name))),
        *(
            f"public_oracle.{name}"
            for name in _PROSE_PUBLIC_FORBIDDEN
            if not _absent(public.get(name))
        ),
    )


def _oracle_on_prose(fields, site):
    """One OracleOnProse refusal per supplied field, each with what, why and how."""
    return tuple(
        _ValueProblem(
            f"OracleOnProse: {site(name)}",
            f"{site(name)} supplies an oracle field, but every target of this slice is a "
            "prose asset, and a prose-only slice holds no executable oracle.",
            "Drop the oracle fields from this slice, or name the machine-contract source "
            "file it changes as a target.",
            site(name),
        )
        for name in fields
    )


def _flag_site(slice):
    """Where a forbidden field is named on the command line: its flag, else its design path."""
    return lambda name: _PROSE_FLAGS.get(name, f"design.slices.{slice or 'new'}.{name}")


def _required_defects(spec, path, value):
    """The required fields a record lacks, reported with the kinds its schema gives them."""
    return tuple(
        _invalid(
            f"{path}.{name}",
            "List requires at least one element."
            if spec.index[name].kind == "array"
            else "Required value is missing.",
            _missing_kind(spec, spec.index[name]),
        )
        for name in spec.required_fields
        if name not in value or _absent(value[name])
    )


def _required_slice_defects(path, design):
    """An oracle-bearing slice's required fields, and its public oracle's when it has one."""
    public = design.get("public_oracle")
    return (
        *_required_defects(SLICE_DESIGN, path, design),
        *(
            _required_defects(PUBLIC_ORACLE, f"{path}.public_oracle", public)
            if isinstance(public, Mapping)
            else ()
        ),
    )


def _slice_requirements(identity, design):
    """A prose-only slice forbids oracle fields; any other slice keeps its required fields."""
    path = f"design.slices.{identity}"
    if is_prose_only(design):
        return _oracle_on_prose(
            _supplied_oracle_fields(design), lambda name: f"{path}.{name}"
        )
    return _required_slice_defects(path, design)


def _design_requirements(design):
    """The per-slice rules of a design record; its shape is checked by DESIGN_SHAPE."""
    slices = design.get("slices") if isinstance(design, Mapping) else None
    if not isinstance(slices, Mapping):
        return ()
    return tuple(
        defect
        for identity, own in slices.items()
        if isinstance(own, Mapping)
        for defect in _slice_requirements(identity, own)
    )


def split_locator(locator):
    """The posix-normalized file of a locator and its line suffix (empty when absent)."""
    path, _, line = locator.partition(":")
    return posixpath.normpath(path), line


# The parts a policy may ask for by dotted path, each with the verb that records the asked item.
# A list is passed through without being named: the rows of acceptance and expectations.
ASKED_VERBS = MappingProxyType(
    {
        "product.scope_out": "product scope-out add",
        "acceptance.covers": "acceptance row add",
        "expectations.rows.promises": "expectations row add",
    }
)
ASKED_PATHS = tuple(ASKED_VERBS)
ASKED_KINDS = tuple(dict.fromkeys(path.split(".")[0] for path in ASKED_PATHS))


def _holds(spec, segments):
    """Whether the record shape holds the member path, lists passed through."""
    if spec.kind == "array":
        return _holds(spec.members[0], segments)
    if not segments:
        return True
    return segments[0] in spec.index and _holds(spec.index[segments[0]], segments[1:])


def _holds_path(path):
    segments = path.split(".")
    root = ROLE_SCHEMAS.get(segments[0])
    return root is not None and _holds(root, segments[1:])


def policy_shape():
    """The members a policy may name: {member: (has a recording verb, is a list of records)}."""
    return {
        **{
            name: (
                spec.kind == "array",
                spec.kind == "array" and spec.members[0].kind == "record",
            )
            for name, spec in RECORDS.members
        },
        **dict.fromkeys(SLICE_MEMBERS, (True, False)),
        **{path: (True, False) for path in ASKED_PATHS if _holds_path(path)},
    }


def recording_verb(member):
    """The verb that records a policy member: its asked path's verb, its slice member's set verb, else its analysis add verb."""
    if member in ASKED_VERBS:
        return ASKED_VERBS[member]
    action = "set" if member in SLICE_MEMBERS else "add"
    return "design " + verb_name(member) + " " + action


def _spec_at(spec, segments):
    """The spec a member path names; a record that does not hold a segment passes it over."""
    if spec.kind == "array":
        return _spec_at(spec.members[0], segments)
    if not segments:
        return spec
    head, rest = segments[0], segments[1:]
    if head in spec.index:
        return _spec_at(spec.index[head], rest)
    return _spec_at(spec, rest)


def member_spec(name):
    """The spec a policy member names: a design analysis in RECORDS, a slice member, or an asked path's part."""
    if name in SLICE_MEMBERS:
        return SLICE_MEMBERS[name]
    segments = name.split(".")
    if len(segments) == 1:
        return _spec_at(RECORDS, segments)
    return _spec_at(ROLE_SCHEMAS[segments[0]], segments[1:])


def asked_spec(spec, segments, minimum):
    """The spec with the member at `segments` required and holding at least `minimum` items.

    A list is passed through without being named, so an acceptance row is reached as
    `covers`. A record that does not hold a segment passes it over, which reaches an
    expectations row through its `rows` list.
    """
    if spec.kind == "array":
        return replace(spec, members=(asked_spec(spec.members[0], segments, minimum),))
    if not segments:
        return spec
    head, rest = segments[0], segments[1:]
    if head not in spec.index:
        return asked_spec(spec, rest, minimum)
    child = spec.index[head]
    if rest:
        updated, required = asked_spec(child, rest, minimum), spec.required
    else:
        updated = (
            replace(child, minimum=minimum, required_error=RequiredError.MissingFact)
            if child.kind == "array"
            else child
        )
        required = (
            (*spec.required, head) if head not in spec.required else spec.required
        )
    return replace(
        spec,
        required=required,
        members=tuple(
            (name, updated if name == head else member) for name, member in spec.members
        ),
    )


def asked_schema(kind, spec, policy):
    """The part's spec with every member the policy asks for under `kind` required."""
    if policy is None:
        return spec
    for member in policy.members.values():
        segments = member.name.split(".")
        if member.minimum and segments[0] == kind:
            spec = asked_spec(spec, segments[1:], member.minimum)
    return spec


@cache
def _parsed_policy(text):
    analyses = RECORDS.index["not_applicable"].members[0].index["analysis"].members
    return role_policy.parse(text, policy_shape(), analyses, tuple(SLICE_MEMBERS))


def parse_policy(text):
    """The policy of policy.toml text, parsed once per distinct text."""
    return _parsed_policy(text)


def _rows(records, analysis):
    rows = records.get(analysis) if isinstance(records, Mapping) else None
    return tuple(rows) if isinstance(rows, (tuple, list)) else ()


def _not_applicable(records, analysis):
    return tuple(
        row
        for row in _rows(records, "not_applicable")
        if isinstance(row, Mapping) and row.get("analysis") == analysis
    )


def _code_targets(rows):
    """Normalized paths of the targets a slice owes coverage for: prose targets owe none."""
    return tuple(
        posixpath.normpath(row["path"])
        for row in (rows if isinstance(rows, (tuple, list)) else ())
        if isinstance(row, Mapping)
        and isinstance(row.get("path"), str)
        and not prose.is_prose_path(row["path"])
    )


def _scopes(design):
    """(path, records, slice identity or None for shared, code target paths) per record scope."""
    if not isinstance(design, Mapping):
        return ()
    shared = design.get("shared")
    slices = design.get("slices")
    found = [("design.shared", shared, None, ())] if isinstance(shared, Mapping) else []
    if isinstance(slices, Mapping):
        found.extend(
            (
                f"design.slices.{identity}",
                own.get("records"),
                identity,
                _code_targets(own.get("targets")),
            )
            for identity, own in slices.items()
            if isinstance(own, Mapping)
        )
    return tuple(found)


def _site(row):
    """The (locator, symbol) a row names for the repository to resolve, or None."""
    if not isinstance(row, Mapping) or row.get("decision") == "CreateNew":
        return None
    locator, symbol = row.get("locator"), row.get("symbol")
    return (
        (locator, symbol)
        if isinstance(locator, str) and isinstance(symbol, str)
        else None
    )


def design_targets(design):
    """(slice identity, path) of each code target a slice owes coverage for."""
    return tuple(
        (identity, target)
        for _, _, identity, targets in _scopes(design)
        if identity is not None
        for target in targets
    )


def reference_sites(data, policy):
    """The (locator, symbol) of every row of a covering analysis, decoded from design bytes."""
    parsed = parse_json(data, "design")
    if isinstance(parsed, Refused) or not isinstance(parsed.value, Mapping):
        return ()
    payload = parsed.value.get("payload")
    return tuple(
        dict.fromkeys(
            site
            for _, records, _, _ in _scopes(payload)
            for member in policy.covering("target")
            for row in _rows(records, member.name)
            if (site := _site(row)) is not None
        )
    )


def verb_name(analysis):
    """The recording verb's name of an analysis: its record's singular, spelled with hyphens."""
    return analysis.removesuffix("s").replace("_", "-")


def _unknown_analysis_defects(scopes, covered):
    names = [member.name for member in covered]
    return [
        Defect(
            f"PartInvalid: {path}.records.not_applicable[{index}].analysis",
            f"{row.get('analysis')!r} is not an analysis the policy covers.",
            "Use one of: " + ", ".join(names) + ".",
        )
        for path, records, _, _ in scopes
        for index, row in enumerate(_rows(records, "not_applicable"), start=1)
        if isinstance(row, Mapping) and row.get("analysis") not in names
    ]


def _blank_reason_defects(scopes):
    return [
        Defect(
            f"PartInvalid: {path}.records.not_applicable[{index}].reason",
            "A reasoned not-applicable needs a non-empty reason; this one is blank.",
            "Write the reason: nwdes design not-applicable add --in SLICE --analysis ANALYSIS --reason TEXT.",
        )
        for path, records, _, _ in scopes
        for index, row in enumerate(_rows(records, "not_applicable"), start=1)
        if isinstance(row, Mapping)
        and not (isinstance(row.get("reason"), str) and row["reason"].strip())
    ]


def _exclusivity_defects(scopes, member):
    analysis = member.name
    verb = verb_name(analysis)
    return [
        Defect(
            f"PartInvalid: {path}.records.{analysis} holds decisions and a not-applicable",
            "A record scope holds either decisions of an analysis or a reasoned not-applicable of it, never both.",
            f"Remove one of them: nwdes design {verb} remove --at N, or nwdes design not-applicable remove --at N.",
        )
        for path, records, _, _ in scopes
        if _rows(records, analysis) and _not_applicable(records, analysis)
    ]


def _shared_records(scopes):
    return next((records for _, records, identity, _ in scopes if identity is None), {})


def _covered_target(analysis, target, records, shared):
    if _not_applicable(records, analysis) or _not_applicable(shared, analysis):
        return True
    return any(
        split_locator(row.get("locator"))[0] == target
        for source in (records, shared)
        for row in _rows(source, analysis)
        if isinstance(row, Mapping) and isinstance(row.get("locator"), str)
    )


def _target_coverage_defects(scopes, member):
    analysis = member.name
    shared = _shared_records(scopes)
    return [
        Defect(
            f"MissingFact: {path} target {target} has no {analysis} decision",
            f"Each code target of a slice needs a record of {analysis} or a reasoned not-applicable before the design closes.",
            f"Record it with nwdes design {verb_name(analysis)} add --in {identity} {member.shape}, or nwdes design not-applicable add --in {identity} --analysis {analysis} --reason TEXT.",
        )
        for path, records, identity, targets in scopes
        if identity is not None
        for target in targets
        if not _covered_target(analysis, target, records, shared)
    ]


def _design_coverage_defects(scopes, member):
    """A design with code targets owes one record or one reasoned not-applicable of each design-level analysis."""
    analysis = member.name
    if not any(targets for _, _, _, targets in scopes):
        return []
    if any(
        _rows(records, analysis) or _not_applicable(records, analysis)
        for _, records, _, _ in scopes
    ):
        return []
    identity = next(identity for _, _, identity, targets in scopes if targets)
    return [
        Defect(
            f"MissingFact: design has no {analysis} record",
            f"A design with code targets needs a record of {analysis} or a reasoned not-applicable before the design closes.",
            f"Record it with nwdes design {verb_name(analysis)} add --in {identity} {member.shape}, or nwdes design not-applicable add --in {identity} --analysis {analysis} --reason TEXT.",
        )
    ]


def _resolution_defects(scopes, member, resolution):
    return [
        Defect(
            f"PartInvalid: {path}.records.{member.name}[{index}] names {site[0]} and {site[1]}",
            f"The locator {site[0]} and symbol {site[1]} do not resolve: the file must exist under the repository root, the line must lie within it and the symbol must occur in it.",
            f"Correct the locator or symbol, or remove the row with nwdes design {verb_name(member.name)} remove --at {index}.",
        )
        for path, records, _, _ in scopes
        for index, row in enumerate(_rows(records, member.name), start=1)
        if (site := _site(row)) is not None and resolution.get(site) is not True
    ]


def _declares(value):
    return isinstance(value, Mapping) and bool(value)


def _declared_slices(design, member):
    """The identities of the slices that hold their own record of a slice member."""
    slices = design.get("slices") if isinstance(design, Mapping) else None
    if not isinstance(slices, Mapping):
        return frozenset()
    return frozenset(
        identity
        for identity, own in slices.items()
        if isinstance(own, Mapping) and _declares(own.get(member.name))
    )


def _slice_exclusivity_defects(design, scopes, member):
    """A slice holds its declaration of a slice member or a reasoned not-applicable of it, never both."""
    analysis = member.name
    declared = _declared_slices(design, member)
    return [
        Defect(
            f"PartInvalid: {path}.{analysis} holds a declaration and a not-applicable",
            f"A slice holds either its {analysis} declaration or a reasoned not-applicable of {analysis}, never both.",
            f"Remove one of them: nwdes design not-applicable remove --at N, or nwdes design {verb_name(analysis)} remove.",
        )
        for path, records, identity, _ in scopes
        if identity in declared and _not_applicable(records, analysis)
    ]


def _slice_coverage_defects(design, scopes, member):
    """A slice with a code target owes one decision of a slice member: its own record or a reasoned not-applicable in the slice or the shared record."""
    analysis = member.name
    declared = _declared_slices(design, member)
    shared = _shared_records(scopes)
    return [
        Defect(
            f"MissingFact: {path} targets {', '.join(targets)} have no {analysis} decision",
            f"Each slice with a code target needs a record of {analysis} or a reasoned not-applicable before the design closes.",
            f"Record it with nwdes {recording_verb(analysis)} --in {identity} {member.shape}, or nwdes design not-applicable add --in {identity} --analysis {analysis} --reason TEXT.",
        )
        for path, records, identity, targets in scopes
        if identity is not None
        and targets
        and identity not in declared
        and not _not_applicable(records, analysis)
        and not _not_applicable(shared, analysis)
    ]


def _design_obligations(design, policy, resolution):
    """Presence and existence of the analyses the policy covers, per record scope.

    A scope holds at most one of an analysis's rows or its not-applicable. Every code target of
    a slice has a row of each target-covered analysis, paired by path, or a not-applicable of it
    in the slice or the shared record. When any slice has a code target, each design-covered
    analysis has a row or a not-applicable in some scope, and each slice-covered member is
    recorded once: by its slice, or by a not-applicable in the slice or the shared record; a slice
    holds one of the two, never both. Each named locator and symbol must resolve (resolution maps
    the shell's answers). Every not-applicable names a covered analysis.
    """
    scopes = _scopes(design)
    targeted = policy.covering("target")
    designed = policy.covering("design")
    sliced = policy.covering("slice")
    defects = [
        *_unknown_analysis_defects(scopes, (*targeted, *designed, *sliced)),
        *_blank_reason_defects(scopes),
    ]
    for member in (*targeted, *designed):
        defects.extend(_exclusivity_defects(scopes, member))
    for member in targeted:
        defects.extend(_target_coverage_defects(scopes, member))
        defects.extend(_resolution_defects(scopes, member, resolution))
    for member in designed:
        defects.extend(_design_coverage_defects(scopes, member))
    for member in sliced:
        defects.extend(_slice_exclusivity_defects(design, scopes, member))
        defects.extend(_slice_coverage_defects(design, scopes, member))
    return tuple(defects)


def _is_prose_row(row, facts):
    """A NotTested row whose reason is the prose reason: the one row a prose-only slice holds."""
    disposition = row.get("disposition") if isinstance(row, Mapping) else None
    return (
        isinstance(disposition, Mapping)
        and disposition.get("kind") == "NotTested"
        and facts.get(disposition.get("reason")) == PROSE_REASON
    )


def _acceptance_requirements(acceptance, facts):
    """A row of a slice that is not prose-only keeps its stimulus; a prose row has none."""
    if not isinstance(acceptance, Mapping):
        return ()
    return tuple(
        _invalid(
            f"acceptance.{identity}[{index}].stimulus",
            "Required value is missing.",
            True,
        )
        for identity, rows in acceptance.items()
        if isinstance(rows, (tuple, list))
        for index, row in enumerate(rows)
        if isinstance(row, Mapping)
        and not _is_prose_row(row, facts)
        and _absent(row.get("stimulus"))
    )


def _disposition_requirements(raw, facts):
    """A prose-only slice holds exactly one NotTested row, and it is the prose row.

    Non-prose slices are unconstrained here: an authored acceptance part may hold NotTested
    rows of any reason, owned by the acceptance designer. Mirrors _acceptance_for_design.
    """
    design = raw.get("design")
    acceptance = raw.get("acceptance")
    slices = design.get("slices") if isinstance(design, Mapping) else None
    if not isinstance(slices, Mapping) or not isinstance(acceptance, Mapping):
        return ()
    product = raw.get("product")
    product_ids = (
        {
            row.get("id")
            for row in (product.get("slices") or ())
            if isinstance(row, Mapping)
        }
        if isinstance(product, Mapping)
        else set()
    )
    defects = []
    for identity, own in slices.items():
        if identity not in product_ids or not isinstance(own, Mapping):
            continue
        rows = acceptance.get(identity)
        rows = tuple(rows) if isinstance(rows, (tuple, list)) else ()
        prose_rows = tuple(
            index for index, row in enumerate(rows) if _is_prose_row(row, facts)
        )
        if is_prose_only(own) and (len(rows) != 1 or prose_rows != (0,)):
            defects.append(
                _invalid(
                    f"acceptance.{identity}",
                    "A prose-only slice holds exactly one NotTested row with reason "
                    f"prose, verified by EXAMINE; this slice holds {len(rows)} row(s), "
                    f"of which {len(prose_rows)} is such a row.",
                    True,
                    how="Record the slice again with nwdes slice set so its prose row "
                    "is built, or name the machine-contract source file as a target.",
                )
            )
    return tuple(defects)


def _stored_requirements(raw, facts):
    """Rules a stored handoff meets beyond its shape: per-slice oracle and acceptance rules."""
    return (
        *_design_requirements(raw.get("design")),
        *_acceptance_requirements(raw.get("acceptance"), facts),
        *_disposition_requirements(raw, facts),
    )


def prose_acceptance_row(promises, observation):
    """The one NotTested row of a prose-only slice: EXAMINE verifies the prose it covers."""
    return {
        "covers": tuple(promises),
        "expected": observation,
        "user_result": observation,
        "disposition": {
            "kind": "NotTested",
            "reason": PROSE_REASON,
            "owner": PROSE_OWNER,
        },
    }


def _acceptance_for_design(acceptance, design, product, facts, counters):
    """Each prose-only slice holds exactly one NotTested row; any other slice drops a prose row."""
    rows = dict(acceptance)
    product_rows = {row["id"]: row for row in (product or EMPTY).get("slices", ())}
    for identity, own in ((design or EMPTY).get("slices") or EMPTY).items():
        product_row = product_rows.get(identity)
        if product_row is None:
            continue
        kept = tuple(
            row for row in rows.get(identity, ()) if not _is_prose_row(row, facts)
        )
        if is_prose_only(own):
            built, facts, counters = _build(
                ACCEPTANCE_ROW,
                prose_acceptance_row(
                    product_row.get("promises", ()),
                    facts[product_row["observation"]],
                ),
                None,
                facts,
                counters,
            )
            kept = (built,)
        if kept:
            rows[identity] = kept
        else:
            rows.pop(identity, None)
    return freeze(rows), facts, counters


_COVERAGE_TEST_LISTS = ("architectural_tests", "contract_tests")


def _mapping(value):
    return value if isinstance(value, Mapping) else EMPTY


def _sequence(value):
    return tuple(value) if isinstance(value, (tuple, list)) else ()


def _part_of(previous, name):
    """A stored part of the previous handoff: a Record names it, a Handoff holds it as an attribute."""
    if previous is None:
        return None
    return (
        previous.get(name)
        if isinstance(previous, Mapping)
        else getattr(previous, name, None)
    )


def _binds_obligations(row):
    """Whether a Tested row may bind obligation keys: it names obligation slots, or covers a law or test by its bare id, the legacy binding of a retained row."""
    disposition = _mapping(row.get("disposition"))
    return bool(_sequence(disposition.get("obligations"))) or any(
        isinstance(identity, str) and identity[:1] in ("L", "T")
        for identity in _sequence(row.get("covers"))
    )


def coverage_locators(verb, output, previous):
    """The test locators the coverage rule reads: those of the Tested rows that bind obligations, stored and newly produced."""
    if verb != "acceptance":
        return ()
    stored = previous.part("acceptance") if isinstance(previous, HandoffInput) else None
    row_sets = (*_mapping(stored).values(), _sequence(getattr(output, "payload", None)))
    locators = (
        _mapping(row.get("disposition")).get("test")
        for rows in row_sets
        for row in _tested_rows(rows)
        if _binds_obligations(row)
    )
    return tuple(dict.fromkeys(a for a in locators if isinstance(a, str)))


def _coverage_records(design):
    """Each law and architectural or contract test, with its scope: the slice that records it, or None when shared."""
    scopes = (
        (None, _mapping(_mapping(design).get("shared"))),
        *(
            (identity, _mapping(_mapping(own).get("records")))
            for identity, own in _mapping(_mapping(design).get("slices")).items()
        ),
    )
    return tuple(
        (record, scope)
        for scope, records in scopes
        for name in ("laws", *_COVERAGE_TEST_LISTS)
        for record in _sequence(records.get(name))
        if isinstance(record, Mapping) and isinstance(record.get("id"), str)
    )


def _tested_rows(rows):
    return tuple(
        row
        for row in _sequence(rows)
        if isinstance(row, Mapping)
        and _mapping(row.get("disposition")).get("kind") == "Tested"
    )


def obligation_keys(record):
    """The obligation keys a design record owes, derived from its id and treatment and never stored.

    A finite law owes one key per case, a broad law its generative test and one per must-include
    item, a NoTest law none, and each architectural or contract test its own key. Pure.
    """
    identity = record["id"]
    if identity.startswith("T"):
        return (identity,)
    treatment = _mapping(record.get("treatment"))
    if treatment.get("kind") == "Finite":
        return tuple(
            dict.fromkeys(
                f"{identity}/{case}" for case in _sequence(treatment.get("cases"))
            )
        )
    if treatment.get("kind") == "Broad":
        items = _sequence(_mapping(treatment.get("generator")).get("must_include"))
        return tuple(
            dict.fromkeys((identity, *(f"{identity}/{item}" for item in items)))
        )
    return ()


def owed_obligations(design, slice):
    """Each obligation key the slice owes, with the scope of its record: the slice, or None when shared."""
    return tuple(
        (key, scope)
        for record, scope in _coverage_records(design)
        if scope in (None, slice)
        for key in obligation_keys(record)
    )


def owed_obligation_texts(design, facts, slice):
    """Each obligation key the slice owes, with the case text the refusal names for a record the slice owns.

    A shared record's text stays in the architecture brief, so its key carries None. Pure.
    """
    index = {record["id"]: record for record, _ in _coverage_records(design)}
    return tuple(
        (key, None if scope is None else _obligation_text(index, facts, key))
        for key, scope in owed_obligations(design, slice)
    )


def _bound_keys(row, index, retained):
    """The obligation keys one acceptance row binds: its own slots and, for a retained row, every key of each bare id it covers."""
    disposition = _mapping(row.get("disposition"))
    if disposition.get("kind") != "Tested":
        return ()
    legacy = (
        tuple(
            key
            for identity in _sequence(row.get("covers"))
            if isinstance(identity, str) and identity in index
            for key in obligation_keys(index[identity])
        )
        if retained
        else ()
    )
    slots = tuple(
        key for key in _sequence(disposition.get("obligations")) if isinstance(key, str)
    )
    return tuple(dict.fromkeys((*slots, *legacy)))


def _retained_contents(previous, slice):
    """The content of each stored acceptance row of the slice, with its authored text recovered.

    A draft row carries text while a stored row carries fact ids, so a retained row is recognised
    only once both are read as text.
    """
    facts = _part_of(previous, "facts")
    if not isinstance(facts, Mapping):
        return ()
    rows = _sequence(_mapping(_part_of(previous, "acceptance")).get(slice))
    return tuple(_content(expanded(ACCEPTANCE_ROW, row, facts)) for row in rows)


def _binding_rows(design, acceptance, retained, slice):
    """Each acceptance row that binds obligations, as (slice, row, keys).

    A row of the slice being closed is retained when its content equals a stored row of that slice
    (retained holds those contents), and then binds the keys of the bare ids it covers. Rows of
    other slices are stored, so retained.
    """
    index = {record["id"]: record for record, _ in _coverage_records(design)}
    kept = list(retained)
    return tuple(
        (identity, row, keys)
        for identity, rows in acceptance.items()
        for row in _sequence(rows)
        if isinstance(row, Mapping)
        for keys in (
            _bound_keys(row, index, identity != slice or _content(row) in kept),
        )
        if keys
    )


def _obligation_text(index, facts, key):
    """The case text, must-include item, statement or obligation a key names."""
    identity, _, case = key.partition("/")
    texts = _mapping(facts)
    if case:
        return texts.get(case, case)
    record = index.get(identity, EMPTY)
    field = "obligation" if identity.startswith("T") else "statement"
    return texts.get(record.get(field), "")


def _obligation_defects(design, previous, acceptance, slice, resolution):
    """Every obligation the slice owes is bound by a Tested row.

    A slice-scoped obligation is bound by a row of its own slice; a shared one by a row of any slice,
    checked once every product slice holds acceptance rows. A NoTest law owes no key. Each owed key
    with no binding row is listed (OpenObligation) in one pass. A broad law's generative key must be
    bound by a row whose test resolves (resolution maps each locator to the shell's answer), as the
    old MissingGenerativeTest required. Pure: reads only its parameters and the previous handoff.
    """
    facts = _part_of(previous, "facts")
    retained = _retained_contents(previous, slice)
    index = {record["id"]: record for record, _ in _coverage_records(design)}
    product = _mapping(_mapping(design).get("slices"))
    shared_checked = bool(product) and all(
        _sequence(acceptance.get(identity)) for identity in product
    )
    bindings = _binding_rows(design, acceptance, retained, slice)
    defects = []
    for key, scope in owed_obligations(design, slice):
        if scope is None and not shared_checked:
            continue
        bound = tuple(
            binding
            for binding in bindings
            if key in binding[2] and (scope is None or binding[0] == slice)
        )
        if not bound:
            defects.append(
                Defect(
                    f"OpenObligation: {key} {_obligation_text(index, facts, key)}",
                    f"{key} is an obligation of the design that no Tested row of the acceptance part binds.",
                    f"Record a Tested row of {slice} whose obligations list {key}, with the test that observes it.",
                )
            )
        elif _generative_key(index, key) and not any(
            resolution.get(_mapping(row.get("disposition")).get("test")) is True
            for _, row, _ in bound
        ):
            defects.append(
                Defect(
                    f"UnresolvedTest: {key} cites {_mapping(bound[0][1].get('disposition')).get('test')}",
                    f"{key} is a broad law and no test bound to it resolves to a generative test that exists.",
                    f"Cite a test of the form path::name whose name occurs as a whole word in a readable file under the repository root, and record it in the Tested row binding {key}.",
                )
            )
    return tuple(defects)


def _generative_key(index, key):
    """Whether a key is a broad law's generative-test key: a law id, not a case, of treatment Broad."""
    return (
        "/" not in key
        and _mapping(_mapping(index.get(key)).get("treatment")).get("kind") == "Broad"
    )


def _prose_withdrawals(previous, identity, built):
    """Notices for retained oracle fields that a slice made prose-only no longer carries."""
    retained = ((previous.design or EMPTY).get("slices") or EMPTY).get(
        identity
    ) or EMPTY
    retained_public = retained.get("public_oracle") or EMPTY
    built_public = built.get("public_oracle") or EMPTY
    dropped = (
        *(name for name in _PROSE_FORBIDDEN if name in retained and name not in built),
        *(
            f"public_oracle.{name}"
            for name in _PROSE_PUBLIC_FORBIDDEN
            if name in retained_public and name not in built_public
        ),
    )
    return tuple(
        f"WITHDRAWN WHAT: design.slices.{identity}.{name} | WHY: slice set made "
        f"{identity} prose-only, so its retained {name} is no longer carried. | "
        "HOW: a prose-only slice holds no oracle fields; name a machine-contract source "
        "file as a target to keep an oracle."
        for name in dropped
    )


@dataclass(frozen=True)
class TableReference:
    kind: str
    identity: str
    path: str


@dataclass(frozen=True)
class NormalizedInput:
    value: object
    absent_references: tuple[TableReference, ...] = ()


def _normalized_value(spec, value):
    """Normalize a subtree that cannot contain keyed references, without path bookkeeping."""
    if value is None or isinstance(value, (str, int, float)):
        return value
    if spec is None:
        return freeze(value)
    if spec.kind == "choice" and isinstance(value, _MAPPINGS):
        alternative = (
            spec.index.get(value.get(spec.discriminator))
            if isinstance(value.get(spec.discriminator), str)
            else None
        )
        return _normalized_value(alternative, value)
    if spec.kind == "array" and isinstance(value, (tuple, list)):
        return tuple(_normalized_value(spec.members[0], child) for child in value)
    if spec.kind == "record" and isinstance(value, _MAPPINGS):
        return Record(
            (name, _normalized_value(spec.index.get(name), child))
            for name, child in value.items()
            if name not in spec.allowed or not _absent(child)
        )
    return freeze(value)


def normalize_input(spec, value, path=""):
    """Normalize declared fields while retaining unknown keys and absent table targets."""
    if spec is None or not spec.has_table_references:
        return NormalizedInput(_normalized_value(spec, value))
    if spec.kind == "choice" and isinstance(value, _MAPPINGS):
        alternative = (
            spec.index.get(value.get(spec.discriminator))
            if isinstance(value.get(spec.discriminator), str)
            else None
        )
        return normalize_input(alternative, value, path)
    if spec.kind == "array" and isinstance(value, (tuple, list)):
        children = tuple(
            normalize_input(spec.members[0], child, f"{path}[{index}]")
            for index, child in enumerate(value)
        )
        return NormalizedInput(
            tuple(child.value for child in children),
            tuple(
                reference for child in children for reference in child.absent_references
            ),
        )
    if spec.kind in ("record", "table") and isinstance(value, _MAPPINGS):

        def member(pair):
            name, child = pair
            child_path = (path + "." + name).lstrip(".")
            child_spec = (
                spec.members[0] if spec.kind == "table" else spec.index.get(name)
            )
            declared = spec.kind == "table" or name in spec.allowed
            if (
                declared
                and _absent(child)
                and not (spec.kind == "table" and spec.total)
            ):
                omitted = (
                    (TableReference(spec.key_reference, name, child_path),)
                    if spec.kind == "table" and spec.key_reference
                    else ()
                )
                return None, omitted
            normalized = normalize_input(child_spec, child, child_path)
            return (name, normalized.value), normalized.absent_references

        children = tuple(map(member, value.items()))
        return NormalizedInput(
            Record(entry for entry, _ in children if entry is not None),
            tuple(reference for _, references in children for reference in references),
        )
    return NormalizedInput(freeze(value))


def _id_defects(prefix, value, path, why=None):
    if _absent(value):
        return ()
    return (
        ()
        if isinstance(value, str)
        and value.startswith(prefix)
        and _IDENTITY.fullmatch(value)
        else (
            _invalid(
                path,
                why
                if why is not None
                else f"Expected an existing {prefix or 'record'} id, or omit id to create a record.",
                id_kinds=(prefix,) if prefix != "F" else (),
            ),
        )
    )


def _check(spec, value, path, canonical=False, facts=EMPTY):
    if isinstance(value, UnavailableInput):
        return (value.defect,)
    if spec.kind in (
        "text",
        "line",
        "command",
        "string",
        "reference",
        "draft_reference",
        "obligation",
        "prefix",
    ):
        if not isinstance(value, str):
            return (_invalid(path, "Expected text."),)
        if spec.kind == "text" and canonical:
            if not _FACT_ID.fullmatch(value):
                return (
                    (_invalid(path, "Text contains NUL or invalid Unicode."),)
                    if _INVALID_TEXT.search(value)
                    else _id_defects("F", value, path)
                )
            if facts is None:
                return ()
            return (
                ()
                if value in facts
                else (
                    _ValueProblem(
                        f"DanglingReference: {path}",
                        f"Unknown fact {value}.",
                        "Use a fact assigned by nwdes.",
                        path,
                    ),
                )
            )
        if "\0" in value if value.isascii() else _INVALID_TEXT.search(value):
            return (_invalid(path, "Text contains NUL or invalid Unicode."),)
        if spec.kind == "draft_reference" and not any(
            re.fullmatch(re.escape(prefix) + r"[1-9][0-9]*", value)
            for prefix in spec.members
        ):
            return (_invalid(path, "Expected an assigned draft-local observation id."),)
        if spec.kind == "obligation" and not _OBLIGATION_KEY.fullmatch(value):
            return (
                _invalid(
                    path,
                    "Expected an assigned obligation key: L<n>, L<n>/F<n> or T<n>.",
                ),
            )
        if spec.kind == "reference" and not (
            _IDENTITY.fullmatch(value) or (not spec.members and value == "observation")
        ):
            return (_invalid(path, "Expected an assigned record id."),)
        if spec.kind == "prefix" and value and not _ADR_PREFIX.fullmatch(value):
            return (
                _invalid(
                    path,
                    "Use an uppercase ADR prefix with uppercase hyphen-separated segments, or the empty prefix.",
                ),
            )
        if spec.kind in ("line", "command") and (
            not value or value != value.strip() or _LINE_BOUNDARY.search(value)
        ):
            return (
                _invalid(
                    path,
                    "Single-line field is empty, contains a line boundary, or has edge whitespace.",
                ),
            )
        return ()
    if spec.kind == "enum":
        return (
            () if value in spec.members else (_invalid(path, "Unknown enum spelling."),)
        )
    if spec.kind == "adr_status":
        return (
            ()
            if isinstance(value, str) and re.fullmatch(ADR_STATUS_PATTERN, value)
            else (_invalid(path, "Unknown enum spelling."),)
        )
    if spec.kind == "array":
        if not isinstance(value, (list, tuple)):
            return (_invalid(path, "Expected a list.", id_kinds=spec.id_kinds),)
        return (
            *(
                (
                    _invalid(
                        path,
                        "List requires at least one element.",
                        id_kinds=spec.id_kinds,
                    ),
                )
                if len(value) < spec.minimum
                else ()
            ),
            *(
                defect
                for index, child in enumerate(value)
                for defect in _check(
                    spec.members[0], child, f"{path}[{index}]", canonical, facts
                )
            ),
        )
    if spec.kind == "choice":
        if (
            not isinstance(value, _MAPPINGS)
            or not isinstance(value.get(spec.discriminator), str)
            or value[spec.discriminator] not in spec.index
        ):
            return (
                _invalid(
                    path,
                    "Expected one declared " + spec.discriminator + " alternative.",
                    id_kinds=spec.id_kinds,
                ),
            )
        alternative = spec.index[value[spec.discriminator]]
        return _check(
            alternative,
            {
                name: child
                for name, child in value.items()
                if name != spec.discriminator
            },
            path,
            canonical,
            facts,
        )
    if not isinstance(value, _MAPPINGS):
        return (_invalid(path, "Expected an object.", id_kinds=spec.id_kinds),)
    if spec.kind == "table":
        return tuple(
            defect
            for name, child in value.items()
            for defect in (
                *(
                    _id_defects(spec.key_shape, name, path + "." + name)
                    if spec.key_shape
                    else ()
                ),
                *_check(spec.members[0], child, path + "." + name, canonical, facts),
            )
        )
    members = spec.index
    allowed = spec.allowed
    data = value._index if isinstance(value, Record) else value
    return (
        *(
            (
                _invalid(
                    path + ".id",
                    "Canonical record identity is missing.",
                    True,
                    (spec.identity,),
                ),
            )
            if spec.identity and canonical and _absent(data.get("id"))
            else _id_defects(spec.identity, data["id"], path + ".id")
            if spec.identity and "id" in data
            else ()
        ),
        *(
            ()
            if isinstance(value, Record) and value._index.keys() <= allowed
            else tuple(
                _invalid(path + "." + name, "Unknown field.")
                for name in data
                if name not in allowed
            )
        ),
        *(
            _invalid(
                path + "." + name,
                "List requires at least one element."
                if members[name].kind == "array"
                else "Required value is missing.",
                _missing_kind(spec, members[name]),
                members[name].id_kinds,
            )
            for name in spec.required_fields
            if name not in data or _absent(data[name])
        ),
        *(
            defect
            for name, child in data.items()
            if name in members and not _absent(child)
            for defect in _check(
                members[name], child, path + "." + name, canonical, facts
            )
        ),
        *(
            (_invalid(path, "Choose only one of " + ", ".join(spec.exclusive) + "."),)
            if spec.exclusive
            and sum(not _absent(data.get(name)) for name in spec.exclusive) > 1
            else ()
        ),
    )


def check_adr_row(row, path):
    return _check(ADR_ROW, row, path)


def check_adr_selector(value, path):
    return _check(LINE, value, path)


def adr_body_units(row, path):
    def unit(name):
        value = row.get(name)
        problems = (
            (_invalid(path + "." + name, "Required value is missing.", True),)
            if _absent(value)
            else _check(ADR_BODY.index[name], value, path + "." + name)
        )
        return UnavailableInput(problems[0]) if problems else value

    return Record((name, unit(name)) for name in ADR_BODY_FIELDS)


def adr_prefix_input(row):
    prefix = row.get("prefix", "")
    return checked(prefix, _check(PREFIX, prefix, "design.adrs.prefix"))


def adr_status_input(row):
    status = row.get("status")
    return checked(
        status, _check(ADR_ROW.index["status"], status, "design.adrs.status")
    )


FLAG_SPECS = (
    ("request", TEXT, "--request"),
    ("size", WORK.index["size"], "work.size"),
    ("value", TEXT, "work.value"),
    ("paradigm", DESIGN.index["paradigm"], "--paradigm"),
    ("observation", TEXT, "--observation"),
    ("oracle", LINE, "oracle"),
    ("command", array(COMMAND), "verification"),
    ("stimulus", TEXT, "stimulus"),
    ("expected", TEXT, "expected"),
    ("falsifier", TEXT, "falsifier"),
    ("delta", TEXT, "work.rework.delta"),
    ("reason", TEXT, "work.rework.reason"),
)


def _flag_unit(spec, value, path):
    if isinstance(value, UnavailableInput):
        return value
    if spec.kind == "array" and isinstance(value, (tuple, list)):
        return tuple(
            _flag_unit(spec.members[0], child, f"{path}[{index}]")
            for index, child in enumerate(value)
        )
    problems = _check(spec, value, path)
    return UnavailableInput(problems[0]) if problems else freeze(value)


def issue(counters, kind):
    number = counters.get(kind, 0) + 1
    return f"{kind}{number}", Record((*counters.items(), (kind, number)))


def intern(facts, counters, text):
    existing = next(
        (identity for identity, value in facts.items() if value == text), None
    )
    if existing:
        return existing, facts, counters
    identity, issued = issue(counters, "F")
    return identity, Record((*facts.items(), (identity, text))), issued


def _content(value):
    if value is None or isinstance(value, (str, int)):
        return value
    if isinstance(value, Mapping):
        return {
            name: _content(child)
            for name, child in value.items()
            if name != "id" and child not in (None, (), [], EMPTY)
        }
    if isinstance(value, (tuple, list)):
        return tuple(map(_content, value))
    return value


class InspectedFields(Record):
    """Field units of a refused input, potentially including unavailable leaves."""


def _prior_row(spec, child, previous, facts, content=None):
    if not spec.has_ids or not isinstance(child, Mapping):
        return None
    if isinstance(previous, UnavailableInput):
        return previous
    if isinstance(child.get("id"), UnavailableInput):
        return child["id"]
    rows = previous if isinstance(previous, (tuple, list)) else ()
    if child.get("id"):
        return next(
            (
                entry
                for entry in rows
                if isinstance(entry, Mapping) and entry.get("id") == child["id"]
            ),
            None,
        )
    if spec.identity in ("D", "K"):
        return None
    meaning = _content(child) if content is None else content
    if isinstance(child, InspectedFields):
        missing = _unavailable(meaning)
        if missing is not None:
            return missing
    if not isinstance(facts, (InspectedFields, UnavailableInput)):
        return next(
            (
                entry
                for entry in rows
                if isinstance(entry, Mapping)
                and _content(expanded(spec, entry, facts)) == meaning
            ),
            None,
        )
    candidates = tuple(
        (entry, _content(expanded(spec, entry, facts)))
        for entry in rows
        if isinstance(entry, Mapping)
    )
    matched = next(
        (
            entry
            for entry, content in candidates
            if _unavailable(content) is None and content == meaning
        ),
        None,
    )
    return (
        matched
        if matched is not None
        else next(
            (
                missing
                for _, content in candidates
                if (missing := _unavailable(content)) is not None
            ),
            None,
        )
    )


def _retained_rows(value, previous, facts, spec=None):
    if spec is not None and spec.identity in ("D", "K"):
        return tuple((row, _content(row), index) for index, row in enumerate(value))
    observations = {
        facts[row["observation"]]: row["id"]
        for row in (previous if isinstance(previous, (tuple, list)) else ())
        if isinstance(row, Mapping)
        and isinstance(facts, Mapping)
        and isinstance(row.get("observation"), str)
        and isinstance(facts.get(row["observation"]), str)
        and isinstance(row.get("id"), str)
    }

    def content(row):
        raw = _content(row)
        return (
            {
                **raw,
                "depends_on": tuple(
                    observations.get(reference, reference)
                    for reference in row["depends_on"]
                ),
            }
            if isinstance(row, Mapping)
            and isinstance(row.get("depends_on"), (tuple, list))
            else raw
        )

    def retain(groups, indexed):
        position, row = indexed
        key = content(row)
        match = next(
            (
                index
                for index, (_, prior_key, _) in enumerate(groups)
                if prior_key == key
            ),
            None,
        )
        if match is None:
            return (*groups, (row, key, position))
        prior, _, _ = groups[match]
        if isinstance(row, Mapping) and row.get("id") and not prior.get("id"):
            return tuple(
                (row, key, position) if index == match else group
                for index, group in enumerate(groups)
            )
        return groups

    return reduce(retain, enumerate(value), ())


@dataclass(frozen=True)
class IdentityInspection:
    path: str
    invalid_paths: tuple[str, ...]

    def child(self, suffix):
        return IdentityInspection(self.path + suffix, self.invalid_paths)

    def unavailable(self):
        return bool(self.invalid_paths) and any(
            path == self.path
            or path.startswith(self.path + ".")
            or path.startswith(self.path + "[")
            for path in self.invalid_paths
        )


def _project_ids(spec, value, previous, facts, inspection):
    """Resolve retained identities without issuing identities for new content."""
    if not spec.has_ids or isinstance(previous, UnavailableInput):
        return ()
    if spec.kind == "choice":
        alternative = (
            spec.index.get(value.get(spec.discriminator))
            if isinstance(value, Mapping)
            and isinstance(value.get(spec.discriminator), str)
            else None
        )
        return (
            _project_ids(alternative, value, previous, facts, inspection)
            if alternative
            else _ids(spec, previous)
        )
    if spec.kind == "array":
        if not isinstance(value, (tuple, list)):
            return _ids(spec, previous)
        child_spec = spec.members[0]
        if any(
            inspection.child(f"[{index}]").unavailable()
            and not (
                isinstance(child, Mapping)
                and isinstance(child.get("id"), str)
                and _IDENTITY.fullmatch(child["id"])
            )
            for index, child in enumerate(value)
        ):
            return _ids(spec, previous)
        return tuple(
            identity
            for child, meaning, index in _retained_rows(
                value, previous, facts, child_spec
            )
            for identity in _project_ids(
                child_spec,
                child,
                _prior_row(child_spec, child, previous, facts, meaning),
                facts,
                inspection.child(f"[{index}]"),
            )
        )
    if not isinstance(value, Mapping):
        return _ids(spec, previous)
    if spec.kind == "table":
        return tuple(
            identity
            for name, child in value.items()
            for identity in _project_ids(
                spec.members[0],
                child,
                (previous or {}).get(name),
                facts,
                inspection.child("." + name),
            )
        )
    identity = value.get("id") or (
        (previous or {}).get("id") if spec.identity else None
    )
    return (
        *(
            (identity,)
            if spec.identity
            and isinstance(identity, str)
            and not _id_defects(spec.identity, identity, "")
            else ()
        ),
        *(
            identity
            for name, child_spec in spec.id_children
            if name in value
            for identity in _project_ids(
                child_spec,
                value[name],
                (previous or {}).get(name),
                facts,
                inspection.child("." + name),
            )
        ),
    )


def _future_reference_checks(previous, kind, decoded):
    if kind not in ("product", "design", "expectations"):
        return ()
    if isinstance(getattr(previous, kind), UnavailableInput):
        return ()
    kinds = ROLE_SCHEMAS[kind].id_kinds
    payload = decoded.payload
    current_uses = kind != "product" and _mentions_id_kinds(
        ROLE_SCHEMAS[kind], payload, kinds
    )
    if not current_uses and not any(
        _mentions_id_kinds(spec, getattr(previous, name), kinds)
        for name, spec in CANONICAL_PARTS
        if name != kind and spec.has_references
    ):
        return ()
    inspection = IdentityInspection(
        kind,
        tuple(
            problem.path
            for problem in decoded.shape_errors
            if isinstance(problem, _ValueProblem)
        ),
    )
    projected = _project_ids(
        ROLE_SCHEMAS[kind], payload, getattr(previous, kind), previous.facts, inspection
    )
    slices = (
        tuple(identity for identity in projected if identity.startswith("S"))
        if kind == "product"
        else slice_ids(previous)
    )

    def remaining(name):
        current = getattr(previous, name)
        if slices is None:
            return current
        if isinstance(current, UnavailableInput):
            return current
        if kind == "expectations" and name == "examination":
            return Record(
                (identity, verdict)
                for identity, verdict in current.items()
                if identity in projected
            )
        if kind == "product" and name == "acceptance":
            return Record(
                (identity, child)
                for identity, child in current.items()
                if identity in slices
            )
        if kind == "product" and name == "design" and current is not None:
            slice_parts = current.get("slices", EMPTY)
            return Record(
                (
                    *(
                        (key, child)
                        for key, child in current.items()
                        if key != "slices"
                    ),
                    (
                        "slices",
                        Record(
                            (identity, child)
                            for identity, child in slice_parts.items()
                            if identity in slices
                        )
                        if isinstance(slice_parts, Mapping)
                        else slice_parts,
                    ),
                )
            )
        return current

    known = frozenset(
        (
            *projected,
            *(
                identity
                for name, spec in CANONICAL_PARTS
                if name != kind and spec.has_ids
                for identity in _ids(spec, remaining(name))
            ),
        )
    )
    source = _prior_references(previous)
    targets = _ReferenceTargets(
        known,
        slices,
        tuple(
            dict.fromkeys(
                (
                    *(source.unproduced_kinds if source is not None else ()),
                    *(
                        identity
                        for problem in decoded.shape_errors
                        if isinstance(problem, _ValueProblem)
                        for identity in problem.id_kinds
                    ),
                )
            )
        ),
        source.blocked if source is not None else frozenset(),
        source.defects if source is not None else (),
    )
    return (
        *(
            _references(ROLE_SCHEMAS[kind], payload, targets, kind)
            if current_uses
            else ()
        ),
    )


def _build(spec, value, previous, facts, counters):
    if spec.kind == "text":
        return intern(facts, counters, value)
    if spec.kind in (
        "line",
        "command",
        "string",
        "reference",
        "draft_reference",
        "obligation",
        "enum",
        "prefix",
        "adr_status",
    ):
        return value, facts, counters
    if spec.kind == "choice":
        alternative = spec.index[value[spec.discriminator]]
        built, facts, counters = _build(
            alternative,
            value,
            previous,
            facts,
            counters,
        )
        return (
            Record(((spec.discriminator, value[spec.discriminator]), *built.items())),
            facts,
            counters,
        )
    if spec.kind == "array":
        child_spec = spec.members[0]
        retained = _retained_rows(value, previous, facts, child_spec)

        def item(state, retained):
            result, facts, counters = state
            child, content, _ = retained
            old = _prior_row(child_spec, child, previous, facts, content)
            built, facts, counters = _build(child_spec, child, old, facts, counters)
            return (*result, built), facts, counters

        return reduce(item, retained, ((), facts, counters))
    if spec.kind == "table":

        def item(state, pair):
            result, facts, counters = state
            name, child = pair
            built, facts, counters = _build(
                spec.members[0], child, (previous or {}).get(name), facts, counters
            )
            return (*result, (name, built)), facts, counters

        entries, facts, counters = reduce(item, value.items(), ((), facts, counters))
        return Record(entries), facts, counters
    identity = value.get("id") or (
        (previous or {}).get("id") if spec.identity else None
    )
    if spec.identity and not identity:
        identity, counters = issue(counters, spec.identity)
    initial = (("id", identity),) if identity else ()

    def member(state, pair):
        result, facts, counters = state
        name, child_spec = pair
        if name not in value or _absent(value[name]):
            return state
        child, facts, counters = _build(
            child_spec, value[name], (previous or {}).get(name), facts, counters
        )
        return (*result, (name, child)), facts, counters

    entries, facts, counters = reduce(member, spec.members, (initial, facts, counters))
    return Record(entries), facts, counters


def _project_product_promises(payload, previous=None):
    """Describe the builder's retained/fresh IDs without issuing or interning."""
    product = previous.product if previous is not None else None
    if isinstance(product, UnavailableInput):
        return product
    prior = (product or EMPTY).get("promises", ())
    unavailable = _unavailable(prior)
    if unavailable is not None:
        return unavailable
    facts = previous.facts if previous is not None else EMPTY
    counters = previous.counters if previous is not None else EMPTY
    last = counters if isinstance(counters, UnavailableInput) else counters.get("P", 0)

    def retain(state, retained):
        if isinstance(state, UnavailableInput):
            return state
        rows, last = state
        row, content, _ = retained
        old = _prior_row(PROMISE, row, prior, facts, content)
        if isinstance(old, UnavailableInput):
            return old
        identity = row.get("id") or (old or EMPTY).get("id")
        if identity:
            return (*rows, Record((*row.items(), ("id", identity)))), last
        if isinstance(last, UnavailableInput):
            return last
        return (*rows, Record((*row.items(), ("id", f"P{last + 1}")))), last + 1

    result = reduce(
        retain,
        _retained_rows(payload.get("promises", ()), prior, facts, PROMISE),
        ((), last),
    )
    return result if isinstance(result, UnavailableInput) else result[0]


def product_promise_ids(payload, previous=None):
    rows = _project_product_promises(payload, previous)
    return (
        rows if isinstance(rows, UnavailableInput) else tuple(row["id"] for row in rows)
    )


def slice_promise_problems(row, known, path):
    references = row.get("promises", ())
    how = (
        "Cite existing Request promises with nwdes product slice add --promise P<n>; "
        "use nwdes product promise add for a justified Request promise, or split "
        "unrelated outcomes into a separate nwdes feature new."
    )
    if not references:
        return (
            Defect(
                "MissingFact: " + path + ".promises",
                "Every product slice must serve named promises of this Request's one value.",
                how,
            ),
        )
    if not isinstance(references, (tuple, list)):
        return ()
    return tuple(
        Defect(
            f"DanglingReference: {path}.promises {identity}",
            "This slice cites a promise not carried by this Request.",
            how,
        )
        for identity in references
        if isinstance(identity, str)
        and (identity not in known or _check(PROMISE_REFERENCE, identity, path))
    )


def _product_promise_problems(payload, previous):
    if not isinstance(payload, Mapping) or _check(
        PRODUCT.index["promises"], payload.get("promises", ()), "product.promises"
    ):
        return ()
    known = product_promise_ids(payload, previous)
    if isinstance(known, UnavailableInput):
        return ()
    rows = payload.get("slices", ())
    if _check(PRODUCT.index["slices"], rows, "product.slices"):
        return ()
    covered = frozenset(
        identity
        for row in rows
        if isinstance(row, Mapping) and isinstance(row.get("promises"), (tuple, list))
        for identity in row["promises"]
        if isinstance(identity, str)
    )
    return (
        *(
            defect
            for index, row in enumerate(rows)
            if isinstance(row, Mapping)
            for defect in slice_promise_problems(
                row, known, f"product.slices.{row.get('id', index + 1)}"
            )
        ),
        *(
            Defect(
                "UncoveredPromise: " + identity,
                "No product slice serves this Request promise.",
                "Link a slice with --promise "
                + identity
                + "; use nwdes product promise add for a justified promise, or split "
                "unrelated outcomes into a separate nwdes feature new.",
            )
            for identity in known
            if identity not in covered
        ),
    )


def _ids(spec, value):
    if not spec.has_ids or value is None or isinstance(value, UnavailableInput):
        return ()
    if spec.kind == "choice":
        alternative = (
            spec.index.get(value.get(spec.discriminator))
            if isinstance(value, Mapping)
            and isinstance(value.get(spec.discriminator), str)
            else None
        )
        return _ids(alternative, value) if alternative is not None else ()
    if spec.kind == "array":
        if not isinstance(value, (tuple, list)):
            return ()
        return tuple(
            identity for child in value for identity in _ids(spec.members[0], child)
        )
    if not isinstance(value, Mapping):
        return ()
    if spec.kind == "table":
        return tuple(
            identity
            for child in value.values()
            for identity in _ids(spec.members[0], child)
        )
    return (
        *((value["id"],) if spec.identity and isinstance(value.get("id"), str) else ()),
        *(
            identity
            for name, child_spec in spec.id_children
            if name in value
            for identity in _ids(child_spec, value[name])
        ),
    )


def _record_ids(handoff):
    return (
        *_ids(PRODUCT, handoff.product),
        *_ids(DESIGN, handoff.design),
        *_ids(EXPECTATIONS, handoff.expectations),
    )


def slice_ids(handoff):
    product = handoff.product
    if isinstance(product, UnavailableInput):
        return None
    rows = product.get("slices", ()) if isinstance(product, Mapping) else ()
    if isinstance(rows, UnavailableInput):
        return None
    return tuple(
        row["id"]
        for row in rows
        if isinstance(row, Mapping) and isinstance(row.get("id"), str)
    )


@dataclass(frozen=True)
class _ReferenceTargets:
    """Lookup units retain failed producers rather than inventing empty namespaces."""

    known: frozenset[str]
    slices: tuple[str, ...] | None
    unproduced_kinds: tuple[str, ...] = ()
    blocked: frozenset[str] = frozenset()
    defects: tuple[Defect, ...] = ()


@dataclass(frozen=True)
class HandoffInput:
    """Keep produced identity units even when unrelated input checks refuse."""

    result: Built[Handoff] | Refused
    references: _ReferenceTargets | None
    raw: Record | None = None
    problems: Record = EMPTY

    def part(self, name):
        if isinstance(self.result, Built):
            return getattr(self.result.value, name)
        if self.raw is None:
            return UnavailableInput(self.result.defects[0])
        if (problem := self.problems.get(name)) is not None:
            return UnavailableInput(problem)
        if name not in self.raw and name in ("request", "work", "facts", "counters"):
            return UnavailableInput(
                _missing_work()
                if name == "work"
                else _invalid("handoff." + name, "Required field is missing.", True)
            )
        value = self.raw.get(name)
        if name == "counters" and not isinstance(value, Mapping):
            return UnavailableInput(_invalid("counters", "Expected an object."))
        if name == "facts":
            if not isinstance(value, Mapping):
                return UnavailableInput(_invalid("facts", "Expected an object."))
            if not any(path.startswith("facts.") for path in self.problems):
                return value
            return InspectedFields(
                (
                    identity,
                    UnavailableInput(problem)
                    if (problem := self.problems.get("facts." + identity)) is not None
                    else text,
                )
                for identity, text in value.items()
            )
        spec = CANONICAL_SCHEMAS.get(name)
        if value is None and name not in ("request", "work"):
            return EMPTY if spec is not None and spec.kind == "table" else None
        return _field_units(spec, value, name, self.problems)

    def record_parts(self):
        return Record(
            (name, self.part(name))
            for name in (
                "facts",
                "product",
                "design",
                "acceptance",
                "expectations",
                "charter",
                "examination",
            )
        )


def _field_units(spec, value, path, problems):
    """Project cached producer outcomes, reusing every unaffected immutable subtree."""
    problem = problems.get(path)
    if problem is not None:
        return UnavailableInput(problem)
    if not any(
        name.startswith(path + ".") or name.startswith(path + "[") for name in problems
    ):
        return value
    if spec is not None and spec.kind == "choice":
        alternative = spec.index.get(value.get(spec.discriminator))
        return _field_units(alternative, value, path, problems)
    if isinstance(value, (tuple, list)):
        child_spec = spec.members[0] if spec is not None else None
        return tuple(
            _field_units(child_spec, child, f"{path}[{index}]", problems)
            for index, child in enumerate(value)
        )
    if isinstance(value, Mapping):

        def child_spec(name):
            if spec is None:
                return None
            return spec.members[0] if spec.kind == "table" else spec.index.get(name)

        absent = (
            (*spec.required_fields, *(("id",) if spec.identity else ()))
            if spec is not None and spec.kind == "record"
            else tuple(
                name[len(path) + 1 :]
                for name in problems
                if name.startswith(path + ".")
                and "." not in name[len(path) + 1 :]
                and "[" not in name[len(path) + 1 :]
            )
        )
        return InspectedFields(
            (
                *(
                    (
                        name,
                        _field_units(
                            child_spec(name), child, path + "." + name, problems
                        ),
                    )
                    for name, child in value.items()
                ),
                *(
                    (name, UnavailableInput(problems[path + "." + name]))
                    for name in absent
                    if name not in value and path + "." + name in problems
                ),
            )
        )
    return value


def _unavailable(value):
    if isinstance(value, UnavailableInput):
        return value
    children = (
        value.values()
        if isinstance(value, Mapping)
        else value
        if isinstance(value, (tuple, list))
        else ()
    )
    return next(
        (missing for child in children if (missing := _unavailable(child)) is not None),
        None,
    )


def _reference_available(identity, targets):
    """A negative lookup needs its namespace; a unique known id needs only its own unit."""
    return identity not in targets.blocked and (
        identity in targets.known
        or identity == "observation"
        or not identity.startswith(targets.unproduced_kinds)
    )


def _reference_known(spec, group, identity, targets):
    if group in ("depends_on", "slices"):
        return targets.slices is not None and identity in targets.slices
    if spec.members:
        return identity in targets.known and identity.startswith(spec.members)
    return identity == "observation" or identity in targets.known


def _table_reference_defects(references, targets):
    def inspect(reference):
        scalar = checked(
            reference.identity, _check(REFERENCE, reference.identity, reference.path)
        )
        if isinstance(scalar, Refused):
            return scalar.defects
        if scalar.value.startswith(reference.kind) and not _reference_available(
            scalar.value, targets
        ):
            return ()
        identities = targets.slices if reference.kind == "S" else targets.known
        return (
            (
                Defect(
                    f"DanglingReference: {reference.path}",
                    f"Unknown {reference.kind} target {reference.identity}.",
                    "Use an identity assigned by nwdes for this keyed part.",
                ),
            )
            if not scalar.value.startswith(reference.kind)
            or (identities is not None and scalar.value not in identities)
            else ()
        )

    return tuple(defect for reference in references for defect in inspect(reference))


def _references(spec, value, targets, path=""):
    if not spec.has_references or value is None:
        return ()
    if spec.kind == "choice":
        if (
            isinstance(value, Mapping)
            and isinstance(value.get(spec.discriminator), str)
            and value[spec.discriminator] in spec.index
        ):
            return _references(
                spec.index[value[spec.discriminator]], value, targets, path
            )
        return ()
    if spec.kind == "array":
        return (
            tuple(
                defect
                for index, child in enumerate(value)
                for defect in _references(
                    spec.members[0], child, targets, f"{path}[{index}]"
                )
            )
            if isinstance(value, (tuple, list))
            else ()
        )
    if not isinstance(value, Mapping):
        return ()
    if spec.kind == "table":
        return (
            *_table_reference_defects(
                tuple(
                    TableReference(spec.key_reference, name, path + "." + name)
                    for name in value
                ),
                targets,
            ),
            *(
                defect
                for name, child in value.items()
                for defect in _references(
                    spec.members[0], child, targets, path + "." + name
                )
            ),
        )
    local = tuple(
        Defect(
            f"DanglingReference: {path}.{name}.{identity}",
            f"Unknown reference {identity}.",
            "Use identities already assigned by nwdes.",
        )
        for name in spec.reference_fields
        if isinstance(value.get(name), (tuple, list))
        for index, raw in enumerate(value[name])
        for scalar in (
            checked(
                raw,
                _check(spec.index[name].members[0], raw, f"{path}.{name}[{index}]"),
            ),
        )
        if isinstance(scalar, Built)
        for identity in (scalar.value,)
        if _reference_available(identity, targets)
        if not _reference_known(spec.index[name].members[0], name, identity, targets)
    )
    nested = tuple(
        defect
        for name, child_spec in spec.reference_children
        if name in value
        for defect in _references(
            child_spec, value[name], targets, (path + "." + name).lstrip(".")
        )
    )
    return (*local, *nested)


def validate(handoff: Handoff):
    targets = handoff._references
    return checked(
        handoff,
        (
            *(
                defect
                for name, spec in CANONICAL_PARTS
                for defect in _references(spec, getattr(handoff, name), targets, name)
            ),
        ),
    )


def _fact_references(spec, value):
    if value is None or not spec.has_text:
        return ()
    if spec.kind == "text":
        return (value,)
    if spec.kind == "choice":
        return _fact_references(spec.index[value[spec.discriminator]], value)
    if spec.kind in ("array", "table"):
        children = value.values() if spec.kind == "table" else value
        return tuple(
            identity
            for child in children
            for identity in _fact_references(spec.members[0], child)
        )
    if spec.kind == "record":
        return tuple(
            identity
            for name, child_spec in spec.text_children
            if name in value
            for identity in _fact_references(child_spec, value[name])
        )
    return ()


def _prune(handoff, **changes):
    """Prune the requested projection before constructing its canonical identity index."""
    referenced = {
        identity
        for name, spec in CANONICAL_PARTS
        for identity in _fact_references(
            spec, changes.get(name, getattr(handoff, name))
        )
    }
    source_facts = changes.get("facts", handoff.facts)
    facts = Record(
        (identity, freeze(text))
        for identity, text in source_facts.items()
        if identity in referenced
    )
    if (
        not changes
        and len(facts) == len(source_facts)
        and all(facts[identity] is text for identity, text in source_facts.items())
    ):
        return handoff
    return replace(handoff, **{**changes, "facts": facts})


def build_scope(kind, identity=None):
    if kind == "Project":
        return Built(Project())
    if (
        kind not in ("Feature", "Epic")
        or not isinstance(identity, str)
        or not _SCOPE_ID.fullmatch(identity)
    ):
        return checked(
            None,
            (
                _invalid(
                    "--feature/--epic", "Use a lowercase id with digits and hyphens."
                ),
            ),
        )
    return Built(Feature(identity) if kind == "Feature" else Epic(identity))


def new(request, scope, size, value):
    defects = (
        *_check(TEXT, request, "--request"),
        *_check(WORK, {"size": size, "value": value}, "work"),
    )
    if defects:
        return checked(None, defects)
    request_id, facts, counters = intern(EMPTY, EMPTY, request)
    work, facts, counters = _build(
        WORK, {"size": size, "value": value}, None, facts, counters
    )
    return Built(Handoff(request_id, scope, work, counters, facts))


def prepare_feature(previous, request, scope, size, value):
    fields = (
        (TEXT, request, "--request"),
        (dict(WORK.members)["size"], size, "work.size"),
        (TEXT, value, "work.value"),
    )
    problems = tuple(
        defect
        for spec, raw, path in fields
        if raw is not None
        for defect in _check(spec, raw, path)
    )
    before = (
        (
            expanded(TEXT, previous.request, previous.facts),
            previous.work.get("size"),
            expanded(TEXT, previous.work.get("value"), previous.facts),
        )
        if previous is not None and isinstance(previous.work, Mapping)
        else None
    )
    different = (
        before is not None
        and not problems
        and _unavailable(before) is None
        and all(raw is not None for _, raw, _ in fields)
        and any(old != raw for (_, raw, _), old in zip(fields, before, strict=True))
    )
    defects = (
        *problems,
        *(
            (
                Defect(
                    "FeatureExists: " + getattr(previous.scope, "id", "project"),
                    "The existing request, size or work value differs.",
                    "Use work set, rework set or role verbs to change the existing feature.",
                ),
            )
            if different
            else ()
        ),
    )
    return checked(
        PreparedHandoff(
            lambda: (
                Built(previous)
                if previous is not None
                else new(request, scope, size, value)
            )
        ),
        defects,
    )


def _record_locations(spec, value, path, owner=""):
    if not spec.has_ids or value is None:
        return ()
    if spec.kind == "choice":
        alternative = (
            spec.index.get(value.get(spec.discriminator))
            if isinstance(value, Mapping)
            and isinstance(value.get(spec.discriminator), str)
            else None
        )
        return _record_locations(alternative, value, path, owner) if alternative else ()
    if spec.kind == "array":
        return tuple(
            location
            for index, child in enumerate(
                value if isinstance(value, (tuple, list)) else ()
            )
            for location in _record_locations(
                spec.members[0], child, f"{path}[{index}]", path
            )
        )
    if not isinstance(value, Mapping):
        return ()
    if spec.kind == "table":
        return tuple(
            location
            for name, child in value.items()
            for location in _record_locations(spec.members[0], child, path + "." + name)
        )
    identity = value.get("id")
    identified = (
        spec.identity
        and isinstance(identity, str)
        and not _id_defects(spec.identity, identity, path)
    )
    stem = owner + "." + identity if identified else path
    return (
        *(((identity, owner or path, path),) if identified else ()),
        *(
            location
            for name, child_spec in spec.id_children
            if name in value
            for location in _record_locations(
                child_spec, value[name], stem + "." + name
            )
        ),
    )


def _handoff_locations(handoff):
    return tuple(
        location
        for name, spec in CANONICAL_PARTS
        for location in _record_locations(spec, getattr(handoff, name), name)
    )


def _has_retained_id(spec, value, known):
    if not spec.has_ids or value is None:
        return False
    if spec.kind == "array":
        return isinstance(value, (tuple, list)) and any(
            _has_retained_id(spec.members[0], child, known) for child in value
        )
    if not isinstance(value, Mapping):
        return False
    if spec.kind == "choice":
        alternative = (
            spec.index.get(value.get(spec.discriminator))
            if isinstance(value.get(spec.discriminator), str)
            else None
        )
        return alternative is not None and _has_retained_id(alternative, value, known)
    if spec.kind == "table":
        return any(
            _has_retained_id(spec.members[0], child, known) for child in value.values()
        )
    if spec.identity and "id" in value:
        identity = value["id"]
        return (
            isinstance(identity, str)
            and not _id_defects(spec.identity, identity, "")
            and identity in known
        )
    return any(
        _has_retained_id(child_spec, value[name], known)
        for name, child_spec in spec.id_children
        if name in value
    )


def _mentions_id_kinds(spec, value, kinds):
    if not spec.has_references or value is None:
        return False
    if spec.kind == "array":
        return isinstance(value, (tuple, list)) and any(
            _mentions_id_kinds(spec.members[0], child, kinds) for child in value
        )
    if not isinstance(value, Mapping):
        return False
    if spec.kind == "choice":
        alternative = (
            spec.index.get(value.get(spec.discriminator))
            if isinstance(value.get(spec.discriminator), str)
            else None
        )
        return alternative is not None and _mentions_id_kinds(alternative, value, kinds)
    if spec.kind == "table":
        return (
            spec.key_reference in kinds
            and any(not _check(REFERENCE, identity, "") for identity in value)
        ) or any(
            _mentions_id_kinds(spec.members[0], child, kinds)
            for child in value.values()
        )
    return any(
        isinstance(identity, str)
        and identity.startswith(kinds)
        and not _check(spec.index[name].members[0], identity, "")
        for name in spec.reference_fields
        if isinstance(value.get(name), (tuple, list))
        for identity in value[name]
    ) or any(
        _mentions_id_kinds(child_spec, value[name], kinds)
        for name, child_spec in spec.reference_children
        if name in value
    )


def _ownership_defects(spec, value, previous, path, shape_errors=()):
    references = _prior_references(previous)
    known = (
        references.known - references.blocked if references is not None else frozenset()
    )
    if not _has_retained_id(spec, value, known):
        return ()
    if shape_errors:
        value = _field_units(
            spec,
            value,
            path,
            Record(
                (problem.path, problem)
                for problem in shape_errors
                if isinstance(problem, _ValueProblem)
            ),
        )

    def owned(current_spec, current, old, site):
        if (
            not current_spec.has_ids
            or current is None
            or isinstance(old, UnavailableInput)
        ):
            return ()
        if current_spec.kind == "choice":
            alternative = (
                current_spec.index.get(current.get(current_spec.discriminator))
                if isinstance(current, Mapping)
                and isinstance(current.get(current_spec.discriminator), str)
                else None
            )
            return owned(alternative, current, old, site) if alternative else ()
        if current_spec.kind == "array":
            return tuple(
                defect
                for index, child in enumerate(
                    current if isinstance(current, (tuple, list)) else ()
                )
                for defect in owned(
                    current_spec.members[0],
                    child,
                    _prior_row(current_spec.members[0], child, old, previous.facts),
                    f"{site}[{index}]",
                )
            )
        if not isinstance(current, Mapping):
            return ()
        if (
            current_spec.identity
            and "id" in current
            and (
                not isinstance(current["id"], str)
                or _id_defects(current_spec.identity, current["id"], "")
                or current["id"] not in known
            )
        ):
            return ()
        if current_spec.kind == "table":
            return tuple(
                defect
                for name, child in current.items()
                for defect in owned(
                    current_spec.members[0],
                    child,
                    (old or {}).get(name),
                    site + "." + name,
                )
            )
        local = (
            (
                Defect(
                    f"DanglingReference: {site}.id",
                    f"Id {current['id']} does not belong to this retained parent and list.",
                    "Return this refusal to the same author for a complete corrected "
                    "envelope. An id belongs only to the list and retained parent that issued "
                    "it: to carry this id, return its record in that same list under that same "
                    "parent; for a new record here, omit its id so nwdes assigns one. A parent "
                    "record without its own id is retained by its complete expanded content, "
                    "not its path alone; ids are ignored, absent/empty "
                    "optional values are normalized, and list order is content. Changing a "
                    "model property statement, atoms, assumptions, mutants or other model "
                    "content loses that parent match, so old nested mutant ids cannot be "
                    "carried under it. To retain those ids, restore the complete previous "
                    "model content under the same owning list. For an intentional model "
                    "replacement, keep the revised model and omit all of its old nested ids "
                    "so nwdes can assign new ones. Never invent ids, edit the envelope in the "
                    "host, or change unrelated records.",
                ),
            )
            if current_spec.identity
            and isinstance(current.get("id"), str)
            and current["id"] in known
            and (old or {}).get("id") != current["id"]
            else ()
        )
        return (
            *local,
            *(
                defect
                for name, child_spec in current_spec.id_children
                if name in current
                for defect in owned(
                    child_spec, current[name], (old or {}).get(name), site + "." + name
                )
            ),
        )

    return owned(
        spec,
        value,
        getattr(previous, path, None),
        path,
    )


def _identity_defects(spec, value, references, path):
    previous = references.known
    if not spec.has_ids:
        return ()
    if (
        spec.kind == "choice"
        and isinstance(value, Mapping)
        and isinstance(value.get(spec.discriminator), str)
        and value.get(spec.discriminator) in spec.index
    ):
        return _identity_defects(
            spec.index[value[spec.discriminator]], value, references, path
        )
    if spec.kind == "array" and isinstance(value, (tuple, list)):
        conflicts = tuple(
            Defect(
                f"InconsistentFacts: {path}[{first}], {path}[{index}]",
                f"The same existing id {child['id']} carries different content.",
                "Supply one content for each existing id.",
            )
            for index, child in enumerate(value)
            if isinstance(child, Mapping)
            and isinstance(child.get("id"), str)
            and child["id"] in previous
            and _reference_available(child["id"], references)
            for first, earlier in enumerate(value[:index])
            if isinstance(earlier, Mapping)
            and earlier.get("id") == child["id"]
            and _content(earlier) != _content(child)
        )
        return (
            *conflicts,
            *(
                defect
                for index, child in enumerate(value)
                for defect in _identity_defects(
                    spec.members[0], child, references, f"{path}[{index}]"
                )
            ),
        )
    if spec.kind == "table" and isinstance(value, Mapping):
        return tuple(
            defect
            for name, child in value.items()
            for defect in _identity_defects(
                spec.members[0], child, references, path + "." + name
            )
        )
    if spec.kind == "record" and isinstance(value, Mapping):
        local = (
            (
                Defect(
                    f"DanglingReference: {path}.id",
                    f"The role cannot invent id {value['id']}.",
                    "Omit id to create a record or use an existing id.",
                ),
            )
            if spec.identity
            and isinstance(value.get("id"), str)
            and not _id_defects(spec.identity, value["id"], path + ".id")
            and value["id"] not in previous
            and _reference_available(value["id"], references)
            else ()
        )
        return (
            *local,
            *(
                defect
                for name, child_spec in spec.id_children
                if name in value
                for defect in _identity_defects(
                    child_spec, value[name], references, path + "." + name
                )
            ),
        )
    return ()


ENVELOPE_FIELDS = record(
    ("outcome", "diagnostic"),
    outcome=enum("accepted", "rejected", "indeterminate"),
    diagnostic=STRING,
)


@dataclass(frozen=True)
class _RoleApplication:
    kind: str
    slice: str | None = None
    action: str = "apply"


@dataclass(frozen=True)
class RoleInput:
    """Retain inspectable payload alongside envelope defects for independent checks."""

    payload: object
    outcome: object
    defects: tuple[Defect, ...]
    absent_references: tuple[TableReference, ...] = ()
    shape_errors: tuple[Defect, ...] = ()


@dataclass(frozen=True)
class InvocationRefused(Refused):
    output: RoleInput | None = None


def inspect_output(kind, data, *, policy=None, resolution=EMPTY):
    parsed = parse_json(data, kind)
    if isinstance(parsed, Refused):
        return RoleInput(None, None, parsed.defects)
    envelope = parsed.value
    if not isinstance(envelope, Mapping):
        return RoleInput(
            None,
            None,
            (_invalid(kind, "Expected the outcome, diagnostic, payload envelope."),),
        )
    outcome = envelope.get("outcome")
    defects = (
        *_check(
            ENVELOPE_FIELDS,
            {name: child for name, child in envelope.items() if name != "payload"},
            kind,
        ),
        *(
            (
                _invalid(
                    kind + ".payload", "Required envelope payload is missing.", True
                ),
            )
            if "payload" not in envelope
            else ()
        ),
        *(
            (
                _invalid(
                    kind + ".payload", "A non-accepted output requires null payload."
                ),
            )
            if outcome in ("rejected", "indeterminate")
            and envelope.get("payload") is not None
            else ()
        ),
        *(
            (
                Defect(
                    f"RoleNotAccepted: {kind}",
                    str(envelope.get("diagnostic", "")),
                    "Resolve the role's diagnostic, record corrected values with its verbs and close with --outcome accepted.",
                ),
            )
            if outcome in ("rejected", "indeterminate")
            else ()
        ),
        *(
            (_invalid(kind, "Unknown output kind."),)
            if kind not in ROLE_SCHEMAS
            else ()
        ),
    )
    path = kind + ".payload" if kind == "examine" else kind
    normalized = normalize_input(ROLE_SCHEMAS.get(kind), envelope.get("payload"), path)
    shape = (
        (
            *_check(
                asked_schema(kind, ROLE_CHECKS[kind], policy), normalized.value, path
            ),
            *(_design_requirements(normalized.value) if kind == "design" else ()),
            *(
                _design_obligations(normalized.value, policy, resolution)
                if kind == "design" and policy is not None
                else ()
            ),
        )
        if kind in ROLE_SCHEMAS and outcome == "accepted"
        else ()
    )
    return RoleInput(
        normalized.value, outcome, defects, normalized.absent_references, shape
    )


def _expectation_set_problems(previous, action):
    """Revise needs a fixed set; apply over a fixed set replaces it."""
    return (
        (
            Defect(
                "MissingFact: expectations",
                "No expectation set has been fixed.",
                "Apply the first expectation set before revising it.",
            ),
        )
        if action == "revise" and previous.expectations is None
        else ()
    )


def _expectation_coverage(previous, decoded):
    """Coverage reads each public promise and every produced citing list."""
    if decoded.outcome != "accepted":
        return ()
    payload = _field_units(
        EXPECTATIONS,
        decoded.payload,
        "expectations",
        Record(
            (problem.path, problem)
            for problem in decoded.shape_errors
            if isinstance(problem, _ValueProblem)
        ),
    )
    product = previous.product
    if not isinstance(payload, Mapping) or not isinstance(product, Mapping):
        return ()
    rows = payload.get("rows", ())
    promises = product.get("promises", ())
    if not isinstance(rows, (tuple, list)) or not isinstance(promises, (tuple, list)):
        return ()
    if any(
        not isinstance(row, Mapping)
        or _unavailable(row.get("promises", ())) is not None
        for row in rows
    ):
        return ()
    cited = frozenset(identity for row in rows for identity in row.get("promises", ()))
    return tuple(
        Defect(
            "UncoveredPromise: " + promise["id"],
            "No expectation row cites this public promise.",
            "Cover every current public promise in the expectation rows.",
        )
        for promise in promises
        if _unavailable(promise) is None and promise["id"] not in cited
    )


EXAMINATION_RECORD_HOW = (
    "record each observation with nwdes examine observation add, "
    "cite it with nwdes examine verdict set --observation "
    "and run nwdes examine close."
)


def uncited_verdict(expectation):
    return Defect(
        "UncitedVerdict: " + str(expectation),
        "A verdict rests on evidence the examiner recorded, but this verdict cites no observation.",
        EXAMINATION_RECORD_HOW,
    )


def examination_verdicts(payload):
    observations = {row["id"]: row["text"] for row in payload["observations"]}
    return Record(
        (
            expectation,
            Record(
                (
                    *(
                        (name, value)
                        for name, value in verdict.items()
                        if name != "observations"
                    ),
                    (
                        "observations",
                        tuple(
                            dict.fromkeys(
                                observations[identity]
                                for identity in verdict["observations"]
                            )
                        ),
                    ),
                )
            ),
        )
        for expectation, verdict in payload["verdicts"].items()
    )


def examination_observation_problems(payload):
    verdicts = payload.get("verdicts", EMPTY)
    if not isinstance(verdicts, Mapping):
        return ()
    observations = payload.get("observations", ())
    recorded = (
        frozenset(
            row["id"]
            for row in observations
            if isinstance(row, Mapping) and isinstance(row.get("id"), str)
        )
        if isinstance(observations, (tuple, list))
        else None
    )
    return (
        *(
            uncited_verdict(identity)
            for identity, verdict in verdicts.items()
            if isinstance(verdict, Mapping) and not verdict.get("observations")
        ),
        *(
            Defect(
                "DanglingReference: examine.payload."
                + identity
                + ".observations "
                + citation,
                "The verdict cites an observation not recorded in this examination draft.",
                EXAMINATION_RECORD_HOW,
            )
            for identity, verdict in verdicts.items()
            if recorded is not None and isinstance(verdict, Mapping)
            for citation in verdict.get("observations", ())
            if isinstance(citation, str) and citation not in recorded
        ),
    )


def _examination_problems(previous, decoded):
    fixed = previous.expectations
    missing_set = (
        (
            Defect(
                "MissingFact: expectations",
                "No expectation set has been fixed.",
                "Fix expectations before applying their verdicts.",
            ),
        )
        if fixed is None
        else ()
    )
    if decoded.outcome != "accepted" or not isinstance(decoded.payload, Mapping):
        return missing_set
    rows = (
        ()
        if fixed is None
        else fixed.get("rows", ())
        if isinstance(fixed, Mapping)
        else fixed
    )
    if not isinstance(rows, (tuple, list)):
        return missing_set
    known = frozenset(row["id"] for row in rows if _unavailable(row) is None)
    payload = decoded.payload.get("verdicts", EMPTY)
    if not isinstance(payload, Mapping):
        return missing_set
    return (
        *missing_set,
        *(
            _invalid(
                "examine.payload." + row["id"],
                "The expectation has no supplied verdict.",
                how=EXAMINATION_RECORD_HOW,
            )
            for row in rows
            if _unavailable(row) is None and row["id"] not in payload
        ),
        *(
            _invalid(
                "examine.payload." + identity,
                "The verdict names no current expectation.",
            )
            for identity in payload
            if _unavailable(rows) is None and identity not in known
        ),
        *examination_observation_problems(decoded.payload),
    )


def examination_outcome(verdicts):
    """Derive the outcome of a constructed total verdict set, never judge its evidence."""
    return (
        "accepted"
        if all(verdict["verdict"] == "met" for verdict in verdicts.values())
        else "rejected"
    )


def _acceptance_statement_problems(payload, slice):
    if not isinstance(payload, (tuple, list)):
        return ()
    return tuple(
        Defect(
            f"MissingFact: acceptance.{slice}[{index}].disposition.still_passes_if",
            "A test without its nearest accepted wrong behaviour hides its false positive.",
            "Re-record the row with --still-passes-if naming the nearest plausible wrong behaviour the test would still accept; tighten the test if it breaks the promise.",
        )
        for index, row in enumerate(payload)
        if isinstance(row, Mapping)
        and isinstance(disposition := row.get("disposition"), Mapping)
        and disposition.get("kind") == "Tested"
        and (
            not isinstance(statement := disposition.get("still_passes_if"), str)
            or not statement.strip()
        )
    )


def _covers_prefix_defects(payload, slice, retained, held):
    """Covers of an added or changed acceptance row name a promise; a retained row keeps its stored covers.

    A law or test the design holds is bound through the row's obligation slots, so naming one in covers
    is refused by name. An L or T id the design does not hold is refused by the reference check alone, so
    one fault is one block; any other non-promise prefix is refused here. Pure.
    """
    kept = list(retained)
    return tuple(
        Defect(
            f"UnknownCoverPrefix: acceptance.{slice}[{index}].covers {identity}",
            f"{identity} is not a P record; covers of a row the draft adds or changes name promises only.",
            "Replace it with the P id of the promise it covers, and bind design laws and tests with --obligation KEY.",
        )
        for index, row in enumerate(
            payload if isinstance(payload, (tuple, list)) else ()
        )
        if isinstance(row, Mapping) and _content(row) not in kept
        for identity in _sequence(row.get("covers"))
        if isinstance(identity, str)
        and identity[:1] != "P"
        and (identity[:1] not in ("L", "T") or identity in held)
    )


def _output_problems(
    application: _RoleApplication, decoded, references, previous=None, resolution=EMPTY
):
    kind, slice = application.kind, application.slice
    spec = ROLE_SCHEMAS.get(kind)
    expectation_problems = (
        _expectation_coverage(previous, decoded)
        if kind == "expectations" and previous is not None
        else ()
    )
    examination_problems = (
        _examination_problems(previous, decoded)
        if kind == "examine" and previous is not None
        else ()
    )
    if spec is None or decoded.outcome != "accepted":
        return (*decoded.defects, *expectation_problems, *examination_problems)
    payload = decoded.payload
    supplied_ids = _record_locations(spec, payload, kind)
    return (
        *decoded.defects,
        *decoded.shape_errors,
        *expectation_problems,
        *examination_problems,
        *(
            _acceptance_statement_problems(payload, slice)
            if kind == "acceptance"
            else ()
        ),
        *(
            _covers_prefix_defects(
                payload,
                slice,
                _retained_contents(previous, slice),
                frozenset(
                    record["id"]
                    for record, _ in _coverage_records(_part_of(previous, "design"))
                ),
            )
            if kind == "acceptance"
            else ()
        ),
        *(
            _obligation_defects(
                _part_of(previous, "design"),
                previous,
                {
                    **_mapping(_part_of(previous, "acceptance")),
                    slice: payload,
                },
                slice,
                resolution,
            )
            if kind == "acceptance" and previous is not None
            else ()
        ),
        *(_product_reference_checks(payload) if kind == "product" else ()),
        *(
            _product_promise_problems(payload, previous)
            if kind == "product" and application.action != "slice set"
            else ()
        ),
        *(
            _slice_problems(slice, references, required=True)
            if kind == "acceptance"
            else ()
        ),
        *(
            (
                *(
                    _identity_defects(spec, payload, references, kind)
                    if supplied_ids
                    else ()
                ),
                *(
                    tuple(
                        replace(
                            defect,
                            how=f"Re-run nw-acceptance-designer for {slice} using the current handoff and generated acceptance schema; submit only current assigned identities.",
                        )
                        if kind == "acceptance"
                        and defect.what.startswith("DanglingReference:")
                        else defect
                        for defect in _references(spec, payload, references, kind)
                    )
                    if kind not in ("product", "examine")
                    else ()
                ),
                *_table_reference_defects(decoded.absent_references, references),
            )
            if references is not None
            else ()
        ),
        *(
            (
                *(
                    _ownership_defects(
                        spec, payload, previous, kind, decoded.shape_errors
                    )
                    if supplied_ids
                    else ()
                ),
                *_future_reference_checks(previous, kind, decoded),
            )
            if previous is not None
            else ()
        ),
    )


def check_output(kind: str, data: bytes, references=None, slice=None, previous=None):
    decoded = inspect_output(kind, data)
    return checked(
        decoded.payload,
        _output_problems(_RoleApplication(kind, slice), decoded, references, previous),
    )


def _product_reference_checks(payload):
    if not isinstance(payload, Mapping):
        return ()
    rows = payload.get("slices", ())
    rows = rows if isinstance(rows, (tuple, list)) else ()
    observations = tuple(
        row["observation"]
        for row in rows
        if isinstance(row, Mapping)
        and "observation" in row
        and not _check(TEXT, row["observation"], "")
    )
    return tuple(
        Defect(
            f"DanglingReference: product.slices[{index}].depends_on.{reference}",
            "No output slice has this observation.",
            "Name an observation supplied by another slice in this product output.",
        )
        for index, row in enumerate(rows)
        if isinstance(row, Mapping)
        for reference in (
            row.get("depends_on", ())
            if isinstance(row.get("depends_on", ()), (tuple, list))
            else ()
        )
        if isinstance(reference, str)
        and not _check(STRING, reference, "")
        and reference not in observations
    )


def verification_commands(own, path):
    if not isinstance(own, Mapping):
        return ()
    prefactoring = own.get("prefactoring")
    parts = (
        (own.get("verification"), path + ".verification"),
        (
            prefactoring.get("verification")
            if isinstance(prefactoring, Mapping)
            else None,
            path + ".prefactoring.verification",
        ),
    )
    return tuple(
        (f"{site}[{index}]", command)
        for commands, site in parts
        if isinstance(commands, (tuple, list))
        for index, command in enumerate(commands)
        if not _check(COMMAND, command, f"{site}[{index}]")
    )


def _owed_test_commands(design, identity):
    """The commands of the architectural and contract tests a slice owes.

    A slice owes the tests recorded in its own scope, and the shared ones when it has a code
    target. Pure: reads only its parameters.
    """
    design = _mapping(design)
    own = _mapping(_mapping(design.get("slices")).get(identity))
    scopes = (
        *(
            (_mapping(design.get("shared")),)
            if _code_targets(own.get("targets"))
            else ()
        ),
        _mapping(own.get("records")),
    )
    return tuple(
        command
        for records in scopes
        for name in _COVERAGE_TEST_LISTS
        for record in _sequence(records.get(name))
        for command in (_mapping(record).get("command"),)
        if isinstance(command, str)
    )


def slice_verification(design, identity):
    """The commands a slice's verification runs: those it states, then those of the tests it owes.

    The tool computes the owed commands from the test records, so no record repeats them and a
    verification that omits one cannot be written. A command appears once. Pure.
    """
    own = _mapping(_mapping(_mapping(design).get("slices")).get(identity))
    stated = _sequence(own.get("verification"))
    return tuple(dict.fromkeys((*stated, *_owed_test_commands(design, identity))))


def _owed_commands(payload):
    """Each owed test command of every slice, named by the verification that now runs it."""
    slices = payload.get("slices") if isinstance(payload, Mapping) else None
    return tuple(
        (f"design.slices.{identity}.verification (owed)", command)
        for identity in (slices if isinstance(slices, Mapping) else ())
        for command in _owed_test_commands(payload, identity)
    )


def _design_commands(payload):
    slices = payload.get("slices") if isinstance(payload, Mapping) else None
    return (
        *(
            command
            for identity, own in (slices.items() if isinstance(slices, Mapping) else ())
            for command in verification_commands(own, f"design.slices.{identity}")
        ),
        *_owed_commands(payload),
    )


def _program_problems(commands, programs: ProgramResolution):
    return tuple(
        Defect(
            f"PartInvalid: {path}",
            f"The program of verification command {command!r} does not resolve in the writer's environment.",
            "Install the program on the invoking PATH, or supply an existing root-relative or absolute file; then rerun nwdes slice set or nwdes design close.",
        )
        for path, command in commands
        if not programs.get(command, False)
    )


def apply_output(
    previous: Handoff,
    kind: str,
    data: bytes,
    slice=None,
    *,
    programs: ProgramResolution = EMPTY,
):
    return finish(prepare_output(previous, kind, data, slice, programs=programs))


def prepare_output(
    previous: Handoff,
    kind: str,
    data: bytes,
    slice=None,
    *,
    programs: ProgramResolution = EMPTY,
):
    return _prepare_decoded(
        previous,
        _RoleApplication(kind, slice),
        inspect_output(kind, data),
        programs=programs,
    )


def _prepare_decoded(
    previous,
    application: _RoleApplication,
    decoded,
    *,
    programs: ProgramResolution = EMPTY,
    resolution=EMPTY,
):
    kind, slice = application.kind, application.slice
    payload = decoded.payload
    references = _prior_references(previous)
    problems = (
        *_output_problems(application, decoded, references, previous, resolution),
        *(
            _expectation_set_problems(previous, application.action)
            if kind == "expectations"
            else ()
        ),
        *(
            _program_problems(_design_commands(payload), programs)
            if kind == "design" and decoded.outcome == "accepted"
            else ()
        ),
    )
    if problems:
        return checked(None, problems)
    return Built(
        PreparedHandoff(lambda: _apply_part(previous, kind, payload, slice), decoded)
    )


def _candidate_part(previous, kind, payload, slice):
    spec = CANONICAL_SCHEMAS["examination"] if kind == "examine" else ROLE_SCHEMAS[kind]
    payload = examination_verdicts(payload) if kind == "examine" else payload
    built, facts, counters = _build(
        spec,
        {name: child for name, child in payload.items() if name != "adrs"}
        if kind == "design"
        else payload,
        getattr(previous, kind, None),
        previous.facts,
        previous.counters,
    )
    if kind == "product":
        observations = {
            facts[row["observation"]]: row["id"] for row in built.get("slices", ())
        }
        rows = tuple(
            freeze(
                {
                    **row,
                    **(
                        {
                            "depends_on": tuple(
                                observations.get(reference, reference)
                                for reference in row["depends_on"]
                            )
                        }
                        if "depends_on" in row
                        else {}
                    ),
                }
            )
            for row in built["slices"]
        )
        built = freeze({**built, "slices": rows})
        updated = replace(previous, product=built)
    elif kind == "acceptance":
        updated = replace(
            previous, acceptance=freeze({**previous.acceptance, slice: built})
        )
    elif kind == "charter":
        updated = replace(
            previous, charter=Record((("kind", "Feature"), *built.items()))
        )
    elif kind == "expectations":
        updated = replace(previous, expectations=built)
    elif kind == "examine":
        updated = replace(previous, examination=built)
    elif kind == "design":
        acceptance, facts, counters = _acceptance_for_design(
            previous.acceptance, built, previous.product, facts, counters
        )
        updated = replace(previous, design=built, acceptance=acceptance)
    else:
        updated = replace(previous, **{kind: built})
    return replace(updated, facts=facts, counters=counters)


def _apply_part(previous, kind, payload, slice):
    candidate = _candidate_part(previous, kind, payload, slice)
    operation = (
        "expectations revise"
        if kind == "expectations" and previous.expectations
        else kind + " apply"
    )
    candidate, notices = _withdraw_references(previous, candidate, operation)
    return validate(_prune(replace(candidate, withdrawals=notices)))


def id_order(identity):
    return (
        identity.rstrip("0123456789"),
        int(re.search(r"\d+$", identity)[0]),
    )


def _row_citations(row):
    """The design records an acceptance row cites: its covers and the record each obligation key belongs to.

    An obligation key names its record by the prefix before its slash (L12/F34 belongs to L12), so a
    row bound through obligations is withdrawn with the law or test it binds. Pure.
    """
    keys = _sequence(_mapping(row.get("disposition")).get("obligations"))
    return (
        *_sequence(row.get("covers")),
        *(key.partition("/")[0] for key in keys if isinstance(key, str)),
    )


def _retired_causes(references, retired):
    return tuple(sorted(set(references) & retired, key=id_order))


def _withdraw_references(previous, candidate, operation):
    """Construct the dependency closure and its notices without publishing effects."""
    if operation not in (
        "product apply",
        "design apply",
        "slice set",
        "expectations revise",
        "expectations apply",
    ):
        return candidate, ()
    retired_slices = frozenset(previous._references.slices or ()) - frozenset(
        candidate._references.slices or ()
    )
    architect = "Re-run nw-solution-architect against the current handoff; record corrected values with design verbs and nwdes design close."

    def acceptance_how(key):
        return f"Re-run nw-acceptance-designer for {key} against the current handoff; record coverage with acceptance row add and nwdes acceptance close --slice {key}."

    def notice(path, causes, how, why=None):
        return f"WITHDRAWN WHAT: {path} | WHY: {why or operation + ' retired ' + ', '.join(causes) + '.'} | HOW: {how}"

    design = candidate.design
    if design is not None:
        slices = design.get("slices", EMPTY)
        kept = Record(
            (key, own) for key, own in slices.items() if key not in retired_slices
        )
        design = freeze(
            {
                **design,
                "slices": kept,
                "shared": {
                    name: tuple(
                        {
                            **row,
                            "slices": tuple(
                                slice
                                for slice in row.get("slices", ())
                                if slice not in retired_slices
                            ),
                        }
                        for row in rows
                    )
                    if name in ("decisions", "constraints")
                    else rows
                    for name, rows in (design.get("shared") or EMPTY).items()
                },
            }
        )
    parent_notices = Record(
        (
            key,
            notice(
                f"design.slices.{key}",
                (key,),
                "Re-run nw-solution-architect for any replacement slice chosen by the root; record corrected values with design verbs and nwdes design close.",
            ),
        )
        for key in (previous.design or EMPTY).get("slices", EMPTY)
        if key in retired_slices
    )
    candidate = replace(candidate, design=design)
    retired = previous._references.known - candidate._references.known
    oracles = Record(
        (key, causes)
        for key, own in (design or EMPTY).get("slices", EMPTY).items()
        for causes in (
            _retired_causes(
                (own.get("public_oracle") or EMPTY).get("promises", ()), retired
            ),
        )
        if causes
    )
    if design is not None:
        candidate = replace(
            candidate,
            design=freeze(
                {
                    **design,
                    "slices": Record(
                        (
                            key,
                            Record(
                                (name, child)
                                for name, child in own.items()
                                if key not in oracles or name != "public_oracle"
                            ),
                        )
                        for key, own in design.get("slices", EMPTY).items()
                    ),
                }
            ),
        )
    design_notices = tuple(
        parent_notices[key]
        if key in parent_notices
        else notice(f"design.slices.{key}.public_oracle", oracles[key], architect)
        for key in dict.fromkeys(
            (
                *(previous.design or EMPTY).get("slices", EMPTY),
                *(design or EMPTY).get("slices", EMPTY),
            )
        )
        if key in parent_notices or key in oracles
    )
    acceptance = Record(
        (key, rows)
        for key, rows in candidate.acceptance.items()
        if key not in retired_slices
    )
    acceptance_notices = tuple(
        item
        for key, rows in previous.acceptance.items()
        for item in (
            (
                notice(
                    f"acceptance.{key}",
                    (key,),
                    "Re-run nw-acceptance-designer for any replacement slice chosen by the root; record coverage with acceptance row add and nwdes acceptance close --slice S.",
                ),
            )
            if key in retired_slices
            else tuple(
                notice(f"acceptance.{key}[{index}]", causes, acceptance_how(key))
                for index, row in enumerate(rows)
                for causes in (_retired_causes(_row_citations(row), retired),)
                if causes
            )
        )
    )
    acceptance = Record(
        (
            key,
            tuple(
                row for row in rows if not _retired_causes(_row_citations(row), retired)
            ),
        )
        for key, rows in acceptance.items()
    )
    withdrawn_expectations = Record(
        (row["id"], (f"expectations.rows[{index}] ({row['id']})", causes))
        for index, row in enumerate((previous.expectations or EMPTY).get("rows", ()))
        for causes in (_retired_causes(row.get("promises", ()), retired),)
        if causes
    )
    expectation_notices = tuple(
        notice(
            path,
            causes,
            "Re-run nw-user-examiner --task expectations against the current product; record the revised rows with nwdes expectations close --revise.",
        )
        for path, causes in withdrawn_expectations.values()
    )
    expectations = candidate.expectations
    if expectations is not None:
        expectations = freeze(
            {
                **expectations,
                "rows": tuple(
                    row
                    for row in expectations.get("rows", ())
                    if row["id"] not in withdrawn_expectations
                ),
            }
        )
    kept_expectations = frozenset(
        row["id"] for row in (expectations or EMPTY).get("rows", ())
    )
    examination_notices = tuple(
        notice(
            f"examination.{key}",
            (key,),
            "Re-run nw-user-examiner --task examine "
            + (
                "after revising expectations"
                if key in withdrawn_expectations
                else "against the current expectations"
            )
            + "; "
            + EXAMINATION_RECORD_HOW,
            withdrawn_expectations[key][0] + " was withdrawn."
            if key in withdrawn_expectations
            else None,
        )
        for key in previous.examination
        if key not in kept_expectations
    )
    examination = Record(
        (key, verdict)
        for key, verdict in candidate.examination.items()
        if key in kept_expectations
    )
    return replace(
        candidate,
        acceptance=acceptance,
        expectations=expectations,
        examination=examination,
    ), (
        *design_notices,
        *acceptance_notices,
        *expectation_notices,
        *examination_notices,
    )


def parse(data: bytes):
    return inspect_handoff(data).result


def lift_version_2(raw: Record) -> Record:
    """Lift legacy shared fact references without changing their authored text."""
    design = raw.get("design")
    if not isinstance(design, Mapping):
        return freeze({**raw, "version": 3})
    shared = design.get("shared")
    if not isinstance(shared, Mapping):
        return freeze({**raw, "version": 3})
    counters = raw.get("counters")
    if not isinstance(counters, Mapping):
        return freeze({**raw, "version": 3})

    def lift(state, pair):
        entries, issued = state
        name, kind = pair
        rows = shared.get(name)
        if not isinstance(rows, tuple) or not all(isinstance(row, str) for row in rows):
            return state

        start = issued.get(kind, 0)
        if type(start) is not int or start < 0:
            return state
        lifted = tuple(
            Record((("id", f"{kind}{number}"), ("text", text), ("slices", ())))
            for number, text in enumerate(rows, start + 1)
        )
        return {**entries, name: lifted}, Record(
            (*issued.items(), (kind, start + len(rows)))
        )

    shared, counters = reduce(
        lift, (("decisions", "D"), ("constraints", "K")), (shared, counters)
    )
    return freeze(
        {
            **raw,
            "version": 3,
            "counters": counters,
            "design": {**design, "shared": shared},
        }
    )


def _legacy_charter_shape_problems(raw):
    legacy = raw.get("charters")
    if _absent(legacy):
        return ()
    facts = raw.get("facts")
    return _check(
        LEGACY_CHARTERS,
        legacy,
        "charters",
        canonical=True,
        facts=facts if isinstance(facts, Mapping) else None,
    )


def lift_version_3(raw: Record) -> Record:
    """Preserve legacy charter text and labels in the feature-level choice."""
    legacy = raw.get("charters", EMPTY)
    current = {name: child for name, child in raw.items() if name != "charters"}
    if legacy != EMPTY and not _absent(legacy):
        current["charter"] = (
            Record((("kind", "Feature"), *next(iter(legacy.values())).items()))
            if len(legacy) == 1
            else Record((("kind", "LegacySlices"), ("slices", legacy)))
        )
    return freeze({**current, "version": 4})


def inspect_handoff(data: bytes):
    parsed = parse_json(data, "handoff", "HandoffInvalid")
    if isinstance(parsed, Refused):
        return HandoffInput(parsed, None)
    raw = parsed.value
    legacy_problems = ()
    if isinstance(raw, Record) and raw.get("version") == 2:
        raw = lift_version_2(raw)
    if isinstance(raw, Record) and raw.get("version") == 3:
        legacy_problems = _legacy_charter_shape_problems(raw)
        raw = (
            freeze(
                {
                    **{
                        name: child
                        for name, child in raw.items()
                        if name not in ("charters", "charter")
                    },
                    "version": 4,
                }
            )
            if legacy_problems
            else lift_version_3(raw)
        )
    # Strict JSON spells every null/empty-list value with one of these tokens.
    # Quoted matches conservatively use the schema normalizer as well.
    normalized = (
        normalize_input(HANDOFF_INPUT, raw)
        if b"null" in data or _EMPTY_JSON_ARRAY.search(data)
        else NormalizedInput(raw)
    )
    raw = normalized.value
    if (
        not isinstance(raw, Record)
        or raw.get("schema") != "nwdes.handoff"
        or raw.get("version") != 4
    ):
        return HandoffInput(
            checked(
                None,
                (
                    Defect(
                        "HandoffInvalid: handoff",
                        "Expected an object.",
                        "Supply a canonical handoff.",
                    ),
                ),
            ),
            None,
        )
    allowed = HANDOFF_INPUT.allowed
    unknown = tuple(
        _invalid("handoff." + name, "Unknown field.")
        for name in raw
        if name not in allowed
    )
    missing = tuple(
        _missing_work()
        if name == "work"
        else _invalid("handoff." + name, "Required field is missing.", True)
        for name in ("request", "scope", "work", "facts", "counters")
        if name not in raw or _absent(raw[name])
    )
    scope_raw = raw.get("scope")
    scope = (
        build_scope(scope_raw.get("kind"), scope_raw.get("id"))
        if isinstance(scope_raw, Record)
        else Built(None)
        if "scope" not in raw
        else checked(None, (_invalid("handoff.scope", "Expected a scope object."),))
    )
    scope_keys = tuple(
        _invalid("handoff.scope." + name, "Unknown field.")
        for name in (scope_raw if isinstance(scope_raw, Record) else ())
        if name
        not in (("kind",) if scope_raw.get("kind") == "Project" else ("kind", "id"))
    )
    tables = tuple(
        _invalid(name, "Expected an object.")
        for name in ("facts", "counters")
        if name in raw and not isinstance(raw[name], Record)
    )
    fact_values = raw.get("facts") if isinstance(raw.get("facts"), Record) else EMPTY
    counters = raw.get("counters") if isinstance(raw.get("counters"), Record) else EMPTY
    metadata = (
        *(
            defect
            for identity, text in fact_values.items()
            for defect in _check(TEXT, text, "facts." + identity)
        ),
        *(
            _invalid("facts." + identity, "Expected a fact id assigned by nwdes.")
            for identity in fact_values
            if not _FACT_ID.fullmatch(identity)
        ),
        *(
            _invalid(
                "counters." + kind,
                "Expected the non-negative last-issued integer for a declared id kind.",
            )
            for kind, number in counters.items()
            if kind not in "FPSBLNCYTEDK"
            or len(kind) != 1
            or type(number) is not int
            or number < 0
        ),
    )
    facts = freeze(fact_values)
    locations = tuple(
        location
        for name, spec in CANONICAL_PARTS
        if name in raw
        for location in _record_locations(spec, raw[name], name)
    )
    identities = tuple(identity for identity, _, _ in locations)
    issued = (
        *tuple(identity for identity in facts if _FACT_ID.fullmatch(identity)),
        *identities,
    )
    product = raw.get("product")
    slice_rows = product.get("slices", ()) if isinstance(product, Mapping) else ()
    slices = tuple(
        row["id"]
        for row in (slice_rows if isinstance(slice_rows, tuple) else ())
        if isinstance(row, Mapping)
        and isinstance(row.get("id"), str)
        and not _id_defects("S", row["id"], "")
    )
    first_record_sites = dict(
        reversed(tuple((identity, site) for identity, _, site in locations))
    )
    first_fact_ids = dict(
        reversed(
            tuple(
                (text, identity)
                for identity, text in facts.items()
                if isinstance(text, str)
            )
        )
    )
    part_problems = (
        *tuple(
            defect
            for name, spec in CHECKED_PARTS
            if name in raw and not _absent(raw[name])
            for defect in _check(
                spec,
                raw[name],
                name,
                True,
                facts._index if isinstance(raw.get("facts"), Record) else None,
            )
        ),
        *_stored_requirements(raw, facts),
    )
    record_problems = tuple(
        Defect(
            f"InconsistentFacts: {site}.id",
            f"Record id {identity} also identifies {first_record_sites[identity]}.",
            "Use the canonical handoff emitted by nwdes; each record id identifies one record.",
        )
        for identity, _, site in locations
        if first_record_sites[identity] != site
    )
    namespace_problems = tuple(
        problem
        for problem in part_problems
        if isinstance(problem, _ValueProblem) and problem.id_kinds
    )
    damaged_records = frozenset(
        identity
        for identity, _, site in locations
        if any(
            isinstance(problem, _ValueProblem)
            and (
                problem.path == site
                or problem.path.startswith((site + ".", site + "["))
            )
            for problem in part_problems
        )
    )
    targets = _ReferenceTargets(
        frozenset(
            identity
            for identity, _, site in locations
            if site.startswith(("product.", "design.", "expectations."))
        ),
        slices,
        tuple(
            dict.fromkeys(
                (
                    *(
                        kind
                        for problem in namespace_problems
                        for kind in problem.id_kinds
                    ),
                    *(
                        identity[0]
                        for identity, _, _ in locations
                        if identity in damaged_records
                    ),
                )
            )
        ),
        frozenset(
            (
                *damaged_records,
                *(
                    identity
                    for identity, _, site in locations
                    if first_record_sites[identity] != site
                ),
            )
        ),
        (*record_problems, *namespace_problems),
    )
    defects = (
        *unknown,
        *missing,
        *tables,
        *scope_keys,
        *(scope.defects if isinstance(scope, Refused) else ()),
        *metadata,
        *record_problems,
        *(
            Defect(
                f"InconsistentFacts: facts.{identity}",
                f"The same text is already interned as {first_fact_ids[text]}.",
                "Use the canonical handoff emitted by nwdes with one fact id per text.",
            )
            for identity, text in facts.items()
            if isinstance(text, str) and first_fact_ids[text] != identity
        ),
        *(
            _invalid(
                "counters." + kind,
                "Last-issued counter is behind an existing identity.",
            )
            for kind in dict.fromkeys(identity[0] for identity in issued)
            if isinstance(raw.get("counters"), Record)
            and type(counters.get(kind, 0)) is int
            and counters.get(kind, 0) >= 0
            and counters.get(kind, 0)
            < max(int(identity[1:]) for identity in issued if identity[0] == kind)
        ),
        *_table_reference_defects(normalized.absent_references, targets),
        *(
            defect
            for name, spec in CANONICAL_PARTS
            if name in raw
            for defect in _references(spec, raw[name], targets, name)
        ),
        *part_problems,
        *legacy_problems,
    )
    if defects:
        fields = Record(
            (
                *(
                    (problem.path, problem)
                    for problem in (
                        *tables,
                        *metadata,
                        *part_problems,
                        *legacy_problems,
                    )
                    if isinstance(problem, _ValueProblem)
                ),
                *((("charter", legacy_problems[0]),) if legacy_problems else ()),
            )
        )
        return HandoffInput(checked(None, defects), targets, raw, fields)
    value = Handoff(
        raw["request"],
        scope.value,
        freeze(raw["work"]),
        freeze(raw["counters"]),
        facts,
        **{
            name: freeze(raw[name])
            for name in (
                "product",
                "design",
                "acceptance",
                "expectations",
                "charter",
                "examination",
            )
            if name in raw and not _absent(raw[name])
        },
    )
    return HandoffInput(Built(value), targets, raw)


def _comparison_value(value):
    if (
        isinstance(value, tuple)
        and value
        and all(isinstance(child, Mapping) and "id" in child for child in value)
    ):
        return {child["id"]: child for child in value}
    return value


def compare(previous: Handoff, new: Handoff):
    """Compare schema observations; only TEXT fields denote interned facts."""

    def changes(old, current, path):
        if old == current:
            return ()
        old, current = _comparison_value(old), _comparison_value(current)
        if isinstance(old, Mapping) and isinstance(current, Mapping):
            old_keys = {
                key for key, child in old.items() if child not in (None, (), EMPTY)
            }
            new_keys = {
                key for key, child in current.items() if child not in (None, (), EMPTY)
            }
            return tuple(
                pair
                for key in sorted(old_keys | new_keys)
                for pair in (
                    (("ADDED", (path + "." + key).lstrip(".")),)
                    if key not in old_keys
                    else (("REMOVED", (path + "." + key).lstrip(".")),)
                    if key not in new_keys
                    else changes(old[key], current[key], (path + "." + key).lstrip("."))
                )
            )
        if (
            isinstance(old, tuple)
            and isinstance(current, tuple)
            and len(old) == len(current)
        ):
            return tuple(
                pair
                for index, (before, after) in enumerate(zip(old, current, strict=True))
                for pair in changes(before, after, f"{path}[{index}]")
            )
        return () if old == current else (("REPLACED", path),)

    def view(handoff):
        return {
            name: expanded(spec, getattr(handoff, name), handoff.facts)
            for name, spec in CANONICAL_PARTS
        } | {
            "scope": handoff.scope,
        }

    return changes(view(previous), view(new), "")


def project_design(design, slice):
    """Keep a slice and only the shared decisions and constraints that govern it."""
    if design is None or isinstance(design, UnavailableInput):
        return design
    shared = design.get("shared") or EMPTY
    parts = design.get("slices") or EMPTY
    if isinstance(shared, UnavailableInput) or isinstance(parts, UnavailableInput):
        return design
    return Record(
        (
            *((("paradigm", design["paradigm"]),) if "paradigm" in design else ()),
            (
                "shared",
                Record(
                    (
                        name,
                        tuple(
                            freeze({**row, "slices": (slice,)})
                            for row in sorted(
                                shared.get(name, ()), key=lambda row: int(row["id"][1:])
                            )
                            if slice in row.get("slices", ())
                        ),
                    )
                    for name in ("decisions", "constraints")
                ),
            ),
            ("slices", Record(((slice, parts[slice]),)) if slice in parts else EMPTY),
        )
    )


def affected_slices(previous: Handoff, new: Handoff) -> tuple[str, ...]:
    """Compute changes in slice-owned designs and cited shared record meaning."""
    old_design, new_design = previous.design or EMPTY, new.design or EMPTY
    old_own, new_own = old_design.get("slices", EMPTY), new_design.get("slices", EMPTY)
    own_ids = old_own.keys() | new_own.keys()
    affected = {
        identity
        for identity in own_ids
        if expanded(SLICE_DESIGN, old_own.get(identity), previous.facts)
        != expanded(SLICE_DESIGN, new_own.get(identity), new.facts)
    }

    def changed_members(before, after):
        old_members = frozenset(before.get("slices", ()))
        new_members = frozenset(after.get("slices", ()))
        changed_text = previous.facts.get(before.get("text")) != new.facts.get(
            after.get("text")
        )
        return old_members | new_members if changed_text else old_members ^ new_members

    def shared_changes(name):
        old_records = {
            row["id"]: row for row in old_design.get("shared", EMPTY).get(name, ())
        }
        new_records = {
            row["id"]: row for row in new_design.get("shared", EMPTY).get(name, ())
        }
        return frozenset(
            slice
            for identity in old_records.keys() | new_records.keys()
            for slice in changed_members(
                old_records.get(identity, EMPTY), new_records.get(identity, EMPTY)
            )
        )

    return tuple(
        sorted(
            affected | shared_changes("decisions") | shared_changes("constraints"),
            key=lambda identity: int(identity[1:]),
        )
    )


def expanded(spec, value, facts):
    """Use field meaning, not an F-shaped string, to recover authored values."""
    if value is None or isinstance(value, UnavailableInput):
        return value
    if spec.kind == "text":
        return facts if isinstance(facts, UnavailableInput) else facts[value]
    if spec.kind == "choice":
        return expanded(spec.index[value[spec.discriminator]], value, facts)
    if spec.kind == "record":
        return {
            name: expanded(spec.index[name], child, facts)
            if name in spec.index
            else child
            for name, child in value.items()
        }
    if spec.kind == "table":
        return {
            name: expanded(spec.members[0], child, facts)
            for name, child in value.items()
        }
    if spec.kind == "array":
        return tuple(expanded(spec.members[0], child, facts) for child in value)
    return value


def set_work(previous, values, slice=None, rework=False):
    return finish(prepare_work(previous, values, slice, rework))


def prepare_work(previous, values, slice=None, rework=False):
    supplied = (
        _check(REWORK, values, "work.rework")
        if rework and values is not None
        else ()
        if rework
        else _check(WORK_PATCH, values, "work")
    )
    references = _prior_references(previous)
    target = _slice_problems(slice, references)
    if target:
        return checked(None, (*supplied, *target))
    if slice is not None and (
        references is None
        or references.slices is None
        or not _reference_available(slice, references)
    ):
        return checked(
            None,
            (
                *supplied,
                *_unit_defects(previous.product),
                *(references.defects if references is not None else ()),
            ),
        )
    current = (
        next(
            row.get("work", EMPTY)
            for row in previous.product["slices"]
            if isinstance(row, Mapping) and row.get("id") == slice
        )
        if slice
        else previous.work
    )
    if isinstance(current, UnavailableInput):
        return checked(None, (*supplied, current.defect))
    absent = (
        (_missing_work(slice),) if rework and values is not None and not current else ()
    )
    if supplied or absent:
        return checked(None, (*supplied, *absent))
    if rework and values is None and not current:
        return Built(PreparedHandoff(lambda: Built(previous)))
    payload = expanded(WORK, current, previous.facts)
    raw = (
        (
            {**payload, "rework": values}
            if values is not None
            else {name: child for name, child in payload.items() if name != "rework"}
        )
        if rework
        else {**payload, **values}
    )
    defects = _check(WORK, raw, "work")
    if defects:
        return checked(None, defects)
    return Built(PreparedHandoff(lambda: _apply_work(previous, current, raw, slice)))


def _apply_work(previous, current, raw, slice):
    built, facts, counters = _build(
        WORK, raw, current, previous.facts, previous.counters
    )
    if slice:
        product = freeze(
            {
                **previous.product,
                "slices": tuple(
                    freeze({**row, "work": built}) if row["id"] == slice else row
                    for row in previous.product["slices"]
                ),
            }
        )
        result = replace(previous, product=product, facts=facts, counters=counters)
    else:
        result = replace(previous, work=built, facts=facts, counters=counters)
    return Built(_prune(result))


@dataclass(frozen=True)
class _SlicePromises:
    """The pending slice's positional own list and effective non-own citations."""

    owned: tuple[str, ...]
    supplied: tuple[str, ...]
    cited: tuple[str, ...]

    @property
    def retained(self):
        return self.owned[: len(self.supplied)] if self.supplied else self.owned

    @property
    def removed(self):
        return (
            frozenset(self.owned[len(self.supplied) :])
            if self.supplied
            else frozenset()
        )

    def payload(self, rows):
        if not self.supplied:
            return rows
        replacements = Record(zip(self.owned, self.supplied, strict=False))
        removed = self.removed
        return (
            *(
                {"kind": "Outcome", "id": row["id"], "text": replacements[row["id"]]}
                if row["id"] in replacements
                else row
                for row in rows
                if row["id"] not in removed
            ),
            *(
                {"kind": "Outcome", "text": text}
                for text in self.supplied[len(self.owned) :]
            ),
        )

    def references(self, rows):
        return (
            *self.retained,
            *(
                next(
                    row["id"]
                    for row in rows
                    if row["kind"] == "Outcome" and row["text"] == text
                )
                for text in self.supplied[len(self.owned) :]
            ),
            *self.cited,
        )


def _slice_promises(previous, values):
    scalar = parse_slice_id(values.slice)
    flags = (
        *_check(array(TEXT), values.promises, "--promise"),
        *_check(array(PROMISE_REFERENCE), values.cites, "--cites"),
        *(scalar.defects if isinstance(scalar, Refused) else ()),
    )
    if flags:
        return checked(None, flags)
    if values.slice is None:
        return Built(_SlicePromises((), values.promises, values.cites))
    product = previous.product
    design = previous.design
    if isinstance(product, UnavailableInput):
        return product
    if isinstance(design, UnavailableInput):
        return design
    promises = (product or EMPTY).get("promises", ())
    slices = (design or EMPTY).get("slices") or EMPTY
    missing = _unavailable((promises, slices))
    if missing is not None:
        return missing
    selected = slices.get(values.slice) or EMPTY
    oracle = selected.get("public_oracle") or EMPTY
    shared = frozenset(
        identity
        for key, own in slices.items()
        if key != values.slice
        for identity in (own.get("public_oracle") or EMPTY).get("promises", ())
    )
    known = frozenset(row["id"] for row in promises)
    owned = tuple(
        identity
        for identity in oracle.get("promises", ())
        if identity in known and identity not in shared and identity not in values.cites
    )
    own_ids = frozenset(owned)
    cited = values.cites or tuple(
        identity for identity in oracle.get("promises", ()) if identity not in own_ids
    )
    return Built(_SlicePromises(owned, values.promises, cited))


@dataclass(frozen=True)
class SliceValues:
    observation: str | None
    design: Record
    paradigm: str | None = None
    slice: str | None = None
    promises: tuple[str, ...] = ()
    cites: tuple[str, ...] = ()
    decisions: tuple[str, ...] | None = None
    constraints: tuple[str, ...] | None = None

    @property
    def intent(self):
        return freeze(
            {
                "observation": self.observation,
                **({"id": self.slice} if self.slice else {}),
            }
        )


def set_slice(
    previous: Handoff, values: SliceValues, *, programs: ProgramResolution = EMPTY
):
    return finish(prepare_slice(previous, values, programs=programs))


def _missing_slice_flags(values):
    fields = {"observation": values.observation}
    if isinstance(values.design, Mapping) and not is_prose_only(values.design):
        fields.update(
            oracle=values.design.get("oracle"),
            command=values.design.get("verification"),
        )
        public = values.design.get("public_oracle", EMPTY)
        if public is None:
            public = EMPTY
        if isinstance(public, Mapping):
            fields.update((name, public.get(name)) for name in PUBLIC_ORACLE.required)
    return tuple(
        missing_flag(name)
        for name in _REQUIRED_FLAGS["slice"]
        if name in fields and _absent(fields[name])
    )


def _resolve_slice_values(previous, values, supplied):
    """Resolve creation or retention only from the selected produced design unit."""
    scalar = parse_slice_id(values.slice)
    if isinstance(scalar, Refused):
        return scalar
    current = None
    if scalar.value is not None:
        design = previous.design
        if isinstance(design, UnavailableInput):
            return design
        slices = (design or EMPTY).get("slices", EMPTY)
        if isinstance(slices, UnavailableInput):
            return slices
        current = slices.get(scalar.value)
        missing = _unavailable(current if current is not None else slices)
        if missing is not None:
            return missing
    if current is None:
        return checked(values, (*supplied, *_missing_slice_flags(values)))
    if supplied:
        return checked(None, supplied)
    retained = expanded(SLICE_DESIGN, current, previous.facts)
    missing = _unavailable(retained)
    if missing is not None:
        return missing
    observation = values.observation
    if observation is None:
        product = previous.product
        if isinstance(product, UnavailableInput):
            return product
        slices = (product or EMPTY).get("slices", ())
        if isinstance(slices, UnavailableInput):
            return slices
        target = next(
            (
                row
                for row in slices
                if isinstance(row, Mapping) and row.get("id") == scalar.value
            ),
            None,
        )
        missing = _unavailable(target if target is not None else slices)
        if missing is not None:
            return missing
        if target is None:
            return UnavailableInput(
                next(
                    iter(
                        _slice_problems(scalar.value, _prior_references(previous))
                        or _prior_references(previous).defects
                    )
                )
            )
        observation = expanded(TEXT, target["observation"], previous.facts)
        if isinstance(observation, UnavailableInput):
            return observation
    design = {**retained, **values.design}
    public = values.design.get("public_oracle")
    if public:
        design["public_oracle"] = {**retained.get("public_oracle", {}), **public}
    elif "public_oracle" in retained:
        design["public_oracle"] = retained["public_oracle"]
    else:
        design.pop("public_oracle", None)
    targets = values.design.get("targets")
    if targets:
        changed = frozenset(row["change"] for row in targets)
        design["targets"] = tuple(
            row
            for change in TARGET.index["change"].members
            for row in (targets if change in changed else retained.get("targets", ()))
            if row["change"] == change
        )
    return Built(replace(values, observation=observation, design=freeze(design)))


def _slice_observation_problems(previous, slice, observation):
    scalar = parse_slice_id(slice)
    if (
        not isinstance(scalar, Built)
        or scalar.value is None
        or not isinstance(observation, Built)
        or observation.value is None
    ):
        return ()
    product = previous.product
    if product is None or isinstance(product, UnavailableInput):
        return ()
    slices = product.get("slices", ())
    if isinstance(slices, UnavailableInput):
        return ()
    if not any(
        isinstance(row, Mapping) and row.get("id") == scalar.value for row in slices
    ):
        return ()
    return tuple(
        Defect(
            "InconsistentFacts: --observation",
            f"An observation identifies one slice and equals {row['id']}'s observation.",
            f"Give {scalar.value} a distinct observation or update {row['id']} "
            f"with --slice {row['id']}.",
        )
        for row in slices
        if isinstance(row, Mapping)
        and isinstance(row.get("id"), str)
        and row["id"] != scalar.value
        and _unavailable(row) is None
        and expanded(TEXT, row["observation"], previous.facts) == observation.value
    )


def _slice_citation_problems(previous, values):
    if values.decisions is None and values.constraints is None:
        return ()
    design = previous.design
    if isinstance(design, UnavailableInput):
        return (design.defect,)
    shared = (design or EMPTY).get("shared") or EMPTY
    if isinstance(shared, UnavailableInput):
        return (shared.defect,)

    def inspect(name, flag, cited, kind):
        if cited is None:
            return ()
        problems = (
            *_unit_defects(cited),
            *_check(array(Spec("reference", (kind,))), cited, "--" + flag),
        )
        rows = shared.get(name, ())
        unavailable = _unit_defects(rows)
        if problems or unavailable:
            return (*problems, *unavailable)
        known = frozenset(row["id"] for row in rows)
        return tuple(
            Defect(
                f"DanglingReference: --{flag} {identity}",
                f"No shared {flag} has identity {identity}.",
                f"Use an existing shared {flag} id from the architecture brief.",
            )
            for identity in cited
            if identity not in known
        )

    return (
        *inspect("decisions", "decision", values.decisions, "D"),
        *inspect("constraints", "constraint", values.constraints, "K"),
    )


def _slice_membership(shared, identity, values):
    updates = {"decisions": values.decisions, "constraints": values.constraints}
    return Record(
        (
            name,
            tuple(
                freeze(
                    {
                        **row,
                        "slices": tuple(
                            sorted(
                                (set(row.get("slices", ())) - {identity})
                                | ({identity} if row["id"] in updates[name] else set()),
                                key=lambda slice: int(slice[1:]),
                            )
                        ),
                    }
                )
                for row in rows
            )
            if name in updates and updates[name] is not None
            else rows,
        )
        for name, rows in shared.items()
    )


def _slice_commands(previous, values):
    design = previous.design
    slices = design.get("slices") if isinstance(design, Mapping) else None
    current = (
        slices.get(values.slice)
        if isinstance(slices, Mapping) and isinstance(values.slice, str)
        else None
    )
    patch = normalize_input(SLICE_DESIGN, values.design).value
    return verification_commands(
        {
            **(current if isinstance(current, Mapping) else EMPTY),
            **(patch if isinstance(patch, Mapping) else EMPTY),
        },
        f"design.slices.{values.slice or 'new'}",
    )


def prepare_slice(
    previous: Handoff, values: SliceValues, *, programs: ProgramResolution = EMPTY
):
    values = replace(values, design=normalize_input(SLICE_DESIGN, values.design).value)
    observation, design_values, paradigm, slice, cites = (
        values.observation,
        values.design,
        values.paradigm,
        values.slice,
        values.cites,
    )
    prior_design = previous.design
    selected = (
        paradigm
        if paradigm is not None
        else prior_design
        if isinstance(prior_design, UnavailableInput)
        else (prior_design or {}).get("paradigm")
    )
    observed = checked(
        observation,
        _check(TEXT, observation, "--observation") if observation is not None else (),
    )
    supplied = (
        *(observed.defects if isinstance(observed, Refused) else ()),
        *_check(SLICE_PATCH, design_values, f"design.slices.{slice or 'new'}"),
    )
    resolved = _resolve_slice_values(previous, values, supplied)
    prose_slice = isinstance(resolved, Built) and is_prose_only(resolved.value.design)
    design_path = f"design.slices.{slice or 'new'}"
    promise_plan = _slice_promises(previous, values)
    defects = (
        *supplied,
        *(
            resolved.defects
            if isinstance(resolved, Refused)
            else _unit_defects(resolved)
        ),
        *(
            _check(DESIGN.index["paradigm"], selected, "--paradigm")
            if selected
            else (
                _invalid(
                    "--paradigm", "The first slice needs its design paradigm.", True
                ),
            )
        ),
        *(
            (
                _check(SLICE_PATCH, resolved.value.design, design_path)
                + (
                    ()
                    if prose_slice
                    else _required_slice_defects(design_path, resolved.value.design)
                )
            )
            if isinstance(resolved, Built)
            else ()
        ),
        *(
            _oracle_on_prose(_supplied_oracle_fields(values.design), _flag_site(slice))
            if prose_slice
            else ()
        ),
        *(
            _check(PUBLIC_ORACLE, EMPTY, f"design.slices.{slice}.public_oracle")
            if isinstance(resolved, Built)
            and isinstance(promise_plan, Built)
            and not prose_slice
            and "public_oracle" not in resolved.value.design
            and (promise_plan.value.supplied or promise_plan.value.cited)
            else ()
        ),
        *(
            _references(
                PUBLIC_ORACLE,
                {"promises": cites},
                _prior_references(previous),
                "--cites",
            )
            if _prior_references(previous) is not None
            else ()
        ),
        *_slice_problems(
            slice,
            None
            if isinstance(prior_design, UnavailableInput)
            or isinstance((prior_design or EMPTY).get("slices"), UnavailableInput)
            else _prior_references(previous),
        ),
        *(
            promise_plan.defects
            if isinstance(promise_plan, Refused)
            else _unit_defects(promise_plan)
        ),
        *_slice_observation_problems(previous, slice, observed),
        *_slice_citation_problems(previous, values),
        *_program_problems(_slice_commands(previous, values), programs),
    )
    if defects:
        return checked(None, defects)
    values = replace(resolved.value, paradigm=selected)
    observation = values.observation
    product = (
        expanded(PRODUCT, previous.product, previous.facts) if previous.product else {}
    )
    missing = _unavailable(product)
    if missing is not None:
        return checked(None, (missing.defect,))
    intent = values.intent
    observations = {
        row["id"]: observation if row["id"] == slice else row["observation"]
        for row in product.get("slices", ())
    }
    slices = tuple(
        {
            **row,
            **(
                {
                    "depends_on": tuple(
                        observations[identity] for identity in row["depends_on"]
                    )
                }
                if "depends_on" in row
                else {}
            ),
        }
        for row in product.get("slices", ())
    )
    updated_slices = (
        [{**row, **intent} if row["id"] == slice else row for row in slices]
        if slice
        else [*slices, intent]
    )
    promise_rows = promise_plan.value.payload(product.get("promises", ()))
    promise_product = {**product, "promises": promise_rows}
    projected_promises = _project_product_promises(promise_product, previous)
    if isinstance(projected_promises, UnavailableInput):
        return checked(None, (projected_promises.defect,))
    references = promise_plan.value.references(projected_promises)
    if slice is None:
        coverage = slice_promise_problems(
            {"promises": references},
            tuple(row["id"] for row in projected_promises),
            "product.slice",
        )
        if coverage:
            return checked(None, coverage)
    updated_slices = [
        {**row, "promises": references}
        if references
        and ((slice and row.get("id") == slice) or (not slice and row is intent))
        else row
        for row in updated_slices
    ]
    payload = {
        **promise_product,
        "slices": updated_slices,
    }
    product_result = _prepare_decoded(
        previous,
        _RoleApplication("product", slice, "slice set"),
        inspect_output(
            "product",
            serialize(
                freeze(
                    {
                        "outcome": "accepted",
                        "diagnostic": "",
                        "payload": payload,
                    }
                )
            ),
        ),
    )
    if isinstance(product_result, Refused):
        return product_result
    return Built(
        PreparedHandoff(
            lambda: _apply_slice(
                previous,
                values,
                product_result.value,
                promise_plan.value,
            )
        )
    )


def _apply_slice(previous, values, product, promises):
    current = _candidate_part(previous, "product", product.output.payload, None)
    selected, design_values = values.paradigm, values.design
    identity = values.slice or next(
        row["id"]
        for row in current.product["slices"]
        if current.facts[row["observation"]] == values.observation
    )
    prose_slice = is_prose_only(design_values)
    raw = {
        name: child
        for name, child in design_values.items()
        if not (prose_slice and name in _PROSE_FORBIDDEN)
    }
    public = design_values.get("public_oracle") or EMPTY
    if prose_slice:
        public = {
            name: child
            for name, child in public.items()
            if name not in _PROSE_PUBLIC_FORBIDDEN
        }
    references = promises.references(
        expanded(
            PRODUCT.index["promises"],
            current.product.get("promises", ()),
            current.facts,
        )
    )
    if "public_oracle" in design_values or references:
        raw["public_oracle"] = {**public, "promises": references}
    built, facts, counters = _build(
        SLICE_DESIGN, raw, None, current.facts, current.counters
    )
    design = freeze(
        {
            **(current.design or {}),
            "paradigm": selected,
            "shared": _slice_membership(
                (current.design or {}).get("shared", EMPTY), identity, values
            ),
            "slices": {**(current.design or {}).get("slices", {}), identity: built},
        }
    )
    acceptance, facts, counters = _acceptance_for_design(
        current.acceptance, design, current.product, facts, counters
    )
    candidate = replace(
        current, design=design, facts=facts, counters=counters, acceptance=acceptance
    )
    candidate, notices = _withdraw_references(previous, candidate, "slice set")
    withdrawn = _prose_withdrawals(previous, identity, built) if prose_slice else ()
    return validate(_prune(replace(candidate, withdrawals=(*withdrawn, *notices))))


def snapshot_adrs(handoff, snapshot):
    if handoff.design is None:
        return handoff
    return _prune(replace(handoff, design=freeze({**handoff.design, "adrs": snapshot})))


def parse_slice_id(value, required=False):
    """Parse slice identities at the shared invocation and role boundary."""
    if isinstance(value, UnavailableInput):
        return checked(None, (value.defect,))
    if value is None:
        return checked(None, (missing_flag("slice"),) if required else ())
    scalar = _check(LINE, value, "--slice")
    return checked(value, scalar or _id_defects("S", value, "--slice"))


def _slice_problems(value, references, required=False):
    scalar = parse_slice_id(value, required)
    if isinstance(scalar, Refused):
        return scalar.defects
    if scalar.value is None or references is None or references.slices is None:
        return ()
    if not _reference_available(scalar.value, references):
        return ()
    return (
        (
            Defect(
                f"DanglingReference: --slice {scalar.value}",
                "No slice has this id.",
                "Use an existing slice identity assigned by nwdes.",
            ),
        )
        if scalar.value not in references.slices
        else ()
    )


@dataclass(frozen=True)
class InvocationInput:
    verb: str
    action: str | None
    values: Record
    roots: Built | Refused
    scope: Built | Refused
    defects: tuple[Defect, ...]


_REPEATED_FLAGS = (
    "command",
    "support",
    "create",
    "extend",
    "promise",
    "cites",
    "handoff",
)
_SCALAR_FLAGS = (
    "repo_root",
    "project_root",
    "feature",
    "epic",
    "request",
    "size",
    "value",
    "delta",
    "reason",
    "slice",
    "observation",
    "paradigm",
    "oracle",
    "stimulus",
    "expected",
    "falsifier",
    "kind",
)
_EXTRA_FLAG_SPECS = (
    ("support", array(LINE), "--support"),
    ("create", array(LINE), "--create"),
    ("extend", array(LINE), "--extend"),
    ("promise", array(TEXT), "--promise"),
    ("cites", array(PROMISE_REFERENCE), "--cites"),
    ("decision", array(Spec("reference", ("D",))), "--decision"),
    ("constraint", array(Spec("reference", ("K",))), "--constraint"),
)
_FLAG_SPEC_INDEX = MappingProxyType(
    {name: (spec, path) for name, spec, path in (*FLAG_SPECS, *_EXTRA_FLAG_SPECS)}
)
_INVOCATION_DEFAULTS = Record(
    (
        *(
            (name, None)
            for name in (*_SCALAR_FLAGS, "previous", "new", "decision", "constraint")
        ),
        *((name, ()) for name in _REPEATED_FLAGS),
        ("product", False),
    )
)
_REQUIRED_FLAGS = MappingProxyType(
    {
        "feature": ("request", "size", "value"),
        "work": ("size", "value"),
        "slice": (
            "observation",
            "oracle",
            "stimulus",
            "expected",
            "falsifier",
            "command",
        ),
        "acceptance": ("slice",),
        "schema": ("handoff",),
        "delta": ("previous", "new"),
    }
)
_ACTIVE_FLAGS = MappingProxyType(
    {
        "feature": frozenset(("request", "size", "value")),
        "work": frozenset(("size", "value")),
        "slice": frozenset(
            (
                "observation",
                "paradigm",
                "oracle",
                "stimulus",
                "expected",
                "falsifier",
                "command",
                "support",
                "create",
                "extend",
                "promise",
                "cites",
                "decision",
                "constraint",
            )
        ),
    }
)


_ORACLE_FLAGS = frozenset(("oracle", "stimulus", "expected", "falsifier", "command"))


def _required_flags(verb, action, slice=None):
    return (
        ()
        if verb == "slice" and slice is not None
        else (("delta", "reason") if action == "set" else ())
        if verb == "rework"
        else _REQUIRED_FLAGS.get(verb, ())
    )


def _unit_defects(value):
    if isinstance(value, UnavailableInput):
        return (value.defect,)
    children = (
        value.values()
        if isinstance(value, Mapping)
        else value
        if isinstance(value, (tuple, list))
        else ()
    )
    return tuple(defect for child in children for defect in _unit_defects(child))


def invocation(verb, action, flags, project_root_is_directory=True):
    """Produce argv units without I/O; roots and scope fail independently."""
    required = frozenset(_required_flags(verb, action, flags.get("slice")))
    if verb == "slice" and prose.prose_only(
        (*(flags.get("create") or ()), *(flags.get("extend") or ()))
    ):
        required -= _ORACLE_FLAGS
    active = (
        (frozenset(("delta", "reason")) if action == "set" else frozenset())
        if verb == "rework"
        else _ACTIVE_FLAGS.get(verb, frozenset())
    )

    def unit(name, default):
        value = flags.get(name, default)
        if name in required and not value:
            return UnavailableInput(missing_flag(name))
        if name == "slice" and verb in (
            "work",
            "rework",
            "slice",
            "schema",
            "acceptance",
        ):
            scalar = parse_slice_id(value, required=name in required)
            return (
                UnavailableInput(scalar.defects[0])
                if isinstance(scalar, Refused)
                else scalar.value
            )
        if name in active and value is not None:
            spec, path = _FLAG_SPEC_INDEX[name]
            return _flag_unit(spec, value, path)
        return freeze(value)

    values = Record(
        (name, unit(name, default)) for name, default in _INVOCATION_DEFAULTS.items()
    )
    root_problems = (
        *(
            defect
            for name in ("repo_root", "project_root")
            for defect in _unit_defects(values[name])
        ),
        *(
            (
                Defect(
                    "MissingFact: --project-root",
                    "The project root is not an existing directory.",
                    "Supply the existing project configuration root.",
                ),
            )
            if verb not in ("schema", "delta")
            and not isinstance(values["project_root"], UnavailableInput)
            and not project_root_is_directory
            else ()
        ),
    )
    roots = checked(
        (flags.get("repo_root"), flags.get("project_root")),
        root_problems if verb not in ("schema", "delta") else (),
    )
    scope = (
        Built(None)
        if verb in ("schema", "delta")
        else build_scope("Project")
        if values["product"]
        else build_scope(
            "Feature" if values["feature"] else "Epic",
            values["feature"] or values["epic"],
        )
        if values["feature"] or values["epic"]
        else checked(None, (missing_flag("feature/--epic"),))
    )
    problems = checked(
        None,
        (
            *_unit_defects(values),
            *(root_problems if verb != "delta" else ()),
            *(scope.defects if isinstance(scope, Refused) else ()),
        ),
    )
    return InvocationInput(
        verb,
        action,
        values,
        roots,
        scope,
        problems.defects if isinstance(problems, Refused) else (),
    )


def _invocation_slice(values):
    return SliceValues(
        observation=values["observation"],
        paradigm=values["paradigm"],
        slice=values["slice"],
        promises=values["promise"],
        cites=values["cites"],
        decisions=values["decision"],
        constraints=values["constraint"],
        design=Record(
            (
                ("oracle", values["oracle"]),
                ("verification", values["command"]),
                ("supports", values["support"]),
                (
                    "targets",
                    tuple(
                        Record((("path", path), ("change", change)))
                        for name, change in (("create", "Create"), ("extend", "Extend"))
                        for path in values[name]
                    ),
                ),
                (
                    "public_oracle",
                    Record(
                        (name, values[name])
                        for name in ("stimulus", "expected", "falsifier")
                    ),
                ),
            )
        ),
    )


def _prior_references(previous):
    if isinstance(previous, Record) and "reference_units" in previous:
        return previous["reference_units"]
    return previous._references


def _invocation_source(prior, scope):
    if prior is None:
        return None
    if isinstance(prior.result, Built):
        return prior.result.value
    return Record(
        (
            *prior.record_parts().items(),
            ("request", prior.part("request")),
            ("work", prior.part("work")),
            ("counters", prior.part("counters")),
            ("scope", scope),
            ("reference_units", prior.references),
        )
    )


def invocation_commands(call, prior, output=None):
    if not isinstance(call.roots, Built) or not isinstance(call.scope, Built):
        return ()
    if call.verb == "design":
        return (
            _design_commands(output.payload)
            if output is not None and output.outcome == "accepted"
            else ()
        )
    if call.verb != "slice":
        return ()
    source = _invocation_source(prior, call.scope.value)
    return (
        _slice_commands(source, _invocation_slice(call.values))
        if source is not None
        else ()
    )


def _invocation_transition(call, previous, output, programs, resolution=EMPTY):
    values = call.values
    verb = call.verb
    if verb == "feature":
        return prepare_feature(
            previous,
            values["request"],
            call.scope.value if isinstance(call.scope, Built) else None,
            values["size"],
            values["value"],
        )
    if verb in ROLE_SCHEMAS:
        if output is None:
            return checked(
                None, (_invalid(verb, "Role output bytes were not supplied.", True),)
            )
        return _prepare_decoded(
            previous,
            _RoleApplication(verb, values["slice"], call.action),
            output,
            programs=programs,
            resolution=resolution,
        )
    if verb == "work":
        return prepare_work(
            previous,
            {"size": values["size"], "value": values["value"]},
            values["slice"],
        )
    if verb == "rework":
        return prepare_work(
            previous,
            {"delta": values["delta"], "reason": values["reason"]}
            if call.action == "set"
            else None,
            values["slice"],
            rework=True,
        )
    if verb == "slice":
        return prepare_slice(previous, _invocation_slice(values), programs=programs)
    return Built(PreparedHandoff(lambda: Built(previous)))


def prepare_invocation(
    call: InvocationInput,
    previous: HandoffInput | None,
    output=None,
    *,
    programs: ProgramResolution = EMPTY,
    resolution=EMPTY,
):
    """Inspect all produced argv/prior units; expose construction only after refusal is empty."""
    readable = isinstance(call.roots, Built) and isinstance(call.scope, Built)
    decoded = (
        (output if isinstance(output, RoleInput) else inspect_output(call.verb, output))
        if call.verb in ROLE_SCHEMAS
        and output is not None
        and isinstance(call.roots, Built)
        else None
    )
    prior = previous if readable else None
    prior_problems = (
        prior.result.defects
        if prior is not None and isinstance(prior.result, Refused)
        else ()
    )
    missing = (
        (
            Defect(
                f"FeatureUnknown: {getattr(call.scope.value, 'id', 'project')}",
                "No handoff exists for this scope.",
                "Create the feature with feature new first.",
            ),
        )
        if readable and prior is None and call.verb != "feature"
        else ()
    )
    source = _invocation_source(prior, call.scope.value) if readable else None
    if source is not None or (readable and prior is None and call.verb == "feature"):
        result = _invocation_transition(call, source, decoded, programs, resolution)
    elif (
        call.verb in ROLE_SCHEMAS
        and output is not None
        and isinstance(call.roots, Built)
    ):
        result = checked(
            decoded.payload,
            _output_problems(
                _RoleApplication(call.verb, call.values["slice"], call.action),
                decoded,
                None,
            ),
        )
    else:
        result = checked(None, _unit_defects(call.values))
    problems = (
        *call.defects,
        *prior_problems,
        *missing,
        *(result.defects if isinstance(result, Refused) else ()),
    )
    refused = checked(None, problems)
    return (
        InvocationRefused(refused.refusal, decoded)
        if isinstance(refused, Refused)
        else result
    )
