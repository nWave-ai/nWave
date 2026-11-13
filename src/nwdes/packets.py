"""Public examination and review packets, constructed only after independent checks."""

import errno
import json
import posixpath
import re
import shlex
import sys
from collections.abc import Mapping
from dataclasses import dataclass, replace
from enum import Enum
from itertools import groupby


try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

from nwdes import documents, prose
from nwdes import handoff as model
from nwdes.contracts import Built, Defect, Refused, checked, strict_object


class PacketKind(Enum):
    Examine = "examine"
    Review = "review"


@dataclass(frozen=True)
class PublicExamination:
    """Resolved public-authored fields only: no handoff, private record or facts map."""

    promises: tuple[model.Record, ...]
    slices: tuple[model.Record, ...]
    expectations: tuple[model.Record, ...]
    workspace: "ExaminationWorkspace | None" = None
    charter: model.Record | None = None
    scope: tuple[str, str | None] = ("Project", None)


@dataclass(frozen=True)
class ReviewPacket:
    slices: tuple[model.Record, ...]
    diff: str | None
    acceptance_document: str
    architecture_document: str
    paths: tuple[str, ...] = ()


@dataclass(frozen=True)
class _PreparedPacket:
    kind: PacketKind
    handoff: model.Handoff
    diff: str | None
    handoff_argument: str | None = None
    slice_id: str | None = None
    workspace: "ExaminationWorkspace | None" = None

    def build(self):
        if self.kind is PacketKind.Examine:
            return Built(
                render_examination(_public_examination(self.handoff, self.workspace))
            )
        references = documents.fact_references(self.handoff, (self.diff,))
        handoff = (
            references.project(self.handoff) if references is not None else self.handoff
        )
        text = render_review(
            _review_packet(
                handoff,
                self.diff,
                self.handoff_argument,
                self.slice_id,
            )
        )
        return Built(references.expand(text) if references is not None else text)


_PUBLIC_ORACLE = replace(
    model.PUBLIC_ORACLE,
    members=tuple(
        (name, spec) for name, spec in model.PUBLIC_ORACLE.members if name != "promises"
    ),
)
_MODEL_PROPERTY = model.MODEL.index["properties"].members[0]
MODEL_SUMMARY = replace(
    model.MODEL,
    required=("path",),
    members=(
        ("path", model.MODEL.index["path"]),
        (
            "properties",
            model.array(
                replace(
                    _MODEL_PROPERTY,
                    required=("name",),
                    members=(("name", _MODEL_PROPERTY.index["name"]),),
                )
            ),
        ),
    ),
)
REVIEW_RECORDS = replace(
    model.RECORDS,
    members=tuple(
        (name, model.array(MODEL_SUMMARY) if name == "models" else spec)
        for name, spec in model.RECORDS.members
    ),
)
_NO_HANDOFF = model.UnavailableInput(model.missing_flag("handoff"))


def _problem(kind, name, why):
    return Defect(
        kind + ": " + name,
        why,
        "Use the packet's named inputs and current expectation ids.",
    )


def _defects(result):
    return result.defects if isinstance(result, Refused) else ()


def _kind(value):
    if value is None:
        return checked(None, (model.missing_flag("kind"),))
    selected = next((kind for kind in PacketKind if kind.value == value), None)
    return (
        Built(selected)
        if selected is not None
        else checked(
            None, (_problem("PartInvalid", "--kind", "Use examine or review."),)
        )
    )


def _expectation_rows(previous):
    if previous is None:
        return _NO_HANDOFF
    part = previous.part("expectations")
    if isinstance(part, model.UnavailableInput) or part is None:
        return part
    return part.get("rows", ())


def _legacy_charter_problems(previous):
    charter = previous.part("charter") if previous is not None else None
    if not isinstance(charter, Mapping) or charter.get("kind") != "LegacySlices":
        return ()
    return (
        Defect(
            "InconsistentFacts: legacy per-slice charters "
            + ", ".join(charter["slices"]),
            "One charter must cover the complete Feature; legacy slice charters do not establish that scope.",
            "Run nwdes prompt --role nw-product-owner --task charter, then record the feature charter and run nwdes charter close to replace the legacy charters.",
        ),
    )


def examination_problems(previous):
    charter_problems = _legacy_charter_problems(previous)
    rows = _expectation_rows(previous)
    return (
        *charter_problems,
        *(
            (
                _problem(
                    "MissingFact", "expectations", "No expectation set has been fixed."
                ),
            )
            if rows is None
            else ()
        ),
    )


def _prepare(kind, previous, evidence, initial=()):
    problems = (
        *initial,
        *_defects(kind),
        *(_defects(previous.result) if previous is not None else ()),
        *_defects(evidence),
        *(
            examination_problems(previous)
            if isinstance(kind, Built) and kind.value is PacketKind.Examine
            else ()
        ),
    )
    inspected = checked(None, problems)
    if isinstance(inspected, Refused):
        return inspected
    return Built(
        _PreparedPacket(
            kind.value,
            previous.result.value,
            evidence.value,
        )
    )


def _with_handoff_argument(prepared, handoff_argument):
    return (
        prepared
        if isinstance(prepared, Refused)
        else Built(replace(prepared.value, handoff_argument=handoff_argument))
    )


