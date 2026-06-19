"""Composition root for the F-07 multi-`Slice-Id:` batched-commit slice.

Friction F-07 (docs/analysis/atdd-pure-dogfooding-friction-2026-05-20.md).
Wires the PRODUCTION exit-gate CLI -- `des.cli.verify_slice_commit_completeness`
-- against a real git repository under pytest `tmp_path`.

Layer 3 (subprocess / FS / git acceptance): the driving port is the
`verify_slice_commit_completeness` CLI argv entry point; the only driven port
is the real filesystem + a real git repo under `tmp_path`. Example-only, no PBT
machinery (Mandate 9/11) -- sad paths are enumerated, never generated.

`verify_slice_commit_completeness` has a pure-read git contract: it reads
`git show` + `.feature` files and MUST NOT mutate the repository. The
`capture_universe` method exposes the observable git state so a `Then` step can
assert via `assert_state_delta` that the gate writes nothing (Mandate 8).

Business logic lives here as the single source of truth; step bodies delegate
to `MultiSliceComposition` methods and never inline logic (Mandate-12
criterion 3).

Regression contract (F-07): the multi-trailer scenarios FAIL on master --
`verify_slice_commit_completeness.extract_slice_id` returns only the FIRST
`Slice-Id:` trailer it finds, so a batched commit's later-listed slices are
never verified. They PASS once the F-07 fix lands (the gate verifies EVERY
listed slice). The single-trailer and zero-trailer scenarios are no-regression
pins -- they already pass on master and must keep passing.
"""

from __future__ import annotations

import contextlib
import io
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from des.cli.verify_slice_commit_completeness import (
    main as verify_slice_commit_completeness_main,
)

from .domain_types import ExitGateVerdict, SliceCoverage, SliceId, TrailerShape


# The slices an interleaved batched session covers. A real `@slice-NN`-tagged
# `.feature` file is authored per slice so the completeness gate has a true
# scenario set to match the commit against.
_SLICE_A = SliceId("slice-01")
_SLICE_B = SliceId("slice-02")
_BATCHED_SLICES = (_SLICE_A, _SLICE_B)


def _feature_text(slice_id: SliceId) -> str:
    """Minimal real Gherkin tagging `slice_id` -- a non-empty scenario set."""
    return (
        f"Feature: {slice_id} demo capability\n"
        "\n"
        f"  @{slice_id}\n"
        "  Scenario: the demo capability delivers its observable outcome\n"
        "    Given the demo precondition holds\n"
        "    When the operator triggers the demo capability\n"
        "    Then the demo outcome is observed\n"
    )


@dataclass
class CompletenessResult:
    """Observable outcome of one `verify_slice_commit_completeness` invocation.

    `verdict` is the user-observable ACCEPTED/REJECTED of the exit gate.
    `output` is the gate's single-line JSON payload -- the diagnostic surface a
    `Then` step inspects for the named missing slice.
    """

    exit_code: int
    output: str

    @property
    def verdict(self) -> ExitGateVerdict:
        """The gate accepts the commit iff it exits 0."""
        return (
            ExitGateVerdict.ACCEPTED
            if self.exit_code == 0
            else ExitGateVerdict.REJECTED
        )


