"""Immutable ownership evidence and finite cleanup plans; no filesystem effects."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, replace
from enum import Enum
from typing import TYPE_CHECKING, TypeAlias


if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass(frozen=True)
class IdentityRow:
    path: str
    sha256: str


@dataclass(frozen=True)
class HookTemplate:
    event: str
    matcher: str
    command: str


@dataclass(frozen=True)
class ReleaseIdentity:
    files: frozenset[IdentityRow]
    hook_templates: tuple[HookTemplate, ...]


@dataclass(frozen=True)
class FileLeaf:
    path: str
    sha256: str
    size: int
    mtime_ns: int
    md5: str | None = None


@dataclass(frozen=True)
class SymlinkLeaf:
    path: str
    target: str


@dataclass(frozen=True)
class SizeMtime:
    size: int
    mtime: int


@dataclass(frozen=True)
class SourceHash:
    header_hash: bytes


@dataclass(frozen=True)
class PycacheLeaf:
    path: str
    source_path: str
    header: SizeMtime | SourceHash
    source_hash: bytes | None
    md5: str | None = None


@dataclass(frozen=True)
class Dir:
    path: str
    children: tuple[Node, ...]


Node: TypeAlias = FileLeaf | SymlinkLeaf | PycacheLeaf | Dir


@dataclass(frozen=True)
class HookEntry:
    file: str
    event: str
    matcher: str
    index: int
    command: str
    raw: object


@dataclass(frozen=True)
class SettingsDocument:
    path: str
    resolved_path: str
    entries: tuple[HookEntry, ...]
    path_segments: tuple[str, ...]


@dataclass(frozen=True)
class CodexReceipt:
    path: str
    hooks_file: str
    python_path: str
    pythonpath: str
    rendered_entries: tuple[str, ...]
    launcher_path: str
    launcher_sources: tuple[str, ...]


@dataclass(frozen=True)
class CursorReceipt:
    path: str
    hooks_file: str
    python_path: str
    pythonpath: str
    event: str
    rendered_entries: tuple[object, ...]


@dataclass(frozen=True)
class CopilotReceipt:
    path: str
    hook_file: str
    python_path: str
    pythonpath: str
    rendered_config: object
    actual_config: object | None = None


@dataclass(frozen=True)
class OpencodeReceipt:
    path: str
    shim_file: str
    version: str
    sha256: str


@dataclass(frozen=True)
class ScriptsKey:
    manifest_path: str
    key: str
    files: tuple[str, ...]


@dataclass(frozen=True)
class OmpReceipt:
    path: str
    files: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class RuntimeTreeReceipt:
    path: str
    recorded_tree_hash: str
    computed_tree_hash: str | None
    receipt_sha256: str


@dataclass(frozen=True)
class Reservation:
    path: str
    tree: str
    reserved: str
    receipt_sha256: str
    tree_hash: str
    owned: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class UnwitnessedReceipt:
    path: str
    why: str


Receipt: TypeAlias = (
    CodexReceipt
    | CursorReceipt
    | CopilotReceipt
    | OpencodeReceipt
    | ScriptsKey
    | OmpReceipt
    | RuntimeTreeReceipt
    | UnwitnessedReceipt
)


@dataclass(frozen=True)
class CodexWitness:
    manifest: object
    hooks_document: object
    hooks_path: str
    matched_command: str


@dataclass(frozen=True)
class CleanupOutcome:
    exit_code: int
    codex_witness: CodexWitness | None


@dataclass(frozen=True)
class PathSegment:
    file: str
    segment: str


Candidate: TypeAlias = (
    Node | HookEntry | ScriptsKey | PathSegment | Receipt | Reservation
)


class Witness(Enum):
    W1 = "W1"
    W2 = "W2"
    W3 = "W3"
    W4 = "W4"
    W5 = "W5"


@dataclass(frozen=True)
class Owned:
    candidate: Candidate
    witness: Witness


@dataclass(frozen=True)
class Kept:
    candidate: Candidate
    failed_witness: Witness
    why: str


@dataclass(frozen=True)
class Partition:
    owned: tuple[Owned, ...]
    kept: tuple[Kept, ...]
    reservations: tuple[Reservation, ...] = ()
    indeterminate: tuple[UnwitnessedReceipt, ...] = ()


@dataclass(frozen=True)
class RemoveFile:
    path: str


@dataclass(frozen=True)
class RemoveDir:
    path: str


@dataclass(frozen=True)
class DropEntry:
    file: str
    event: str
    matcher: str
    index: int


@dataclass(frozen=True)
class DropKey:
    manifest_path: str
    key: str


@dataclass(frozen=True)
class DropPathSegment:
    file: str
    segment: str


@dataclass(frozen=True)
class Reserve:
    reservation: Reservation
    record: bytes


@dataclass(frozen=True)
class RemoveRecorded:
    path: str
    md5: str
    original: str


@dataclass(frozen=True)
class RemoveReceipt:
    path: str
    sha256: str
    original: str


@dataclass(frozen=True)
class RemoveReservedDir:
    path: str
    original: str | None


@dataclass(frozen=True)
class RemoveControl:
    path: str
    tree: str


Removal: TypeAlias = (
    RemoveFile
    | RemoveDir
    | DropEntry
    | DropKey
    | DropPathSegment
    | Reserve
    | RemoveRecorded
    | RemoveReceipt
    | RemoveReservedDir
    | RemoveControl
)


@dataclass(frozen=True)
class Plan:
    removals: tuple[Removal, ...]


def walk(tree: tuple[Node, ...]) -> tuple[Node, ...]:
    # Iterative traversal also admits deeply nested finite candidate trees.
    result = []
    pending = list(reversed(tree))
    while pending:
        node = pending.pop()
        result.append(node)
        if isinstance(node, Dir):
            pending.extend(reversed(node.children))
    return tuple(result)


def prune(
    tree: tuple[Node, ...],
    owned_leaf: Callable[[FileLeaf | SymlinkLeaf | PycacheLeaf], bool],
) -> tuple[Node, ...]:
    retained = {}
    for node in reversed(walk(tree)):
        if isinstance(node, Dir):
            children = tuple(
                retained[c.path] for c in node.children if c.path in retained
            )
            if children or not node.children:
                retained[node.path] = replace(node, children=children)
        elif isinstance(node, SymlinkLeaf) or not owned_leaf(node):
            retained[node.path] = node
    return tuple(retained[n.path] for n in tree if n.path in retained)


def _host(path: str, hosts: tuple[tuple[str, str], ...]) -> str | None:
    return max(
        (
            root
            for _, root in hosts
            if path == root or path.startswith(root.rstrip("/") + "/")
        ),
        key=len,
        default=None,
    )


def _template_owned(
    entry: HookEntry,
    home: str,
    identity: ReleaseIdentity,
    hosts: tuple[tuple[str, str], ...],
) -> bool:
    host = _host(entry.file, hosts)
    if host is None:
        return False
    libraries = (
        home.rstrip("/") + "/.claude/lib/python",
        host.rstrip("/") + "/lib/python",
        "$HOME/.claude/lib/python",
    )
    interpreter = r"(?:[^\s]*/)?python(?:3(?:\.\d+)?)?"
    for template in identity.hook_templates:
        if (entry.event, entry.matcher) != (template.event, template.matcher):
            continue
        for lib in libraries:
            pattern = re.escape(template.command.replace("{lib}", lib)).replace(
                re.escape("{python}"), interpreter
            )
            if re.fullmatch(pattern, entry.command):
                return True
    return False


def _receipt_entry(entry: HookEntry, receipts: tuple[Receipt, ...]) -> bool:
    for receipt in receipts:
        if (
            isinstance(receipt, CodexReceipt)
            and entry.file == receipt.hooks_file
            and entry.event == "PreToolUse"
        ):
            if entry.command in receipt.rendered_entries:
                return True
        if (
            isinstance(receipt, CursorReceipt)
            and entry.file == receipt.hooks_file
            and entry.event == receipt.event
            and entry.raw in receipt.rendered_entries
        ):
            return True
    return False


def _bin_context(
    node: Node,
    hosts: tuple[tuple[str, str], ...],
    release_paths: frozenset[str],
    recorded_files: frozenset[str],
) -> bool:
    host = _host(node.path, hosts)
    if host is None or not node.path.removeprefix(host.rstrip("/") + "/").startswith(
        "bin/"
    ):
        return False
    # The shared bin tree also supplies W5's occupancy evidence. Its unrelated
    # entries are not cleanup candidates, but remain in the tree for pruning.
    source = node.source_path if isinstance(node, PycacheLeaf) else node.path
    relative = source.removeprefix(host.rstrip("/") + "/")
    return not any(
        relative == path or relative.startswith(path + "/") for path in release_paths
    ) and not any(
        source == path or source.startswith(path + "/") for path in recorded_files
    )


# Published DESIGN boundary: keep immutable snapshots and selected roots explicit.
def partition(  # noqa: PLR0913, PLR0917
    home: str,
    tree: tuple[Node, ...],
    documents: tuple[SettingsDocument, ...],
    receipts: tuple[Receipt, ...],
    identity: ReleaseIdentity,
    reservations: tuple[Reservation, ...] = (),
    *,
    hosts: tuple[tuple[str, str], ...],
) -> Partition:
    runtime = _runtime_selection(tree, receipts, reservations)
    nodes = tuple(node for node in walk(tree) if node.path not in runtime.excluded)
    by_path = {node.path: node for node in nodes}
    release = {(row.path, row.sha256) for row in identity.files}
    release_paths = frozenset(row.path for row in identity.files)
    owned_files = frozenset(
        node.path
        for node in nodes
        if isinstance(node, FileLeaf)
        and (host := _host(node.path, hosts)) is not None
        and (node.path.removeprefix(host.rstrip("/") + "/"), node.sha256) in release
    )
    recorded_files = frozenset(
        path
        for r in receipts
        for path in (
            (r.shim_file,)
            if isinstance(r, OpencodeReceipt)
            else (r.hook_file,)
            if isinstance(r, CopilotReceipt)
            else tuple(p for p, _ in r.files)
            if isinstance(r, OmpReceipt)
            else (r.launcher_path,)
            if isinstance(r, CodexReceipt)
            else ()
        )
    )
    verdicts: list[Owned | Kept] = [*runtime.owned, *runtime.kept]
    for node in nodes:
        if _bin_context(node, hosts, release_paths, recorded_files):
            continue
        if isinstance(node, Dir):
            if not node.children:
                verdicts.append(
                    Kept(node, Witness.W1, "already empty, not emptied by this removal")
                )
            continue
        if isinstance(node, PycacheLeaf):
            source = by_path.get(node.source_path)
            header = node.header
            matches = (
                isinstance(source, FileLeaf)
                and source.path in owned_files
                and (
                    (
                        isinstance(header, SizeMtime)
                        and (header.size, header.mtime)
                        == (source.size % 2**32, source.mtime_ns // 10**9 % 2**32)
                    )
                    or (
                        isinstance(header, SourceHash)
                        and node.source_hash is not None
                        and header.header_hash == node.source_hash
                        and len(header.header_hash) == 8
                    )
                )
            )
            verdicts.append(
                Owned(node, Witness.W2)
                if matches
                else Kept(
                    node,
                    Witness.W2,
                    "cache header does not identify an owned sibling source",
                )
            )
        else:
            verdicts.append(
                Owned(node, Witness.W1)
                if node.path in owned_files
                else Kept(
                    node,
                    Witness.W1,
                    "symlink is never owned"
                    if isinstance(node, SymlinkLeaf)
                    else "path and bytes do not match the release identity",
                )
            )
    for document in documents:
        for entry in document.entries:
            if _receipt_entry(entry, receipts):
                verdicts.append(Owned(entry, Witness.W4))
            elif _template_owned(entry, home, identity, hosts):
                verdicts.append(Owned(entry, Witness.W3))
            else:
                witness = (
                    Witness.W4
                    if any(
                        name in {"cursor", "codex"} and root == _host(entry.file, hosts)
                        for name, root in hosts
                    )
                    or any(
                        isinstance(r, CursorReceipt) and r.hooks_file == entry.file
                        for r in receipts
                    )
                    else Witness.W3
                )
                verdicts.append(
                    Kept(
                        entry,
                        witness,
                        "entry does not equal a witnessed hook rendering",
                    )
                )
    # Receipt witnesses may replace a failed release witness, never a symlink.
    receipt_paths: dict[str, str] = {}
    for receipt in receipts:
        if isinstance(receipt, OpencodeReceipt):
            receipt_paths[receipt.shim_file] = receipt.sha256
        elif isinstance(receipt, OmpReceipt):
            receipt_paths.update(receipt.files)
        elif isinstance(receipt, CodexReceipt):
            node = by_path.get(receipt.launcher_path)
            if isinstance(node, FileLeaf) and node.sha256 in {
                hashlib.sha256(source.encode("utf-8")).hexdigest()
                for source in receipt.launcher_sources
            }:
                receipt_paths[node.path] = node.sha256
        elif isinstance(receipt, CopilotReceipt):
            node = by_path.get(receipt.hook_file)
            if (
                receipt.actual_config is not None
                and receipt.actual_config == receipt.rendered_config
                and isinstance(node, FileLeaf)
            ):
                receipt_paths[receipt.hook_file] = node.sha256
    verdicts = [
        Owned(v.candidate, Witness.W4)
        if (
            isinstance(v.candidate, FileLeaf)
            and receipt_paths.get(v.candidate.path) == v.candidate.sha256
        )
        else Kept(
            v.candidate,
            Witness.W4,
            "artifact does not match its receipt witness; kept for its owner",
        )
        if isinstance(v, Kept)
        and isinstance(v.candidate, (FileLeaf, PycacheLeaf, SymlinkLeaf))
        and v.candidate.path in recorded_files
        else v
        for v in verdicts
    ]
    removable = {
        v.candidate.path
        for v in verdicts
        if isinstance(v, Owned) and isinstance(v.candidate, (FileLeaf, PycacheLeaf))
    }
    for receipt in receipts:
        if getattr(receipt, "path", None) in runtime.excluded:
            continue
        if isinstance(receipt, ScriptsKey):
            passes = all(
                path not in by_path or path in removable for path in receipt.files
            )
        elif isinstance(receipt, CodexReceipt):
            passes = (
                receipt.launcher_path not in by_path
                or receipt.launcher_path in removable
            )
        elif isinstance(receipt, CursorReceipt):
            # Edited entries are not receipt artifacts; the exact recorded rendering alone belongs to it.
            passes = True
        elif isinstance(receipt, CopilotReceipt):
            passes = (
                receipt.actual_config is not None
                and receipt.actual_config == receipt.rendered_config
            )
        elif isinstance(receipt, OpencodeReceipt):
            passes = receipt.shim_file not in by_path or receipt.shim_file in removable
        elif isinstance(receipt, OmpReceipt):
            passes = all(
                path not in by_path or path in removable for path, _ in receipt.files
            )
        elif isinstance(receipt, UnwitnessedReceipt):
            passes = False
        else:
            passes = False
        if isinstance(receipt, ScriptsKey):
            verdicts.append(
                Owned(receipt, Witness.W4)
                if passes
                else Kept(receipt, Witness.W4, "a recorded file is preserved")
            )
        elif receipt.path in by_path:
            verdicts = [
                v
                for v in verdicts
                if getattr(v.candidate, "path", None) != receipt.path
            ]
            node = by_path[receipt.path]
            verdicts.append(
                Owned(receipt, Witness.W4)
                if passes and isinstance(node, FileLeaf)
                else Kept(
                    receipt,
                    Witness.W4,
                    receipt.why
                    if isinstance(receipt, UnwitnessedReceipt)
                    else "a recorded artifact is preserved or receipt is not a regular file",
                )
            )
    removed = frozenset(
        v.candidate.path
        for v in verdicts
        if isinstance(v, Owned) and hasattr(v.candidate, "path")
    )
    remaining = {n.path for n in walk(prune(tree, lambda n: n.path in removed))}
    for document in documents:
        host = _host(document.path, hosts)
        if host is None:
            continue
        segment = host.rstrip("/") + "/bin"
        if segment in document.path_segments:
            candidate = PathSegment(document.path, segment)
            empty = not any(
                p.startswith(segment + "/") for p in remaining
            ) and not isinstance(by_path.get(segment), SymlinkLeaf)
            verdicts.append(
                Owned(candidate, Witness.W5)
                if empty
                else Kept(
                    candidate, Witness.W5, "host bin directory still holds user files"
                )
            )
    return Partition(
        tuple(v for v in verdicts if isinstance(v, Owned)),
        tuple(v for v in verdicts if isinstance(v, Kept)),
        runtime.reservations,
        runtime.indeterminate,
    )


def plan(
    partition: Partition,
    tree: tuple[Node, ...],
    documents: tuple[SettingsDocument, ...],
) -> Plan:
    file_paths = frozenset(
        v.candidate.path
        for v in partition.owned
        if hasattr(v.candidate, "path")
        and not isinstance(v.candidate, Dir)
        and not (
            isinstance(v.candidate, (RuntimeTreeReceipt, Reservation))
            or (
                v.witness == Witness.W4
                and any(
                    v.candidate.path.startswith(r.tree + "/")
                    or v.candidate.path.startswith(r.reserved + "/")
                    for r in partition.reservations
                )
            )
        )
    )
    after = {n.path for n in walk(prune(tree, lambda n: n.path in file_paths))}
    receipt_paths = frozenset(
        v.candidate.path
        for v in partition.owned
        if isinstance(
            v.candidate,
            (
                CodexReceipt,
                CursorReceipt,
                CopilotReceipt,
                OpencodeReceipt,
                OmpReceipt,
                RuntimeTreeReceipt,
            ),
        )
    )
    files = tuple(
        RemoveFile(path)
        for path in sorted(
            file_paths, key=lambda p: (p in receipt_paths, "/__pycache__/" not in p, p)
        )
    )
    directories = tuple(
        RemoveDir(n.path)
        for n in sorted(
            (n for n in walk(tree) if isinstance(n, Dir) and n.path not in after),
            key=lambda n: (-n.path.count("/"), n.path),
        )
    )
    drops = tuple(
        DropEntry(c.file, c.event, c.matcher, c.index)
        if isinstance(c, HookEntry)
        else DropKey(c.manifest_path, c.key)
        if isinstance(c, ScriptsKey)
        else DropPathSegment(c.file, c.segment)
        for v in partition.owned
        if isinstance((c := v.candidate), (HookEntry, ScriptsKey, PathSegment))
    )
    return Plan(files + directories + drops + _runtime_steps(partition, tree))


def apply(
    tree: tuple[Node, ...],
    documents: tuple[SettingsDocument, ...],
    removals: tuple[Removal, ...],
) -> tuple[tuple[Node, ...], tuple[SettingsDocument, ...]]:
    for removal in removals:
        if isinstance(removal, Reserve):
            tree = _reserve_tree(tree, removal)
    current = {node.path: node for node in walk(tree)}
    paths = frozenset(
        r.path
        for r in removals
        if isinstance(r, (RemoveFile, RemoveDir, RemoveReservedDir, RemoveControl))
        or (
            isinstance(r, RemoveRecorded)
            and isinstance(current.get(r.path), (FileLeaf, PycacheLeaf))
            and current[r.path].md5 == r.md5
        )
        or (
            isinstance(r, RemoveReceipt)
            and isinstance(current.get(r.path), FileLeaf)
            and current[r.path].sha256 == r.sha256
        )
    )
    retained = {}
    for node in reversed(walk(tree)):
        if node.path not in paths:
            retained[node.path] = (
                replace(
                    node,
                    children=tuple(
                        retained[c.path] for c in node.children if c.path in retained
                    ),
                )
                if isinstance(node, Dir)
                else node
            )
    drops = {
        (r.file, r.event, r.matcher, r.index)
        for r in removals
        if isinstance(r, DropEntry)
    }
    segments = {(r.file, r.segment) for r in removals if isinstance(r, DropPathSegment)}

    def clean(document: SettingsDocument) -> SettingsDocument:
        entries = tuple(
            e
            for e in document.entries
            if (e.file, e.event, e.matcher, e.index) not in drops
        )
        counts = {}
        indexed = []
        for entry in entries:
            key = (entry.event, entry.matcher)
            indexed.append(replace(entry, index=counts.get(key, 0)))
            counts[key] = counts.get(key, 0) + 1
        return replace(
            document,
            entries=tuple(indexed),
            path_segments=tuple(
                s for s in document.path_segments if (document.path, s) not in segments
            ),
        )

    return tuple(retained[n.path] for n in tree if n.path in retained), tuple(
        clean(d) for d in documents
    )


def drop_key(document: dict[str, object], removal: DropKey) -> dict[str, object]:
    """Retire only the planned family key; unknown JSON is retained as data."""
    return {key: value for key, value in document.items() if key != removal.key}


def locator(candidate: Candidate | Removal) -> str:
    if isinstance(candidate, Reserve):
        return candidate.reservation.tree
    if isinstance(candidate, (RemoveRecorded, RemoveReceipt, RemoveReservedDir)):
        return candidate.original if candidate.original is not None else candidate.path
    if isinstance(candidate, RemoveControl):
        return candidate.tree
    if isinstance(candidate, (HookEntry, DropEntry)):
        return f"{candidate.file}#{candidate.event}[{candidate.matcher}]"
    if isinstance(candidate, (ScriptsKey, DropKey)):
        return f"{candidate.manifest_path}#{candidate.key}"
    if isinstance(candidate, (PathSegment, DropPathSegment)):
        return f"{candidate.file}#env.PATH[{candidate.segment}]"
    return candidate.path


def report_lines(plan: Plan, partition: Partition) -> tuple[str, ...]:
    return tuple(
        f"REMOVED {locator(r)}" for r in plan.removals if reports_removal(r, partition)
    ) + tuple(preserved_line(v) for v in partition.kept)


def reports_removal(removal: Removal, partition: Partition) -> bool:
    if isinstance(removal, Reserve) or (
        isinstance(removal, RemoveReservedDir) and removal.original is None
    ):
        return False
    if isinstance(removal, RemoveControl):
        return not any(
            getattr(v.candidate, "path", "").startswith(removal.tree + "/")
            for v in partition.kept
        )
    return True


def preserved_line(value: Kept) -> str:
    return preserved_path_line(
        locator(value.candidate), value.failed_witness, value.why
    )


def preserved_path_line(path: str, witness: Witness, why: str) -> str:
    return f"PRESERVED {path} {witness.value}: {why}"


RESERVED_SUFFIX = ".nwave-removing"
CONTROL_SUFFIX = ".nwave-removal.json"
RUNTIME_RECEIPT = "_install_manifest.json"


def canonical_tree_hash(pairs: tuple[tuple[str, str], ...]) -> str:
    digest = hashlib.sha256()
    for relative, md5 in sorted(pairs, key=lambda pair: tuple(pair[0].split("/"))):
        digest.update(f"{relative}\0{md5}\n".encode())
    return "sha256:" + digest.hexdigest()


def render_reservation(reservation: Reservation) -> bytes:
    document = {
        "tree": reservation.tree,
        "reserved": reservation.reserved,
        "receipt_sha256": reservation.receipt_sha256,
        "tree_hash": reservation.tree_hash,
        "owned": sorted(reservation.owned),
    }
    return (json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )


def parse_reservation(path: str, data: bytes) -> Reservation | None:
    try:
        raw = json.loads(data)
        if not isinstance(raw, dict) or set(raw) != {
            "tree",
            "reserved",
            "receipt_sha256",
            "tree_hash",
            "owned",
        }:
            return None
        if not all(
            isinstance(raw[key], str)
            for key in ("tree", "reserved", "receipt_sha256", "tree_hash")
        ):
            return None
        tree = raw["tree"]
        if not tree.startswith("/") or tree.endswith("/") or "\0" in tree:
            return None
        if path != tree + CONTROL_SUFFIX or raw["reserved"] != tree + RESERVED_SUFFIX:
            return None
        if (
            re.fullmatch("[0-9a-f]{64}", raw["receipt_sha256"]) is None
            or re.fullmatch("sha256:[0-9a-f]{64}", raw["tree_hash"]) is None
        ):
            return None
        if not isinstance(raw["owned"], list):
            return None
        pairs = []
        for pair in raw["owned"]:
            if (
                not isinstance(pair, list)
                or len(pair) != 2
                or not all(isinstance(value, str) for value in pair)
            ):
                return None
            relative, md5 = pair
            if (
                any(part in ("", ".", "..") for part in relative.split("/"))
                or "\0" in relative
                or "\\" in relative
            ):
                return None
            if re.fullmatch("[0-9a-f]{32}", md5) is None:
                return None
            pairs.append((relative, md5))
        if pairs != sorted(pairs) or len({relative for relative, _ in pairs}) != len(
            pairs
        ):
            return None
        reservation = Reservation(
            path,
            tree,
            raw["reserved"],
            raw["receipt_sha256"],
            raw["tree_hash"],
            tuple(pairs),
        )
        return reservation if render_reservation(reservation) == data else None
    except (ValueError, UnicodeError, TypeError, RecursionError):
        return None


def _cache_matches(cache: PycacheLeaf, source: Node | None) -> bool:
    return isinstance(source, FileLeaf) and (
        (
            isinstance(cache.header, SizeMtime)
            and (cache.header.size, cache.header.mtime)
            == (source.size % 2**32, source.mtime_ns // 10**9 % 2**32)
        )
        or (
            isinstance(cache.header, SourceHash)
            and cache.source_hash is not None
            and len(cache.header.header_hash) == 8
            and cache.header.header_hash == cache.source_hash
        )
    )


def _whole_tree_failure(
    root: str, receipt: RuntimeTreeReceipt, nodes: dict[str, Node]
) -> str | None:
    if not isinstance(nodes.get(root), Dir):
        return "runtime tree is not a regular directory"
    if not isinstance(nodes.get(receipt.path), FileLeaf):
        return "runtime receipt is absent or is not a regular file"
    if receipt.computed_tree_hash is None:
        return "runtime tree contains a symlink"
    if receipt.computed_tree_hash != receipt.recorded_tree_hash:
        return "runtime tree hash does not match its receipt"
    return _runtime_member_failure(root, receipt.path, nodes)


def _runtime_member_failure(
    root: str, receipt_path: str, nodes: dict[str, Node]
) -> str | None:
    if not isinstance(nodes.get(root), Dir):
        return "runtime tree is not a regular directory"
    for node in nodes.values():
        if not node.path.startswith(root + "/"):
            continue
        if isinstance(node, Dir):
            if not node.children:
                return f"already-empty directory {node.path} is not owned"
        elif isinstance(node, SymlinkLeaf):
            return f"symlink {node.path} is not owned"
        elif isinstance(node, FileLeaf):
            if node.path != receipt_path and (
                not node.path.endswith(".py") or node.md5 is None
            ):
                return f"foreign or unreadable file {node.path} is not owned"
        elif (
            node.md5 is None
            or not node.source_path.startswith(root + "/")
            or not node.source_path.endswith(".py")
            or not _cache_matches(node, nodes.get(node.source_path))
        ):
            return f"cache {node.path} does not identify an owned source"
    return None


@dataclass(frozen=True)
class _RuntimeSelection:
    owned: tuple[Owned, ...]
    kept: tuple[Kept, ...]
    reservations: tuple[Reservation, ...]
    excluded: frozenset[str]
    indeterminate: tuple[UnwitnessedReceipt, ...]


def _runtime_selection(
    tree: tuple[Node, ...],
    receipts: tuple[Receipt, ...],
    reservations: tuple[Reservation, ...],
) -> _RuntimeSelection:
    nodes = {node.path: node for node in walk(tree)}
    runtime = {
        receipt.path.rsplit("/", 1)[0]: receipt
        for receipt in receipts
        if isinstance(receipt, RuntimeTreeReceipt)
    }
    bad_receipts = {
        receipt.path.rsplit("/", 1)[0]: receipt
        for receipt in receipts
        if isinstance(receipt, UnwitnessedReceipt)
        and receipt.path.endswith("/" + RUNTIME_RECEIPT)
    }
    controls = {reservation.tree: reservation for reservation in reservations}
    bad_controls = {
        receipt.path.removesuffix(CONTROL_SUFFIX): receipt
        for receipt in receipts
        if isinstance(receipt, UnwitnessedReceipt)
        and receipt.path.endswith(CONTROL_SUFFIX)
    }
    roots = set(runtime) | set(bad_receipts) | set(controls) | set(bad_controls)
    roots.update(
        node.path.removesuffix(RESERVED_SUFFIX)
        for node in tree
        if node.path.endswith(RESERVED_SUFFIX)
    )
    roots.difference_update(
        root for root in tuple(roots) if root.endswith(RESERVED_SUFFIX)
    )
    owned, kept, active, indeterminate = [], [], [], []
    excluded = set()

    def protect(root: str) -> None:
        excluded.update(
            path for path in nodes if path == root or path.startswith(root + "/")
        )

    for root in sorted(roots):
        reserved = root + RESERVED_SUFFIX
        control_path = root + CONTROL_SUFFIX
        reservation = controls.get(root)
        conflict = bad_controls.get(root)
        if reservation is not None:
            for location in (root, reserved):
                receipt_path = location + "/" + RUNTIME_RECEIPT
                leaf = nodes.get(receipt_path)
                witness = runtime.get(location)
                if leaf is not None and (
                    not isinstance(leaf, FileLeaf)
                    or witness is None
                    or witness.receipt_sha256 != reservation.receipt_sha256
                    or witness.recorded_tree_hash != reservation.tree_hash
                ):
                    conflict = UnwitnessedReceipt(
                        control_path,
                        "control record is bound to a different receipt or tree hash",
                    )
                    break
        if conflict is not None:
            protect(root)
            protect(reserved)
            protect(control_path)
            indeterminate.append(conflict)
            continue
        receipt = runtime.get(root)
        invalid = bad_receipts.get(root)
        if reservation is not None and reserved in nodes:
            protect(reserved)
            protect(root)
            excluded.add(control_path)
            active.append(reservation)
            recorded = dict(reservation.owned)
            blocked = False
            for node in nodes.values():
                if not node.path.startswith(reserved + "/") or isinstance(node, Dir):
                    continue
                if node.path == reserved + "/" + RUNTIME_RECEIPT:
                    continue
                relative = node.path.removeprefix(reserved + "/")
                if (
                    isinstance(node, (FileLeaf, PycacheLeaf))
                    and node.md5 is not None
                    and recorded.get(relative) == node.md5
                ):
                    owned.append(Owned(node, Witness.W4))
                else:
                    blocked = True
                    kept.append(
                        Kept(
                            node,
                            Witness.W4,
                            "file no longer matches the reserved ownership record",
                        )
                    )
            reserved_receipt = runtime.get(reserved)
            if reserved_receipt is not None:
                if blocked:
                    kept.append(
                        Kept(
                            reserved_receipt,
                            Witness.W4,
                            "a reserved member is preserved",
                        )
                    )
                else:
                    owned.append(Owned(reserved_receipt, Witness.W4))
            if not isinstance(nodes[reserved], Dir):
                kept.append(
                    Kept(
                        nodes[reserved], Witness.W4, "reserved tree is not a directory"
                    )
                )
            continue
        if reservation is not None and root not in nodes:
            excluded.add(control_path)
            active.append(reservation)
            continue
        failure = (
            _whole_tree_failure(root, receipt, nodes)
            if receipt is not None
            else invalid.why
            if invalid
            else _runtime_member_failure(root, root + "/" + RUNTIME_RECEIPT, nodes)
            if reservation is not None
            else None
        )
        if reservation is not None:
            pairs = tuple(
                sorted(
                    (node.path.removeprefix(root + "/"), node.md5)
                    for node in nodes.values()
                    if isinstance(node, (FileLeaf, PycacheLeaf))
                    and node.path.startswith(root + "/")
                    and node.path != root + "/" + RUNTIME_RECEIPT
                    and node.md5 is not None
                )
            )
            if (
                receipt.computed_tree_hash
                if receipt is not None
                else _hash_from_nodes(root, nodes)
            ) != reservation.tree_hash or pairs != reservation.owned:
                failure = (
                    failure or "tree no longer verifies against its control record"
                )
            active.append(reservation)
            excluded.add(control_path)
        if reserved in nodes:
            protect(reserved)
            kept.append(
                Kept(
                    nodes[reserved],
                    Witness.W4,
                    "reserved name has no matching control record",
                )
            )
            failure = failure or f"reserved name {reserved} is occupied"
        if receipt is None and invalid is None and reservation is None:
            continue
        if failure is not None:
            excluded.add(root)
            receipt_value = receipt if receipt is not None else invalid
            if receipt_value is not None:
                excluded.add(receipt_value.path)
                kept.append(Kept(receipt_value, Witness.W4, failure))
            continue
        protect(root)
        members = tuple(
            sorted(
                (node.path.removeprefix(root + "/"), node.md5)
                for node in nodes.values()
                if isinstance(node, (FileLeaf, PycacheLeaf))
                and node.path.startswith(root + "/")
                and node.path != root + "/" + RUNTIME_RECEIPT
            )
        )
        if reservation is None:
            reservation = Reservation(
                control_path,
                root,
                reserved,
                receipt.receipt_sha256,
                receipt.recorded_tree_hash,
                members,
            )
            active.append(reservation)
        owned.append(Owned(receipt if receipt is not None else reservation, Witness.W4))
        owned.extend(
            Owned(node, Witness.W4)
            for node in nodes.values()
            if isinstance(node, (FileLeaf, PycacheLeaf))
            and node.path.startswith(root + "/")
            and node.path != root + "/" + RUNTIME_RECEIPT
        )
    return _RuntimeSelection(
        tuple(owned),
        tuple(kept),
        tuple(active),
        frozenset(excluded),
        tuple(indeterminate),
    )


def _runtime_steps(partition: Partition, tree: tuple[Node, ...]) -> tuple[Removal, ...]:
    nodes = {node.path: node for node in walk(tree)}
    owned = {getattr(value.candidate, "path", None) for value in partition.owned}
    result = []
    for reservation in partition.reservations:
        root, reserved = reservation.tree, reservation.reserved
        receipt_path = root + "/" + RUNTIME_RECEIPT
        fresh = (receipt_path in owned or reservation.path in owned) and root in nodes
        location = root if fresh else reserved
        if fresh:
            result.append(Reserve(reservation, render_reservation(reservation)))
        elif reserved not in nodes:
            result.append(RemoveControl(reservation.path, root))
            continue
        for relative, md5 in reservation.owned:
            path = location + "/" + relative
            if path in nodes and path in owned:
                result.append(
                    RemoveRecorded(
                        reserved + "/" + relative, md5, root + "/" + relative
                    )
                )
        blocked = any(
            getattr(value.candidate, "path", "").startswith(reserved + "/")
            or getattr(value.candidate, "path", None) == reserved
            for value in partition.kept
        )
        if blocked:
            continue
        receipt_leaf = nodes.get(location + "/" + RUNTIME_RECEIPT)
        if receipt_leaf is not None:
            result.append(
                RemoveReceipt(
                    reserved + "/" + RUNTIME_RECEIPT,
                    reservation.receipt_sha256,
                    receipt_path,
                )
            )
        directories = sorted(
            (
                node.path
                for node in nodes.values()
                if isinstance(node, Dir) and node.path.startswith(location + "/")
            ),
            key=lambda path: (-path.count("/"), path),
        )
        result.extend(
            RemoveReservedDir(
                reserved + path.removeprefix(location),
                root + path.removeprefix(location),
            )
            for path in directories
        )
        result.append(RemoveReservedDir(reserved, None))
        result.append(RemoveControl(reservation.path, root))
    return tuple(result)


def verified_removal_bytes(
    removal: RemoveRecorded | RemoveReceipt, data: bytes
) -> bytes | None:
    actual = (
        hashlib.md5(data).hexdigest()
        if isinstance(removal, RemoveRecorded)
        else hashlib.sha256(data).hexdigest()
    )
    expected = removal.md5 if isinstance(removal, RemoveRecorded) else removal.sha256
    return data if actual == expected else None


def reservation_conflict_line(problem: UnwitnessedReceipt) -> str:
    return (
        f"WHAT: runtime removal control record {problem.path!r} does not match. "
        f"WHY: {problem.why}. "
        "HOW: restore its matching receipt and tree or move the conflicting record aside before rerunning."
    )


def remaining_reserved_members(
    reservation: Reservation, tree: tuple[Node, ...]
) -> tuple[Kept, ...]:
    return tuple(
        Kept(
            node,
            Witness.W4,
            "a file remains in the reserved tree; its receipt and control record are retained",
        )
        for node in walk(tree)
        if (
            node.path.startswith(reservation.reserved + "/")
            and not isinstance(node, Dir)
            and node.path != reservation.reserved + "/" + RUNTIME_RECEIPT
        )
        or (isinstance(node, SymlinkLeaf) and node.path == reservation.reserved)
    )


def _reserve_tree(tree: tuple[Node, ...], step: Reserve) -> tuple[Node, ...]:
    reservation = step.reservation

    def moved(path: str) -> str:
        return (
            reservation.reserved + path.removeprefix(reservation.tree)
            if path == reservation.tree or path.startswith(reservation.tree + "/")
            else path
        )

    rebuilt = {}
    for node in reversed(walk(tree)):
        if isinstance(node, Dir):
            rebuilt[node.path] = replace(
                node,
                path=moved(node.path),
                children=tuple(rebuilt[child.path] for child in node.children),
            )
        elif isinstance(node, PycacheLeaf):
            rebuilt[node.path] = replace(
                node, path=moved(node.path), source_path=moved(node.source_path)
            )
        else:
            rebuilt[node.path] = replace(node, path=moved(node.path))
    result = tuple(rebuilt[node.path] for node in tree)
    if reservation.path not in rebuilt:
        record = FileLeaf(
            reservation.path,
            hashlib.sha256(step.record).hexdigest(),
            len(step.record),
            0,
            hashlib.md5(step.record).hexdigest(),
        )
        parent = reservation.path.rsplit("/", 1)[0]
        if parent in rebuilt and isinstance(rebuilt[parent], Dir):
            with_record = {}
            for node in reversed(walk(result)):
                if isinstance(node, Dir):
                    children = tuple(with_record[child.path] for child in node.children)
                    with_record[node.path] = replace(
                        node,
                        children=(*children, record)
                        if node.path == parent
                        else children,
                    )
                else:
                    with_record[node.path] = node
            result = tuple(with_record[node.path] for node in result)
        else:
            result += (record,)
    return result


def _hash_from_nodes(root: str, nodes: dict[str, Node]) -> str | None:
    descendants = tuple(
        node for node in nodes.values() if node.path.startswith(root + "/")
    )
    if any(
        isinstance(node, SymlinkLeaf)
        or (
            isinstance(node, FileLeaf)
            and node.path.endswith(".py")
            and node.md5 is None
        )
        for node in descendants
    ):
        return None
    return canonical_tree_hash(
        tuple(
            (node.path.removeprefix(root + "/"), node.md5)
            for node in descendants
            if isinstance(node, FileLeaf)
            and node.path.endswith(".py")
            and node.md5 is not None
        )
    )


def occupied_runtime_partition(
    home: str,
    reservation: Reservation,
    tree: tuple[Node, ...],
    identity: ReleaseIdentity,
    *,
    hosts: tuple[tuple[str, str], ...],
) -> Partition:
    """Partition a blocked admitted tree by W1/W2, retaining its runtime receipt."""
    receipt_path = reservation.tree + "/" + RUNTIME_RECEIPT
    # Whole-tree admission excludes every receipt except this tree's own.
    result = partition(home, tree, (), (), identity, hosts=hosts)
    receipt = next((node for node in walk(tree) if node.path == receipt_path), None)
    return replace(
        result,
        owned=tuple(
            v
            for v in result.owned
            if getattr(v.candidate, "path", None) != receipt_path
        ),
        kept=tuple(
            v
            for v in result.kept
            if getattr(v.candidate, "path", None)
            not in (reservation.tree, receipt_path)
        )
        + (
            (
                Kept(
                    receipt,
                    Witness.W4,
                    f"reserved name {reservation.reserved} is occupied or atomic no-replace rename is unavailable",
                ),
            )
            if receipt is not None
            else ()
        ),
    )
