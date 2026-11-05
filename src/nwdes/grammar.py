"""Command grammar and generated references for role value verbs."""

import shlex
from dataclasses import dataclass

from nwdes import drafts
from nwdes.contracts import Built, Refused, refuse


@dataclass(frozen=True)
class Verb:
    name: str
    actions: tuple[str, ...] = ()


VERBS = (
    Verb("feature", ("new",)),
    Verb("slice", ("set",)),
    Verb("work", ("set",)),
    Verb("rework", ("set", "clear")),
    Verb("document"),
    Verb("delta"),
    Verb("prompt"),
    Verb("packet"),
    Verb("lane", ("open", "compose", "rekey", "integrate")),
    Verb("measure"),
    Verb("commit"),
    *(
        Verb(
            kind,
            (
                *(verb.name for verb in drafts.role_verbs(kind)),
                *(("probe", "read") if kind == "examine" else ()),
            ),
        )
        for kind in drafts.KINDS
    ),
)

SINGLE_OPTIONS = (
    "repo-root",
    "project-root",
    "global-config",
    "feature",
    "epic",
    "request",
    "size",
    "value",
    "slice",
    "delta",
    "reason",
    "observation",
    "paradigm",
    "oracle",
    "stimulus",
    "expected",
    "falsifier",
    "previous",
    "new",
)
REPEATED_OPTIONS = (
    "handoff",
    "command",
    "support",
    "create",
    "extend",
    "promise",
    "cites",
    "decision",
    "constraint",
)

PROMPT_OPTIONS = (
    "role",
    "handoff",
    "task",
    "slice",
    "phase",
    "diff",
    "commit",
    "root-context",
    "repo-root",
    "jev",
)
RETIRED_ARGUMENTS = ("--observation", "--observation-file")


def retired(argv):
    return tuple(
        name
        for name in RETIRED_ARGUMENTS
        if any(token == name or token.startswith(name + "=") for token in argv)
    )


PACKET_OPTIONS = ("kind", "handoff", "diff", "root-context")
ROOT_CONTEXT_HELP = (
    "extra recommendations and context from the orchestrating LLM, printed verbatim, "
    "never interpreted"
)
PRODUCT_VALUE_AUDIT = (
    "GDP-9: Does every slice contribute to this one value, or did you bundle unrelated "
    "outcomes? Do not answer yes by default. Split unrelated outcomes into a separate "
    "nwdes feature new."
)


@dataclass(frozen=True)
class Argument:
    flag: str
    meaning: str


@dataclass(frozen=True)
class Command:
    verb: str
    action: str | None
    synopsis: str
    arguments: tuple[Argument, ...]
    refusals: tuple[tuple[str, str], ...]
    example: str

    @property
    def name(self) -> str:
        return self.verb if self.action is None else f"{self.verb} {self.action}"

    @property
    def summary(self) -> str:
        return f"nwdes {self.name}  {self.synopsis}"


ROOT_DEFAULTS = {
    "repo-root": "repository root; omitted defaults to the absolute current directory at invocation",
    "project-root": "configuration root; omitted defaults to the repository root (--repo-root)",
}


ROOT_ARGUMENTS = (
    Argument("--repo-root", ROOT_DEFAULTS["repo-root"]),
    Argument("--project-root", ROOT_DEFAULTS["project-root"]),
    Argument(
        "--global-config",
        "global destination configuration file; omitted defaults to ~/.nwave/config.json",
    ),
    Argument(
        "--feature",
        "feature identity; omitted selects --epic scope, or project scope with document --product",
    ),
)
SLICE_ARGUMENT = Argument("--slice", "slice identity")
HANDOFF_ARGUMENT = Argument("--handoff", "input handoff file")
ROOT_REFUSALS = (
    ("MissingFact", "a required value or input file is absent"),
    ("PartInvalid", "a supplied value is outside its declared domain"),
    ("ConfigurationMalformed", "a read configuration tier is malformed"),
    ("HandoffInvalid", "a read handoff has invalid structure or facts"),
)
REFERENCE_REFUSAL = (
    ("DanglingReference", "a reference does not name an existing fact"),
)
ROLE_REFUSALS = (
    *ROOT_REFUSALS,
    ("RoleNotAccepted", "the role output is not accepted"),
    *REFERENCE_REFUSAL,
)