def _diff(flags, data):
    path = flags.get("diff")
    if path is None:
        return Built(None)
    if isinstance(data, model.UnavailableInput):
        return checked(None, (data.defect,))
    if data is None:
        return checked(
            None,
            (
                _problem(
                    "MissingFact",
                    "--diff " + path,
                    "The named diff file does not exist.",
                ),
            ),
        )
    try:
        return Built(data.decode("utf-8"))
    except UnicodeError as error:
        return checked(
            None, (_problem("InputUnreadable", "--diff " + path, str(error)),)
        )


def prepare_packet(flags, previous, diff):
    """The packet read/produce table over already-read inputs; return refusal or a ready plan."""
    refused = examination_admission(flags)
    if refused:
        return checked(None, refused)
    kind = _kind(flags.get("kind"))
    path = flags.get("handoff")
    missing = (
        (model.missing_flag("handoff"),)
        if path is None
        else (
            _problem(
                "MissingFact",
                "--handoff " + path,
                "The named handoff file does not exist.",
            ),
        )
        if previous is None
        else ()
    )
    admission = tuple(
        _problem(
            "InconsistentFacts",
            "--" + flag,
            f"An examination packet has no {flag} input.",
        )
        for flag in ("diff",)
        if isinstance(kind, Built)
        and kind.value is PacketKind.Examine
        and flags.get(flag)
    )
    return _with_handoff_argument(
        _prepare(
            kind,
            previous if path is not None else None,
            _diff(flags, diff),
            (*missing, *admission),
        ),
        path,
    )


def examine(handoff, observations=(), *, workspace=None):
    admission = examination_admission({"kind": "examine", "observation": observations})
    if admission:
        return checked(None, admission)
    previous = model.HandoffInput(Built(handoff), handoff._references)
    prepared = _prepare(Built(PacketKind.Examine), previous, Built(None))
    if isinstance(prepared, Refused):
        return prepared
    return replace(prepared.value, workspace=workspace).build()


def review(
    handoff, observations=(), diff=None, *, handoff_argument=None, slice_id=None
):
    admission = examination_admission({"kind": "review", "observation": observations})
    if admission:
        return checked(None, admission)
    previous = model.HandoffInput(Built(handoff), handoff._references)
    prepared = _prepare(
        Built(PacketKind.Review),
        previous,
        Built(diff),
    )
    if isinstance(prepared, Refused):
        return prepared
    return replace(
        prepared.value, handoff_argument=handoff_argument, slice_id=slice_id
    ).build()


def _resolved(spec, value, facts):
    if value is None:
        return None
    if spec.kind == "text":
        return facts[value]
    if spec.kind == "choice":
        fields = _resolved(spec.index[value[spec.discriminator]], value, facts)
        return model.Record(
            ((spec.discriminator, value[spec.discriminator]), *fields.items())
        )
    if spec.kind == "array":
        return tuple(_resolved(spec.members[0], child, facts) for child in value)
    if spec.kind == "table":
        return model.Record(
            (name, _resolved(spec.members[0], child, facts))
            for name, child in value.items()
        )
    if spec.kind == "record":
        return model.Record(
            (
                *((("id", value["id"]),) if spec.identity else ()),
                *(
                    (name, _resolved(child, value[name], facts))
                    for name, child in spec.members
                    if name in value
                ),
            )
        )
    return value


def _public_slice(handoff, intent):
    identity = intent["id"]
    design = ((handoff.design or model.EMPTY).get("slices") or model.EMPTY).get(
        identity
    ) or model.EMPTY
    return model.Record(
        (
            ("id", identity),
            ("observation", handoff.facts[intent["observation"]]),
            (
                "public_oracle",
                _resolved(_PUBLIC_ORACLE, design.get("public_oracle"), handoff.facts),
            ),
        )
    )


def _public_examination(handoff, workspace):
    product = handoff.product or model.EMPTY
    return PublicExamination(
        _resolved(
            model.PRODUCT.index["promises"], product.get("promises", ()), handoff.facts
        ),
        tuple(_public_slice(handoff, intent) for intent in product.get("slices", ())),
        _resolved(
            model.EXPECTATIONS.index["rows"],
            (handoff.expectations or model.EMPTY).get("rows", ()),
            handoff.facts,
        ),
        workspace,
        _resolved(model.CHARTER, handoff.charter, handoff.facts),
        (handoff.scope.kind, getattr(handoff.scope, "id", None)),
    )


def _review_slice(handoff, intent):
    identity = intent["id"]
    design = ((handoff.design or model.EMPTY).get("slices") or model.EMPTY).get(
        identity
    ) or model.EMPTY
    return model.Record(
        (
            ("id", identity),
            ("observation", handoff.facts[intent["observation"]]),
            (
                "targets",
                tuple(
                    model.Record((("path", row["path"]), ("change", row["change"])))
                    for row in design.get("targets", ())
                ),
            ),
            ("oracle", design.get("oracle")),
            ("supports", design.get("supports", ())),
            ("verification", model.slice_verification(handoff.design, identity)),
            (
                "public_oracle",
                _resolved(_PUBLIC_ORACLE, design.get("public_oracle"), handoff.facts),
            ),
            (
                "records",
                _resolved(
                    REVIEW_RECORDS, design.get("records") or model.EMPTY, handoff.facts
                ),
            ),
            (
                "shared",
                model.Record(
                    (name, tuple(row["id"] for row in rows))
                    for name, rows in (
                        (
                            model.project_design(handoff.design, identity)
                            or model.EMPTY
                        ).get("shared")
                        or model.EMPTY
                    ).items()
                ),
            ),
            (
                "acceptance",
                documents.acceptance_rows(handoff.acceptance.get(identity, ())),
            ),
        )
    )


