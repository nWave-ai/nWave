"""Role value verbs and immutable draft edits derived from the handoff Spec tree."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from enum import Enum
from functools import reduce
from types import MappingProxyType

from nwdes import handoff as h
from nwdes.contracts import Built, Defect, Refused, checked, refuse


KINDS = (*h.ROLE_SCHEMAS, "craft", "review")
ROOT_NAMES = ("repo-root", "project-root", "global-config", "feature", "epic", "slice")
BOOL = h.Spec("boolean")
INTEGER = h.Spec("integer")


class ReviewSubject(Enum):
    ORACLE = "oracle"
    SLICE = "slice"
    CANDIDATE = "candidate"


REVIEW_SUBJECT = h.enum(*(subject.value for subject in ReviewSubject))
CRAFT_FILE = h.record(
    ("path", "change"), path=h.LINE, change=h.enum("Created", "Modified", "Deleted")
)
CRAFT_COMMAND = h.record(("command", "exit"), command=h.COMMAND, exit=INTEGER)
CRAFT_ACTOR = h.enum("nw-software-crafter", "nw-functional-software-crafter")
REVIEW_FINDING = h.record(
    ("location", "obligation", "observation", "remediation", "owner"),
    location=h.LINE,
    obligation=h.TEXT,
    observation=h.TEXT,
    remediation=h.TEXT,
    owner=h.enum("oracle", "design", "implementation", "product"),
)
REVIEW_OBSERVATION = h.record(("id", "text"), id=h.LINE, text=h.TEXT)
FINDING_ROLES = MappingProxyType(
    {
        "oracle": "nw-acceptance-designer",
        "design": "nw-solution-architect",
        "implementation": MappingProxyType(
            {
                "functional": "nw-functional-software-crafter",
                "object_oriented": "nw-software-crafter",
                "procedural": "nw-software-crafter",
            }
        ),
        "product": "nw-product-owner",
    }
)


@dataclass(frozen=True)
class ReviewEvidence:
    commit: str
    dirty: tuple[str, ...]
    content: str | None = None


def evidence_dirty(status_entries, destinations):
    """True when a changed path outside git-ignored paths and the feature directory exists.

    nwdes writes the feature directory's documents, drafts and run records itself, so they
    never change the reviewed candidate.
    """
    prefix = destinations.rstrip("/") + "/"
    return any(
        code != "!!" and not path.startswith(prefix) for code, path in status_entries
    )


def content_digest(files):
    """Digest of approved oracle bytes: (path, bytes or None) pairs, each path sorted."""
    lines = (
        json.dumps(
            [path, "missing" if data is None else hashlib.sha256(data).hexdigest()]
        )
        for path, data in sorted(files, key=lambda pair: pair[0])
    )
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def candidate_scope(scope):
    """True for a candidate review, which names the whole feature rather than one slice."""
    return isinstance(scope, _CandidateScope)


def review_evidence(commit, status_entries, destinations, files=None, others=()):
    """Clean-tree evidence; an oracle review judges its own files by content instead.

    The oracle and supports of the feature's other slices (others) are test files of work that
    is not under review: they are not dirty evidence for this review and are not bound.
    """
    owned = (
        frozenset()
        if files is None
        else frozenset(path for path, _ in files) | frozenset(others)
    )
    return ReviewEvidence(
        commit,
        tuple(
            path
            for code, path in status_entries
            if evidence_dirty(((code, path),), destinations) and path not in owned
        ),
        None if files is None else content_digest(files),
    )


def oracle_slice(scope):
    """The slice an oracle review approves, or None for any other review scope."""
    return scope.slice if isinstance(scope, _OracleScope) else None


def needs_review_evidence(kind, verb):
    return kind == "review" and verb in ("close", "observation add", "observation set")


def stamp_review(edit, evidence):
    if isinstance(edit, (Add, Replace)) and edit.path == ("observations",):
        return replace(
            edit,
            value=h.freeze(
                {
                    **edit.value,
                    "commit": evidence.commit,
                    "clean": not evidence.dirty,
                    **_content_field(evidence),
                }
            ),
        )
    return edit


def _content_field(evidence):
    return {} if evidence.content is None else {"content": evidence.content}


def review_record(draft, evidence, outcome, diagnostic):
    observations = draft.get("observations", ())
    how = (
        "Record current evidence on clean reviewed HEAD with nwdes review observation add. "
        "To reuse a prior run, record the current comparison establishing unchanged relevant "
        "inputs/runtime and cite the original run commit, argv, exit and output. "
        "Never restamp old output as a new execution; rerun affected checks if equivalence "
        "is unestablished."
    )
    problems = (
        *(
            (
                Defect(
                    "ReviewUnobserved: review",
                    "A review needs evidence recorded by its reviewer.",
                    how,
                ),
            )
            if not observations
            else ()
        ),
        *(
            Defect(
                "StaleObservation: " + row["id"],
                "The observation was not recorded on clean HEAD "
                + evidence.commit
                + " with no other dirty path and the same oracle content.",
                how,
            )
            for row in observations
            if row.get("commit") != evidence.commit
            or row.get("clean") is not True
            or evidence.dirty
            or row.get("content") != evidence.content
        ),
    )
    return checked(
        h.freeze(
            {
                "findings": draft.get("findings", ()),
                "observations": observations,
                "commit": evidence.commit,
                "outcome": outcome,
                "diagnostic": diagnostic,
                **_content_field(evidence),
            }
        ),
        problems,
    )


def owner_lines(record, paradigm, flags):
    findings = record.get("findings", ())
    return "\n".join(
        "OWNER "
        + owner
        + " "
        + role
        + " FINDINGS "
        + ",".join(map(str, positions))
        + "\nnwdes review findings "
        + flags
        + " --owner "
        + owner
        for owner, target in FINDING_ROLES.items()
        for positions in (
            tuple(i for i, row in enumerate(findings, 1) if row["owner"] == owner),
        )
        if positions
        for role in (
            target.get(paradigm, "nw-software-crafter")
            if isinstance(target, Mapping)
            else target,
        )
    )


def owner_findings(record, owner):
    text = "\n\n".join(
        "\n".join(
            name + ": " + row[name] for name in REVIEW_FINDING.index if name != "owner"
        )
        for row in record.get("findings", ())
        if row["owner"] == owner
    )
    return (text or "None.") + "\n"


@dataclass(frozen=True)
class RoleField:
    name: str
    spec: h.Spec
    required: bool = False
    repeated: bool = False
    alternative: str | None = None
    role_refused: bool = False

    @property
    def choices(self):
        return self.spec.members if self.spec.kind in ("enum", "adr_status") else None

    @property
    def text(self):
        return self.spec.kind == "text"


@dataclass(frozen=True)
class RoleVerb:
    kind: str
    name: str
    fields: tuple[RoleField, ...]
    exclusive: tuple[tuple[str, ...], ...] = ()

    @property
    def record(self):
        return self.name.rsplit(" ", 1)[0] if " " in self.name else ""

    @property
    def action(self):
        return self.name.rsplit(" ", 1)[-1]


@dataclass(frozen=True)
class _OracleScope:
    slice: str


@dataclass(frozen=True)
class _SliceScope:
    slice: str


@dataclass(frozen=True)
class _CandidateScope:
    pass


@dataclass(frozen=True)
class Legacy:
    slice: str | None


ReviewScope = _OracleScope | _SliceScope | _CandidateScope | Legacy


def review_scope(
    subject: str | ReviewSubject | None, slice_id: str | None, *, replay: bool = False
) -> Built[ReviewScope] | Refused:
    if subject is None and replay:
        return Built(Legacy(slice_id))
    parsed_slice = h.parse_slice_id(slice_id)
    try:
        selected = ReviewSubject(subject)
    except (ValueError, TypeError):
        selected = None
    problems = (
        *(parsed_slice.defects if isinstance(parsed_slice, Refused) else ()),
        *(
            (
                Defect(
                    "PartInvalid: --subject",
                    "A live review needs a declared subject; legacy scope is only for replay without a subject.",
                    "Use --subject oracle or slice with --slice S<n>, or --subject candidate without --slice.",
                ),
            )
            if selected is None and not (subject is None and replay)
            else ()
        ),
        *(
            (
                Defect(
                    "PartInvalid: --slice",
                    "An oracle or slice review needs a slice to name its own record.",
                    "Repeat the review verb with --subject "
                    + selected.value
                    + " --slice S<n> naming the reviewed slice.",
                ),
            )
            if selected in (ReviewSubject.ORACLE, ReviewSubject.SLICE)
            and slice_id is None
            else ()
        ),
        *(
            (
                Defect(
                    "PartInvalid: --slice",
                    "A candidate review names the complete feature, not an individual slice.",
                    "Repeat the review verb with --subject candidate without --slice.",
                ),
            )
            if selected is ReviewSubject.CANDIDATE and slice_id is not None
            else ()
        ),
    )
    if problems:
        return checked(None, problems)
    match selected:
        case ReviewSubject.ORACLE:
            return Built(_OracleScope(parsed_slice.value))
        case ReviewSubject.SLICE:
            return Built(_SliceScope(parsed_slice.value))
        case ReviewSubject.CANDIDATE:
            return Built(_CandidateScope())


@dataclass(frozen=True)
class DraftKey:
    kind: str
    scope: str | ReviewScope | None = None

    def __post_init__(self):
        if (self.kind == "review") != isinstance(self.scope, ReviewScope):
            raise TypeError("Review keys require a scope returned by review_scope.")

    @property
    def filename(self):
        match self.scope:
            case _OracleScope(slice_id):
                suffix = ".oracle." + slice_id
            case _SliceScope(slice_id):
                suffix = ".slice." + slice_id
            case _CandidateScope():
                suffix = ".candidate"
            case Legacy(slice_id):
                suffix = "." + slice_id if slice_id else ""
            case slice_id:
                suffix = "." + slice_id if slice_id else ""
        return self.kind + suffix + ".json"


@dataclass(frozen=True)
class Add:
    path: tuple[str | int, ...]
    value: object
    issued_prefix: str = ""
    counter: str = ""


@dataclass(frozen=True)
class Set:
    path: tuple[str | int, ...]
    value: object
    merge: bool = False


@dataclass(frozen=True)
class Remove:
    path: tuple[str | int, ...]
    at: int | None = None
    identity: str | None = None


@dataclass(frozen=True)
class Replace:
    path: tuple[str | int, ...]
    value: object
    at: int | None = None
    identity: str | None = None
    children: tuple[str, ...] = ()


Edit = Add | Set | Remove | Replace


@dataclass(frozen=True)
class FieldRequirement:
    name: str
    missing: Callable[[Mapping], tuple[Defect, ...]]


@dataclass(frozen=True)
class Row:
    name: str
    path: tuple[str, ...]
    spec: h.Spec
    action: str = "add"
    place: str = ""
    scalar: bool = False
    issued_prefix: str = ""
    counter: str = ""
    key: RoleField | None = None
    requirement: FieldRequirement | None = None

    @property
    def edit_spec(self):
        if not self.issued_prefix:
            return self.spec
        return replace(
            self.spec,
            members=tuple(pair for pair in self.spec.members if pair[0] != "id"),
            required=tuple(name for name in self.spec.required if name != "id"),
        )

    def asked_edit_spec(self, kind, policy):
        """The edit spec with each member the policy asks for required: what the close enforces."""
        return h.asked_schema(kind, self.edit_spec, policy)

    def required_problems(self, values):
        requirement = self.requirement
        return (
            requirement.missing(values)
            if requirement is not None and not values.get(requirement.name)
            else ()
        )

    def role_field(self, group):
        forced = self.requirement is not None and self.requirement.name == group[0].name
        return RoleField(
            group[0].name,
            group[0].spec,
            any(field.required for field in group) or forced,
            group[0].repeated,
            "|".join(dict.fromkeys(field.alternative for field in group))
            if all(field.alternative for field in group)
            else None,
            role_refused=forced,
        )


def _has_identity(spec):
    return bool(spec.identity) or (
        spec.kind == "choice" and any(_has_identity(child) for _, child in spec.members)
    )


def _row_for(kind, verb):
    return next(
        (
            row
            for row in _rows(kind)
            if verb
            in tuple(
                (row.name + " " if row.name else "") + action
                for action in (row.action, "remove", "set")
            )
        ),
        None,
    )


def _scalar(spec):
    return h.record(("text",), text=spec)


def _missing_observation(values):
    return (h.uncited_verdict(values.get("expectation")),)


def _missing_promise(values):
    return h.slice_promise_problems(h.EMPTY, (), "product.slice")


def _rows(kind):
    if kind == "product":
        return tuple(
            Row(
                name,
                (key,),
                spec.members[0]
                if spec.members[0].kind in ("record", "choice")
                else _scalar(spec.members[0]),
                scalar=spec.members[0].kind not in ("record", "choice"),
                requirement=(
                    FieldRequirement("promise", _missing_promise)
                    if name == "slice"
                    else None
                ),
            )
            for name, key in (
                ("promise", "promises"),
                ("scope-in", "scope_in"),
                ("scope-out", "scope_out"),
                ("decision", "decisions"),
                ("journey", "journey"),
                ("slice", "slices"),
            )
            for spec in (h.PRODUCT.index[key],)
        )
    if kind == "design":
        names = {
            "decisions": "decision",
            "constraints": "constraint",
            "constructors": "constructor",
            "laws": "law",
            "claims": "claim",
            "states": "state",
            "models": "model",
            "risks": "risk",
            "architectural_tests": "architectural-test",
            "contract_tests": "contract-test",
            "observations": "observation",
        }
        records = tuple(
            Row(
                names.get(key, key.replace("_", "-")),
                ("records", key),
                (
                    h.SHARED_RECORDS.index[key].members[0]
                    if key in ("decisions", "constraints")
                    else spec.members[0]
                )
                if spec.kind == "array"
                else spec,
                "add" if spec.kind == "array" else "set",
                "records",
            )
            for key, spec in h.RECORDS.members
        )
        # Failures and model children have their own authoring verbs.
        records = tuple(
            Row(
                row.name,
                row.path,
                h.record(
                    tuple(k for k in row.spec.required if k != "failures"),
                    **{k: v for k, v in row.spec.members if k != "failures"},
                ),
                row.action,
                row.place,
            )
            if row.name == "boundaries"
            else row
            for row in records
        )
        return (
            Row(
                "paradigm",
                ("paradigm",),
                h.record(("value",), value=h.DESIGN.index["paradigm"]),
                "set",
            ),
            *records,
            Row(
                "failure",
                ("records", "boundaries", "failures"),
                h.FAILURE,
                place="records",
            ),
            *(
                Row(
                    "model-" + name,
                    ("records", "models", "model", key),
                    h.MODEL.index[key].members[0],
                    place="model",
                )
                for name, key in (
                    ("property", "properties"),
                    ("atom", "atoms"),
                    ("mutant", "mutants"),
                )
            ),
            Row(
                "slice",
                (),
                h.record(("oracle",), oracle=h.LINE, supports=h.array(h.LINE)),
                "set",
                "slice",
            ),
            Row(
                "verification",
                ("verification",),
                h.record(("command",), command=h.COMMAND),
                place="slice",
                scalar=True,
            ),
            Row("target", ("targets",), h.TARGET, place="slice"),
            Row("public-oracle", ("public_oracle",), h.PUBLIC_ORACLE, "set", "slice"),
            Row("prefactoring", ("prefactoring",), h.PREFACTORING, "set", "slice"),
            Row("adr", ("adrs",), h.ADR_ROW),
        )
    if kind == "acceptance":
        return (Row("row", (), h.ACCEPTANCE_ROW),)
    if kind == "expectations":
        return (Row("row", ("rows",), h.EXPECTATIONS.index["rows"].members[0]),)
    if kind == "charter":
        return (
            Row(
                "",
                (),
                h.record(
                    ("intent", "exploration", "negative"),
                    intent=h.TEXT,
                    exploration=h.TEXT,
                    negative=h.TEXT,
                ),
                "set",
            ),
            Row("positive", ("positive",), _scalar(h.TEXT), scalar=True),
        )
    if kind == "examine":
        return (
            Row(
                "observation",
                ("observations",),
                h.EXAMINATION_OBSERVATION,
                issued_prefix="O",
                counter="next_observation",
            ),
            Row(
                "verdict",
                ("verdicts",),
                h.EXAMINATION_VERDICT,
                "set",
                key=RoleField("expectation", h.REFERENCE, True),
                requirement=FieldRequirement("observation", _missing_observation),
            ),
        )
    if kind == "craft":
        return (
            Row("file", ("files",), CRAFT_FILE),
            Row("command", ("commands",), CRAFT_COMMAND),
        )
    if kind == "review":
        return (
            Row(
                "observation",
                ("observations",),
                REVIEW_OBSERVATION,
                issued_prefix="R",
                counter="next_review_observation",
            ),
            Row("finding", ("findings",), REVIEW_FINDING),
        )
    return ()


_ALIASES = {
    "promises": "promise",
    "supports": "support",
    "cases": "case",
    "assumptions": "assumption",
    "driven_ports": "driven-port",
    "observations": "observation",
    "obligations": "obligation",
}


def _flag(path):
    return "-".join(_ALIASES.get(part, part.replace("_", "-")) for part in path)


def _fields(spec, path=(), required=True, alternative=None, selected=None):
    if spec.kind == "record":
        present = required or (
            selected is not None
            and any(
                value is not None
                and (name == _flag(path) or name.startswith(_flag(path) + "-"))
                for name, value in selected.items()
            )
        )
        return tuple(
            field
            for name, child in spec.members
            if child.kind != "array"
            or child.members[0].kind not in ("record", "choice")
            for field in _fields(
                child,
                (*path, name),
                present and name in spec.required,
                alternative,
                selected,
            )
        )
    if spec.kind == "choice":
        selector = path or (spec.discriminator,)
        return (
            RoleField(
                _flag(selector), h.enum(*spec.index), required, alternative=alternative
            ),
            *tuple(
                field
                for tag, child in spec.members
                if selected is None or selected.get(_flag(selector)) == tag
                for field in _fields(
                    child,
                    path if not path else path[:-1],
                    required if selected is not None else False,
                    tag,
                    selected,
                )
            ),
        )
    if spec.kind == "array":
        return (
            RoleField(
                _flag(path),
                spec.members[0],
                required and bool(spec.minimum),
                True,
                alternative,
            ),
        )
    return (RoleField(_flag(path), spec, required, alternative=alternative),)


_VERBS_HELD: dict[tuple[str, int], tuple[object, tuple]] = {}


def role_verbs(kind, policy=None):
    """The verbs of one role kind under one policy, built once per distinct policy.

    The tables are pure over `kind` and `policy`; the cache holds the policy itself
    so a hit means the same object, and its id cannot be reused while held.
    """
    held = _VERBS_HELD.get((kind, id(policy)))
    if held is not None and held[0] is policy:
        return held[1]
    built = _role_verbs(kind, policy)
    _VERBS_HELD[(kind, id(policy))] = (policy, built)
    return built


def _role_verbs(kind, policy=None):
    if kind not in KINDS:
        return ()
    roots = (
        *(
            RoleField(
                name,
                h.IDENTITY if name in ("feature", "epic") else h.LINE,
                name == "slice" and kind in ("acceptance", "craft"),
            )
            for name in ROOT_NAMES
            if name != "slice" or kind not in ("charter", "examine")
        ),
        *((RoleField("subject", REVIEW_SUBJECT, True),) if kind == "review" else ()),
    )
    opening = RoleVerb(
        kind,
        "open",
        (*roots, RoleField("from-current", BOOL, True)),
    )
    outcome = (
        h.enum("accepted", "rejected")
        if kind in ("craft", "review")
        else h.enum("accepted", "rejected", "indeterminate")
    )
    closing = RoleVerb(
        kind,
        "close",
        (
            *roots,
            RoleField("outcome", outcome, True),
            RoleField("diagnostic", h.TEXT, True),
            *((RoleField("revise", BOOL),) if kind == "expectations" else ()),
            *((RoleField("blocked-by", h.LINE),) if kind == "craft" else ()),
            *(
                (RoleField("role", CRAFT_ACTOR, role_refused=True),)
                if kind == "craft"
                else ()
            ),
        ),
    )

    def verbs(row):
        selectors = (
            (RoleField("shared", BOOL), RoleField("in", h.REFERENCE))
            if row.place in ("records", "model")
            else (RoleField("in", h.REFERENCE, True),)
            if row.place == "slice"
            else ()
        )
        if row.place == "model":
            selectors = (*selectors, RoleField("model", INTEGER, True))
        if row.key is not None:
            selectors = (*selectors, row.key)
        declared = _fields(row.asked_edit_spec(kind, policy))
        groups = tuple(
            tuple(field for field in declared if field.name == name)
            for name in dict.fromkeys(field.name for field in declared)
        )
        fields = tuple(row.role_field(group) for group in groups)
        exclusive = (("shared", "in"),) if row.place in ("records", "model") else ()
        name = row.name + " " if row.name else ""
        remove_fields = (
            ()
            if row.key is not None
            else (RoleField("at", INTEGER), RoleField("id", h.LINE))
        )
        return (
            RoleVerb(
                kind,
                name + row.action,
                (*roots, *selectors, *fields),
                (*exclusive, *((row.spec.exclusive,) if row.spec.exclusive else ())),
            ),
            *(
                (
                    RoleVerb(
                        kind,
                        name + "set",
                        (
                            *roots,
                            *selectors,
                            *(
                                (RoleField("id", h.LINE), RoleField("at", INTEGER))
                                if (
                                    row.name in ("decision", "constraint")
                                    and kind == "design"
                                )
                                or bool(row.issued_prefix)
                                else (RoleField("id", h.LINE, True),)
                                if _has_identity(row.spec)
                                else (RoleField("at", INTEGER, True),)
                            ),
                            *fields,
                        ),
                        (
                            *exclusive,
                            *(
                                (("id", "at"),)
                                if (
                                    row.name in ("decision", "constraint")
                                    and kind == "design"
                                )
                                or bool(row.issued_prefix)
                                else ()
                            ),
                            *((row.spec.exclusive,) if row.spec.exclusive else ()),
                        ),
                    ),
                )
                if row.action == "add"
                else ()
            ),
            RoleVerb(
                kind,
                name + "remove",
                (*roots, *selectors, *remove_fields),
                (
                    *exclusive,
                    *((("at", "id"),) if row.key is None else ()),
                ),
            ),
        )

    return (
        opening,
        *tuple(verb for row in _rows(kind) for verb in verbs(row)),
        closing,
        *(
            (
                RoleVerb(
                    kind,
                    "findings",
                    (*roots, RoleField("owner", REVIEW_FINDING.index["owner"], True)),
                ),
            )
            if kind == "review"
            else ()
        ),
        RoleVerb(kind, "abort", roots),
    )


def _value(spec, values, path=()):
    if spec.kind == "record":
        pairs = tuple(
            (name, _value(child, values, (*path, name))) for name, child in spec.members
        )
        if path and not any(value not in (None, (), h.EMPTY) for _, value in pairs):
            return None
        return h.Record((name, value) for name, value in pairs if value is not None)
    if spec.kind == "choice":
        selector = values.get(_flag(path or (spec.discriminator,)))
        if selector not in spec.index:
            return None
        body = _value(spec.index[selector], values, path[:-1] if path else ())
        return h.Record((*body.items(), (spec.discriminator, selector)))
    value = values.get(_flag(path))
    if spec.kind == "array":
        return tuple(value or ())
    return value


def _problems(spec, value, path):
    if spec.kind == "integer":
        return () if type(value) is int else (h._invalid(path, "Expected an integer."),)
    if spec.kind == "record" and any(
        child.kind == "integer" for _, child in spec.members
    ):
        # Integer leaves belong to command evidence, outside the handoff tree.
        ordinary = h.record(
            tuple(name for name in spec.required if spec.index[name].kind != "integer"),
            **{name: child for name, child in spec.members if child.kind != "integer"},
        )
        return (
            *h._check(
                ordinary,
                h.Record((k, v) for k, v in value.items() if k in ordinary.index),
                path,
            ),
            *tuple(
                p
                for k, child in spec.members
                if child.kind == "integer"
                for p in _problems(child, value.get(k), path + "." + k)
            ),
        )
    return h._check(spec, value, path)


def prepare_edit(kind, verb, values, previous=None, policy=None):
    row = _row_for(kind, verb)
    if row is None:
        return refuse(
            "PartInvalid: role verb",
            "The record is not declared for this role.",
            "Choose a verb from nwdes " + kind + " --help.",
        )
    path = row.path
    spec = row.asked_edit_spec(kind, policy)
    if row.place in ("records", "model", "slice"):
        selected = values.get("in")
        if row.place == "slice" or selected:
            path = ("slices", selected, *path)
            if row.name in ("decision", "constraint"):
                spec = _scalar(h.TEXT)
        else:
            path = ("shared", *path[1:])
        if row.place in ("records", "model") and bool(values.get("shared")) == bool(
            selected
        ):
            return refuse(
                "PartInvalid: PLACE",
                "Select exactly one of --shared and --in.",
                "Supply the record's owning place.",
            )
        if row.place == "model":
            position = values.get("model")
            if type(position) is not int or position < 1:
                return refuse(
                    "PartInvalid: --model",
                    "Model positions are one-based.",
                    "Select a model previously added in this PLACE.",
                )
            path = tuple(position - 1 if part == "model" else part for part in path)
    if row.key is not None:
        path = (*path, values[row.key.name])
    if verb.endswith("remove"):
        return (
            Remove(path)
            if row.key is not None
            else Remove(path, values.get("at"), values.get("id"))
        )
    required = row.required_problems(values)
    if required:
        return checked(None, required)
    value = _value(spec, values)
    if kind == "product" and row.name == "slice":
        defects = h.slice_promise_problems(
            value, value.get("promises", ()), "product.slice"
        )
        if defects:
            return checked(None, defects)
    defects = _problems(spec, value, kind + "." + row.name)
    if defects:
        return checked(None, defects)
    if row.name == "paradigm":
        value = value["value"]
    elif row.scalar or (
        kind == "design" and row.name in ("decision", "constraint") and values.get("in")
    ):
        value = value["command" if row.name == "verification" else "text"]
    if verb.endswith("set") and row.action == "add":
        children = (
            tuple(
                name
                for name, child in spec.members
                if child.kind == "array"
                and child.members[0].kind in ("record", "choice")
            )
            if spec.kind == "record"
            else ()
        )
        selected_value = (
            h.Record(
                (name, child) for name, child in value.items() if name not in children
            )
            if isinstance(value, Mapping)
            else value
        )
        return Replace(
            path, selected_value, values.get("at"), values.get("id"), children
        )
    return (
        Add(path, value, row.issued_prefix, row.counter)
        if row.action == "add"
        else Set(path, value, row.name in ("slice", "boundaries") or kind == "charter")
    )


def empty(kind):
    if kind == "craft":
        return h.Record((("files", ()), ("commands", ())))
    if kind == "review":
        return h.Record(
            (("findings", ()), ("observations", ()), ("next_review_observation", 1))
        )
    if kind == "examine":
        return h.Record(
            (("observations", ()), ("verdicts", h.EMPTY), ("next_observation", 1))
        )
    return () if kind == "acceptance" else h.EMPTY


def _replace_at(data, path, transform):
    if not path:
        return transform(data)
    key, *rest = path
    if isinstance(key, int):
        if not isinstance(data, tuple) or key >= len(data):
            return refuse(
                "DanglingReference: --model",
                "The selected model does not exist in this draft.",
                "Add the model before its children, or select its one-based position.",
            )
        value = _replace_at(data[key], tuple(rest), transform)
        return (
            value
            if isinstance(value, Refused)
            else (*data[:key], value, *data[key + 1 :])
        )
    current = data if isinstance(data, Mapping) else h.EMPTY
    value = _replace_at(current.get(key, h.EMPTY), tuple(rest), transform)
    return (
        value
        if isinstance(value, Refused)
        else h.Record((*((k, v) for k, v in current.items() if k != key), (key, value)))
    )


def apply_edit(draft, edit, previous=None):
    if isinstance(edit, Add) and edit.issued_prefix:
        number = draft[edit.counter]
        row = h.Record((("id", edit.issued_prefix + str(number)), *edit.value.items()))
        return h.Record(
            (
                *draft.items(),
                (edit.counter, number + 1),
                (edit.path[0], (*draft.get(edit.path[0], ()), row)),
            )
        )
    if edit.path == ("slices",) and isinstance(edit, (Add, Replace)):
        if _problems(
            h.PRODUCT.index["promises"], draft.get("promises", ()), "product.promises"
        ):
            return refuse(
                "PartInvalid: product.promises",
                "The draft promises cannot be resolved.",
                "Correct the promises with nwdes product promise add before adding slices.",
            )
        known = h.product_promise_ids(draft, previous)
        if isinstance(known, h.UnavailableInput):
            return checked(None, (known.defect,))
        defects = h.slice_promise_problems(edit.value, known, "product.slice")
        if defects:
            return checked(None, defects)

    def change(current):
        if isinstance(edit, Add):
            return (*(current if isinstance(current, tuple) else ()), edit.value)
        if isinstance(edit, Set):
            return (
                h.Record((*current.items(), *edit.value.items()))
                if edit.merge
                and isinstance(current, Mapping)
                and isinstance(edit.value, Mapping)
                else edit.value
            )
        if isinstance(edit, Remove) and edit.at is None and edit.identity is None:
            return None
        if isinstance(edit, Remove) and (
            not isinstance(current, tuple)
            and current not in (h.EMPTY, None)
            and edit.at == 1
        ):
            return None
        rows = current if isinstance(current, tuple) else ()
        index = (
            edit.at - 1
            if type(edit.at) is int
            else next(
                (
                    i
                    for i, row in enumerate(rows)
                    if isinstance(row, Mapping) and row.get("id") == edit.identity
                ),
                -1,
            )
        )
        if index < 0 or index >= len(rows):
            return refuse(
                "DanglingReference: draft row "
                + str(edit.identity if edit.identity is not None else edit.at),
                "The selected row does not exist in this draft at "
                + ".".join(map(str, edit.path))
                + ".",
                (
                    "Use --id with an id retained by open --from-current."
                    if edit.identity is not None
                    else "Use an existing one-based --at position; "
                    "open --from-current seeds the rows of the published record."
                )
                + (
                    " To create a fresh row, use its add verb instead."
                    if isinstance(edit, Replace)
                    else ""
                ),
            )
        if isinstance(edit, Replace):
            prior = rows[index]
            value = (
                h.Record(
                    (
                        *(
                            (name, prior[name])
                            for name in edit.children
                            if name in prior
                        ),
                        *edit.value.items(),
                        *((("id", prior["id"]),) if "id" in prior else ()),
                    )
                )
                if isinstance(edit.value, Mapping)
                else edit.value
            )
            return (*rows[:index], value, *rows[index + 1 :])
        return (*rows[:index], *rows[index + 1 :])

    result = _replace_at(draft, edit.path, change)
    return result


def seed(previous, kind, slice=None, *, adr_bodies=h.EMPTY):
    if previous is None:
        return empty(kind)
    if kind in ("craft", "review"):
        if not isinstance(previous, Mapping):
            return refuse(
                "PartInvalid: published " + kind + " run record",
                "Expected an object holding the recorded row collections.",
                "Restore run evidence produced by nwdes "
                + kind
                + " close before retrying open --from-current.",
            )
        # A reopened review keeps its findings and no observations: each observation is bound to
        # the commit that recorded it, and a new round records its own. Its id counter continues
        # after the published ids, so no new id repeats a published one.
        return h.freeze(
            {
                name: (
                    max(
                        (
                            h.id_order(row["id"])[1]
                            for row in previous.get("observations", ())
                        ),
                        default=0,
                    )
                    + 1
                    if kind == "review" and name == "next_review_observation"
                    else ()
                    if kind == "review" and name == "observations"
                    else previous.get(name, rows)
                )
                for name, rows in empty(kind).items()
            }
        )
    if kind not in h.ROLE_SCHEMAS:
        return empty(kind)
    if kind == "acceptance":
        value = previous.acceptance.get(slice, ())
    elif kind == "charter":
        value = h.Record(
            (name, previous.charter[name])
            for name in h.CHARTER.index
            if previous.charter is not None and name in previous.charter
        )
    elif kind == "examine":
        return _seed_examination(previous)
    else:
        value = getattr(previous, kind) or h.EMPTY
    result = h.expanded(h.ROLE_SCHEMAS[kind], value, previous.facts)
    if kind == "product" and isinstance(result, Mapping):
        observations = {
            row["id"]: row["observation"] for row in result.get("slices", ())
        }
        result = h.Record(
            (
                *((k, v) for k, v in result.items() if k != "slices"),
                (
                    "slices",
                    tuple(
                        h.Record(
                            (
                                *((k, v) for k, v in row.items() if k != "depends_on"),
                                (
                                    "depends_on",
                                    tuple(
                                        observations.get(identity, identity)
                                        for identity in row.get("depends_on", ())
                                    ),
                                ),
                            )
                        )
                        for row in result.get("slices", ())
                    ),
                ),
            )
        )
    if kind == "design" and result.get("adrs"):
        result = h.Record(
            (
                *((name, value) for name, value in result.items() if name != "adrs"),
                (
                    "adrs",
                    tuple(
                        h.Record(
                            (
                                *row.items(),
                                *zip(
                                    h.ADR_BODY_FIELDS,
                                    adr_bodies[row["key"]],
                                    strict=True,
                                ),
                            )
                        )
                        if adr_bodies.get(row["key"]) is not None
                        else row
                        for row in result["adrs"]
                    ),
                ),
            )
        )
    return h.freeze(result)


def _seed_examination(previous):
    verdicts = h.expanded(
        h.CANONICAL_SCHEMAS["examination"], previous.examination, previous.facts
    )

    def verdict(state, pair):
        observations, recorded = state
        expectation, value = pair
        texts = value.get("observations", ())
        unique = tuple(dict.fromkeys((*observations, *texts)))
        citations = tuple("O" + str(unique.index(text) + 1) for text in texts)
        return unique, (
            *recorded,
            (
                expectation,
                h.Record(
                    (
                        *(
                            (name, child)
                            for name, child in value.items()
                            if name != "observations"
                        ),
                        ("observations", citations),
                    )
                ),
            ),
        )

    observations, recorded = reduce(
        verdict, sorted(verdicts.items(), key=lambda pair: int(pair[0][1:])), ((), ())
    )
    return h.Record(
        (
            (
                "observations",
                tuple(
                    h.Record((("id", "O" + str(index)), ("text", text)))
                    for index, text in enumerate(observations, 1)
                ),
            ),
            ("verdicts", h.Record(recorded)),
            ("next_observation", len(observations) + 1),
        )
    )


def issued(kind, verb, before, after):
    row = _row_for(kind, verb)
    if row is None or not row.issued_prefix or not verb.endswith("add"):
        return None
    rows = after.get(row.path[0], ())
    return rows[-1]["id"] if len(rows) > len(before.get(row.path[0], ())) else None


def _plain(value, *, keep_null=False):
    if isinstance(value, Mapping):
        return {
            key: _plain(child, keep_null=keep_null)
            for key, child in value.items()
            if keep_null or child is not None
        }
    if isinstance(value, tuple):
        return [_plain(child, keep_null=keep_null) for child in value]
    return value


def envelope_bytes(draft, outcome, diagnostic):
    if isinstance(draft, Mapping) and "next_observation" in draft:
        draft = h.Record(
            (name, value) for name, value in draft.items() if name != "next_observation"
        )
    return json.dumps(
        {
            "outcome": outcome,
            "diagnostic": diagnostic,
            "payload": _plain(draft) if outcome == "accepted" else None,
        },
        ensure_ascii=False,
    ).encode("utf-8")


def draft_bytes(draft, *, keep_null=False):
    return json.dumps(_plain(draft, keep_null=keep_null), ensure_ascii=False).encode(
        "utf-8"
    )


def record_bytes(record):
    return draft_bytes(record, keep_null=True) + b"\n"


def run(ports, kind, verb, values):
    name = verb.name if isinstance(verb, RoleVerb) else verb
    if name not in tuple(row.name for row in role_verbs(kind)):
        return refuse(
            "PartInvalid: role verb",
            "The requested verb is not declared for this kind.",
            "Use nwdes " + kind + " --help.",
        )
    return ports.run_role(kind, name, values)


def _inline_argument_values(field, value):
    """Leave file-backed text to its reader rather than validating its path as content."""
    if value is None:
        return ()
    if (
        field.text
        and isinstance(value, tuple)
        and len(value) == 2
        and isinstance(value[0], bool)
    ):
        return () if value[0] else (value[1],)
    return (value,)


def argument_problems(kind, name, supplied, previous=None):
    """Compose independent scope and row-argument defects before draft effects."""
    values = {key.replace("_", "-"): value for key, value in supplied.items()}
    scope_problems = ()
    if kind == "review":
        scope = values.get("review-scope")
        if scope is None:
            scope = review_scope(
                values.get("subject"),
                values.get("slice"),
                replay=values.get("review-replay", False),
            )
        scope_problems = scope.defects if isinstance(scope, Refused) else ()
    row = _row_for(kind, name)
    if row is None or name.endswith("remove"):
        return scope_problems
    required = row.required_problems(values)
    if required:
        return (*scope_problems, *required)
    spec = (
        _scalar(h.TEXT)
        if kind == "design"
        and row.name in ("decision", "constraint")
        and values.get("in")
        else row.edit_spec
    )
    active = _fields(spec, selected=values)
    allowed = frozenset(field.name for field in active)
    return (
        *scope_problems,
        *(
            tuple(
                defect
                for field in active
                for value in _inline_argument_values(field, values.get(field.name))
                for defect in _problems(
                    field.spec, value, "review." + row.name + "." + field.name
                )
            )
            if kind == "review"
            else ()
        ),
        *(
            (
                h._invalid(
                    "--id" if _has_identity(spec) else "--at",
                    "Select the retained row by its identity."
                    if _has_identity(spec)
                    else "This row has no identity; select its one-based position.",
                    True,
                ),
            )
            if name.endswith("set")
            and row.action == "add"
            and values.get("id") is None
            and (
                values.get("at") is None
                or (_has_identity(spec) and not row.issued_prefix)
            )
            else ()
        ),
        *(
            h._invalid(
                "--" + field.name, "This selected alternative requires its value.", True
            )
            for field in active
            if field.required and values.get(field.name) is None
        ),
        *(
            h._invalid(
                "--" + field.name,
                "This field does not belong to the selected alternative.",
            )
            for field in _fields(row.edit_spec)
            if field.name not in allowed and values.get(field.name) is not None
        ),
    )
