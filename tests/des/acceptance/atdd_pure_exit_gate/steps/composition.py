"""Composition root for the slice-14 G_COMMIT exit-gate acceptance slice.

slice-14 of the atdd-pure-roadmap-free-rollout (Mandate-12, Pillar 3). Wires the
PRODUCTION exit-gate CLIs against a real git repository under pytest `tmp_path`:

  E1 -- `des.cli.verify_slice_commit_completeness.main` (slice-commit
        completeness; git-aware; pure-function).
  E2 -- `des.cli.run_contract_gate.main` (the canonical contract gate;
        emits a `gate_scope_digest`; `--collect-only` digest-only path).

The `G_COMMIT` DES exit gate is the conjunction of E1 and E2: a slice reaches
COMMIT/PASS only if BOTH hold. The DES gate object itself is wired in the
ATDD-pure workflow YAML by slice-14; this composition exercises the gate's two
assertions through their CLIs -- the same surfaces the DES gate invokes -- so
the ATs are honest regardless of the YAML wiring detail.

Layer 3 (subprocess / FS / git acceptance): the driving port is the exit-gate
CLI set; the only driven port is the real filesystem + a real git repo under
`tmp_path`. Example-only, no PBT machinery (Mandate 9/11).

Business logic lives here as the single source of truth; step bodies delegate
to `ExitGateComposition` methods and never inline logic (Mandate-12 criterion 3).

Regression contract: the slice-14 ATs FAIL on master -- `des.cli.run_contract_gate`
and `des.cli.verify_slice_commit_completeness` do not exist as working CLIs
(they are RED scaffolds whose `main()` raises AssertionError). They PASS once
slice-14 lands.
"""

from __future__ import annotations

import contextlib
import io
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from des.cli.run_contract_gate import main as run_contract_gate_main
from des.cli.verify_slice_commit_completeness import (
    main as verify_slice_commit_completeness_main,
)

from .domain_types import (
    CommitFeatureContent,
    ExitGateVerdict,
    FeatureId,
    GateScopeDigestState,
    SliceId,
)


# The slice this acceptance suite builds commits for. A real `@slice-NN`-tagged
# `.feature` file is created in the repo so the completeness gate has a true
# scenario set to match the commit against.
_DEMO_SLICE = SliceId("slice-99")

# A `@slice-99` scenario the demo `.feature` file declares -- minimal but real
# Gherkin so `verify_slice_commit_completeness` parses a non-empty scenario set.
_DEMO_FEATURE_TEXT = """\
Feature: slice-99 demo capability

  @slice-99
  Scenario: the demo capability delivers its observable outcome
    Given the demo precondition holds
    When the operator triggers the demo capability
    Then the demo outcome is observed
"""

# A stale `Gate-Scope:` digest -- a syntactically valid 64-hex string that does
# NOT match any fresh `run_contract_gate.py --collect-only` digest. Models a
# digest copied from a narrower crafter-picked subset run (RCA Branch B).
_STALE_DIGEST = "0" * 64


@dataclass
class ExitGateResult:
    """Observable outcome of one `G_COMMIT` exit-gate evaluation.

    `verdict` is the user-observable PASS/FAIL of the exit gate -- the
    conjunction of the E1 (completeness) and E2 (contract-gate-scope) checks.
    """

    e1_exit_code: int
    e1_output: str
    e2_exit_code: int
    e2_output: str

    @property
    def verdict(self) -> ExitGateVerdict:
        """The exit gate passes iff BOTH assertions return exit 0."""
        both_pass = self.e1_exit_code == 0 and self.e2_exit_code == 0
        return ExitGateVerdict.PASS if both_pass else ExitGateVerdict.FAIL

    @property
    def output(self) -> str:
        """Combined diagnostic output of both assertions."""
        return f"{self.e1_output}\n{self.e2_output}"