@dataclass
class MultiSliceComposition:
    """Production-wired composition root for the F-07 multi-trailer slice.

    `repo_dir` is a real tmp_path directory initialised as a git repository.
    The two slices' `.feature` files, production code, and the batched
    `G_COMMIT` commit (with one of three trailer shapes, and either complete or
    one-slice-deficient AT coverage) are provisioned via the dedicated methods
    so each scenario builds exactly the commit state it needs.
    """

    repo_dir: Path
    _committed: bool = field(default=False)

    # --- repo lifecycle ------------------------------------------------------

    def create_repository(self) -> None:
        """Initialise a real git repository as the deliver project."""
        self.repo_dir.mkdir(parents=True, exist_ok=True)
        self._git("init", "--quiet")
        self._git("config", "user.email", "f07@example.test")
        self._git("config", "user.name", "F-07 AT")
        # A baseline commit so HEAD~1 exists and `git show` has a parent.
        (self.repo_dir / ".gitkeep").write_text("", encoding="utf-8")
        self._git("add", ".gitkeep")
        self._git("commit", "--quiet", "-m", "chore: baseline")

    def _feature_path(self, slice_id: SliceId) -> Path:
        """A slice's `.feature` AT file inside the repo working tree."""
        return self.repo_dir / "tests" / "acceptance" / f"{slice_id}_demo.feature"

    def _production_path(self, slice_id: SliceId) -> Path:
        """A slice's production-code file inside the repo working tree."""
        return self.repo_dir / "src" / f"{slice_id}_capability.py"

    # --- Given: build the batched slices' working tree -----------------------

    def author_batched_slices(self) -> None:
        """Author both slices' `.feature` AT files and production code on disk.

        Mirrors an interleaved session where DISTILL authored ATs for two
        slices and DELIVER wrote production code for both. Whether each slice's
        AT files reach the batched commit is decided by `commit_batched`.
        """
        for slice_id in _BATCHED_SLICES:
            feature_path = self._feature_path(slice_id)
            feature_path.parent.mkdir(parents=True, exist_ok=True)
            feature_path.write_text(_feature_text(slice_id), encoding="utf-8")
            production_path = self._production_path(slice_id)
            production_path.parent.mkdir(parents=True, exist_ok=True)
            production_path.write_text(
                f"def {slice_id.replace('-', '_')}_capability() -> str:\n"
                "    return 'demo outcome'\n",
                encoding="utf-8",
            )

    # --- When: produce the batched G_COMMIT commit ---------------------------

    def commit_batched(
        self, trailer_shape: TrailerShape, coverage: SliceCoverage
    ) -> None:
        """Create the interleaved-session `G_COMMIT` commit in the requested shape.

        `trailer_shape` decides which `Slice-Id:` trailer lines the commit
        message carries (the F-07 input axis). `coverage` decides whether every
        listed slice's `.feature` AT files are staged, or one slice's are held
        back (the completeness input axis).
        """
        self._stage_production_code()
        self._stage_feature_files(coverage)
        message = _COMMIT_MESSAGE_BUILDERS[trailer_shape]()
        self._git("commit", "--quiet", "-m", message)
        self._committed = True

    def _stage_production_code(self) -> None:
        """Stage both slices' production-code files into the index."""
        for slice_id in _BATCHED_SLICES:
            path = self._production_path(slice_id)
            self._git("add", str(path.relative_to(self.repo_dir)))

    def _stage_feature_files(self, coverage: SliceCoverage) -> None:
        """Stage the `.feature` AT files per the requested coverage shape."""
        staged = _STAGED_SLICES_BY_COVERAGE[coverage]
        for slice_id in staged:
            path = self._feature_path(slice_id)
            self._git("add", str(path.relative_to(self.repo_dir)))

    # --- exit-gate evaluation (driving port) ---------------------------------

    def evaluate_completeness_gate(self) -> CompletenessResult:
        """Evaluate `verify_slice_commit_completeness` over the batched commit.

        Invokes the production CLI through its argv entry point against the
        real git repo at HEAD -- the same surface the DES `G_COMMIT` exit gate
        invokes.
        """
        exit_code, output = self._invoke_cli(
            verify_slice_commit_completeness_main,
            ["--repo", str(self.repo_dir), "--commit", "HEAD"],
        )
        return CompletenessResult(exit_code=exit_code, output=output)

    # --- universe capture (Mandate 8) ----------------------------------------

    def capture_universe(self) -> dict[str, object]:
        """Port-exposed observable snapshot for assert_state_delta (Mandate 8).

        `verify_slice_commit_completeness` is pure-function: it reads
        `git show` + `.feature` files and MUST NOT mutate the repository. The
        universe is the observable git state -- the HEAD sha and the working
        tree cleanliness -- the state-delta guard proves the gate reads without
        writing or committing.
        """
        return {
            "git.head_sha": self._git("rev-parse", "HEAD").strip(),
            "git.status_porcelain": self._git("status", "--porcelain"),
        }

    # --- low-level helpers ---------------------------------------------------

    def _git(self, *args: str) -> str:
        """Run a git command inside the repo and return its stdout."""
        completed = subprocess.run(
            ["git", *args],
            cwd=self.repo_dir,
            capture_output=True,
            text=True,
            check=True,
        )
        return completed.stdout

    @staticmethod
    def _invoke_cli(entry, argv: list[str]) -> tuple[int, str]:
        """Invoke a CLI `main(argv)` capturing exit code + combined output."""
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
            exit_code = entry(argv)
        return exit_code, buffer.getvalue()


# --- module-level typed dispatch (Mandate-12 criterion 3) --------------------
# Keeping these as module-level dicts lets `commit_batched` stay control-flow
# free -- each branch is a typed lookup, not an `if`.

_COMMIT_HEADER = "feat(demo): batched interleaved slices\n\n"


def _single_trailer_message() -> str:
    """A commit message carrying exactly one `Slice-Id:` trailer (slice-01)."""
    return _COMMIT_HEADER + f"Slice-Id: {_SLICE_A}"


def _multiple_trailers_message() -> str:
    """A commit message carrying one `Slice-Id:` trailer line per batched slice.

    The F-07 shape: an interleaved batched commit lists every slice it covers
    as a separate `Slice-Id:` trailer line.
    """
    return _COMMIT_HEADER + "\n".join(
        f"Slice-Id: {slice_id}" for slice_id in _BATCHED_SLICES
    )


def _no_trailer_message() -> str:
    """A commit message carrying no `Slice-Id:`/`Step-Id:` trailer at all."""
    return _COMMIT_HEADER.rstrip()


_COMMIT_MESSAGE_BUILDERS = {
    TrailerShape.SINGLE: _single_trailer_message,
    TrailerShape.MULTIPLE: _multiple_trailers_message,
    TrailerShape.NONE: _no_trailer_message,
}

# Which slices' `.feature` AT files get staged into the batched commit.
# COMPLETE stages both; ONE_MISSING holds slice-02's AT file back -- it was
# authored on disk but never persisted into the commit.
_STAGED_SLICES_BY_COVERAGE = {
    SliceCoverage.COMPLETE: _BATCHED_SLICES,
    SliceCoverage.ONE_MISSING: (_SLICE_A,),
}

# The slice whose AT files ONE_MISSING holds back -- the deficient slice the
# exit-gate diagnostic must name.
DEFICIENT_SLICE: SliceId = _SLICE_B
