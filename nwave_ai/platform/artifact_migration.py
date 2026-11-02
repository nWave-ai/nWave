"""Persisted artifact migration: discovery, classification and in-place upcast (ADR-AUM-001).

Moved from the removed DES update service under S5-OQ1, as one platform owner with its closure:
the filesystem port and its real adapter, the pure many-to-one workflow shape migration with its
packaged transition catalog, and the auto-update service that discovers, classifies and applies
eligible migrations. The versioning kernel is the kept ``nwave_ai.platform.artifact_versioning``.
"""

from __future__ import annotations

import json
import os
import stat
from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

from nwave_ai.platform.artifact_versioning import (
    ArtifactFromFutureRuntime,
    ArtifactVersioningKernel,
    read_version,
)


if TYPE_CHECKING:
    from pathlib import Path


class SnapshotRefusalReason(Enum):
    """Closed set of reasons one regular-file snapshot cannot be acquired."""

    NO_FOLLOW_UNAVAILABLE = "no-follow-unavailable"
    UNOPENABLE = "unopenable"
    IDENTITY_CHANGED = "identity-changed"
    BYTES_CHANGED = "bytes-changed"
    UNREADABLE = "unreadable"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class RegularFileSnapshot:
    """Opaque success value: bytes read from one validated no-follow open.

    The bytes are held by the snapshot precisely so no consumer reopens the
    path to obtain them again.  A reopen is a different observation of a
    different file, whatever the locator still says.
    """

    path: Path
    content: bytes
    mode: int


@dataclass(frozen=True)
class SnapshotRefusal:
    """Opaque failure value carrying its own WHAT / WHY / HOW.

    A refusal never carries success bytes, so no caller can mistake a refused
    acquisition for a degraded read.
    """

    reason: SnapshotRefusalReason
    what: str
    why: str
    how: str


