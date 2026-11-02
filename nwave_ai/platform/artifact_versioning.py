"""Kernel: schema-version detection + per-type upcaster chains for persisted
JSON artifacts that DES rereads across sessions/releases.

Backlog: F-ARTIFACT-VERSIONING-UPCASTING (docs/product/backlog.md). Users
upgrading nWave between releases hit artifact-format changes mid-feature.
This kernel is the reusable, event-sourcing-style upcaster pattern Ale and
Attila agreed on the 2026-08-20 call: version every persisted artifact, ship
one incremental upcaster function per shape change, and a consumer only ever
reads the LATEST shape.

Design:
  - A ``"schema-version"`` integer field. Absence of the key means version 0
    (a legacy, pre-versioning artifact) -- never an error.
  - A type's CURRENT version is the length of its registered upcaster chain.
  - Each upcaster is a pure ``dict -> dict`` function transforming EXACTLY
    v(n) -> v(n+1). ``upcast_to_current`` applies the SUFFIX of the chain
    starting at the doc's declared version, then stamps the final
    schema-version -- idempotent on a doc already at the current version.
  - A doc declaring a version GREATER than the runtime's known current
    version for its type (the file is newer than the runtime, e.g. after a
    downgrade) is refused LOUD via ``ArtifactFromFutureRuntime`` -- never
    silently truncated or ignored (GDP-6: no silent-wrong).

No filesystem I/O and no module-level mutable registry here: an
``ArtifactVersioningKernel`` is a plain, constructor-injected value built
once by the driven-adapter call site that owns a type's registrations. This
keeps the kernel pure (safe to sit in ``domain/``, same rationale as
``telemetry_paths.py``) and keeps tests free of cross-test global-state
pollution -- each test builds its own throwaway kernel with fake types.

Naming convention note: this kernel standardizes on the HYPHENATED
``"schema-version"`` key, matching the existing ``DeliveryContract`` field
(``compile_contract.py``'s ``SCHEMA_VERSION`` / ``"schema-version"``) -- the
one artifact type in this tree already versioned before this kernel existed.
Two PRE-EXISTING, UNRELATED underscored ``"schema_version"`` conventions
also exist (``schema_version_detector.py``'s legacy TDD step-file phase
cycling, and ``repo_source_probe.py``'s freshness/repo-source manifest) --
both out of this kernel's scope; do not conflate them with this key.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any


#: The field name every versioned artifact declares its shape version under.
SCHEMA_VERSION_KEY = "schema-version"

#: A pure v(n) -> v(n+1) transform. Never mutates its input.
Upcaster = Callable[[dict[str, Any]], dict[str, Any]]


class ArtifactFromFutureRuntime(Exception):
    """A doc's schema-version exceeds this runtime's known current version.

    Raised by ``ArtifactVersioningKernel.upcast_to_current`` -- never
    silently truncated, never ignored (GDP-6).
    """

    def __init__(
        self, artifact_type: str, doc_version: int, runtime_version: int
    ) -> None:
        self.artifact_type = artifact_type
        self.doc_version = doc_version
        self.runtime_version = runtime_version
        super().__init__(
            f"WHAT: a '{artifact_type}' artifact declares "
            f"{SCHEMA_VERSION_KEY}={doc_version}, newer than this runtime's "
            f"known current version ({runtime_version}) for that type. "
            "WHY: this runtime has no upcaster past its own current "
            "version, so reading the file as-is would silently drop or "
            "misinterpret whatever fields the newer shape added -- "
            "downgrade is not supported. "
            "HOW: update nWave to a release that knows "
            f"{SCHEMA_VERSION_KEY}={doc_version} for '{artifact_type}', or "
            "restore this file from a copy written by a runtime at or "
            f"below version {runtime_version}."
        )


def read_version(doc: Mapping[str, Any]) -> int:
    """The doc's declared schema-version; a missing key is version 0.

    A present-but-non-int value (including ``bool``, which is an ``int``
    subclass in Python but never a meaningful version) also degrades to 0
    rather than raising -- a malformed version field is treated as "no
    version declared", the same fail-open posture ``DESConfig`` uses
    elsewhere in this tree for malformed config values.
    """
    raw = doc.get(SCHEMA_VERSION_KEY, 0)
    if isinstance(raw, bool) or not isinstance(raw, int):
        return 0
    return raw


@dataclass(frozen=True)
class ArtifactVersioningKernel:
    """Per-artifact-type upcaster chains, dict-in/dict-out, no I/O, no globals.

    ``upcasters`` maps an artifact type name to its ORDERED chain of pure
    v(n) -> v(n+1) functions; the chain length IS that type's current
    version. Build one instance at the driven-adapter call site that owns a
    type's registrations (e.g. one per config/receipt reader module); an
    unregistered type behaves as "current version 0, no upcasters" rather
    than raising, so a caller may probe a not-yet-versioned type safely.
    """

    upcasters: Mapping[str, Sequence[Upcaster]] = field(default_factory=dict)

    def current_version(self, artifact_type: str) -> int:
        """The latest known version for ``artifact_type``; 0 if unregistered."""
        return len(self.upcasters.get(artifact_type, ()))

    def upcast_to_current(
        self, doc: Mapping[str, Any], artifact_type: str
    ) -> dict[str, Any]:
        """Return ``doc`` upcast to ``artifact_type``'s current shape.

        Applies the suffix of the registered chain starting at the doc's own
        declared version, then stamps the resulting schema-version. Never
        mutates ``doc``. Idempotent: a doc already at the current version is
        returned with identical content (schema-version re-stamped to the
        same value).

        Raises ``ArtifactFromFutureRuntime`` when the doc's declared version
        exceeds this kernel's current version for the type -- the doc is a
        file written by a newer runtime than this one.
        """
        doc_version = read_version(doc)
        chain = tuple(self.upcasters.get(artifact_type, ()))
        latest = len(chain)
        if doc_version > latest:
            raise ArtifactFromFutureRuntime(artifact_type, doc_version, latest)
        result: dict[str, Any] = dict(doc)
        for upcaster in chain[doc_version:]:
            result = upcaster(result)
        result[SCHEMA_VERSION_KEY] = latest
        return result