def _review_packet(handoff, diff, handoff_argument=None, slice_id=None):
    slices = tuple(
        _review_slice(handoff, intent)
        for intent in (handoff.product or model.EMPTY).get("slices", ())
        if slice_id is None or intent["id"] == slice_id
    )
    paths = tuple(
        dict.fromkeys(
            path
            for slice in slices
            for path in (
                *(row["path"] for row in slice["targets"]),
                slice["oracle"],
                *slice["supports"],
            )
            if path is not None
        )
    )
    return ReviewPacket(
        slices,
        diff,
        documents.acceptance_document(handoff.scope, handoff_argument),
        documents.architecture_document(handoff.scope, handoff_argument),
        paths,
    )


def _labelled(label, text):
    return (
        label
        + ":\n"
        + (documents.fenced(text, language="") if text is not None else "None.\n")
    )


def _public_oracle(oracle):
    return "".join(
        _labelled(label, oracle.get(name) if oracle is not None else None)
        for label, name in (
            ("Stimulus", "stimulus"),
            ("Expected", "expected"),
            ("Falsifier", "falsifier"),
        )
    )


def _promise(promise):
    body = (
        documents.fenced(promise["text"], language="")
        if promise["kind"] == "Outcome"
        else "".join(
            _labelled(label, promise[name])
            for label, name in (
                ("Title", "title"),
                ("Given", "given"),
                ("When", "when"),
                ("Then", "then"),
            )
        )
    )
    return "### " + documents.escaped(promise["id"]) + "\n" + body


def _charter(charter):
    if charter is None:
        return "None.\n"
    return "".join(
        "### " + name + "\n\n" + body
        for name, body in documents.charter_sections(charter)
    )


def _row_obligations(row):
    """What the examiner checks the row against: its lacuna, blocking, isolation and needs.

    A legacy row has no lacuna field and says so; an absent blocking flag is blocking and
    an absent isolated flag is sequential, the defaults the row contract states.
    """
    lacuna = row.get("lacuna")
    needs = row.get("needs")
    return (
        (
            "Lacuna: not recorded\n"
            if lacuna is None
            else "Lacuna:\n" + documents.fenced(lacuna, language="")
        )
        + (
            "Blocking: non-blocking\n"
            if row.get("blocking") == "no"
            else "Blocking: blocking\n"
        )
        + ("Run: isolated\n" if row.get("isolated") == "yes" else "Run: in sequence\n")
        + ("" if needs is None else "Needs:\n" + documents.fenced(needs, language=""))
    )


def render_examination(packet: PublicExamination):
    return (
        "## Scope\n"
        + "Kind: "
        + packet.scope[0]
        + "\n"
        + ("Id: " + packet.scope[1] + "\n" if packet.scope[1] is not None else "")
        + "## Promises\n"
        + ("".join(_promise(promise) for promise in packet.promises) or "None.\n")
        + "".join(
            "## Slice "
            + documents.escaped(slice["id"])
            + "\n"
            + _labelled("Observation", slice["observation"])
            + _public_oracle(slice["public_oracle"])
            for slice in packet.slices
        )
        + "## Charter\n"
        + _charter(packet.charter)
        + "## Expectations\n"
        + (
            "".join(
                "### "
                + documents.escaped(row["id"])
                + "\n"
                + "Promises: "
                + ", ".join(
                    documents.escaped(identity) for identity in row.get("promises", ())
                )
                + "\n"
                + documents.fenced(row["text"], language="")
                + _row_obligations(row)
                for row in packet.expectations
            )
            or "None.\n"
        )
        + render_workspace(packet.workspace)
    )


def _list(label, values):
    return label + ": " + (",".join(values) or "None.") + "\n"


def _targets(rows, paths):
    return "Targets:\n" + (
        "".join(
            _list(change, (paths[row["path"]] for row in group))
            for change, group in groupby(rows, lambda row: row["change"])
        )
        or "None.\n"
    )


def _render_review_slice(slice, paths):
    return (
        "## Slice "
        + documents.escaped(slice["id"])
        + "\n"
        + _labelled("Observation", slice["observation"])
        + _targets(slice["targets"], paths)
        + "Oracle: "
        + (paths[slice["oracle"]] if slice["oracle"] is not None else "None.")
        + "\n"
        + _list("Supports", tuple(paths[path] for path in slice["supports"]))
        + "Verification:\n"
        + (
            documents.render_resolved_field(
                model.SLICE_DESIGN.index["verification"], slice["verification"]
            )
            if slice["verification"]
            else "None.\n"
        )
        + "Public oracle:\n"
        + (
            _public_oracle(slice["public_oracle"])
            if slice["public_oracle"] is not None
            else "None.\n"
        )
        + "Records:\n"
        + documents.render_resolved_field(
            REVIEW_RECORDS, slice["records"], level=4, compact=True
        )
        + _list(
            "Shared",
            (identity for rows in slice["shared"].values() for identity in rows),
        )
        + "Acceptance: ### "
        + documents.escaped(slice["id"])
        + "\n"
        + slice["acceptance"]
    )


def render_review(packet: ReviewPacket):
    paths = {path: f"@{index}" for index, path in enumerate(packet.paths, 1)}
    return (
        "Acceptance: "
        + documents.inline(packet.acceptance_document)
        + "; read via file tool. Rows: locator/owner, covers, obligations.\n"
        + "## Paths\n"
        + documents.path_index(
            tuple((identity, path) for path, identity in paths.items())
        )
        + "Shared records: "
        + documents.inline(packet.architecture_document)
        + " ## Shared records; read via file tool.\n"
        + "".join(_render_review_slice(slice, paths) for slice in packet.slices)
        + "## Diff\n"
        + (
            documents.fenced_diff(packet.diff)
            if packet.diff is not None
            else "None supplied.\n"
        )
    )