class FileSystemPort(ABC):
    """Port for file system operations."""

    def acquire_regular_snapshot(
        self, path: Path, *, role: str
    ) -> RegularFileSnapshot | SnapshotRefusal:
        """Acquire one byte-stable snapshot of a regular file, or refuse.

        The default implementation deliberately REFUSES rather than reading:
        acquisition requires a validated no-follow open capability that only
        the real filesystem adapter owns.  A permissive default would let an
        adapter copy share the very defect this operation exists to exclude.
        """
        return SnapshotRefusal(
            reason=SnapshotRefusalReason.UNSUPPORTED,
            what=f"this filesystem cannot acquire a {role} snapshot",
            why="only the real filesystem adapter owns no-follow acquisition",
            how="inject the real filesystem adapter (RealFileSystem)",
        )

    @abstractmethod
    def read_json(self, path: Path) -> dict:
        """Read and parse JSON file.

        Args:
            path: Absolute path to JSON file

        Returns:
            Parsed JSON data as dictionary

        Raises:
            FileNotFoundError: If file doesn't exist
            JSONDecodeError: If file is not valid JSON
        """
        pass

    @abstractmethod
    def write_json(self, path: Path, data: dict) -> None:
        """Write data as formatted JSON file.

        Args:
            path: Absolute path to target JSON file
            data: Dictionary to write as JSON
        """
        pass

    @abstractmethod
    def exists(self, path: Path) -> bool:
        """Check if path exists.

        Args:
            path: Path to check

        Returns:
            True if path exists
        """
        pass

    def read_bytes(self, path: Path) -> bytes:
        """Read exact bytes at a path for persistence and recovery checks."""
        return path.read_bytes()

    def replace_text_atomically(self, path: Path, text: bytes) -> None:
        """Publish complete canonical bytes with one same-directory replace."""
        temporary = path.with_name(f".{path.name}.tmp")
        mode = path.stat().st_mode
        created = False
        try:
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            flags |= getattr(os, "O_NOFOLLOW", 0)
            descriptor = os.open(temporary, flags, mode & 0o777)
            created = True
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(text)
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(temporary, mode)  # noqa: PTH101 - preserve os-level port seam
            os.replace(temporary, path)  # noqa: PTH105 - replace is the injected port seam
        finally:
            if created and temporary.exists():
                temporary.unlink()

    def snapshot_and_replace(self, path: Path, data: dict) -> Path:
        """Back up ``path`` then atomically replace it with JSON ``data``.

        The default implementation deliberately lives on the driven port so
        application services do not acquire a second, direct filesystem
        capability.  The backup is created before the temporary file can be
        published and is retained if replacement fails.
        """
        backup = self._next_backup_path(path)
        backup.write_bytes(self.read_bytes(path))
        temporary = path.with_name(f".{path.name}.nwave-tmp")
        try:
            payload = json.dumps(data, indent=2).encode("utf-8")
            with temporary.open("wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            temporary.replace(path)
            directory = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        except BaseException:
            if temporary.exists():
                temporary.unlink()
            raise
        return backup

    @staticmethod
    def _next_backup_path(path: Path) -> Path:
        candidate = path.with_name(f"{path.name}.bak")
        suffix = 0
        while candidate.exists():
            suffix += 1
            candidate = path.with_name(f"{path.name}.bak.{suffix}")
        return candidate


def _same_file_identity(first: os.stat_result, second: os.stat_result) -> bool:
    return (
        first.st_dev,
        first.st_ino,
        stat.S_IFMT(first.st_mode),
    ) == (
        second.st_dev,
        second.st_ino,
        stat.S_IFMT(second.st_mode),
    )


def _same_file_snapshot(first: os.stat_result, second: os.stat_result) -> bool:
    """True when identity and byte-relevant metadata stayed stable."""
    return _same_file_identity(first, second) and (
        first.st_size,
        first.st_mtime_ns,
        first.st_ctime_ns,
    ) == (
        second.st_size,
        second.st_mtime_ns,
        second.st_ctime_ns,
    )


class RealFileSystem(FileSystemPort):
    """Production implementation of file system operations.

    Wraps standard Python file I/O operations for JSON files.
    """

    def read_json(self, path: Path) -> dict:
        """Read and parse JSON file.

        Args:
            path: Absolute path to JSON file

        Returns:
            Parsed JSON data as dictionary

        Raises:
            FileNotFoundError: If file doesn't exist
            JSONDecodeError: If file is not valid JSON
        """
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def write_json(self, path: Path, data: dict) -> None:
        """Write data as formatted JSON file.

        Args:
            path: Absolute path to target JSON file
            data: Dictionary to write as JSON
        """
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def exists(self, path: Path) -> bool:
        """Check if path exists.

        Args:
            path: Path to check

        Returns:
            True if path exists
        """
        return path.exists()

    def acquire_regular_snapshot(
        self, path: Path, *, role: str
    ) -> RegularFileSnapshot | SnapshotRefusal:
        """Read one byte-stable snapshot from the same no-follow regular FD.

        No-follow is a CAPABILITY, not a flag that may silently degrade to
        ``0``: without it an ordinary open cannot bind the validated path to
        the opened file, so the file is never opened at all.

        Metadata brackets replacement and ordinary writes, but timestamps are
        not a byte oracle on every filesystem.  The last path observation is
        therefore followed by a second read from the still-open FD.  Equality
        with the first read is the linearization check, and the final read is
        the value the snapshot carries.  Mutation after that observation
        belongs to the downstream frozen-digest point-of-use comparison;
        perpetual path immutability is neither possible nor claimed here.
        """
        no_follow = getattr(os, "O_NOFOLLOW", None)
        if no_follow is None:
            return SnapshotRefusal(
                reason=SnapshotRefusalReason.NO_FOLLOW_UNAVAILABLE,
                what=f"this platform has no no-follow open capability for the {role}",
                why=(
                    "an ordinary open cannot bind the validated path to the "
                    "opened file, so no closure member may be opened at all"
                ),
                how=(
                    "run this DES step on a platform whose os module exposes O_NOFOLLOW"
                ),
            )
        try:
            before = path.lstat()
            flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | no_follow
            descriptor = os.open(path, flags)
        except OSError as exc:
            return SnapshotRefusal(
                reason=SnapshotRefusalReason.UNOPENABLE,
                what=f"the {role} cannot be opened without following links ({exc})",
                why=f"delivery closure requires stable readable {role} bytes",
                how=f"replace the {role} with a readable regular file and rerun",
            )
        try:
            opened = os.fstat(descriptor)
            if not stat.S_ISREG(opened.st_mode) or not _same_file_snapshot(
                before, opened
            ):
                return self._identity_changed(role, "opened")
            stream = os.fdopen(descriptor, "rb", closefd=True)
            descriptor = -1
            return self._stable_snapshot(stream, path, opened=opened, role=role)
        except OSError as exc:
            return SnapshotRefusal(
                reason=SnapshotRefusalReason.UNREADABLE,
                what=f"the {role} cannot be read ({exc})",
                why=f"delivery closure requires readable {role} bytes",
                how="fix the file permissions and rerun the same DES step",
            )
        finally:
            if descriptor >= 0:
                os.close(descriptor)

    def _stable_snapshot(
        self, stream, path: Path, *, opened: os.stat_result, role: str
    ) -> RegularFileSnapshot | SnapshotRefusal:
        with stream:
            first_content = stream.read()
            after_first_read = os.fstat(stream.fileno())
            after_path = path.lstat()
            if not _same_file_snapshot(
                opened, after_first_read
            ) or not _same_file_snapshot(after_first_read, after_path):
                return self._identity_changed(role, "read")

            stream.seek(0, os.SEEK_SET)
            before_final_read = os.fstat(stream.fileno())
            final_content = stream.read()
            after_final_read = os.fstat(stream.fileno())
            if not _same_file_snapshot(
                after_path, before_final_read
            ) or not _same_file_snapshot(before_final_read, after_final_read):
                return self._identity_changed(role, "read")
            if first_content != final_content:
                return SnapshotRefusal(
                    reason=SnapshotRefusalReason.BYTES_CHANGED,
                    what=f"the {role} bytes changed while it was read",
                    why="delivery closure requires one byte-stable observation",
                    how=f"stop concurrent mutation of the {role} and rerun",
                )
            return RegularFileSnapshot(
                path=path,
                content=final_content,
                mode=after_final_read.st_mode,
            )

    @staticmethod
    def _identity_changed(role: str, phase: str) -> SnapshotRefusal:
        why = (
            "path validation and byte reading must bind the same regular file"
            if phase == "opened"
            else "closure bytes must belong to the declared stable locator"
        )
        return SnapshotRefusal(
            reason=SnapshotRefusalReason.IDENTITY_CHANGED,
            what=f"the {role} identity changed while it was {phase}",
            why=why,
            how="stop concurrent replacement of the file and rerun",
        )


#: A pure tag-shape transform. Never mutates its input.
_Transform = Callable[[dict[str, Any]], dict[str, Any]]


class WorkflowMigrationOutcome(str, Enum):
    """The three, and only three, outcomes Layer 2 classification can reach.

    No fourth "guessed" state is constructible (ADR-AUM-001 Decision 4 /
    obligation INVALID_STATE): a workflow artifact is either not yet
    inspected (``PENDING``), successfully reshaped onto the target tag
    (``MIGRATED``), or has no registered path and is refused rather than
    guessed (``INDETERMINATE``).
    """

    PENDING = "Pending"
    MIGRATED = "Migrated"
    INDETERMINATE = "Indeterminate"


class WorkflowShapeUnmappable(Exception):
    """A doc's declared shape tag has no registered forward map.

    Raised by ``apply_workflow_migration`` -- never silently swallowed into a
    returned sentinel, never a bare ``KeyError`` leaking out of an unguarded
    dict lookup (ADR-AUM-001 Four-layer failure laws table, Domain row).
    """

    def __init__(self, tag: object, to_tag: str, registered: tuple[str, ...]) -> None:
        self.tag = tag
        self.to_tag = to_tag
        super().__init__(
            f"WHAT: a workflow artifact declares shape tag {tag!r}, which has "
            f"no registered forward map toward {to_tag!r}. "
            "WHY: apply_workflow_migration only transforms tags a "
            f"WorkflowMigrationMap explicitly registers -- the known forward "
            f"tags for this map are {registered!r}. "
            "HOW: register a forward map for this tag in the owning "
            "WorkflowMigrationMap, or leave the artifact unmigrated and "
            "report it Indeterminate rather than guessing its shape."
        )

    def with_details(self, details: str) -> WorkflowShapeUnmappable:
        """Attach field evidence while retaining the WHAT/WHY/HOW diagnosis."""
        self.args = (f"{self.args[0]} DETAIL: {details}.",)
        return self


@dataclass(frozen=True)
class WorkflowMigrationMap:
    """A many-to-one shape-tag migration: several legacy tags collapse onto one target.

    ``to_tag`` is the single target shape tag. ``forward`` maps each
    registered source tag to the pure ``dict -> dict`` transform reshaping a
    doc from that tag's shape into ``to_tag``'s shape. Build one instance at
    the driven-adapter call site that owns a family's registrations --
    mirrors ``ArtifactVersioningKernel``, no I/O, no globals.
    """

    to_tag: str
    forward: Mapping[str, _Transform] = field(default_factory=dict)
    legacy_fields: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    required_fields: tuple[str, ...] = ()

    def can_migrate(self, tag: object) -> bool:
        """Whether ``tag`` has a registered forward transform toward ``to_tag``."""
        return isinstance(tag, str) and tag in self.forward


def apply_workflow_migration(
    doc: Mapping[str, Any], tag: object, migration_map: WorkflowMigrationMap
) -> dict[str, Any]:
    """Pure ``dict -> dict``: reshape ``doc`` (declared shape ``tag``) to ``migration_map.to_tag``.

    Never mutates ``doc``. Raises ``WorkflowShapeUnmappable`` for a tag with
    no registered forward transform.
    """
    if tag == migration_map.to_tag:
        return dict(doc)
    if not migration_map.can_migrate(tag):
        raise WorkflowShapeUnmappable(
            tag, migration_map.to_tag, tuple(migration_map.forward)
        )
    source_fields = set(doc)
    mapped_fields = set(migration_map.legacy_fields)
    invalid_names = [
        name for name in mapped_fields if not isinstance(name, str) or not name
    ]
    if invalid_names:
        raise WorkflowShapeUnmappable(
            tag, migration_map.to_tag, tuple(migration_map.forward)
        ).with_details(
            f"legacy-field map contains empty or invalid names {invalid_names!r}"
        )
    missing = sorted(set(migration_map.required_fields) - source_fields)
    unknown = sorted(source_fields - mapped_fields)
    if missing or unknown or not migration_map.legacy_fields:
        details = []
        if missing:
            details.append(f"missing required source fields {missing!r}")
        if unknown:
            details.append(f"unknown legacy fields {unknown!r}")
        if not migration_map.legacy_fields:
            details.append("the installed legacy-field map is empty")
        raise WorkflowShapeUnmappable(
            tag,
            migration_map.to_tag,
            tuple(migration_map.forward),
        ).with_details("; ".join(details))
    transform = migration_map.forward[tag]  # type: ignore[index]
    result = transform(dict(doc))
    for field_name, disposition in migration_map.legacy_fields.items():
        if field_name not in result:
            continue
        if not isinstance(disposition, Mapping):
            raise WorkflowShapeUnmappable(
                tag, migration_map.to_tag, tuple(migration_map.forward)
            ).with_details(f"field {field_name!r} has no valid disposition")
        kind = disposition.get("disposition")
        destination = disposition.get("destination")
        if kind == "transform" and not isinstance(disposition.get("rule"), str):
            raise WorkflowShapeUnmappable(
                tag, migration_map.to_tag, tuple(migration_map.forward)
            ).with_details(f"field {field_name!r} has no named transform rule")
        if kind in {"copy", "transform"}:
            if not isinstance(destination, str) or not destination:
                raise WorkflowShapeUnmappable(
                    tag, migration_map.to_tag, tuple(migration_map.forward)
                ).with_details(f"field {field_name!r} has no named destination")
            if destination != field_name:
                result[destination] = result[field_name]
        elif kind == "retire":
            if not isinstance(destination, str) or not destination:
                raise WorkflowShapeUnmappable(
                    tag, migration_map.to_tag, tuple(migration_map.forward)
                ).with_details(
                    f"retired field {field_name!r} has no preservation destination"
                )
            result[destination] = result[field_name]
            if destination != field_name:
                del result[field_name]
        else:
            raise WorkflowShapeUnmappable(
                tag, migration_map.to_tag, tuple(migration_map.forward)
            ).with_details(f"field {field_name!r} has unknown disposition {kind!r}")
    result["tag"] = migration_map.to_tag
    return result


class WorkflowTransitionCatalogError(Exception):
    """A packaged transition graph cannot safely determine one migration route."""

    def __init__(self, reason: str) -> None:
        super().__init__(
            "WHAT: the packaged workflow-transition catalog is invalid. "
            f"WHY: {reason}. "
            "HOW: publish one well-formed acyclic catalog with a single "
            "terminal and exactly one outgoing transition per source."
        )


@dataclass(frozen=True)
class WorkflowTransitionCatalog:
    """Pure topology over immutable per-edge workflow migration maps."""

    transitions: tuple[WorkflowMigrationMap, ...]
    malformed_reason: str | None = None

    def route_from(self, tag: object) -> tuple[WorkflowMigrationMap, ...]:
        """Return the sole ordered route from ``tag`` to the catalog terminal."""
        by_source, terminal = self._validated_graph()
        if not isinstance(tag, str) or (tag not in by_source and tag != terminal):
            raise WorkflowTransitionCatalogError(
                f"unknown source tag {tag!r} has no route to terminal {terminal!r}"
            )
        route: list[WorkflowMigrationMap] = []
        current = tag
        while current != terminal:
            transition = by_source[current]
            route.append(transition)
            current = transition.to_tag
        return tuple(route)

    def _validated_graph(
        self,
    ) -> tuple[dict[str, WorkflowMigrationMap], str]:
        if self.malformed_reason is not None:
            raise WorkflowTransitionCatalogError(
                f"malformed catalog: {self.malformed_reason}"
            )
        if not self.transitions:
            raise WorkflowTransitionCatalogError(
                "malformed catalog: it has no transitions"
            )

        by_source: dict[str, WorkflowMigrationMap] = {}
        destinations: set[str] = set()
        for transition in self.transitions:
            if not isinstance(transition.to_tag, str) or not transition.to_tag:
                raise WorkflowTransitionCatalogError(
                    "malformed catalog: an edge has no target tag"
                )
            sources = tuple(transition.forward)
            if not sources or any(
                not isinstance(source, str) or not source for source in sources
            ):
                raise WorkflowTransitionCatalogError(
                    "malformed catalog: an edge has no source tag"
                )
            for source in sources:
                if source in by_source:
                    raise WorkflowTransitionCatalogError(
                        f"duplicate source tag {source!r} makes the route ambiguous"
                    )
                by_source[source] = transition
            destinations.add(transition.to_tag)

        self._reject_cycle(by_source)
        terminals = destinations - set(by_source)
        if len(terminals) != 1:
            raise WorkflowTransitionCatalogError(
                f"the catalog has {len(terminals)} terminal tags, not exactly one terminal"
            )
        return by_source, next(iter(terminals))

    @staticmethod
    def _reject_cycle(by_source: dict[str, WorkflowMigrationMap]) -> None:
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(source: str) -> None:
            if source in visiting:
                raise WorkflowTransitionCatalogError("the catalog contains a cycle")
            if source in visited:
                return
            visiting.add(source)
            target = by_source[source].to_tag
            if target in by_source:
                visit(target)
            visiting.remove(source)
            visited.add(source)

        for source in by_source:
            visit(source)


_MISSING = object()

# Mirrors the ALREADY-LANDED consumer (des_config.py:_GLOBAL_CONFIG_VERSIONING):
# one identity v0->v1 upcaster, current version 1. A second kernel instance
# here (rather than importing the private module-level one) keeps this
# service's own registrations self-contained, same discipline
# ArtifactVersioningKernel's docstring recommends (one instance per owning
# call site).
_GLOBAL_CONFIG_ARTIFACT_TYPE = "global-config"


def _global_config_v0_to_v1(doc: dict[str, Any]) -> dict[str, Any]:
    """v0 (no schema-version key) -> v1. Identity: v1 only introduces the key."""
    return dict(doc)


_GLOBAL_CONFIG_KERNEL = ArtifactVersioningKernel(
    upcasters={_GLOBAL_CONFIG_ARTIFACT_TYPE: (_global_config_v0_to_v1,)}
)


def _is_kernel_int(raw: Any) -> bool:
    """A non-negative, non-bool int suitable for the kernel's chain index."""
    return isinstance(raw, int) and not isinstance(raw, bool) and raw >= 0


def _is_global_config(root: Path, path: Path) -> bool:
    return path == root / ".nwave" / "config.json"


def _is_expectation_charter(root: Path, path: Path) -> bool:
    return path.parent == root / ".nwave" / "expectation-charters"


@dataclass(frozen=True)
class ArtifactClassification:
    """One discovered artifact's discovery+classification row (obligation 6)."""

    path: Path
    declared_version_display: str
    kernel_readable: bool
    status: str
    planned_action: str
    reason: str


@dataclass(frozen=True)
class DryRunPlan:
    """Zero-write plan: every discovered artifact, classified. Never mutates.

    The Plan-value pattern (dry_run/preview functions return a value, never
    a side effect) makes "preview wrote to disk" structurally impossible to
    observe from this type alone.
    """

    classifications: tuple[ArtifactClassification, ...]


@dataclass(frozen=True)
class ApplyPlan:
    """Validated replacements; constructing this value performs no writes."""

    replacements: tuple[tuple[Path, dict[str, Any]], ...]


class AutoUpdateMigrationService:
    """Owns discovery, validation, and persistence for registered families."""

    def __init__(
        self,
        filesystem: FileSystemPort,
        *,
        workflow_transition_catalog: WorkflowTransitionCatalog | None = None,
    ) -> None:
        self._filesystem = filesystem
        self._workflow_transition_catalog = workflow_transition_catalog

    def dry_run(self, root: Path) -> DryRunPlan:
        """Discover + classify every artifact under ``root/.nwave``. Never writes.

        A registered type from a future runtime refuses with its path.
        """
        classifications = tuple(
            self._classify(root, path) for path in self._discover(root)
        )
        return DryRunPlan(classifications=classifications)

    def apply(self, root: Path) -> tuple[Path, ...]:
        """Validate the complete batch, then snapshot-and-replace its members."""
        plan = self._plan_apply(root)
        replaced: list[Path] = []
        for path, data in plan.replacements:
            self._filesystem.snapshot_and_replace(path, data)
            replaced.append(path)
        return tuple(replaced)

    def _plan_apply(self, root: Path) -> ApplyPlan:
        if not (root / ".nwave").is_dir():
            self._refuse(root, "the update root has no readable .nwave directory")
        replacements: list[tuple[Path, dict[str, Any]]] = []
        for path in self._discover(root):
            doc = self._read_document(path)
            if _is_expectation_charter(root, path):
                if doc.get("phase") == "COMPLETED":
                    continue
                self._validate_workflow_version(path, doc)
                tag = doc.get("tag")
                if self._workflow_transition_catalog is None:
                    self._refuse(
                        path, "the installed workflow-transition catalog is unavailable"
                    )
                assert self._workflow_transition_catalog is not None
                try:
                    route = self._workflow_transition_catalog.route_from(tag)
                    migrated = dict(doc)
                    current_tag = tag
                    for transition in route:
                        migrated = apply_workflow_migration(
                            migrated, current_tag, transition
                        )
                        current_tag = transition.to_tag
                except WorkflowTransitionCatalogError as exc:
                    raise WorkflowTransitionCatalogError(
                        f"artifact {path}: {exc}"
                    ) from exc
                except WorkflowShapeUnmappable as exc:
                    raise exc.with_details(f"path {path}") from exc
                if migrated != doc:
                    replacements.append((path, migrated))
                continue
            if _is_global_config(root, path):
                raw_version = doc.get("schema-version", _MISSING)
                if raw_version is not _MISSING and not _is_kernel_int(raw_version):
                    self._refuse(path, "schema-version is not a non-negative integer")
                migrated = self._upcast_global_config(path, doc)
                if migrated != doc:
                    replacements.append((path, migrated))
                continue
            self._refuse(path, "the artifact type has no registered migration path")
        return ApplyPlan(replacements=tuple(replacements))

    @staticmethod
    def _validate_workflow_version(path: Path, doc: dict[str, Any]) -> None:
        raw_version = doc.get("schema-version", _MISSING)
        if raw_version is _MISSING:
            AutoUpdateMigrationService._refuse(
                path, "the workflow artifact has no declared schema-version"
            )
        if not _is_kernel_int(raw_version):
            AutoUpdateMigrationService._refuse(
                path, "schema-version is not a non-negative integer"
            )

    def _read_document(self, path: Path) -> dict[str, Any]:
        try:
            doc = self._filesystem.read_json(path)
        except (json.JSONDecodeError, UnicodeError, OSError) as exc:
            self._refuse(path, f"JSON input cannot be read or parsed: {exc}")
        if not isinstance(doc, dict):
            self._refuse(
                path,
                f"JSON input must be an object; found {type(doc).__name__}",
            )
        return doc

    @staticmethod
    def _upcast_global_config(path: Path, doc: dict[str, Any]) -> dict[str, Any]:
        try:
            return _GLOBAL_CONFIG_KERNEL.upcast_to_current(
                doc, _GLOBAL_CONFIG_ARTIFACT_TYPE
            )
        except ArtifactFromFutureRuntime as exc:
            raise ValueError(f"artifact {path}: {exc}") from exc

    @staticmethod
    def _refuse(path: Path, reason: str) -> None:
        raise WorkflowShapeUnmappable(path, "current", (reason,))

    def _discover(self, root: Path) -> list[Path]:
        nwave_dir = root / ".nwave"
        if not nwave_dir.is_dir():
            return []
        return sorted(path for path in nwave_dir.rglob("*.json") if path.is_file())

    def _classify(self, root: Path, path: Path) -> ArtifactClassification:
        doc = self._read_document(path)
        raw_version = doc.get("schema-version", _MISSING)
        kernel_readable = raw_version is _MISSING or _is_kernel_int(raw_version)
        declared_display = "<absent>" if raw_version is _MISSING else repr(raw_version)

        if _is_global_config(root, path):
            return self._classify_global_config(
                path, doc, kernel_readable, declared_display
            )
        if _is_expectation_charter(root, path):
            return self._classify_expectation_charter(
                path, doc, kernel_readable, declared_display
            )
        return ArtifactClassification(
            path=path,
            declared_version_display=declared_display,
            kernel_readable=kernel_readable,
            status="Indeterminate",
            planned_action="Indeterminate",
            reason=(
                "artifact type is not registered with any known versioning "
                "family; declared value is reported verbatim, never coerced"
            ),
        )

    def _classify_global_config(
        self,
        path: Path,
        doc: dict[str, Any],
        kernel_readable: bool,
        declared_display: str,
    ) -> ArtifactClassification:
        raw_version = doc.get("schema-version", _MISSING)
        if (
            isinstance(raw_version, int)
            and not isinstance(raw_version, bool)
            and raw_version < 0
        ):
            self._refuse(
                path, "schema-version is negative; a non-negative integer is required"
            )
        if not kernel_readable:
            return ArtifactClassification(
                path=path,
                declared_version_display=declared_display,
                kernel_readable=False,
                status="Indeterminate",
                planned_action="Indeterminate",
                reason=(
                    "declared schema-version is present but not a well-typed "
                    "integer; never silently coerced or defaulted"
                ),
            )
        # Keep a future-version refusal attached to the artifact path.
        self._upcast_global_config(path, doc)
        current = _GLOBAL_CONFIG_KERNEL.current_version(_GLOBAL_CONFIG_ARTIFACT_TYPE)
        declared = read_version(doc)
        needs_upcast = declared < current
        return ArtifactClassification(
            path=path,
            declared_version_display=declared_display,
            kernel_readable=True,
            status="InFlight",
            planned_action="Upcast" if needs_upcast else "PreserveHistory",
            reason=(
                f"registered 'global-config' family, kernel current version "
                f"is {current}"
            ),
        )

    def _classify_expectation_charter(
        self,
        path: Path,
        doc: dict[str, Any],
        kernel_readable: bool,
        declared_display: str,
    ) -> ArtifactClassification:
        # Structural guard (Decision 6): a Completed artifact is classified
        # from its own declared terminal-phase field alone, before either
        # layer is consulted -- an unmappable tag on a Completed artifact
        # can therefore never raise.
        if doc.get("phase") == "COMPLETED":
            return ArtifactClassification(
                path=path,
                declared_version_display=declared_display,
                kernel_readable=kernel_readable,
                status="Completed",
                planned_action="PreserveHistory",
                reason=(
                    "declared terminal-phase is COMPLETED; never touched "
                    "regardless of shape tag (structural guard)"
                ),
            )
        tag = doc.get("tag")
        route_error: str | None = None
        try:
            route = (
                self._workflow_transition_catalog.route_from(tag)
                if self._workflow_transition_catalog is not None
                else None
            )
        except WorkflowTransitionCatalogError as exc:
            route = None
            route_error = str(exc)
        if route:
            planned_action = "Upcast"
            reason = (
                f"in flight; shape tag {tag!r} is resolved by the packaged "
                "workflow-transition catalog"
            )
        elif route == ():
            planned_action = "PreserveHistory"
            reason = "in flight; shape tag already equals the catalog terminal"
        else:
            planned_action = "Indeterminate"
            reason = route_error or (
                "in flight; no registered migration path for this "
                "artifact's declared shape -- never guessed"
            )
        return ArtifactClassification(
            path=path,
            declared_version_display=declared_display,
            kernel_readable=kernel_readable,
            status="InFlight",
            planned_action=planned_action,
            reason=reason,
        )