DESIGN_REFUSALS = (
    ("InconsistentFacts", "new or changed ADR body slots repeat normalized text"),
    (
        "AdrDeclarationDropped",
        "an accepted declaration is omitted without an explicit accepted successor",
    ),
    (
        "AdrSelectorRequired",
        "a changed-body row repeats an accepted ADR title without a selector",
    ),
    ("AdrAcceptedImmutable", "an accepted or superseded ADR body changes"),
    ("AdrTransitionInvalid", "a successor does not name an accepted predecessor"),
    ("AdrForeignLayout", "an ADR has an unsupported layout"),
    ("AdrKeyClash", "multiple ADR files have the same key"),
)

LANE_ARGUMENTS = (
    Argument(
        "--repo-root",
        "main project worktree root; omitted defaults to the main worktree of the invocation directory's repository, including from a lane or subdirectory; repository lane settings are read from "
        'ROOT/.nwave/config.json, for example {"lanes": {"trunk": "main"}} when main '
        "is the intended existing trunk; preserve other settings",
    ),
    Argument("--feature", "feature identity naming lanes/F and lane/F"),
)
LANE_REFUSALS = (
    ROOT_REFUSALS[0],
    ROOT_REFUSALS[1],
    ROOT_REFUSALS[2],
    (
        "LaneOutsideProject",
        "the root or resolved lane path is outside the project, or the feature identity is invalid",
    ),
    ("GitUnavailable", "git 2.38 or newer is unavailable on PATH"),
    (
        "LaneTrunkUndeclared",
        'lanes.trunk is not declared; set {"lanes": {"trunk": "BRANCH"}} in '
        "ROOT/.nwave/config.json, where ROOT is --repo-root and BRANCH is the intended "
        "existing trunk branch",
    ),
    *REFERENCE_REFUSAL,
)


EXAMINATION_COMMANDS = (
    Command(
        "examine",
        "probe",
        "Run a declared candidate console script with workspace-relative arguments.",
        (
            Argument(
                "--workspace",
                "required public examination workspace emitted by the examine prompt",
            ),
            Argument(
                "-- ARGV",
                "declared console script and arguments; paths resolve from workspace scratch",
            ),
        ),
        (
            (
                "ProbeRefused",
                "command is not declared or an argument escapes the workspace; exit 2",
            ),
            (
                "WorkspaceContaminated",
                "workspace differs from its committed public projection; exit 2",
            ),
            ("InputUnreadable", "git or the interpreter cannot run; exit 1"),
        ),
        "nwdes examine probe --workspace W -- nwdes --help",
    ),
    Command(
        "examine",
        "read",
        "Print a public file or list a public directory.",
        (
            Argument(
                "--workspace",
                "required public examination workspace emitted by the examine prompt",
            ),
            Argument(
                "PATH",
                "optional path relative to W/public; omitted lists that directory",
            ),
        ),
        (
            (
                "ReadRefused",
                "path escapes public, traverses a symlink or is unreadable; exit 2",
            ),
            (
                "WorkspaceContaminated",
                "workspace differs from its committed public projection; exit 2",
            ),
            ("InputUnreadable", "git cannot read the candidate at HEAD; exit 1"),
        ),
        "nwdes examine read --workspace W docs/guides",
    ),
)