class Launch(Enum):
    """How a probed command starts: an interpreter runs a module entry, or the declared file itself."""

    INTERPRETER = "interpreter"
    DECLARED_EXECUTABLE = "declared-executable"


PYTHON_MANIFEST = "pyproject.toml"
# the neutral declaration of public commands; it decides with pyproject.toml, see declare
DECLARATION_FILE = ".nwave/examine.json"
# the committed configuration whose examine.public declares public prose beyond the defaults
CONFIG_FILE = ".nwave/config.json"
# every committed source the examiner reads: the declared commands and the declared prose
MANIFESTS = (PYTHON_MANIFEST, DECLARATION_FILE)
_COMMAND_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*")
_DECLARATION_KEYS = frozenset({"commands", "build"})
_COMMAND_KEYS = frozenset({"name", "path"})


@dataclass(frozen=True)
class DeclaredCommand:
    """One public command a declaration names, with what runs for it: MODULE:FUNCTION or a path."""

    name: str
    target: str


@dataclass(frozen=True)
class Declaration:
    """What a candidate declares about its examination; required paths must be executables."""

    launch: Launch
    commands: tuple[DeclaredCommand, ...]
    package_parents: tuple[str, ...] | None = None
    required: tuple[str, ...] = ()
    build: str = ""


@dataclass(frozen=True)
class PublicProjection:
    files: tuple[tuple[str, bytes], ...]
    launch: Launch
    commands: tuple[DeclaredCommand, ...]
    package_parents: tuple[str, ...] | None
    build: str


@dataclass(frozen=True)
class ExaminationWorkspace:
    path: str
    index: tuple[str, ...]


@dataclass(frozen=True)
class WorkspaceEntry:
    path: str
    kind: str
    content: bytes = b""
    writable: bool = False


@dataclass(frozen=True)
class ProbePlan:
    argv: tuple[str, ...]
    cwd: str
    environment: tuple[tuple[str, str], ...]
    candidate: str
    executable: str | None = None
    remedy: str = ""


@dataclass(frozen=True)
class ProbeRuntime:
    candidate: str
    executable: str
    has_source_directory: bool
    environment: Mapping[str, str]


@dataclass(frozen=True)
class ReadPlan:
    path: str


def self_gathered(flag):
    return Defect(
        "SelfGatheredEvidence: " + flag,
        "The examiner gathers its own evidence in the examination workspace; "
        "the reviewer gathers its own evidence at the reviewed commit; the host supplies none.",
        "Rebuild without "
        + flag
        + "; gather and record your own observations through the role's recording verbs.",
    )


def examination_admission(flags):
    names = ("--observation",) if flags.get("observation") else ()
    return tuple(
        self_gathered(name)
        for name in dict.fromkeys(
            (
                *names,
                *(
                    ("--root-context",)
                    if flags.get("kind") == "examine"
                    and flags.get("root_context") is not None
                    else ()
                ),
            )
        )
    )


def public_entries(listing, patterns):
    return tuple(
        (name, metadata.split()[2])
        for row in listing.decode("utf-8", "surrogateescape").split("\0")
        if row
        for metadata, name in (row.split("\t", 1),)
        if prose.is_public_path(name, patterns)
    )


def workspace_contaminated(entries):
    return Defect(
        "WorkspaceContaminated: " + ", ".join(entries),
        "The workspace differs from the committed public projection and scratch, "
        "contains a symlink or checkout path, or is inside a checkout.",
        "Build a fresh examination workspace with nwdes prompt --role nw-user-examiner "
        "--task examine, using a system temporary directory outside both checkouts.",
    )


def _unreadable_python(why):
    return Defect(
        "InputUnreadable: pyproject.toml at HEAD",
        why,
        "Commit a readable build manifest declaring the candidate console scripts.",
    )


def _python_declaration(manifest):
    try:
        data = tomllib.loads(manifest.decode("utf-8"))
        scripts = data.get("project", {}).get("scripts", {})
        packages = (
            data.get("tool", {})
            .get("hatch", {})
            .get("build", {})
            .get("targets", {})
            .get("wheel", {})
            .get("packages", ())
        )
        parents = tuple(dict.fromkeys(posixpath.dirname(name) for name in packages))
    except (ValueError, UnicodeError, TypeError, AttributeError) as error:
        return checked(None, (_unreadable_python(str(error)),))
    if not isinstance(scripts, dict) or any(
        not isinstance(value, str) or ":" not in value for value in scripts.values()
    ):
        return checked(
            None, (_unreadable_python("Console scripts must declare MODULE:FUNCTION."),)
        )
    return Built(
        Declaration(
            Launch.INTERPRETER,
            tuple(DeclaredCommand(name, target) for name, target in scripts.items()),
            parents or None,
        )
    )


def _declaration_defect(why):
    return Defect(
        f"InputUnreadable: {DECLARATION_FILE} at HEAD",
        why,
        f"Commit {DECLARATION_FILE} as a JSON object: a commands list of objects, each with the name "
        "of a public command and the relative path of its built executable, and optionally build with "
        "the text that builds them; then rebuild the examine prompt.",
    )


