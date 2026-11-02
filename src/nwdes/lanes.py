"""Pure lane admission over read-only observations; effects consume admitted plans."""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from fnmatch import fnmatchcase

from nwdes import documents, handoff
from nwdes.contracts import Built, Defect, Refused, checked
from nwdes.destinations import local_path, parse_lane_setting


@dataclass(frozen=True)
class LaneLocation:
    root: str
    feature: str

    @property
    def path(self):
        return "lanes/" + self.feature

    @property
    def branch(self):
        return "lane/" + self.feature


@dataclass(frozen=True)
class OpenPlan:
    location: LaneLocation
    trunk: str
    present: bool


@dataclass(frozen=True)
class ComposePlan:
    location: LaneLocation
    trunk: str
    expected: str


@dataclass(frozen=True)
class RekeyPlan:
    location: LaneLocation
    key: str


@dataclass(frozen=True)
class Candidate:
    expected: str
    tip: str


@dataclass(frozen=True)
class Checkout:
    root: str
    branch: str


@dataclass(frozen=True)
class Disposable:
    path: str
    pattern: str


@dataclass(frozen=True)
class IntegrationPlan:
    checkout: Checkout
    candidate: Candidate
    location: LaneLocation
    disposable: tuple[Disposable, ...]
    worktree: bool
    branch: str | None
    already_integrated: bool


LanePlan = OpenPlan | ComposePlan | RekeyPlan | IntegrationPlan


@dataclass(frozen=True)
class Merged:
    commit: str


def integrated(
    candidate: Candidate, observed: str, root: str = "ROOT", feature: str = "F"
) -> Built[Merged] | Refused:
    confirmed = checked(
        None,
        ()
        if observed == candidate.tip
        else (
            problem(
                "IntegrationMismatch",
                observed,
                f"Observed trunk {observed}; expected candidate {candidate.tip}.",
                "Inspect the trunk, rerun nwdes lane compose "
                f"--repo-root {root} --feature {feature}, then rerun nwdes lane integrate "
                f"--repo-root {root} --feature {feature} --expected EXPECTED "
                "--candidate CANDIDATE with the two values it prints.",
            ),
        ),
    )
    return confirmed if isinstance(confirmed, Refused) else Built(Merged(observed))


def _available(value):
    return not isinstance(value, (handoff.UnavailableInput, Refused))


def _produced(observed, name):
    return name in observed and _available(observed[name])


def observation_defects(value):
    if isinstance(value, handoff.UnavailableInput):
        return (value.defect,)
    if isinstance(value, Refused):
        return value.defects
    if isinstance(value, Defect):
        return (value,)
    children = (
        value.values()
        if isinstance(value, Mapping)
        else value
        if isinstance(value, (tuple, list))
        else ()
    )
    return tuple(defect for child in children for defect in observation_defects(child))


def _finalization(lane, observed, disposable, candidate):
    worktree = lane is not None and lane.get("path") == "worktree"
    branch = lane is not None and lane.get("branch") is not None
    merged = (
        (
            problem(
                "LaneNotMerged",
                "",
                "The lane tip is not contained in CANDIDATE.",
                "Run nwdes lane compose again and integrate with the two values it prints.",
            ),
        )
        if branch
        and isinstance(candidate, Built)
        and _produced(observed, "candidate")
        and bool(observed["candidate"])
        and _produced(observed, "lane_in_candidate")
        and not observed["lane_in_candidate"]
        else ()
    )
    status = (
        tuple(observed["status"]) if worktree and _produced(observed, "status") else ()
    )
    classified = (
        tuple(
            (
                path,
                next(
                    (
                        pattern
                        for pattern in disposable.value
                        if fnmatchcase(
                            path, pattern + "*" if pattern.endswith("/") else pattern
                        )
                    ),
                    None,
                ),
            )
            for code, path in status
            if code in ("??", "!!")
        )
        if isinstance(disposable, Built)
        else ()
    )
    undeclared = tuple(
        problem(
            "LaneFileUndeclared",
            path,
            "No project disposable pattern covers this file.",
            "If this file is user work, move it outside the lane and rerun the same lane "
            "integrate. If it belongs to the project, commit it in the lane, run nwdes lane "
            "compose again and integrate with the two values it prints. Only if it is "
            "intentionally safe to delete, merge "
            '{"lanes": {"disposable": ["PATTERN"]}} into ROOT/.nwave/config.json in the '
            "main worktree passed as --repo-root, preserving all other settings, lanes.trunk "
            "and existing patterns, commit that change on trunk, run nwdes lane compose "
            "again and integrate with the two values it prints. PATTERN is a deliberate "
            "lane-worktree-relative POSIX path pattern, not prefixed with lanes/FEATURE; "
            "one list entry per pattern. lane integrate deletes matching paths and removes "
            "the lane; no patterns are built in. Never "
            "declare user work disposable merely to finish.",
        )
        for path, pattern in classified
        if pattern is None
    )
    return checked(
        (classified, worktree, branch),
        (*merged, *_tracked(status, "LaneUncommitted"), *undeclared),
    )


