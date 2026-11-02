"""Git's argv-only process boundary and read-only lane observations."""

import re
import subprocess
from pathlib import Path

from nwdes import documents, handoff, lanes
from nwdes.contracts import Built, Defect
from nwdes.shell.ports import GitResult, Unreadable


def run_git(
    root: str | None, arguments: tuple[str, ...], *, env=None
) -> GitResult | Unreadable:
    try:
        result = subprocess.run(
            ["git", *arguments], cwd=root, env=env, capture_output=True, check=False
        )
        return GitResult(result.returncode, result.stdout, result.stderr)
    except OSError as error:
        return Unreadable("git " + " ".join(arguments), str(error))


def scrubbed_env(environ):
    return {
        name: value for name, value in environ.items() if not name.startswith("GIT_")
    }


def failure_reason(result):
    if isinstance(result, Unreadable):
        return f"git could not start: {result.reason}."
    message = result.stderr.decode("utf-8", "replace").rstrip()
    return (
        f"git exited {result.code}: {message}"
        if message
        else f"git exited {result.code} with no message."
    )


def _available(value):
    return not isinstance(value, handoff.UnavailableInput)


class _Inspection:
    def __init__(self, root, observed):
        self.root = root
        self.observed = observed
        self.failures = []

    def unavailable(self, step, reason):
        self.failures.append(Unreadable(step, reason))
        return handoff.UnavailableInput(
            Defect(
                "InputUnreadable: " + step,
                reason,
                "Make this git query available before retrying the lane verb.",
            )
        )

    def query(self, *arguments, allowed=(0,), cwd=None, strip=True):
        result = run_git(cwd or self.root, arguments)
        step = "git " + " ".join(arguments)
        if isinstance(result, Unreadable):
            return self.unavailable(step, failure_reason(result))
        if result.code not in allowed:
            return self.unavailable(step, failure_reason(result))
        if result.code:
            return None
        text = result.stdout.decode("utf-8", "surrogateescape")
        return text.removesuffix("\n") if strip else text

    def tree_entries(self, tree, directory):
        listing = self.query("ls-tree", "-r", "-z", tree, "--", directory, strip=False)
        if not _available(listing):
            return listing
        return {
            name: metadata.split()[2]
            for row in listing.split("\x00")
            if row
            for metadata, name in (row.split("\t", 1),)
            if documents.parse_adr_filename(name.rsplit("/", 1)[-1]) is not None
        }

    def tree_files(self, entries):
        if not _available(entries):
            return entries
        files = {}
        for name, identity in entries.items():
            data = self.query("cat-file", "blob", identity, strip=False)
            files[name] = (
                data.encode("utf-8", "surrogateescape") if _available(data) else data
            )
        return files

    def integrate(self, flags):
        observed = self.observed
        observed["head"] = self.query("symbolic-ref", "-q", "HEAD", allowed=(0, 1))
        observed["rootstatus"] = _status_entries(
            self.query(
                "status", "--porcelain", "-z", "--untracked-files=all", strip=False
            )
        )
        if lanes.commit_valid(flags.get("candidate")):
            observed["candidate"] = self.query(
                "rev-parse",
                "--verify",
                "-q",
                flags["candidate"] + "^{commit}",
                allowed=(0, 1),
            )
        candidate = observed.get("candidate")
        if (
            lanes.commit_valid(flags.get("expected"))
            and candidate is not None
            and _available(candidate)
        ):
            answer = self.query(
                "merge-base",
                "--is-ancestor",
                flags["expected"],
                candidate,
                allowed=(0, 1),
            )
            observed["descends"] = answer is not None if _available(answer) else answer

    def worktree(self, feature, verb, config, path):
        observed = self.observed
        listing = self.query("worktree", "list", "--porcelain", "-z", strip=False)
        branch = self.query(
            "rev-parse", "--verify", "-q", "refs/heads/lane/" + feature, allowed=(0, 1)
        )
        if not _available(listing) or not _available(branch):
            observed["lane"] = listing if not _available(listing) else branch
            return
        worktree = any(
            "worktree " + str(path) in block.split("\x00")
            and "branch refs/heads/lane/" + feature in block.split("\x00")
            for block in listing.split("\x00\x00")
            if block
        )
        try:
            present = path.exists() or path.is_symlink()
        except OSError as error:
            observed["lane"] = self.unavailable(str(path), str(error))
            return
        observed["lane"] = {
            "path": "worktree" if worktree else "other" if present else None,
            "branch": branch,
        }
        if worktree and verb in ("compose", "integrate"):
            observed["status"] = _status_entries(
                self.query(
                    "status",
                    "--porcelain",
                    "-z",
                    "--untracked-files=all",
                    *(("--ignored",) if verb == "integrate" else ()),
                    cwd=str(path),
                    strip=False,
                )
            )
        trunk = observed.get("trunk")
        candidate = observed.get("candidate")
        if (
            verb == "integrate"
            and branch is not None
            and candidate is not None
            and _available(candidate)
        ):
            answer = self.query(
                "merge-base", "--is-ancestor", branch, candidate, allowed=(0, 1)
            )
            observed["lane_in_candidate"] = (
                answer is not None if _available(answer) else answer
            )
        if (
            worktree
            and verb in ("compose", "rekey")
            and trunk is not None
            and _available(trunk)
        ):
            self.composition(verb, branch, trunk, config)

    def composition(self, verb, tip, trunk, config):
        observed = self.observed
        base = self.query("merge-base", trunk, tip)
        observed["base"] = base
        directory = config.get("adr.directory", "docs/product/architecture")
        if isinstance(directory, str):
            trunk_entries = (
                self.tree_entries(trunk, directory) if verb == "rekey" else None
            )
            trunk_files = self.tree_files(trunk_entries) if verb == "rekey" else None
            if _available(base):
                base_entries = self.tree_entries(base, directory)
                if _available(base_entries):
                    if verb != "rekey":
                        trunk_entries = self.tree_entries(trunk, directory)
                    lane_entries = self.tree_entries(tip, directory)
                    sides = {}
                    for side, entries in (
                        ("trunk", trunk_entries),
                        ("lane", lane_entries),
                    ):
                        if _available(entries):
                            if side == "trunk" and verb == "rekey":
                                files = {
                                    name: data
                                    for name, data in trunk_files.items()
                                    if name not in base_entries
                                }
                            else:
                                files = self.tree_files(
                                    {
                                        name: identity
                                        for name, identity in entries.items()
                                        if name not in base_entries
                                    }
                                )
                            sides[side] = documents.added_adrs(base_entries, files)
                        else:
                            sides[side] = entries
                    observed["adds"] = sides
                else:
                    observed["adds"] = base_entries
            if verb == "rekey":
                observed["trunk_register"] = (
                    tuple(
                        entry
                        for name, data in trunk_files.items()
                        for entry in (
                            documents.read_adr({name.rsplit("/", 1)[-1]: data}).value
                            if _available(data)
                            else (data,)
                        )
                    )
                    if _available(trunk_files)
                    else trunk_files
                )
        if verb == "compose":
            self.merged(tip, trunk, directory)

    def merged(self, tip, trunk, directory):
        result = run_git(
            self.root, ("merge-tree", "--write-tree", "--name-only", "-z", tip, trunk)
        )
        if isinstance(result, Unreadable) or result.code not in (0, 1):
            reason = (
                result.reason
                if isinstance(result, Unreadable)
                else result.stderr.decode("utf-8", "replace")
            )
            self.observed["merge"] = self.unavailable(
                "git merge-tree --write-tree", reason
            )
            return
        records = result.stdout.decode("utf-8", "surrogateescape").split("\x00")
        tree = records[0]
        paths = records[1 : records.index("", 1)] if result.code else ()
        merged = {"conflicts": tuple(paths)}
        if isinstance(directory, str):
            entries = self.tree_entries(tree, directory)
            if _available(entries):
                keys = {}
                for name in entries:
                    key = documents.parse_adr_filename(name.rsplit("/", 1)[-1])
                    keys.setdefault(key.text, []).append(name)
                merged["adr"] = keys
            else:
                merged["adr"] = entries
        self.observed["merge"] = merged