def declared_path_problem(path):
    """Why a declared path is not admitted, or None. The rule follows the host's path semantics. On POSIX
    only '/' separates segments and only a leading '/' is absolute, so a backslash, a colon or a drive-like
    prefix is an ordinary in-root name and is admitted. On Windows '\\' also separates segments, a leading
    backslash is UNC or device, and a leading drive letter and colon is refused. On every host, refused: an
    empty path; a path no UTF-8 file name can carry (an unpaired surrogate); a leading separator (absolute);
    a NUL or control character; and a segment that is empty, '.' or '..'."""
    if path == "":
        return "is empty, so it names no file"
    try:
        path.encode("utf-8")
    except UnicodeEncodeError:
        return "is not valid UTF-8 text: it holds an unpaired surrogate, so no file name can carry it"
    windows = sys.platform == "win32"
    separators = "/\\" if windows else "/"
    if path.startswith(tuple(separators)):
        return (
            "starts with a slash or a backslash, so it is absolute, a UNC or a device path"
            if windows
            else "starts with a slash, so it is absolute"
        )
    if windows and re.match(r"[A-Za-z]:", path):
        return (
            "starts with a drive letter and a colon, so it names a drive-relative file"
        )
    if any(ord(character) < 32 or ord(character) == 127 for character in path):
        return "contains a NUL or control character"
    if any(
        segment in ("", ".", "..")
        for segment in re.split(f"[{re.escape(separators)}]", path)
    ):
        return "has an empty, '.' or '..' segment, which can leave the candidate"
    return None


def _command_problem(entry, earlier):
    """Why one command entry is not admitted, or None when its name and path are plain."""
    if not isinstance(entry, dict) or set(entry) != _COMMAND_KEYS:
        return "each command is an object with exactly the keys name and path"
    name, path = entry["name"], entry["path"]
    if not isinstance(name, str) or not _COMMAND_NAME.fullmatch(name):
        return (
            f"command name {name!r} is not a plain word: it starts with a letter or digit, "
            "then holds letters, digits, '-' or '_'"
        )
    if name in earlier:
        return f"command {name} is declared more than once"
    if not isinstance(path, str):
        return f"the path of command {name} is not a relative path inside the candidate"
    problem = declared_path_problem(path)
    if problem is not None:
        return f"the path {path!r} of command {name} {problem}"
    return None


def _first_problem(entries):
    names = ()
    for entry in entries:
        problem = _command_problem(entry, names)
        if problem is not None:
            return problem
        names = (*names, entry["name"])
    return None


def _neutral_declaration(text):
    """The declaration HEAD commits in DECLARATION_FILE, or its first defect."""
    try:
        raw = json.loads(text.decode("utf-8"), object_pairs_hook=strict_object)
    except (ValueError, UnicodeError) as error:
        return checked(None, (_declaration_defect(f"it is not valid JSON ({error})"),))
    if not isinstance(raw, dict):
        return checked(None, (_declaration_defect("it is not a JSON object"),))
    unknown = sorted(set(raw) - _DECLARATION_KEYS)
    if unknown:
        return checked(
            None,
            (
                _declaration_defect(
                    "it holds keys the examiner does not read: " + ", ".join(unknown)
                ),
            ),
        )
    entries = raw.get("commands")
    if not isinstance(entries, list) or not entries:
        return checked(
            None,
            (
                _declaration_defect(
                    "commands must be a non-empty list of command objects"
                ),
            ),
        )
    build = raw.get("build", "")
    if not isinstance(build, str):
        return checked(
            None,
            (
                _declaration_defect(
                    "build must be the text that builds the executables"
                ),
            ),
        )
    problem = _first_problem(entries)
    if problem is not None:
        return checked(None, (_declaration_defect(problem),))
    return Built(
        Declaration(
            Launch.DECLARED_EXECUTABLE,
            tuple(DeclaredCommand(entry["name"], entry["path"]) for entry in entries),
            None,
            tuple(entry["path"] for entry in entries),
            build,
        )
    )


def _config_defect(why):
    return Defect(
        "InputUnreadable: examine.public in " + CONFIG_FILE + " at HEAD",
        why,
        "Commit "
        + CONFIG_FILE
        + " with examine.public as a JSON array of relative paths or globs, such as "
        '["docs/runbooks/**.md", "README.md"], or remove the examine key to keep the default '
        "prose, then rebuild the examine prompt.",
    )


def _public_problem(entry):
    """Why one declared public pattern is not admitted, or None when it is a plain relative pattern."""
    if not isinstance(entry, str):
        return f"entry {entry!r} is not a string"
    problem = declared_path_problem(entry)
    if problem is not None:
        return f"entry {entry!r} {problem}"
    return None


