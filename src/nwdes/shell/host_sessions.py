"""Read-only native session, repository and published-record adapters."""

import re
from pathlib import Path

from nwdes import measurement
from nwdes.contracts import Built, Defect, Refused, checked
from nwdes.shell.git import failure_reason, run_git
from nwdes.shell.ports import Unreadable


def read_named(path: str, flag: str):
    try:
        raw = Path(path).read_bytes()
        raw.decode("utf-8", errors="strict")
        return Built(raw)
    except FileNotFoundError:
        return checked(
            None,
            (
                Defect(
                    f"MissingFact: {flag} {path}",
                    "Named file does not exist.",
                    "Supply an existing file for this flag.",
                ),
            ),
        )
    except (OSError, UnicodeError) as error:
        return checked(
            None,
            (
                Defect(
                    f"InputUnreadable: {flag} {path}",
                    str(error),
                    "Supply a readable strict UTF-8 file.",
                ),
            ),
        )


def read_tree(path: str):
    root = Path(path).absolute()
    read = read_named(path, "--host-sessions")
    if isinstance(read, Refused):
        return read

    def children(parent):
        store = parent.with_suffix("")
        try:
            paths = sorted(store.glob("*.jsonl"))
        except OSError as error:
            return (), (
                Defect(
                    "InputUnreadable: " + str(store),
                    str(error),
                    "Restore access to the native session store.",
                ),
            )
        files, defects = (), ()
        for child in paths:
            try:
                raw, error = child.read_bytes(), None
            except OSError as failure:
                raw, error = b"", str(failure)
            files += (
                measurement.SessionFile(
                    child.relative_to(root.parent).as_posix(), str(parent), raw, error
                ),
            )
            nested, failures = children(child)
            files += nested
            defects += failures
        return files, defects

    descendants, defects = children(root)
    return checked(
        measurement.SessionTree(
            root.name,
            str(root),
            measurement.SessionFile(root.name, None, read.value),
            descendants,
        ),
        defects,
    )


def read_history(root, candidate, handoff_path, events):
    if candidate is None:
        return None, ("no candidate",)
    if not re.fullmatch(r"[0-9a-f]{40}", candidate):
        return None, ("candidate " + candidate + " unresolvable",)
    causes = []

    def query(*argv):
        result = run_git(root, tuple(argv))
        if isinstance(result, Unreadable) or result.code:
            causes.append("git " + " ".join(argv) + " " + failure_reason(result))
            return None
        return result.stdout

    resolved = query("rev-parse", "--verify", candidate + "^{commit}")
    if resolved is None:
        return None, ("candidate " + candidate + " unresolvable", *causes)
    head_raw = query("rev-parse", "--verify", "HEAD^{commit}")
    ancestor_raw = query(
        "rev-list", "--first-parent", "--reverse", "--timestamp", candidate
    )
    head_history = query(
        "rev-list", "--first-parent", "--reverse", "--timestamp", "HEAD"
    )
    head = head_raw.decode().strip() if head_raw else ""

    def metadata(raw):
        result = []
        for row in (raw or b"").decode().splitlines():
            fields = row.split()
            try:
                stamp, identity = fields
                seconds = int(stamp)
            except ValueError:
                causes.append("malformed git commit metadata " + row)
                continue
            result.append(measurement.Commit(identity, seconds, (), {}))
        return tuple(result)

    ancestor_metadata = metadata(ancestor_raw)
    head_metadata = metadata(head_history)
    ancestors = tuple(commit.id for commit in ancestor_metadata)
    head_ids = tuple(commit.id for commit in head_metadata)
    if candidate in head_ids:
        chain = head_ids[head_ids.index(candidate) + 1 :]
    else:
        chain = []
        causes.append("candidate " + candidate + " not on HEAD first-parent history")
    directory = handoff_path.rsplit("/", 1)[0]
    paths = (
        handoff_path,
        *sorted(
            {
                measurement.record_path(handoff_path, event.part, event.scope)
                for event in events
                if event.part in ("craft", "review")
            }
        ),
    )
    file_causes = {}

    metadata_by_id = {
        commit.id: commit for commit in (*ancestor_metadata, *head_metadata)
    }
    if candidate not in metadata_by_id:
        return None, tuple(causes or ("missing candidate metadata " + candidate,))
    snapshots = measurement.history_snapshot_ids(
        ancestor_metadata,
        tuple(metadata_by_id[identity] for identity in chain),
        events,
    )
    chain_ids = frozenset(chain)

    def commit(identity):
        changed = (
            query("diff-tree", "--no-commit-id", "--name-only", "-r", "-z", identity)
            if identity in chain_ids
            else None
        )
        files = {}
        for path in paths if identity in snapshots else ():
            result = run_git(root, ("show", identity + ":" + path))
            if not isinstance(result, Unreadable) and result.code == 0:
                files[path] = result.stdout
            else:
                reason = failure_reason(result)
                file_causes[(identity, path)] = reason
                if "does not exist" in reason or "exists on disk, but not in" in reason:
                    files[path] = None
                else:
                    causes.append("git object " + identity + ":" + path + " " + reason)
        return measurement.Commit(
            identity,
            metadata_by_id[identity].committer_s,
            tuple(
                part.decode("utf-8", "surrogateescape")
                for part in (changed or b"").split(b"\x00")
                if part
            ),
            files,
        )

    commits = {
        identity: commit(identity) for identity in dict.fromkeys((*ancestors, *chain))
    }
    current = {}
    for path in paths:
        try:
            current[path] = (Path(root) / path).read_bytes()
        except FileNotFoundError:
            current[path] = None
        except OSError as error:
            file_causes[(None, path)] = str(error)
    status = query("status", "--porcelain", "-z", "--untracked-files=all")
    entries = (status or b"").split(b"\x00")
    dirty = []
    index = 0
    while index < len(entries):
        row = entries[index]
        index += 1
        if not row:
            continue
        name = row[3:].decode("utf-8", "surrogateescape")
        if not name.startswith(directory + "/"):
            dirty.append(name)
        if b"R" in row[:2] or b"C" in row[:2]:
            if index < len(entries):
                old = entries[index].decode("utf-8", "surrogateescape")
                if not old.startswith(directory + "/"):
                    dirty.append(old)
                index += 1
    return measurement.History(
        commits[candidate],
        tuple(commits[c] for c in ancestors),
        tuple(commits[c] for c in chain),
        current,
        status is not None and not dirty,
        head,
        tuple(sorted(dirty)),
        tuple(dict.fromkeys(causes)),
        file_causes,
    ), ()