def _integration(flags, observed, repository, trunk, trunk_tip):
    expected = _flag(flags, "expected", commit_valid)
    candidate = _flag(flags, "candidate", commit_valid)
    resolved = (
        checked(
            observed.get("candidate"),
            ()
            if observed.get("candidate")
            else (
                problem(
                    "DanglingReference",
                    "--candidate",
                    "The candidate is not a commit in this repository.",
                    "Supply a full existing commit id from lane compose.",
                ),
            ),
        )
        if isinstance(repository, Built)
        and isinstance(candidate, Built)
        and _produced(observed, "candidate")
        else None
    )
    checkout = (
        (
            problem(
                "NotOnTrunk",
                "",
                f"Root HEAD is {observed.get('head')}, not refs/heads/{trunk.value}.",
                "Check out the declared trunk in the repository root.",
            ),
        )
        if isinstance(repository, Built)
        and isinstance(trunk, Built)
        and _produced(observed, "head")
        and observed.get("head") != "refs/heads/" + trunk.value
        else ()
    )
    dirty = (
        tuple(
            problem(
                "TrunkDirty",
                path,
                "The root worktree has uncommitted changes.",
                "Commit or restore the root worktree before integrating.",
            )
            for _, path in observed.get("rootstatus", ())
        )
        if isinstance(repository, Built) and _produced(observed, "rootstatus")
        else ()
    )
    moved = (
        (
            problem(
                "TrunkMoved",
                "",
                f"Expected {expected.value}; observed {trunk_tip.value}.",
                "Run nwdes lane compose again and use its EXPECTED and CANDIDATE values.",
            ),
        )
        if isinstance(expected, Built)
        and isinstance(trunk_tip, Built)
        and trunk_tip.value
        not in (
            expected.value,
            candidate.value if isinstance(candidate, Built) else None,
        )
        else ()
    )
    forward = (
        (
            problem(
                "NotFastForward",
                "",
                "The candidate does not descend from the expected commit.",
                "Run nwdes lane compose again before integrating.",
            ),
        )
        if isinstance(repository, Built)
        and isinstance(expected, Built)
        and isinstance(resolved, Built)
        and _produced(observed, "descends")
        and not observed.get("descends")
        else ()
    )
    return checked(
        (expected, resolved),
        (*_defects(expected, candidate, resolved), *checkout, *dirty, *moved, *forward),
    )