def public_declaration(text):
    """The public patterns HEAD's configuration declares, or the first defect.

    An absent configuration or an absent examine key declares none, so the defaults apply alone.
    Every other shape the examine key can take that the examiner does not read is refused.
    """
    if text is None:
        return Built(())
    try:
        raw = json.loads(text.decode("utf-8"), object_pairs_hook=strict_object)
    except (ValueError, UnicodeError) as error:
        return checked(
            None,
            (
                _config_defect(
                    f"{CONFIG_FILE} is not valid JSON ({error}), so its declaration cannot be read"
                ),
            ),
        )
    if not isinstance(raw, dict):
        return checked(
            None,
            (
                _config_defect(
                    f"{CONFIG_FILE} is not a JSON object, so its declaration cannot be read"
                ),
            ),
        )
    if "examine" not in raw:
        return Built(())
    examine = raw["examine"]
    if not isinstance(examine, dict):
        return checked(
            None,
            (_config_defect("examine must be a JSON object that holds public"),),
        )
    unknown = sorted(set(examine) - {"public", "level"})
    if unknown:
        return checked(
            None,
            (
                _config_defect(
                    "examine holds keys the examiner does not read: "
                    + ", ".join(unknown)
                ),
            ),
        )
    if "public" not in examine:
        # ``level`` is read by the examine level reader; a configuration that sets only the level declares no prose.
        return Built(())
    public = examine["public"]
    if not isinstance(public, list) or not public:
        return checked(
            None,
            (
                _config_defect(
                    "examine.public must be a non-empty JSON array of relative paths or globs"
                ),
            ),
        )
    problem = next(
        (found for found in map(_public_problem, public) if found is not None), None
    )
    if problem is not None:
        return checked(
            None,
            (
                _config_defect(
                    "examine.public "
                    + problem
                    + ": a declared pattern is relative to the candidate and names no "
                    "absolute, parent or empty segment"
                ),
            ),
        )
    return Built(tuple(prose.PublicPattern(entry) for entry in dict.fromkeys(public)))


def _no_declaration():
    return Defect(
        "InputUnreadable: no examination declaration at HEAD",
        "examining a candidate needs its public commands and the built executable each one runs, "
        "and HEAD commits no declaration of them",
        f"Commit {DECLARATION_FILE} naming each public command and the relative path of its built "
        "executable, then rebuild the examine prompt.",
    )


def declaration_unreadable():
    return Defect(
        f"InputUnreadable: {DECLARATION_FILE} at HEAD",
        f"HEAD commits {DECLARATION_FILE} as something other than a regular file: a directory or a submodule",
        f"Commit {DECLARATION_FILE} as a regular JSON file naming each public command and the relative "
        "path of its built executable, then rebuild the examine prompt.",
    )


def _rebuild(build, where="the candidate checkout"):
    """How a refusal asks for the build: the candidate's declared build text, or a plain instruction."""
    if build:
        return f"run {build} in {where}"
    return f"build the executable again in {where}"


def _missing_executable(path, build):
    return Defect(
        "InputUnreadable: " + path,
        "the declared command runs the executable at this path, and no regular executable file is there",
        f"Remove anything at {path} that is not a regular file, then {_rebuild(build)} so that {path} "
        "is a regular executable file, then rebuild the examine prompt.",
    )


def _not_executable(path, build):
    return Defect(
        "InputUnreadable: " + path,
        "the declared command runs the file at this path, and that file has no execute permission",
        f"Run chmod +x -- {shlex.quote(path)} in the candidate checkout, then rebuild the examine prompt.",
    )


def _symlink_executable(path, build):
    return Defect(
        "InputUnreadable: " + path,
        "the declared path ends in a symlink, so the examiner would run a file other than the built "
        "executable at this path",
        f"Remove the symlink at {path} and {_rebuild(build)} so that {path} is the built executable "
        "as a regular file, then rebuild the examine prompt.",
    )


def _symlink_directory_executable(path, build):
    return Defect(
        "InputUnreadable: " + path,
        "a directory on the declared path is a symlink, so the built executable would be written "
        "and run through a link",
        f"Remove the symlinked directory on the path to {path} (the symlink, not a real directory) "
        f"and {_rebuild(build)}, which creates real directories and the built executable at {path}, "
        "then rebuild the examine prompt.",
    )


def _not_directory_executable(path, build):
    return Defect(
        "InputUnreadable: " + path,
        "a component of the declared path is not a directory: it is a regular file where a directory is needed",
        f"Remove the file where a directory is needed on the path to {path} and {_rebuild(build)}, which "
        f"creates the directories and the built executable at {path}, then rebuild the examine prompt.",
    )


def _no_access_executable(path, build):
    return Defect(
        "InputUnreadable: " + path,
        "the declared path cannot be opened by this user: a directory on it cannot be searched by "
        "this user",
        f"Give the user who runs the examine prompt search permission on every directory on the "
        f"path to {path}, then rebuild the examine prompt.",
    )


def _unreadable_executable(path, build):
    return Defect(
        "InputUnreadable: " + path,
        "the system cannot open the declared path for a reason the examiner does not name",
        f"Shorten the declared file name if the file system refuses its length; otherwise fix the "
        f"file-system error on the path to {path}; then {_rebuild(build)} so that {path} is the built "
        "executable, then rebuild the examine prompt.",
    )


def _no_descriptor_walk(path, build):
    return Defect(
        "InputUnreadable: " + path,
        "this platform cannot open each name of the declared path without following a symbolic link, "
        "so the examiner cannot pin the file it would run",
        "Examine the candidate on a platform with descriptor-relative no-follow opens (Linux or macOS): "
        "run the examine prompt there, then probe and read there.",
    )


def _not_readable(path, build):
    return Defect(
        "InputUnreadable: " + path,
        "this platform has no O_PATH, so the examiner opens each directory and the file on the declared "
        "path for reading, and this user cannot read one of them",
        f"Give the user who runs the examine prompt read permission on the file at {path} and read and "
        "search permission on every directory on the path (chmod u+rx on each directory, chmod u+r on "
        "the file), then rebuild the examine prompt.",
    )