def observe_lane(root, feature, verb, config, flags):
    observed = {"config": config}
    version = run_git(root if root and Path(root).is_dir() else None, ("--version",))
    match = (
        re.search(rb"git version (\d+)\.(\d+)", version.stdout)
        if isinstance(version, GitResult) and version.code == 0
        else None
    )
    observed["git"] = tuple(map(int, match.groups())) if match else None
    if observed["git"] is None or observed["git"] < (2, 38) or root is None:
        return observed, ()
    if not Path(root).is_dir():
        observed["toplevel"] = False
        return observed, ()
    inspection = _Inspection(root, observed)
    top = inspection.query("rev-parse", "--show-toplevel", allowed=(0, 128))
    common = (
        inspection.query("rev-parse", "--git-common-dir", allowed=(0, 128))
        if top is not None and _available(top)
        else top
    )
    if not _available(top) or not _available(common):
        observed["toplevel"] = top if not _available(top) else common
        return observed, tuple(inspection.failures)
    try:
        base = Path(root).resolve()
        observed["toplevel"] = bool(
            top is not None
            and Path(top).resolve() == base
            and common is not None
            and (base / common).resolve() == (base / ".git").resolve()
            and (base / ".git").is_dir()
        )
    except (OSError, RuntimeError) as error:
        observed["toplevel"] = handoff.UnavailableInput(
            Defect(
                "LaneOutsideProject: --repo-root",
                str(error),
                "Supply a resolvable main worktree root.",
            )
        )
        return observed, tuple(inspection.failures)
    if not observed["toplevel"]:
        return observed, tuple(inspection.failures)
    trunk = config.get("lanes.trunk")
    if lanes.branch_valid(trunk):
        observed["trunk"] = inspection.query(
            "rev-parse", "--verify", "-q", "refs/heads/" + trunk, allowed=(0, 1)
        )
    scope = handoff.build_scope("Feature", feature)
    path = None
    if isinstance(scope, Built):
        try:
            parent = (base / "lanes").resolve()
            path = (base / "lanes" / feature).resolve()
            observed["lane_outside"] = not parent.is_relative_to(
                base
            ) or not path.is_relative_to(base)
        except (OSError, RuntimeError) as error:
            observed["lane_outside"] = handoff.UnavailableInput(
                Defect(
                    "LaneOutsideProject: lanes/" + feature,
                    str(error),
                    "Use a lane path without cyclic or unreadable symlinks.",
                )
            )
    if verb == "integrate":
        inspection.integrate(flags)
    if path is not None and observed.get("lane_outside") is False:
        inspection.worktree(feature, verb, config, path)
    return observed, tuple(inspection.failures)


def _status_entries(raw):
    if not _available(raw):
        return raw
    records = iter(raw.split("\x00"))
    entries = []
    for record in records:
        if not record:
            continue
        code, path = record[:2], record[3:]
        entries.append((code, path))
        if "R" in code or "C" in code:
            next(records, None)
    return tuple(entries)