def _rekey_checks(flags, observed, exists, trunk_tip, adr):
    key = _flag(flags, "key", _adr_key_valid)
    entries = (
        tuple(observed.get("register", ()))
        if isinstance(exists, Built)
        and isinstance(adr, Built)
        and _produced(observed, "register")
        else None
    )
    keys = (
        tuple(dict.fromkeys(entry[0] for entry in entries))
        if entries is not None
        else ()
    )
    target = (
        tuple(row for row in entries if row[0] == key.value)
        if entries is not None and isinstance(key, Built)
        else None
    )
    register_problems = (
        (
            problem(
                "AdrKeyClash",
                key.value,
                ", ".join(row[1] for row in target),
                "Keep one ADR file for the selected key.",
            ),
        )
        if target is not None and len(target) > 1
        else (
            problem(
                "AdrForeignLayout",
                key.value,
                "The selected ADR file does not have the supported layout.",
                "Migrate this ADR to the nwdes layout before rekeying.",
            ),
        )
        if target and target[0][2] is False
        else ()
    )
    missing = (
        (
            problem(
                "DanglingReference",
                "--key",
                "The lane register has no ADR for this key.",
                "Supply the key of an ADR present in the lane.",
            ),
        )
        if target == ()
        else ()
    )
    own = (
        (
            problem(
                "InconsistentFacts",
                "--key",
                "The lane did not add this key since the merge base.",
                "Rekey only an ADR added by this lane.",
            ),
        )
        if isinstance(key, Built)
        and isinstance(exists, Built)
        and isinstance(trunk_tip, Built)
        and isinstance(adr, Built)
        and _produced(observed, "base")
        and _produced(observed, "adds")
        and _produced(observed["adds"], "lane")
        and key.value not in observed.get("adds", {}).get("lane", {})
        else ()
    )
    superseded = (
        tuple(
            problem(
                "DanglingReference",
                predecessor,
                "The superseded ADR is absent from the lane register.",
                "Restore the superseded ADR before rekeying.",
            )
            for predecessor in observed.get("supersedes", {}).get(key.value, ())
            if predecessor not in keys
        )
        if target and len(target) == 1 and target[0][2] is True
        else ()
    )
    return (*_defects(key), *register_problems, *missing, *own, *superseded)


def _previous_checks(flags, inspection, exists, ready):
    previous = (
        (
            (
                problem(
                    "FeatureUnknown",
                    flags["feature"],
                    "The lane has no feature handoff.",
                    "Run nwdes feature new inside the lane.",
                ),
            )
            if inspection is None
            else inspection.result.defects
            if isinstance(inspection.result, Refused)
            else ()
        )
        if isinstance(exists, Built) and ready
        else ()
    )
    return previous


def _adr_key_valid(value):
    key = (
        documents.parse_adr_filename("ADR-" + value + ".md")
        if isinstance(value, str)
        else None
    )
    return key is not None and key.text == value


def problem(kind, subject, why, how):
    return Defect(f"{kind}: {subject}", why, how)


def _feature(flags):
    supplied = _flag(flags, "feature")
    if isinstance(supplied, Refused):
        return supplied
    scope = handoff.build_scope("Feature", supplied.value)
    return (
        checked(
            None,
            (
                problem(
                    "LaneOutsideProject",
                    "--feature",
                    "The value is not a valid feature id.",
                    "Supply a lowercase feature id with digits and hyphens.",
                ),
            ),
        )
        if isinstance(scope, Refused)
        else scope
    )


def branch_valid(value):
    return (
        isinstance(value, str)
        and bool(value)
        and not value.startswith(("-", "/"))
        and not value.endswith(("/", "."))
        and not any(
            ord(character) < 33 or ord(character) == 127 or character in "~^:?*[\\"
            for character in value
        )
        and ".." not in value
        and "@{" not in value
        and all(
            part and not part.startswith(".") and not part.endswith(".lock")
            for part in value.split("/")
        )
    )


def commit_valid(value):
    return (
        isinstance(value, str)
        and re.fullmatch(r"[0-9a-fA-F]{40}|[0-9a-fA-F]{64}", value) is not None
    )


def configuration(config):
    """Retain one result per configuration key, including failed siblings."""
    values = (
        ("lanes.trunk", config.get("lanes.trunk")),
        ("lanes.disposable", config.get("lanes.disposable", ())),
        ("adr.directory", config.get("adr.directory", "docs/product/architecture")),
    )
    parsed = tuple(
        None
        if not _available(value)
        else checked(
            None,
            (
                problem(
                    "LaneTrunkUndeclared",
                    key,
                    "The project has no declared trunk.",
                    "Create or update .nwave/config.json under the main worktree passed as "
                    '--repo-root, preserving other settings, with {"lanes": {"trunk": "BRANCH"}}. '
                    "Replace BRANCH with the repository's intended existing trunk branch "
                    "(for example main), then retry this lane command.",
                ),
            ),
        )
        if key == "lanes.trunk" and key not in config
        else parse_lane_setting("lane configuration", key, value)
        if key.startswith("lanes.")
        else checked(
            value,
            ()
            if local_path(value)
            else (
                problem(
                    "ConfigurationMalformed",
                    key,
                    "The configuration value is not a repository-relative directory.",
                    "Declare adr.directory as a repository-relative path.",
                ),
            ),
        )
        for key, value in values
    )
    trunk = parsed[0]
    branch = (
        checked(
            None,
            (
                problem(
                    "ConfigurationMalformed",
                    "lanes.trunk",
                    "The trunk value is not a valid Git branch name.",
                    "Declare a branch name without forbidden characters.",
                ),
            ),
        )
        if isinstance(trunk, Built) and not branch_valid(trunk.value)
        else trunk
    )
    return branch, *parsed[1:]