_EXECUTABLE_REFUSALS = {
    "not_executable": _not_executable,
    "symlink": _symlink_executable,
    "symlink_directory": _symlink_directory_executable,
    "not_directory": _not_directory_executable,
    "no_access": _no_access_executable,
    "not_readable": _not_readable,
    "no_descriptor_walk": _no_descriptor_walk,
    "unreadable": _unreadable_executable,
}


def executable_defect(path, status, build):
    """The refusal for a declared executable that cannot be run from the checkout, named by its cause."""
    refuse = _EXECUTABLE_REFUSALS.get(status, _missing_executable)
    return refuse(path, build)


def executable_launch_failure(path, error, build):
    """The refusal for a declared executable the system will not start, named by the error's cause.

    error is the OSError of the launch: EACCES or EPERM is a file system that refuses execution (noexec),
    ENOEXEC is a file that is not a program, and any other error has no remedy the examiner can name.
    """
    reason = error.strerror or str(error)
    if error.errno in (errno.EACCES, errno.EPERM):
        return Defect(
            "InputUnreadable: " + path,
            f"the system refuses to run the file ({reason}); the file system holding the checkout "
            "may be mounted noexec, and rebuilding in the same checkout cannot change that",
            "Copy the candidate checkout with cp -a CHECKOUT NEW_LOCATION to a filesystem mounted "
            f"with exec, {_rebuild(build, 'the copy')}, then examine the copy.",
        )
    if error.errno == errno.ENOEXEC:
        return Defect(
            "InputUnreadable: " + path,
            f"the file at {path} is not a program the system can run ({reason})",
            f"Remove the file at {path}, then {_rebuild(build)} so that {path} is the built executable, "
            "then rebuild the examine prompt.",
        )
    return Defect(
        "InputUnreadable: " + path,
        f"the system cannot start the file at {path} ({reason})",
        "nothing to run: the examiner names no command for this error; check the file system "
        "holding the checkout, then rebuild the examine prompt.",
    )


def _listed(declared):
    return ", ".join(sorted(command.name for command in declared.value.commands))


def _contradiction(console, neutral):
    return Defect(
        f"InputUnreadable: {PYTHON_MANIFEST} and {DECLARATION_FILE} at HEAD",
        f"{PYTHON_MANIFEST} declares the console commands {_listed(console)}, and "
        f"{DECLARATION_FILE} declares {_listed(neutral)}: the two name different public "
        "commands, so the examiner cannot tell which commands are public",
        f"Make {PYTHON_MANIFEST} and {DECLARATION_FILE} name the same public commands, or remove "
        f"the [project.scripts] table from {PYTHON_MANIFEST} so {DECLARATION_FILE} decides, then "
        "rebuild the examine prompt.",
    )


def declare(manifests):
    """One declaration from what HEAD commits. The explicit declaration decides; pyproject.toml decides
    alone only when it declares no console script, and two declarations that name different commands
    are refused naming both files."""
    python = manifests.get(PYTHON_MANIFEST)
    explicit = manifests.get(DECLARATION_FILE)
    console = None if python is None else _python_declaration(python)
    if isinstance(console, Refused):
        return console
    if explicit is None:
        return console if console is not None else checked(None, (_no_declaration(),))
    neutral = _neutral_declaration(explicit)
    if isinstance(neutral, Refused) or console is None or not console.value.commands:
        return neutral
    if {command.name for command in console.value.commands} == {
        command.name for command in neutral.value.commands
    }:
        return neutral
    return checked(None, (_contradiction(console, neutral),))


@dataclass(frozen=True)
class FileIdentity:
    """What makes a declared file the same file: its device, inode, size and modification time."""

    device: int
    inode: int
    size: int
    mtime_ns: int


def file_identity(status) -> FileIdentity:
    return FileIdentity(
        status.st_dev, status.st_ino, status.st_size, status.st_mtime_ns
    )


def same_file(first: FileIdentity, second: FileIdentity) -> bool:
    """A path start is allowed only when every identity field agrees with the verified file."""
    return first == second


def executable_changed(path, build):
    """The refusal for a declared file that is no longer the file verified before its descriptor start."""
    return Defect(
        "InputUnreadable: " + path,
        "the declared file changed after its descriptor launch was refused: it is no longer the "
        "file that was verified, so it is not started",
        f"Do not replace {path} while the examination runs; {_rebuild(build)}, then rebuild the "
        "examine prompt.",
    )


def launched_by_path_note(path, error):
    """The outcome line for a declared file started by its path after the system refused its descriptor."""
    return (
        f"nwdes examine probe: {path} launched by path, because the system refused its descriptor "
        f"launch ({error.strerror or error}); the same file was verified again by device, inode, "
        "size and modification time.\n"
    )


def required_paths(declared):
    return declared.value.required if isinstance(declared, Built) else ()


def public_projection(entries, blobs, declared, candidate, executables):
    """entries are the public (name, identity) pairs; executables maps each required path to its status."""
    tainted = tuple(name for name, _ in entries if candidate.encode() in blobs[name])
    if tainted:
        return checked(None, (workspace_contaminated(tainted),))
    if isinstance(declared, Refused):
        return declared
    value = declared.value
    problems = tuple(
        executable_defect(path, executables.get(path, "missing"), value.build)
        for path in value.required
        if executables.get(path, "missing") != "ok"
    )
    if problems:
        return checked(None, problems)
    return Built(
        PublicProjection(
            tuple((name, blobs[name]) for name, _ in entries),
            value.launch,
            value.commands,
            value.package_parents,
            value.build,
        )
    )


def _under(path, root):
    return path == root or path.startswith(root.rstrip("/") + "/")


