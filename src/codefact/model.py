"""Immutable values shared by code-fact providers and their resolution fold."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import TypeAlias


class Confidence(str, Enum):
    APPROX = "approx"
    BINDING_RESOLVED = "binding-resolved"
    NOISY = "noisy"


class ReasonCode(str, Enum):
    LIVE_NON_CALLABLE = "live-non-callable"
    ABSENT = "absent"


CAPABILITY_CALLERS_OF = "query.callers-of"
CAPABILITY_READS_OF = "query.reads-of"
CAPABILITY_NEVER_WIRED = "query.never-wired"
CAPABILITY_ATOMS_IN_FILE = "query.atoms-in-file"
CAPABILITY_ADR_SECTION = "query.adr-section"
CAPABILITY_SIMILAR_RESPONSIBILITY = "query.similar-responsibility"
STABLE_CORE_CAPABILITY_IDS = frozenset(
    {
        CAPABILITY_CALLERS_OF,
        CAPABILITY_READS_OF,
        CAPABILITY_NEVER_WIRED,
        CAPABILITY_ATOMS_IN_FILE,
        CAPABILITY_ADR_SECTION,
    }
)
TRACE_DETAIL_MAX_CHARS = 200
TRACE_EXEMPLARS_MAX = 3
REFERENCE_SHAPES = ("bare-name", "dotted-attribute")
D3_CAUSES = frozenset(
    {
        "unreadable-target",
        "unparseable-source",
        "out-of-scope-language",
        "provider-error",
        "provider-timeout",
        "unrepresented-reference-shape",
    }
)
Request: TypeAlias = Mapping[str, object]


@dataclass(frozen=True)
class Capability:
    id: str
    stability: str = "stable"
    contract_version: str = "1.0.0"
    io_schema: str = "code-fact.v1"
    providing_adapter: str = "negotiated"


@dataclass(frozen=True)
class Source:
    content: bytes | None
    mtime: float


@dataclass(frozen=True)
class Snapshot:
    root: str
    entries: Mapping[str, Source] = field(default_factory=dict)
    file_root: bool = False
    pruned: bool = False
    index_root: str = ""
    index_entries: Mapping[str, Source] = field(default_factory=dict)
    display_root: str | None = None

    def absolute(self, relative: str) -> str:
        return self.root if self.file_root else self.root.rstrip("/") + "/" + relative

    def location(self, relative: str) -> str:
        root = self.root if self.display_root is None else self.display_root
        if self.file_root:
            return root
        return relative if root == "." else root.rstrip("/") + "/" + relative


@dataclass(frozen=True)
class Coverage:
    missing: tuple[str, ...] = ()
    stale: tuple[str, ...] = ()
    empty_unindexed: tuple[str, ...] = ()

    @classmethod
    def complete(cls) -> Coverage:
        return cls()

    def uncovered(self) -> tuple[str, ...]:
        return tuple(sorted(set(self.missing + self.stale)))

    def is_complete(self) -> bool:
        return not self.uncovered()


@dataclass(frozen=True)
class IndexPresent:
    graph_sha256: str
    manifest_sha256: str
    indexed_files: int
    kind: str = field(default="present", init=False)


@dataclass(frozen=True)
class LiveSource:
    kind: str = field(default="live-source", init=False)


IndexSnapshot: TypeAlias = IndexPresent | LiveSource


@dataclass(frozen=True)
class TraceEntry:
    provider_id: str
    event: str
    scope: str = "complete"
    fault_count: int = 0
    exemplars: tuple[str, ...] = ()
    detail: str = ""

    def __post_init__(self) -> None:
        invalid = (
            "provider_id"
            if not self.provider_id.strip()
            else "event"
            if self.event
            not in {
                "answered",
                "attempted",
                *("failed:" + cause for cause in D3_CAUSES),
            }
            else "scope"
            if self.scope not in {"complete", "filtered", "unfiltered"}
            else "fault_count"
            if self.fault_count < 0
            else "exemplars"
            if len(self.exemplars) > TRACE_EXEMPLARS_MAX
            else "detail"
            if len(self.detail) > TRACE_DETAIL_MAX_CHARS
            else None
        )
        if invalid:
            raise ValueError(
                f"WHAT: invalid TraceEntry.{invalid}. WHY: traces have a closed vocabulary and finite bounds. HOW: supply an admitted value within the trace bounds."
            )


@dataclass(frozen=True)
class Answers:
    confidence: str
    represents: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.confidence not in {c.value for c in Confidence}:
            raise ValueError(
                "WHAT: invalid confidence. WHY: confidence is closed. HOW: use a Confidence value."
            )


@dataclass(frozen=True)
class Stale:
    index: IndexSnapshot
    coverage: Coverage

    def uncovered(self) -> tuple[str, ...]:
        return self.coverage.uncovered()


@dataclass(frozen=True)
class Passes:
    cause: str | None = None


Cover: TypeAlias = Answers | Stale | Passes


@dataclass(frozen=True)
class Reply:
    payload: object
    evidence_count: int | None = None
    fault_count: int = 0
    exemplars: tuple[str, ...] = ()
    scope: str = "complete"
    index: IndexSnapshot = field(default_factory=LiveSource)
    coverage: Coverage = field(default_factory=Coverage.complete)


@dataclass(frozen=True)
class Fault:
    cause: str
    fault_count: int = 0
    exemplars: tuple[str, ...] = ()
    scope: str = "complete"


@dataclass(frozen=True)
class Provider:
    id: str
    cover: Callable[[Capability, Request, Snapshot], Cover]
    answer: Callable[[Capability, Request, Snapshot], Reply | Fault]


@dataclass(frozen=True)
class Answered:
    provider_id: str
    confidence: str
    payload: object
    trace: tuple[TraceEntry, ...]
    index: IndexSnapshot = field(default_factory=LiveSource)
    coverage: Coverage = field(default_factory=Coverage.complete)
    evidence_count: int | None = None


@dataclass(frozen=True)
class Indeterminate:
    provider_id: str
    index: IndexSnapshot
    coverage: Coverage
    trace: tuple[TraceEntry, ...]

    def uncovered(self) -> tuple[str, ...]:
        return self.coverage.uncovered()


@dataclass(frozen=True)
class Unsupported:
    capability_id: str
    consulted: tuple[str, ...]
    trace: tuple[TraceEntry, ...] = ()


@dataclass(frozen=True)
class Failed:
    cause: str
    trace: tuple[TraceEntry, ...] = ()


Resolution: TypeAlias = Answered | Indeterminate | Unsupported | Failed


@dataclass(frozen=True)
class Refreshed:
    index: IndexPresent
    coverage: Coverage


@dataclass(frozen=True)
class RefreshRefused:
    reason: str


@dataclass(frozen=True)
class RefreshIndeterminate:
    changed: tuple[str, ...]
    reason: str = "index changed during refresh"


RefreshOutcome: TypeAlias = Refreshed | RefreshRefused | RefreshIndeterminate


def observation_count(payload: object) -> int | None:
    if not isinstance(payload, dict):
        return None
    counts = tuple(
        len(v)
        for k, v in payload.items()
        if k
        in {
            "sites",
            "call_sites",
            "read_sites",
            "atoms",
            "files",
            "candidates",
            "matches",
        }
        and isinstance(v, list)
    )
    return sum(counts) if counts else None