def _flag(flags, name, predicate=lambda value: True, kind="PartInvalid"):
    value = flags.get(name)
    return checked(
        value,
        (
            problem(
                "MissingFact",
                "--" + name.replace("_", "-"),
                "The required flag is absent.",
                "Supply --" + name.replace("_", "-") + ".",
            ),
        )
        if value is None
        else ()
        if predicate(value)
        else (
            problem(
                kind,
                "--" + name.replace("_", "-"),
                "The supplied value cannot identify this lane input.",
                "Supply a valid --" + name.replace("_", "-") + " value.",
            ),
        ),
    )


def _defects(*results):
    return tuple(
        defect
        for result in results
        if isinstance(result, Refused)
        for defect in result.defects
    )


def _exists(lane):
    return (
        checked(
            lane,
            ()
            if lane.get("path") == "worktree" and lane.get("branch")
            else (
                problem(
                    "DanglingReference",
                    "--feature",
                    "No worktree for this feature is open on its lane branch.",
                    "Run nwdes lane open for this feature.",
                ),
            ),
        )
        if lane is not None
        else None
    )


def _tracked(status, kind):
    return tuple(
        problem(
            kind,
            path,
            "The worktree has an uncommitted tracked change.",
            "Commit or restore this path with git before retrying.",
        )
        for code, path in status
        if code not in ("??", "!!")
    )


def _compose_checks(observed, exists, trunk_tip, adr):
    clean = (
        _tracked(observed["status"], "LaneUncommitted")
        if isinstance(exists, Built) and _produced(observed, "status")
        else ()
    )
    can_merge = isinstance(exists, Built) and isinstance(trunk_tip, Built)
    merge = observed["merge"] if _produced(observed, "merge") else {}
    conflicts = (
        tuple(
            problem(
                "MergeConflict",
                path,
                "The read-only merge found conflicting changes.",
                "Resolve the changes on the lane and commit them before composing.",
            )
            for path in merge["conflicts"]
        )
        if can_merge and _produced(merge, "conflicts")
        else ()
    )
    adds = observed["adds"] if _produced(observed, "adds") else {}
    taken = (
        tuple(
            problem(
                "AdrKeyTaken",
                key,
                "Trunk and lane added different bodies at the same ADR key.",
                f"Run nwdes lane rekey --key {key} for this feature.",
            )
            for key, body in adds["trunk"].items()
            if key in adds["lane"]
            and _available(body)
            and _available(adds["lane"][key])
            and not documents.adr_body_equal(key, body, adds["lane"][key])
        )
        if can_merge
        and isinstance(adr, Built)
        and _produced(observed, "base")
        and _produced(adds, "trunk")
        and _produced(adds, "lane")
        else ()
    )
    clashes = (
        tuple(
            problem(
                "AdrKeyClash",
                key,
                ", ".join(paths),
                "Keep one ADR file for each key before composing.",
            )
            for key, paths in merge["adr"].items()
            if len(paths) > 1
        )
        if can_merge and isinstance(adr, Built) and _produced(merge, "adr")
        else ()
    )
    return (*clean, *taken, *conflicts, *clashes)