def inspect_workspace(projection, workspace, checkout_roots, entries):
    expected_files = {"public/" + name: content for name, content in projection.files}
    expected_dirs = frozenset(
        (
            "public",
            "scratch",
            *(parent for name in expected_files for parent in _parents(name)),
        )
    )
    actual = {entry.path: entry for entry in entries}
    problems = tuple(
        sorted(
            (
                *(name for name in expected_files if name not in actual),
                *(name for name in expected_dirs if name not in actual),
                *(
                    entry.path
                    for entry in entries
                    if entry.kind == "link" and not entry.path.startswith("scratch/")
                ),
                *(
                    entry.path
                    for entry in entries
                    if not entry.path.startswith("scratch/")
                    and (
                        (
                            entry.path in expected_files
                            and (
                                entry.kind != "file"
                                or entry.content != expected_files[entry.path]
                                or entry.writable
                            )
                        )
                        or (entry.path in expected_dirs and entry.kind != "dir")
                        or entry.path not in expected_files.keys() | expected_dirs
                    )
                ),
                *(
                    ("workspace",)
                    if any(_under(workspace, root) for root in checkout_roots)
                    else ()
                ),
            )
        )
    )
    return (
        checked(None, (workspace_contaminated(problems),))
        if problems
        else Built(
            ExaminationWorkspace(workspace, tuple(name for name, _ in projection.files))
        )
    )


def _parents(name):
    parent = posixpath.dirname(name)
    return () if not parent else (parent, *_parents(parent))


_PROBE_LAUNCHER = (
    "import sys,importlib;"
    "roots,entry,args=__import__('json').loads(sys.argv[1]);"
    "sys.path[:0]=roots;sys.argv=args;"
    "module,function=entry.split(':',1);"
    "target=importlib.import_module(module);"
    "target=__import__('functools').reduce(getattr,function.split('.'),target);"
    "sys.exit(target())"
)


def _probe_argv(executable, import_roots, entry, argv):
    return (
        executable,
        "-I",
        "-B",
        "-c",
        _PROBE_LAUNCHER,
        json.dumps((import_roots, entry, argv)),
    )


def _import_roots(projection, runtime):
    if projection.package_parents:
        return tuple(
            posixpath.join(runtime.candidate, parent)
            for parent in projection.package_parents
        )
    return (
        *((runtime.candidate + "/src",) if runtime.has_source_directory else ()),
        runtime.candidate,
    )


def _program(projection, target, argv, runtime):
    """The argv to run and the declared file to run it from, when the launch is a declared file."""
    if projection.launch is Launch.DECLARED_EXECUTABLE:
        return tuple(argv), target
    return (
        _probe_argv(
            runtime.executable,
            _import_roots(projection, runtime),
            target,
            argv,
        ),
        None,
    )


def prepare_probe(
    projection, workspace, argv, resolved_arguments, runtime: ProbeRuntime
):
    bad = tuple(
        arg
        for arg, resolved in zip(argv[1:], resolved_arguments, strict=True)
        if posixpath.isabs(arg)
        or posixpath.isabs(
            arg.split("=", 1)[1] if arg.startswith("--") and "=" in arg else arg
        )
        or not _under(resolved, workspace.path)
    )
    commands = {command.name: command.target for command in projection.commands}
    if not argv or argv[0] not in commands or bad:
        return checked(
            None,
            (
                Defect(
                    "ProbeRefused: " + (" ".join(argv) or "empty command"),
                    "Only declared console scripts with workspace-relative arguments are admitted. "
                    "Admitted commands: " + ", ".join(commands),
                    "Use nwdes examine probe --workspace W -- COMMAND ARGS with an admitted "
                    "command and arguments resolving inside W from scratch.",
                ),
            ),
        )
    scratch = workspace.path + "/scratch"
    program, executable = _program(projection, commands[argv[0]], argv, runtime)
    return Built(
        ProbePlan(
            program,
            scratch,
            (
                ("PATH", runtime.environment.get("PATH", "")),
                ("LANG", runtime.environment.get("LANG", "C.UTF-8")),
                ("HOME", scratch),
                ("TMPDIR", scratch),
            ),
            runtime.candidate,
            executable,
            projection.build,
        )
    )


def prepare_read(workspace, path, resolved, symlink):
    public = workspace.path + "/public"
    if posixpath.isabs(path) or not _under(resolved, public) or symlink:
        return checked(
            None,
            (
                Defect(
                    "ReadRefused: " + path,
                    "Read accepts only paths under the public projection with no symlink component.",
                    "Use nwdes examine read --workspace W with a path relative to W/public.",
                ),
            ),
        )
    return Built(ReadPlan(resolved))


def mask_candidate(data, candidate):
    return data.replace(candidate.encode(), b"<candidate>")


def render_workspace(workspace):
    if workspace is None:
        return "## Workspace\nNone.\n"
    quoted = shlex.quote(workspace.path)
    return (
        "## Workspace\n" + workspace.path + "\n"
        "The examiner gathers its own observations here. Read public documents with "
        "nwdes examine read and gather evidence with nwdes examine probe. Record each "
        "observation through the generated examination recording verbs before citing it.\n"
        "Public projection index:\n"
        + "".join("- " + name + "\n" for name in workspace.index)
        + "Read: nwdes examine read --workspace "
        + quoted
        + " [PATH]\n"
        + "Probe: nwdes examine probe --workspace "
        + quoted
        + " -- COMMAND ARGS\n"
    )
