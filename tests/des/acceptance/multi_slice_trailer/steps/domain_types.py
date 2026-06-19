"""Domain types for the F-07 multi-`Slice-Id:` batched-commit regression slice.

Friction F-07 (docs/analysis/atdd-pure-dogfooding-friction-2026-05-20.md):
the per-slice `G_COMMIT` contract assumed one commit carrying a single
`Slice-Id: slice-NN` trailer, but the whole-tree-stashing pre-commit hook
forces interleaved multi-slice work to batch into ONE commit. A batched commit
has no single `Slice-Id:` and `verify_slice_commit_completeness` rejects it.

The intended fix this regression suite pins: the exit gate ACCEPTS a commit
carrying MULTIPLE `Slice-Id:` trailers (one trailer line per slice the batched
commit covers) and verifies slice-commit completeness for EACH listed slice.
A single-`Slice-Id:` commit keeps working unchanged; a zero-trailer commit is
still rejected `MalformedInput`.

Every domain noun used in the Gherkin is expressed once here as a typed enum or
NewType (Mandate-12 criterion 1). Step bodies and the composition service
consume these typed parameters -- no raw `str` where a domain enum exists.
"""

from __future__ import annotations

from enum import Enum
from typing import NewType


# A slice identifier as carried by a `Slice-Id:` / `Step-Id:` commit trailer
# (e.g. "slice-01").
SliceId = NewType("SliceId", str)


class TrailerShape(str, Enum):
    """The `Slice-Id:` trailer shape the batched `G_COMMIT` commit carries.

    SINGLE  -- exactly one `Slice-Id:` trailer line. The pre-F-07 happy path;
               pinned as a no-regression case.
    MULTIPLE -- two or more `Slice-Id:` trailer lines, one per slice the
               batched commit covers. The F-07 case the gate must learn to
               accept and verify per-listed-slice.
    NONE    -- no `Slice-Id:`/`Step-Id:` trailer at all. Still rejected as
               `MalformedInput` -- the gate cannot know which slices to verify.
    """

    SINGLE = "single"
    MULTIPLE = "multiple"
    NONE = "none"


class SliceCoverage(str, Enum):
    """Whether every listed slice's `.feature` AT files are in the commit.

    COMPLETE   -- every slice named by a `Slice-Id:` trailer has its
                  `@slice-NN`-tagged `.feature` files staged into the commit.
    ONE_MISSING -- one listed slice's `.feature` AT files were authored on disk
                  but never staged into the commit. The exit gate must reject
                  the commit and name the deficient slice.
    """

    COMPLETE = "complete"
    ONE_MISSING = "one_missing"


class ExitGateVerdict(str, Enum):
    """The user-observable verdict of the slice-commit-completeness exit gate.

    ACCEPTED -- the gate exited 0; every listed slice is complete. The batched
                commit certifies all the slices it lists.
    REJECTED -- the gate exited non-zero. Either a listed slice is incomplete
                (exit 1, names the slice) or the commit carries no trailer at
                all (exit 2, `MalformedInput`).
    """

    ACCEPTED = "accepted"
    REJECTED = "rejected"


# Gherkin-phrase -> typed-value lookups. Keeping these as module-level dicts
# lets each step body stay a single typed lookup + a single composition call
# (Mandate-12 criterion 3: no control flow in step bodies).

TRAILER_SHAPE_BY_PHRASE: dict[str, TrailerShape] = {
    "a single Slice-Id trailer": TrailerShape.SINGLE,
    "multiple Slice-Id trailers": TrailerShape.MULTIPLE,
    "no Slice-Id trailer": TrailerShape.NONE,
}

SLICE_COVERAGE_BY_PHRASE: dict[str, SliceCoverage] = {
    "every listed slice's acceptance-test files": SliceCoverage.COMPLETE,
    "one listed slice's acceptance-test files missing": SliceCoverage.ONE_MISSING,
}

VERDICT_BY_PHRASE: dict[str, ExitGateVerdict] = {
    "accepts the batched commit": ExitGateVerdict.ACCEPTED,
    "rejects the batched commit": ExitGateVerdict.REJECTED,
}