def prepare_lane(verb, flags, observed, inspection=None) -> Built[LanePlan] | Refused:
    root = _flag(flags, "repo_root")
    feature = _feature(flags)
    version = observed.get("git")
    git = checked(
        version,
        ()
        if version is not None and tuple(version) >= (2, 38)
        else (
            problem(
                "GitUnavailable",
                verb,
                "Git 2.38 or newer could not be found.",
                "Install git >= 2.38 on PATH.",
            ),
        ),
    )
    repository = (
        checked(
            None,
            ()
            if observed.get("toplevel")
            else (
                problem(
                    "LaneOutsideProject",
                    "--repo-root",
                    "The root is not the main worktree's repository top level.",
                    "Supply the main worktree top level as --repo-root.",
                ),
            ),
        )
        if isinstance(root, Built)
        and isinstance(git, Built)
        and _produced(observed, "toplevel")
        else None
    )
    settings = (
        configuration(observed.get("config", {}))
        if isinstance(root, Built)
        else (None, None, None)
    )
    trunk, disposable, adr = settings
    trunk_tip = (
        checked(
            observed.get("trunk"),
            ()
            if observed.get("trunk")
            else (
                problem(
                    "DanglingReference",
                    "lanes.trunk",
                    "The declared trunk branch does not exist.",
                    "Create the declared trunk branch with git.",
                ),
            ),
        )
        if isinstance(repository, Built)
        and isinstance(trunk, Built)
        and _produced(observed, "trunk")
        else None
    )
    location = (
        LaneLocation(root.value, feature.value.id)
        if isinstance(root, Built) and isinstance(feature, Built)
        else None
    )
    confined = (
        checked(
            None,
            (
                problem(
                    "LaneOutsideProject",
                    location.path,
                    "The resolved lane path leaves the repository.",
                    "Choose an in-project lane path without an external symlink.",
                ),
            )
            if observed.get("lane_outside")
            else (),
        )
        if isinstance(repository, Built)
        and isinstance(feature, Built)
        and _produced(observed, "lane_outside")
        else None
    )
    lane = (
        observed["lane"]
        if isinstance(confined, Built) and _produced(observed, "lane")
        else None
    )
    common = (
        *_defects(root, feature, git, repository, confined, *settings, trunk_tip),
        *observation_defects(observed),
    )
    if verb == "integrate":
        candidate = _integration(flags, observed, repository, trunk, trunk_tip)
        cleanup = _finalization(
            lane, observed, disposable, _flag(flags, "candidate", commit_valid)
        )
        admitted = checked(None, (*common, *_defects(candidate, cleanup)))
        if isinstance(admitted, Refused):
            return admitted
        expected, resolved = candidate.value
        classified, worktree, branch = cleanup.value
        return Built(
            IntegrationPlan(
                Checkout(root.value, trunk.value),
                Candidate(expected.value, resolved.value),
                location,
                tuple(Disposable(path, pattern) for path, pattern in classified),
                worktree,
                lane["branch"] if branch else None,
                trunk_tip.value == resolved.value,
            )
        )
    if verb == "open":
        occupied = (
            (
                problem(
                    "LaneOccupied",
                    location.path if lane.get("path") else location.branch,
                    "The lane path or branch is occupied by something other than this lane.",
                    "Use a free feature id or remove the unrelated occupant yourself.",
                ),
            )
            if lane is not None
            and (
                lane.get("path") == "other"
                or (lane.get("path") is None and lane.get("branch") is not None)
            )
            else ()
        )
        admitted = checked(None, (*common, *occupied))
        return (
            admitted
            if isinstance(admitted, Refused)
            else Built(OpenPlan(location, trunk.value, lane.get("path") == "worktree"))
        )
    exists = _exists(lane)
    if verb == "rekey":
        admitted = checked(
            None,
            (
                *common,
                *_defects(exists),
                *_rekey_checks(flags, observed, exists, trunk_tip, adr),
                *_previous_checks(
                    flags, inspection, exists, observed.get("previous_ready", True)
                ),
            ),
        )
        return (
            admitted
            if isinstance(admitted, Refused)
            else Built(RekeyPlan(location, flags["key"]))
        )
    admitted = checked(
        None,
        (
            *common,
            *_defects(exists),
            *_compose_checks(observed, exists, trunk_tip, adr),
        ),
    )
    return (
        admitted
        if isinstance(admitted, Refused)
        else Built(ComposePlan(location, trunk.value, trunk_tip.value))
    )