COMMANDS = (
    Command(
        "feature",
        "new",
        "Create a feature handoff from the request and value.",
        (
            *ROOT_ARGUMENTS,
            Argument(
                "--epic",
                "parent epic identity; omitted leaves the feature without a parent epic",
            ),
            Argument("--request", "request text"),
            Argument("--size", "S, M or L size"),
            Argument("--value", "intended delivered value"),
        ),
        (*ROOT_REFUSALS, ("FeatureExists", "the feature already exists")),
        "nwdes feature new --feature search --request Search --size M --value Find",
    ),
    Command(
        "slice",
        "set",
        "Write a slice's observation and acceptance facts.",
        (
            *ROOT_ARGUMENTS,
            Argument(
                "--slice",
                "slice identity S<n>; omitted creates the next slice; naming one updates that existing slice",
            ),
            Argument(
                "--observation",
                "public observation of the slice; required when creating; omitted keeps the current value on --slice S",
            ),
            Argument(
                "--paradigm",
                "functional, object_oriented or procedural; omitted reuses the previous design paradigm; required for the first slice",
            ),
            Argument(
                "--oracle",
                "oracle path; required when creating unless every --create and --extend target is a prose asset, then forbidden; omitted keeps the current value on --slice S",
            ),
            Argument(
                "--stimulus",
                "public stimulus; required when creating unless every target is a prose asset, then forbidden; omitted keeps the current value on --slice S",
            ),
            Argument(
                "--expected",
                "expected observation; required when creating unless every target is a prose asset, then forbidden; omitted keeps the current value on --slice S",
            ),
            Argument(
                "--falsifier",
                "observation that disproves success; required when creating unless every target is a prose asset, then forbidden; omitted keeps the current value on --slice S",
            ),
            Argument(
                "--command",
                "whole ordered single-line verification command list; the first shlex word must resolve at write time on the invoking PATH, or name an existing root-relative or absolute file; required when creating unless every target is a prose asset, then forbidden; omitted keeps the current value on --slice S",
            ),
            Argument(
                "--support",
                "whole ordered support path list; omitted keeps the current list on --slice S, or uses none when creating; forbidden when every target is a prose asset",
            ),
            Argument(
                "--create",
                "whole ordered Create target list; omitted keeps the current list on --slice S, or uses none when creating",
            ),
            Argument(
                "--extend",
                "whole ordered Extend target list; omitted keeps the current list on --slice S, or uses none when creating",
            ),
            Argument(
                "--promise",
                "whole ordered list of slice-owned promises; omitted preserves the current own promises and their oracle references",
            ),
            Argument(
                "--cites",
                "whole ordered list of other promise references; omitted preserves prior non-own citations; given replaces them; oracle cites own promises first, then these references",
            ),
            Argument(
                "--decision",
                "whole list of cited shared decision ids; repeatable; omitted preserves membership",
            ),
            Argument(
                "--constraint",
                "whole list of cited shared constraint ids; repeatable; omitted preserves membership",
            ),
        ),
        (*ROOT_REFUSALS, *REFERENCE_REFUSAL),
        "nwdes slice set --feature search --observation Find --paradigm functional --oracle tests/search.py --stimulus Search --expected Found --falsifier Missing --command 'python tests/search.py' --promise 'The search result is returned' --extend src/search.py",
    ),
    Command(
        "work",
        "set",
        "Set the current work's size and value.",
        (
            *ROOT_ARGUMENTS,
            Argument("--slice", "slice identity; omitted sets the feature-level work"),
            Argument("--size", "S, M or L size"),
            Argument("--value", "intended delivered value"),
        ),
        (*ROOT_REFUSALS, *REFERENCE_REFUSAL),
        "nwdes work set --feature search --size M --value Find",
    ),
    Command(
        "rework",
        "set",
        "Record rework for the named slice and delta.",
        (
            *ROOT_ARGUMENTS,
            Argument("--slice", "slice identity; omitted sets feature-level rework"),
            Argument("--delta", "delta identity"),
            Argument("--reason", "reason for rework"),
        ),
        (*ROOT_REFUSALS, *REFERENCE_REFUSAL),
        "nwdes rework set --feature search --slice S1 --delta 1 --reason Repair",
    ),
    Command(
        "rework",
        "clear",
        "Clear the named slice's rework.",
        (
            *ROOT_ARGUMENTS,
            Argument("--slice", "slice identity; omitted clears feature-level rework"),
        ),
        (*ROOT_REFUSALS, *REFERENCE_REFUSAL),
        "nwdes rework clear --feature search --slice S1",
    ),
    Command(
        "document",
        None,
        "Render a product or design brief from its handoff.",
        (
            *ROOT_ARGUMENTS,
            Argument(
                "--product",
                "render the project product brief; omitted renders the selected feature or epic handoff",
            ),
            Argument(
                "--handoff",
                "feature handoff for project aggregation, repeatable; omitted adds no feature handoffs; feature and epic mode use their configured handoff",
            ),
        ),
        (
            *ROOT_REFUSALS,
            ("FeatureUnknown", "the feature has no handoff"),
            ("DestinationInvalid", "an output destination is invalid"),
        ),
        "nwdes document --feature search --product",
    ),
    Command(
        "delta",
        None,
        "Compare the facts of two handoffs, followed by AFFECTED slice ids in numeric order.",
        (
            Argument("--previous", "previous handoff file"),
            Argument("--new", "new handoff file"),
        ),
        (ROOT_REFUSALS[0], ROOT_REFUSALS[3]),
        "nwdes delta --previous previous.json --new current.json",
    ),
    Command(
        "prompt",
        None,
        "Build one complete inline role bundle from its template and handoff, ending "
        "with the generated role verb reference. "
        "For an indeterminate product reply requesting Quint work, "
        "use the nw-nwdes skill's host-owned Quint helper recipe, then rebuild the same "
        "product prompt with actual results in --root-context.",
        (
            Argument("--role", "specialist role name"),
            HANDOFF_ARGUMENT,
            Argument(
                "--task",
                "role task; omitted defaults to discuss for the product owner, no task for roles without tasks; the examiner requires a task",
            ),
            Argument(
                "--slice",
                "slice identity; required for nw-acceptance-designer, "
                "nw-acceptance-designer-reviewer, nw-software-crafter and "
                "nw-functional-software-crafter (implementation and prefactoring phases "
                "before-move and after-move-before-behavior); optional for "
                "nw-software-crafter-reviewer to name an embedded slice review, omitted "
                "for its whole-candidate review; omit it for nw-product-owner --task "
                "discuss (also the default task) or --task charter, "
                "nw-solution-architect, nw-user-examiner --task expectations or "
                "--task examine, whose recipes reject it; omission selects no slice",
            ),
            Argument(
                "--phase",
                "prefactoring phase; omitted selects implementation for crafter roles and no prefactoring phase for other roles",
            ),
            Argument(
                "--diff",
                "candidate diff file; for nw-software-crafter-reviewer the whole change "
                "from the slice's base commit, the approved oracle and supports included; "
                "omitted supplies no candidate diff",
            ),
            Argument(
                "--commit",
                "reviewed commit REV; required for review recipes and resolved to the full clean lane HEAD; omitted for other recipes",
            ),
            Argument("--root-context", ROOT_CONTEXT_HELP),
            Argument("--repo-root", ROOT_DEFAULTS["repo-root"]),
            Argument("--project-root", ROOT_DEFAULTS["project-root"]),
            Argument(
                "--jev",
                'authorization for this invocation: authorized or unauthorized; optional, and authorized by default when neither the flag nor a configuration tier declares "jev" (repository over global, default ~/.nwave/config.json); the flag wins over configuration; nwdes itself never writes or persists it',
            ),
            Argument(
                "--baseline-failure",
                "two single-line values ID OWNER; repeatable without a fixed limit; producer bundles only, never examiner or charter bundles; printed, never persisted",
            ),
        ),
        (
            ROOT_REFUSALS[0],
            ROOT_REFUSALS[3],
            *REFERENCE_REFUSAL,
            ("InconsistentFacts", "the role, task or phase cannot be combined"),
            ("PlaceholderUnbound", "a template placeholder has no binding"),
            ("FieldUnused", "a supplied field has no consumer in the prompt"),
            (
                "SelfGatheredEvidence",
                "examine refuses host observations and root context before any read or effect",
            ),
        ),
        "nwdes prompt --role nw-software-crafter-reviewer --handoff feature.handoff.json --jev unauthorized --diff candidate.diff --commit HEAD",
    ),
    Command(
        "packet",
        None,
        "Build an examine or review packet without host observations.",
        (
            Argument("--kind", "examine or review packet"),
            HANDOFF_ARGUMENT,
            Argument(
                "--diff",
                "candidate diff file for a review packet: the whole change from the "
                "slice's base commit, the approved oracle and supports included; "
                "omitted supplies no candidate diff",
            ),
            Argument(
                "--root-context",
                "refused for examine; the examiner gathers its own evidence",
            ),
        ),
        (
            ROOT_REFUSALS[0],
            ROOT_REFUSALS[1],
            ROOT_REFUSALS[3],
            *REFERENCE_REFUSAL,
            ("InconsistentFacts", "an examination packet is given a diff"),
            (
                "SelfGatheredEvidence",
                "examine is given host observations or root context",
            ),
        ),
        "nwdes packet --kind review --handoff feature.handoff.json --diff candidate.diff",
    ),
    Command(
        "lane",
        "open",
        "Open a feature worktree at trunk, or report its existing lane.",
        LANE_ARGUMENTS,
        (
            *LANE_REFUSALS,
            ("LaneOccupied", "the lane path or branch belongs to something else"),
        ),
        "nwdes lane open --feature search",
    ),
    Command(
        "lane",
        "compose",
        "Merge trunk into the lane and print EXPECTED and CANDIDATE commits.",
        LANE_ARGUMENTS,
        (
            *LANE_REFUSALS,
            ("LaneUncommitted", "the lane has tracked changes"),
            ("AdrKeyTaken", "trunk and lane added different ADR bodies at one key"),
            ("MergeConflict", "the prospective merge has conflicted files"),
            ("AdrKeyClash", "the merged tree holds multiple ADR files at one key"),
        ),
        "nwdes lane compose --feature search",
    ),
    Command(
        "lane",
        "rekey",
        "Renumber a lane-added ADR using a number free on both sides.",
        (
            *LANE_ARGUMENTS,
            Argument(
                "--key",
                "ADR key added by this lane; only this key is checked for layout and duplicate files; unrelated ADR keys remain occupied without requiring their layout",
            ),
        ),
        (
            *LANE_REFUSALS,
            ("InconsistentFacts", "the lane did not add the selected key"),
            ("AdrKeyClash", "the lane holds multiple ADR files for the selected key"),
            ("AdrForeignLayout", "the selected lane ADR has an unsupported layout"),
            ("FeatureUnknown", "the lane has no feature handoff"),
            ("HandoffInvalid", "the feature handoff is malformed"),
            ("DestinationInvalid", "an output path is invalid"),
            ("AssetMissing", "an installed brand asset is absent"),
            ("AssetUnreadable", "an installed brand asset cannot be read"),
        ),
        "nwdes lane rekey --feature search --key NWD-001",
    ),
    Command(
        "lane",
        "integrate",
        "Fast-forward trunk to CANDIDATE, then delete declared disposable files and remove the lane worktree and branch without force; one pass refuses every problem and changes nothing; rerun the same command after a failure.",
        (
            *LANE_ARGUMENTS,
            Argument("--expected", "full trunk commit id printed by lane compose"),
            Argument("--candidate", "full candidate commit id printed by lane compose"),
        ),
        (
            *LANE_REFUSALS,
            ("NotOnTrunk", "the root worktree is not on the declared trunk branch"),
            ("TrunkDirty", "the root worktree has uncommitted changes"),
            ("TrunkMoved", "trunk is neither EXPECTED nor CANDIDATE"),
            (
                "NotFastForward",
                "the candidate does not descend from the expected commit",
            ),
            ("LaneNotMerged", "the lane tip is not contained in CANDIDATE"),
            ("LaneUncommitted", "the lane has tracked changes"),
            (
                "LaneFileUndeclared",
                "an untracked or ignored lane-relative path matches no disposable pattern; "
                "only for files intentionally safe to delete, merge "
                '{"lanes": {"disposable": ["PATTERN"]}} into ROOT/.nwave/config.json, '
                "where ROOT is the main worktree passed as --repo-root; preserve other "
                "settings, lanes.trunk and existing patterns; PATTERN is a deliberate "
                "lane-worktree-relative POSIX path pattern, not lanes/FEATURE-prefixed; "
                "lane integrate deletes matches and removes the lane worktree and "
                "branch; no disposable patterns are built in; never declare user work "
                "disposable merely to finish; put the pattern in ROOT/.nwave/config.json "
                "and commit it on trunk, then run lane compose again before integration",
            ),
        ),
        "nwdes lane integrate --feature search --expected aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa --candidate bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    ),
)

MEASURE_OPTIONS = (
    "requests",
    "host-sessions",
    "rework",
    "objective-minutes",
    "candidate",
    "repo-root",
    "project-root",
    "global-config",
    "feature",
    "epic",
)
COMMANDS = (
    *COMMANDS,
    Command(
        "measure",
        None,
        "Read supplied intervals or qualify native delivery evidence; unavailable host evidence is not measured.",
        (
            Argument(
                "--requests",
                "supplied RequestInterval JSON file; omitted selects --host-sessions; exactly one source; not host-recorded",
            ),
            Argument(
                "--host-sessions", "root omp version-3 session file; exactly one source"
            ),
            Argument(
                "--rework",
                "optional root-declared session/request pairs; host mode only; omitted is unknown",
            ),
            Argument(
                "--objective-minutes",
                "optional positive integer objective, printed without a verdict",
            ),
            Argument(
                "--candidate",
                "optional full lowercase commit id; host mode only; unresolved evidence is not measured",
            ),
            *ROOT_ARGUMENTS,
            Argument(
                "--epic",
                "epic identity instead of --feature; omitted uses the feature scope from flags or native commands; host mode only",
            ),
        ),
        (
            (
                "PartInvalid",
                "invalid, unknown or repeated flags, invalid objective or argument combination",
            ),
            ("MissingFact", "a supplied requests file is absent"),
            ("InputUnreadable", "a supplied requests file is unreadable or not UTF-8"),
        ),
        "nwdes measure --host-sessions ROOT_SESSION_FILE --candidate aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa --objective-minutes 5",
    ),
    Command(
        "commit",
        None,
        "Commit only the role's owned files, with configured Git author identity and hooks; the root never commits for another role.",
        (
            *ROOT_ARGUMENTS,
            Argument("--epic", "epic scope when no feature is selected"),
            SLICE_ARGUMENT,
            Argument("--role", "required role that closed and owns the files"),
            Argument(
                "--path",
                "repeatable owned leaf path; omitted selects changed owned files, including run records",
            ),
            Argument(
                "--type",
                "required conventional type: feat, fix, docs, style, refactor, perf, test, build, ci, chore or revert",
            ),
            Argument("--description", "required commit subject description"),
            Argument("--scope", "optional conventional commit message scope"),
            Argument(
                "--body", "optional commit message body, separated by a blank line"
            ),
        ),
        (
            *ROOT_REFUSALS,
            ("InputUnreadable", "git or a required file cannot be read; exit 1"),
            (
                "CommitInProgress",
                "another nwdes close or commit holds the nonblocking Git-directory lock",
            ),
            ("IndexNotClean", "every path already staged must be unstaged first"),
            ("MissingCloseReceipt", "the role has not closed this delivery scope"),
            ("StaleBase", "HEAD differs from the role's close receipt"),
            ("UnownedFile", "an explicit path has no delivery owner"),
            ("NothingToCommit", "no owned file is selected"),
            (
                "CommitRejected",
                "Git or a hook rejected the commit; only this invocation's staged paths are unstaged",
            ),
        ),
        "nwdes commit --feature search --role nw-software-crafter --slice S1 --type feat --scope search --description 'add search'",
    ),
)


def _role_example(kind, verb, scope=("feature", "search"), role=None):
    alternatives = frozenset(
        field.choices[0] for field in verb.fields if field.required and field.choices
    )
    selectors = frozenset(
        names[0]
        for names in verb.exclusive
        if names in (("shared", "in"), ("at", "id"), ("id", "at"))
    )
    defaults = {
        scope[0]: scope[1],
        **({"role": role} if role is not None else {}),
        "slice": "S1",
        "in": "S1",
        "expectation": "E1",
        "promise": "P1",
        "observation": "O1",
        "command": "python -V",
        "verification": "python -V",
        "subject": "candidate",
    }

    def argument(field):
        if field.spec.kind == "boolean":
            return "--" + field.name
        value = defaults.get(
            field.name,
            field.choices[0]
            if field.choices
            else "1"
            if field.spec.kind == "integer"
            else "Value",
        )
        return "--" + field.name + " " + shlex.quote(value)

    return (
        "nwdes "
        + kind
        + " "
        + verb.name
        + " "
        + " ".join(
            argument(field)
            for field in verb.fields
            if field.required
            or field.name == scope[0]
            or (kind == "craft" and verb.name == "close" and field.name == "role")
            or field.name in selectors
            or field.alternative in alternatives
        )
    )


def _role_commands(kind, policy=None):
    return tuple(
        Command(
            kind,
            verb.name,
            "Close the design draft. Retain accepted ADRs through design adr add --key KEY with unchanged body; replace explicitly with --supersedes KEY and an Accepted successor."
            if kind == "design" and verb.name == "close"
            else "Revise authority that is already published with open --from-current, never as the first call of a first recording; the first add/set/remove creates the draft."
            if verb.name == "open"
            else "Link this slice to existing Request promises; --promise is required and repeatable. Add a justified promise with nwdes product promise add, or split unrelated outcomes into a separate nwdes feature new."
            if kind == "product" and verb.name in ("slice add", "slice set")
            else "Record role values through nwdes-owned drafts.",
            tuple(
                Argument(
                    "--" + field.name,
                    ROOT_DEFAULTS.get(field.name)
                    or (
                        (
                            "required; "
                            if field.required
                            else "optional; omitted leaves the field absent or its collection empty; "
                        )
                        + (
                            ", ".join(field.choices)
                            if field.choices
                            else field.spec.kind
                        )
                    )
                    + ("; repeatable" if field.repeated else "")
                    + (
                        "; also accepts --" + field.name + "-file PATH"
                        if field.text
                        else ""
                    ),
                )
                for field in verb.fields
            ),
            (
                *ROLE_REFUSALS,
                *(
                    DESIGN_REFUSALS
                    if kind == "design" and verb.name == "close"
                    else (
                        (
                            "UncoveredPromise",
                            "the revised set leaves a promise without an expectation",
                        ),
                    )
                    if kind == "expectations" and verb.name == "close"
                    else (
                        (
                            "UncitedVerdict",
                            "a verdict cites no recorded observation; record it with examine observation add and cite --observation",
                        ),
                    )
                    if kind == "examine" and verb.name == "close"
                    else ()
                ),
            ),
            _role_example(kind, verb),
        )
        for verb in drafts.role_verbs(kind, policy)
    )


_FIXED_COMMANDS = COMMANDS


_RECORDS_HELD: dict[int, tuple[object, tuple]] = {}


def _role_records(policy=None):
    """The role command records under one policy, built once per distinct policy."""
    held = _RECORDS_HELD.get(id(policy))
    if held is not None and held[0] is policy:
        return held[1]
    built = tuple(
        command
        for kind in drafts.KINDS
        for command in (
            *_role_commands(kind, policy),
            *(EXAMINATION_COMMANDS if kind == "examine" else ()),
        )
    )
    _RECORDS_HELD[id(policy)] = (policy, built)
    return built


COMMANDS = (*_FIXED_COMMANDS, *_role_records())


def help_text(
    verb: str | None = None, action: str | None = None, policy=None
) -> Built[str] | Refused:
    records = tuple(
        record
        for record in (*_FIXED_COMMANDS, *_role_records(policy))
        if verb is None or record.verb == verb
    )
    if not records:
        return refuse(
            f"InconsistentFacts: unknown verb {verb}",
            "No command grammar record names this verb.",
            "Use nwdes --help to choose a declared verb.",
        )
    if action is not None:
        records = tuple(record for record in records if record.action == action)
        if not records:
            return refuse(
                f"InconsistentFacts: unknown action {action}",
                f"No command grammar record names this action for {verb}.",
                f"Use nwdes {verb} --help to choose a declared action.",
            )
    if verb is None or (action is None and records[0].action is not None):
        return Built("".join(record.summary + "\n" for record in records))
    record = records[0]
    return Built(
        "\n".join(
            (
                record.summary,
                "Arguments:",
                *(f"{a.flag}  {a.meaning}" for a in record.arguments),
                "Refusals:",
                *(f"{name}  {condition}" for name, condition in record.refusals),
                f"Example: {record.example}",
            )
        )
        + "\n"
    )


_INSPECTION_FORMS = {
    "--workspace": "--workspace W",
    "PATH": "[PATH]",
    "-- ARGV": "-- ARGV",
}


def _inspection_signature(command):
    return " ".join(
        (
            "nwdes",
            command.verb,
            command.action,
            *(_INSPECTION_FORMS[argument.flag] for argument in command.arguments),
        )
    )


def commit_example(scope, role):
    """The registry's commit form, addressed to a bundle's scope and owning role."""
    record = next(command for command in COMMANDS if command.verb == "commit")
    tokens = shlex.split(record.example)[2:]
    flags = dict(zip(tokens[::2], tokens[1::2], strict=True))
    return " ".join(
        (
            "nwdes commit",
            "--" + scope[0],
            shlex.quote(scope[1]),
            "--role",
            shlex.quote(role),
            "--type",
            shlex.quote(flags["--type"]),
            "--description",
            "Value",
        )
    )


def describe(kind, handoff=None, role=None, policy=None):
    """Render role verbs and their worked examples from the table the CLI parses."""
    if kind == "craft" and role is not None and role not in drafts.CRAFT_ACTOR.members:
        raise ValueError("A craft reference requires one of its two crafter roles.")
    roles = {
        "product": "nw-product-owner --task discuss",
        "charter": "nw-product-owner --task charter",
        "design": "nw-solution-architect",
        "acceptance": "nw-acceptance-designer",
        "expectations": "nw-user-examiner --task expectations",
        "examine": "nw-user-examiner --task examine",
        "craft": "Crafters",
        "review": "Reviewers",
    }
    scope = ("feature", "feature-id")

    def argument(field):
        if kind == "craft" and field.name == "role" and role is not None:
            return "--role " + role
        value = (
            " {" + ",".join(field.choices) + "}"
            if field.choices
            else ""
            if field.spec.kind == "boolean"
            else " "
            + {"text": "T", "line": "L", "command": "C", "integer": "N"}.get(
                field.spec.kind, "ID"
            )
        )
        text = (
            "--"
            + field.name
            + value
            + ("..." if field.repeated else "")
            + ("@" + field.alternative if field.alternative else "")
        )
        return text if field.required else "[" + text + "]"

    verbs = drafts.role_verbs(kind, policy)
    if not verbs:
        return ""
    roots = frozenset(drafts.ROOT_NAMES)
    fields = tuple(field for verb in verbs for field in verb.fields)
    field_kinds = frozenset(field.spec.kind for field in fields)
    names = frozenset(field.name for field in fields)
    additions = {verb.record: verb for verb in verbs if verb.action == "add"}

    def signature(verb):
        inherited = additions.get(verb.record) if verb.action == "set" else None
        shared = (
            frozenset(field.name for field in inherited.fields)
            if inherited
            else frozenset()
        )
        return (
            verb.name
            + " "
            + " ".join(
                argument(field)
                for field in verb.fields
                if field.name not in roots and field.name not in shared
            )
            + ("; fields as " + inherited.name if inherited else "")
        )

    legend = "; ".join(
        text
        for field_kind, text in (
            ("text", "T=text; --FIELD-file PATH reads literal UTF-8"),
            ("line", "L=line"),
            ("identity", "ID=lowercase id with digits and hyphens"),
            ("command", "C=single-line shlex command"),
            ("integer", "N=integer"),
        )
        if field_kind in field_kinds
    )
    inspection = (
        (
            "INSPECT (take --workspace only; not ROOTS):",
            *(_inspection_signature(command) for command in EXAMINATION_COMMANDS),
        )
        if kind == "examine"
        else ()
    )
    examples = (
        *(_role_example(kind, verb, scope, role) for verb in verbs),
        *(command.example for command in EXAMINATION_COMMANDS if kind == "examine"),
    )
    return (
        "## ROLE VERBS\n"
        + roles.get(kind, kind)
        + "\n"
        + "nwdes "
        + kind
        + " VERB ROOTS\nROOTS: "
        + " ".join(argument(field) for field in verbs[0].fields if field.name in roots)
        + "\nSCOPE: every recording verb needs --feature ID or --epic ID."
        + "\n"
        + legend
        + (
            "; --at/--model are 1-based"
            if "model" in names
            else "; --at is 1-based"
            if "at" in names
            else ""
        )
        + ("; ...=repeat" if any(field.repeated for field in fields) else "")
        + (
            "\n@X: only for alternative X; omit other alternatives' flags."
            if any(field.alternative for field in fields)
            else ""
        )
        + ("\nPLACE: exactly one of --shared or --in ID." if kind == "design" else "")
        + "\n"
        + "\n".join(map(signature, verbs))
        + "".join("\n" + line for line in inspection)
        + ("\n\n" + PRODUCT_VALUE_AUDIT if kind == "product" else "")
        + "\n\n## WORKED EXAMPLES\n"
        + "\n".join(examples)
    )