@dataclass
class ExitGateComposition:
    """Production-wired composition root for the slice-14 exit-gate slice.

    `repo_dir` is a real tmp_path directory initialised as a git repository.
    The demo slice's `.feature` file, the production code change, and the
    `G_COMMIT` commit (with or without its AT files, with one of three
    `Gate-Scope:` digest states) are provisioned via the dedicated methods so
    each scenario builds exactly the commit state it needs.
    """

    repo_dir: Path
    feature_id: FeatureId = field(default=FeatureId("atdd-pure-demo"))
    _committed = False

    # --- repo lifecycle ------------------------------------------------------

    def create_repository(self, feature_id: FeatureId) -> None:
        """Initialise a real git repository as the deliver project."""
        self.feature_id = feature_id
        self.repo_dir.mkdir(parents=True, exist_ok=True)
        self._git("init", "--quiet")
        self._git("config", "user.email", "slice14@example.test")
        self._git("config", "user.name", "Slice 14 AT")
        # A baseline commit so HEAD~1 exists and `git show` has a parent.
        (self.repo_dir / ".gitkeep").write_text("", encoding="utf-8")
        self._git("add", ".gitkeep")
        self._git("commit", "--quiet", "-m", "chore: baseline")

    @property
    def feature_path(self) -> Path:
        """The demo slice's `.feature` AT file inside the repo working tree."""
        return self.repo_dir / "tests" / "acceptance" / "slice_99_demo.feature"

    @property
    def production_path(self) -> Path:
        """The demo slice's production-code file inside the repo working tree."""
        return self.repo_dir / "src" / "demo_capability.py"

    # --- Given: build the slice's working tree -------------------------------

    def author_slice_at_files(self) -> None:
        """Author the demo slice's `@slice-99` `.feature` file in the working tree.

        This mirrors DISTILL authoring a slice's ATs on disk. Whether they reach
        the `G_COMMIT` commit is decided by `commit_g_commit`.
        """
        self.feature_path.parent.mkdir(parents=True, exist_ok=True)
        self.feature_path.write_text(_DEMO_FEATURE_TEXT, encoding="utf-8")

    def author_slice_production_code(self) -> None:
        """Author the demo slice's production-code change in the working tree."""
        self.production_path.parent.mkdir(parents=True, exist_ok=True)
        self.production_path.write_text(
            "def demo_capability() -> str:\n    return 'demo outcome'\n",
            encoding="utf-8",
        )

    # --- When: produce the G_COMMIT commit -----------------------------------

    def commit_g_commit(
        self,
        commit_content: CommitFeatureContent,
        digest_state: GateScopeDigestState,
    ) -> None:
        """Create the slice's `G_COMMIT` commit in the requested shape.

        `commit_content` decides whether the slice's `.feature` AT files are
        staged into the commit (E1 input). `digest_state` decides what
        `Gate-Scope:` trailer the commit message carries (E2 input).
        """
        self._git("add", str(self.production_path.relative_to(self.repo_dir)))
        if commit_content is CommitFeatureContent.AT_FILES_INCLUDED:
            self._git("add", str(self.feature_path.relative_to(self.repo_dir)))
        message = self._build_commit_message(digest_state)
        self._git("commit", "--quiet", "-m", message)
        self._committed = True

    def _build_commit_message(self, digest_state: GateScopeDigestState) -> str:
        """Compose the `G_COMMIT` commit message with the chosen trailers."""
        trailers = [f"Slice-Id: {_DEMO_SLICE}"]
        digest = self._resolve_gate_scope_digest(digest_state)
        if digest is not None:
            trailers.append(f"Gate-Scope: {digest}")
        return "feat(demo): slice-99 demo capability\n\n" + "\n".join(trailers)

    def _resolve_gate_scope_digest(
        self, digest_state: GateScopeDigestState
    ) -> str | None:
        """Resolve the `Gate-Scope:` digest value for the requested state.

        MATCHING -- a fresh `run_contract_gate.py --collect-only` digest.
        MISMATCH -- a stale 64-hex digest that matches no fresh digest.
        ABSENT   -- no `Gate-Scope:` trailer at all.
        """
        return _DIGEST_RESOLVERS[digest_state](self)

    def _fresh_collect_only_digest(self) -> str:
        """A fresh gate-scope digest from `run_contract_gate.py --collect-only`."""
        return self._run_contract_gate(["--collect-only", "--print-digest"])[1].strip()

    # --- exit-gate evaluation (driving port) ---------------------------------

    def evaluate_g_commit_exit_gate(self) -> ExitGateResult:
        """Evaluate the `G_COMMIT` DES exit gate over the produced commit.

        The exit gate is the conjunction of E1 (slice-commit completeness) and
        E2 (terminating run == contract gate). Both are invoked through their
        production CLIs against the real git repo -- the same surfaces the DES
        gate object invokes.
        """
        e1_code, e1_out = self._run_verify_completeness()
        e2_code, e2_out = self._run_verify_gate_scope()
        return ExitGateResult(
            e1_exit_code=e1_code,
            e1_output=e1_out,
            e2_exit_code=e2_code,
            e2_output=e2_out,
        )

    def _run_verify_completeness(self) -> tuple[int, str]:
        """E1: invoke `verify_slice_commit_completeness` for the HEAD commit."""
        return self._invoke_cli(
            verify_slice_commit_completeness_main,
            ["--repo", str(self.repo_dir), "--commit", "HEAD"],
        )

    def _run_verify_gate_scope(self) -> tuple[int, str]:
        """E2: verify the commit's `Gate-Scope:` digest matches a fresh digest."""
        return self._invoke_cli(
            run_contract_gate_main,
            ["--repo", str(self.repo_dir), "--commit", "HEAD", "--verify-gate-scope"],
        )

    def _run_contract_gate(self, extra_args: list[str]) -> tuple[int, str]:
        """Invoke `run_contract_gate` with `extra_args` against the repo."""
        return self._invoke_cli(
            run_contract_gate_main, ["--repo", str(self.repo_dir), *extra_args]
        )

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


# slice_id -> digest resolver. Module-level dispatch keeps `_resolve_gate_scope_digest`
# a single typed lookup with no control flow (Mandate-12 criterion 3).
_DIGEST_RESOLVERS = {
    GateScopeDigestState.MATCHING: ExitGateComposition._fresh_collect_only_digest,
    GateScopeDigestState.MISMATCH: lambda _self: _STALE_DIGEST,
    GateScopeDigestState.ABSENT: lambda _self: None,
}
