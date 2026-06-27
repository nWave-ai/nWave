"""Production composition root for the commit-author-identity acceptance suite.

Pillar 3 — "app as in production": the SUT is built from the real production
entry points, never re-implemented here. The four driving surfaces are:

  1. ``is_valid_author_email`` / ``is_valid_author_name`` — pure validator core
     (layer 1/2 in-memory acceptance; direct call, no I/O).
  2. ``validate_author_identity.main()`` — the pre-commit entry, run as a real
     ``git`` subprocess in an isolated ``tmp_path`` repo (layer 3).
  3. ``validate_push_identity.main()`` — the pre-push entry, fed a real ref line
     on stdin over the same isolated repo (layer 3).
  4. ``ci_author_check.main(argv)`` — the authoritative CI runner, driven over a
     commit range in the isolated repo, returning an exit code (layer 3).

The ONE environment substitution is the git repository itself: every git
subprocess runs inside a ``tmp_path`` repo whose ``HOME`` and
``GIT_CEILING_DIRECTORIES`` are redirected so it can NEVER touch the host
``.git/config`` (pairs with the ``tests/conftest.py`` ``_git_ceiling`` +
``_git_pollution_guard`` autouse fixtures). This is the driven-internal FS/git
port at layer 3 (example-based), exactly as the Architecture of Reference and
``docs/architecture/atdd-infrastructure-policy.md`` (``git`` probe row)
prescribe. Nothing is faked: there is no non-deterministic external port in this
feature (no clock/email/network), so there is nothing to substitute.

Production symbols are imported LAZILY inside methods so this module imports
cleanly today (tests COLLECT, never BROKEN). The validators at
``scripts/hooks/{validate_author_identity,validate_push_identity,ci_author_check}.py``
are implemented; the lazy imports resolve to the real functions and the gates
return real verdicts. The test-delta in this module adds NAME-validation and
robustness coverage that is EXPECTED-RED until the push/CI runners are extended
to validate author/committer NAMES (adversarial review R3-F1/F3).

Mandate-12 criteria:
- (2) every service method consumes the typed enums from ``domain_types`` — no
  raw ``str`` where a domain enum exists.
- (3) the step bodies in ``steps_commit_author_identity.py`` are ≤2 statements
  ending in ``composition.<method>(...)`` — all logic lives HERE and in
  production, never inlined in a step.
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from tests.des.acceptance.commit_author_identity.steps.domain_types import (
    ACCEPTED_EMAIL_CLASSES,
    EMAIL_REPRESENTATIVE,
    NAME_REPRESENTATIVE,
    CommitBypass,
    EmailClass,
    FieldRuling,
    GateOutcome,
    IdentityRole,
    NameClass,
    PushRangeShape,
    Verdict,
)


# Path to the shared validator module (DESIGN: scripts/hooks/, zero-shell).
_REPO_ROOT = Path(__file__).resolve().parents[5]
_VALIDATOR_SCRIPT = _REPO_ROOT / "scripts" / "hooks" / "validate_author_identity.py"
_PUSH_SCRIPT = _REPO_ROOT / "scripts" / "hooks" / "validate_push_identity.py"
_CI_SCRIPT = _REPO_ROOT / "scripts" / "hooks" / "ci_author_check.py"

_ZERO_SHA = "0" * 40


def _isolated_git_env(repo: Path) -> dict[str, str]:
    """Env that pins git to ``repo`` and forbids any escape to the host repo.

    ``HOME`` and ``GIT_CONFIG_*`` are redirected into the sandbox so no global
    identity leaks in; ``GIT_CEILING_DIRECTORIES`` stops rev-walk from climbing
    above ``tmp_path``. Identity is supplied per-commit via ``GIT_AUTHOR_*`` /
    ``GIT_COMMITTER_*`` so a test can stage a placeholder identity deliberately.
    """
    env = os.environ.copy()
    env["HOME"] = str(repo)
    env["GIT_CONFIG_GLOBAL"] = str(repo / ".gitconfig-global")
    env["GIT_CONFIG_SYSTEM"] = os.devnull
    env["GIT_CEILING_DIRECTORIES"] = str(repo.parent)
    env["GIT_TEMPLATE_DIR"] = ""
    env["PATH"] = env.get("PATH", "/usr/bin:/bin:/usr/local/bin")
    return env


# ---------------------------------------------------------------------------
# Captured-state record shared across steps (the pytest-bdd ``context`` dict
# replacement — a typed bag of observables the Then-steps assert against).
# ---------------------------------------------------------------------------


@dataclass
class IdentityWorld:
    """Mutable per-scenario state captured at the driving ports.

    Only port-exposed observables live here (exit codes, the validator's
    returned ``(verdict, reason)``, captured stderr) — never internal fields of
    the production validator.
    """

    repo: Path | None = None
    # validator-core observables
    email_ruling: FieldRuling | None = None
    name_ruling: FieldRuling | None = None
    # enforcement-layer observables
    exit_code: int | None = None
    captured_output: str = ""
    # staged-identity bookkeeping for the chained narrative (Pillar 2)
    staged_author_email: str | None = None
    staged_committer_email: str | None = None
    staged_author_name: str | None = None
    staged_committer_name: str | None = None
    range_commit_shas: list[str] = field(default_factory=list)


class IdentityComposition:
    """Wires the production validator + a real isolated git repo (Pillar 3)."""

    def __init__(self) -> None:
        self.world = IdentityWorld()

    # -- repo lifecycle -----------------------------------------------------

    def given_a_fresh_repository(self, tmp_path: Path) -> None:
        """Create an isolated git repo with a known-good baseline commit.

        The baseline is committed with a real allowlisted identity so the repo
        has an upstream to diff against; the offending identity is introduced
        only by the When-steps. No host ``.git`` is ever touched.
        """
        repo = tmp_path / "repo"
        repo.mkdir(parents=True, exist_ok=True)
        self._git(repo, "init", "-q", "-b", "main")
        self._git(repo, "config", "commit.gpgsign", "false")
        self._git(repo, "config", "user.useConfigOnly", "true")
        self._commit(
            repo,
            "chore: baseline",
            author_email="gearoid@users.noreply.github.com",
            author_name="Gearoid O'Treasaigh",
        )
        self.world.repo = repo

    # -- validator-core driving port (layer 1/2, pure) ----------------------

    def validate_email_of_class(self, email_class: EmailClass) -> FieldRuling:
        """Drive the pure ``is_valid_author_email`` over the class representative."""
        from scripts.hooks.validate_author_identity import is_valid_author_email

        literal = EMAIL_REPRESENTATIVE[email_class]
        ok, reason = is_valid_author_email(literal)
        ruling = FieldRuling(Verdict.ACCEPTED if ok else Verdict.REJECTED, reason)
        self.world.email_ruling = ruling
        return ruling

    def validate_name_of_class(self, name_class: NameClass) -> FieldRuling:
        """Drive the pure ``is_valid_author_name`` over the class representative."""
        from scripts.hooks.validate_author_identity import is_valid_author_name

        literal = NAME_REPRESENTATIVE[name_class]
        ok, reason = is_valid_author_name(literal)
        ruling = FieldRuling(Verdict.ACCEPTED if ok else Verdict.REJECTED, reason)
        self.world.name_ruling = ruling
        return ruling

    # -- pre-commit driving port (layer 3, real git) ------------------------

    def commit_with_identity(
        self,
        email_class: EmailClass,
        role: IdentityRole,
    ) -> None:
        """Stage a commit whose ``role`` identity is the class representative.

        The OTHER role is kept allowlisted, so the scenario isolates exactly one
        field — proving author and committer are checked independently.
        """
        repo = self._require_repo()
        good = "gearoid@users.noreply.github.com"
        offending = EMAIL_REPRESENTATIVE[email_class]
        author_email = offending if role is IdentityRole.AUTHOR else good
        committer_email = offending if role is IdentityRole.COMMITTER else good
        # The @precommit scenarios stage a placeholder EMAIL; the name stays a
        # valid one so the gate's verdict is driven by the email under test.
        # Both name + email are recorded so run_precommit_gate can supply the
        # PROSPECTIVE identity to the validator's `git var` exactly as the
        # pending commit would resolve it (pre-commit fires before the commit
        # object exists — research §2.4).
        valid_name = "Gearoid O'Treasaigh"
        self.world.staged_author_email = author_email
        self.world.staged_committer_email = committer_email
        self.world.staged_author_name = valid_name
        self.world.staged_committer_name = valid_name
        self._commit(
            repo,
            "feat: change with staged identity",
            author_email=author_email,
            committer_email=committer_email,
            author_name=valid_name,
        )

    def commit_with_author_name_of_class(self, name_class: NameClass) -> None:
        """Stage a commit whose author NAME is the class representative.

        The author + committer EMAILS are kept clean (allowlisted) so the gate's
        verdict is driven purely by the NAME field under test — proving the
        pre-commit name check exists and is independent of the email check
        (adversarial review H2). The PROSPECTIVE identity (name + emails, both
        roles) is recorded so ``run_precommit_gate`` supplies it to the
        validator's ``git var`` exactly as the pending commit would resolve it.
        """
        repo = self._require_repo()
        good = "gearoid@users.noreply.github.com"
        offending_name = NAME_REPRESENTATIVE[name_class]
        self.world.staged_author_email = good
        self.world.staged_committer_email = good
        self.world.staged_author_name = offending_name
        # committer name stays clean so only the AUTHOR name is under test.
        self.world.staged_committer_name = "Gearoid O'Treasaigh"
        self._commit(
            repo,
            "feat: change with placeholder author name",
            author_email=good,
            committer_email=good,
            author_name=offending_name,
        )

    def make_identity_unresolvable(self) -> None:
        """Put the repo in a state where git can resolve no identity at all.

        The baseline repo already carries ``user.useConfigOnly true``, and no
        ``user.email`` / ``user.name`` is configured repo-locally; with the
        per-call identity env stripped, ``git var GIT_AUTHOR_IDENT`` refuses to
        guess a ``user@hostname`` identity and errors (research §1.3, §2.4). The
        gate must then fail loudly. Recorded on the world (no staged identity) so
        ``run_precommit_gate`` strips the per-call identity env.
        """
        self.world.staged_author_email = None
        self.world.staged_committer_email = None
        self.world.staged_author_name = None
        self.world.staged_committer_name = None

    def run_precommit_gate(self) -> GateOutcome:
        """Run the real pre-commit validator as a git subprocess over the repo.

        Reads ``git var GIT_AUTHOR_IDENT`` / ``GIT_COMMITTER_IDENT`` exactly as
        production does. Pre-commit fires BEFORE the commit object exists, so the
        validator reads the PROSPECTIVE identity — the harness must supply it via
        the subprocess env, mirroring what git would resolve for the pending
        commit (research §2.4). The staged identity (name + email, both roles)
        recorded by ``commit_with_identity`` is threaded through here so the
        verdict is driven by the placeholder under test, not by an unresolvable
        ambient identity. When the world has no staged identity
        (degraded-environment scenario), the per-call identity env is stripped so
        git can resolve nothing and the gate fails loudly. Captures the exit code
        + stderr as the only observables.
        """
        repo = self._require_repo()
        strip_identity = (
            self.world.staged_author_email is None
            and self.world.staged_committer_email is None
        )
        identity = None if strip_identity else self._staged_identity_env()
        result = self._run_validator(
            _VALIDATOR_SCRIPT,
            [],
            repo,
            strip_identity=strip_identity,
            identity=identity,
        )
        self.world.exit_code = result.returncode
        self.world.captured_output = result.stderr
        return GateOutcome.ADMITTED if result.returncode == 0 else GateOutcome.REJECTED

    def _staged_identity_env(self) -> dict[str, str]:
        """The four ``GIT_AUTHOR_*`` / ``GIT_COMMITTER_*`` vars for the pending commit.

        ``git var GIT_AUTHOR_IDENT`` needs BOTH name and email — supplying only
        the emails still errors ("no name was given"). Both roles' name + email
        (as recorded by ``commit_with_identity``) are returned so the validator
        sees exactly the identity the pending commit would carry.
        """
        return {
            "GIT_AUTHOR_NAME": self.world.staged_author_name or "",
            "GIT_AUTHOR_EMAIL": self.world.staged_author_email or "",
            "GIT_COMMITTER_NAME": self.world.staged_committer_name or "",
            "GIT_COMMITTER_EMAIL": self.world.staged_committer_email or "",
        }

    # -- pre-push driving port (layer 3, real git range) --------------------

    def add_range_commit(
        self,
        email_class: EmailClass,
        role: IdentityRole,
        bypass: CommitBypass,
    ) -> None:
        """Append a commit to the pushable range with the given identity.

        ``bypass`` is recorded for narrative fidelity (research §2.7): a
        ``NO_VERIFY`` commit reaches the range because the local gate was
        skipped — the push gate must still catch it. The commit is created the
        same way regardless (the offending identity is what matters to the
        range validator).
        """
        repo = self._require_repo()
        good = "gearoid@users.noreply.github.com"
        offending = EMAIL_REPRESENTATIVE[email_class]
        author_email = offending if role is IdentityRole.AUTHOR else good
        committer_email = offending if role is IdentityRole.COMMITTER else good
        sha = self._commit(
            repo,
            "feat: range commit",
            author_email=author_email,
            committer_email=committer_email,
            author_name="Gearoid O'Treasaigh",
        )
        self.world.range_commit_shas.append(sha)

    def add_range_commit_with_name_of_class(
        self,
        name_class: NameClass,
        role: IdentityRole,
    ) -> None:
        """Append a range commit whose ``role`` NAME is the class representative.

        Author + committer EMAILS are both kept clean (allowlisted) so the ONLY
        offending field is the NAME of the role under test — proving the push /
        CI range runners validate NAMES, not emails alone (adversarial review
        R3-F1). The other role's name stays a real name, isolating exactly one
        field. The placeholder name is recorded as the observable the report must
        name.
        """
        repo = self._require_repo()
        good = "gearoid@users.noreply.github.com"
        real_name = "Gearoid O'Treasaigh"
        offending_name = NAME_REPRESENTATIVE[name_class]
        author_name = offending_name if role is IdentityRole.AUTHOR else real_name
        committer_name = offending_name if role is IdentityRole.COMMITTER else real_name
        sha = self._commit(
            repo,
            "feat: range commit with placeholder name",
            author_email=good,
            committer_email=good,
            author_name=author_name,
            committer_name=committer_name,
        )
        self.world.range_commit_shas.append(sha)
        self.world.staged_author_name = offending_name

    def add_range_commit_with_tab_in_name_hiding_placeholder_name(
        self,
    ) -> None:
        """Append a range commit whose author NAME carries a TAB *and* is a placeholder.

        Robustness vector for the NAME-aware range runner (R3-F1). Git PRESERVES
        a literal tab inside a stored commit name (verified empirically: a stored
        ``%an`` round-trips ``"A\\tB"`` intact). Once the runner reads ``%an`` /
        ``%cn`` and splits on tab, a tab INSIDE the name misaligns the columns —
        a naive ``line.split("\\t")`` reads a name fragment as the author email
        and shifts the real fields right, so the placeholder NAME is never
        validated (smuggled through), or the wrong field is reported.

        Construction (git-faithful, nothing "helps" the gate): the author NAME is
        ``"Test\\tFaker"`` — it BOTH contains a tab AND begins with the known
        placeholder ``Test`` (case-insensitive denylist). Author + committer
        emails are clean. A tab-proof runner (NUL-separated ``-z`` records, per
        the R3-F1 fix) keeps the name in one field, recognises the ``Test``
        placeholder, and refuses the push. A tab-fragile runner either misreads
        the field or never sees ``Test`` — letting the placeholder name through.
        """
        repo = self._require_repo()
        good = "gearoid@users.noreply.github.com"
        tab_placeholder_name = "Test\tFaker"
        sha = self._commit(
            repo,
            "feat: tab in author name hides a placeholder name",
            author_email=good,
            committer_email=good,
            author_name=tab_placeholder_name,
        )
        self.world.range_commit_shas.append(sha)
        self.world.staged_author_name = tab_placeholder_name

    def add_range_commit_with_tab_in_name_hiding_placeholder_email(
        self,
    ) -> None:
        """Append a range commit whose author NAME carries a TAB hiding a placeholder EMAIL.

        Companion to the NAME-hiding case (R3-F1 robustness). Author NAME
        ``"Half\\tok@users.noreply.github.com"`` + author EMAIL ``t@t.com`` (a
        known placeholder). Once the runner reads ``%an``/``%cn``, a naive
        ``\\t``-split sees the name's second half ``ok@users.noreply.github.com``
        (a CLEAN-looking value) as the author email and shifts the real
        placeholder ``t@t.com`` into the committer column — so the placeholder
        author email is never reported AS a placeholder on the author field. A
        NUL-separated runner keeps the name intact and reads ``t@t.com`` as the
        author email, refusing the push and naming it. The placeholder email is
        recorded as the observable the report must name.
        """
        repo = self._require_repo()
        tab_name = "Half\tok@users.noreply.github.com"
        placeholder_author = EMAIL_REPRESENTATIVE[EmailClass.PLACEHOLDER_T_AT_T]
        good = "gearoid@users.noreply.github.com"
        sha = self._commit(
            repo,
            "feat: tab in author name hides placeholder author email",
            author_email=placeholder_author,
            committer_email=good,
            author_name=tab_name,
        )
        self.world.range_commit_shas.append(sha)
        self.world.staged_author_email = placeholder_author

    def add_bypassed_commit_already_on_another_remote(
        self, email_class: EmailClass, role: IdentityRole
    ) -> None:
        """Make a placeholder commit reachable from a SECOND remote-tracking ref.

        Faithfully models the M1 bypass (adversarial review): a placeholder
        commit is committed onto the pushable history AND a remote-tracking ref
        (``refs/remotes/origin/other``) is pointed at it, exactly as it would be
        if that commit had already been pushed to another branch. The pre-push
        ``--not --remotes`` range therefore EXCLUDES the offending commit on a
        new-branch push — yet the push that introduces it into this branch's
        history must still be refused. Nothing here helps the gate: it only
        reproduces the real reachability the production ``--not --remotes`` query
        wrongly subtracts.
        """
        repo = self._require_repo()
        good = "gearoid@users.noreply.github.com"
        offending = EMAIL_REPRESENTATIVE[email_class]
        author_email = offending if role is IdentityRole.AUTHOR else good
        committer_email = offending if role is IdentityRole.COMMITTER else good
        sha = self._commit(
            repo,
            "feat: placeholder commit also on another remote branch",
            author_email=author_email,
            committer_email=committer_email,
            author_name="Gearoid O'Treasaigh",
        )
        self.world.range_commit_shas.append(sha)
        # Point a remote-tracking ref at the offending commit — i.e. it is
        # already published on another branch. `--not --remotes` will subtract
        # exactly this commit from the new-branch push range.
        self._git(repo, "update-ref", "refs/remotes/origin/other", sha)
        # Build clean follow-on work so the new branch HEAD differs from the
        # offending commit (the push introduces real new history on top of it).
        self._commit(
            repo,
            "feat: clean follow-on work",
            author_email=good,
            committer_email=good,
            author_name="Gearoid O'Treasaigh",
        )

    def add_commit_with_tab_in_author_name(self) -> None:
        """Commit a placeholder AUTHOR email behind a TAB-bearing author name.

        Faithfully models the M2 robustness defect (adversarial review): the
        pre-push runner reads ``git log --format=%H\\t%an\\t%ae\\t%ce`` and splits
        on the tab. When the author NAME itself contains a tab, the column split
        misaligns — the runner reads a name fragment as the "author email" and
        the real placeholder author email is shifted into the committer column,
        so the rejection is mis-attributed (or, with a different name shape,
        could be read from the wrong field entirely).

        Construction (verified empirically): author name
        ``"Half\\tok@users.noreply.github.com"`` + author email ``"t@t.com"``
        (a known placeholder) + a clean committer. After the buggy split the
        runner reads ``author_email = "ok@users.noreply.github.com"`` (the name's
        second half — a CLEAN-looking value) and never validates ``t@t.com`` as
        the author field; ``t@t.com`` survives only as whitespace inside the
        garbled committer column. The placeholder author email is therefore
        never reported as a placeholder — the observable the M2 ``Then`` asserts.
        Nothing here helps the gate; the harness only reproduces a real commit
        shape git permits.
        """
        repo = self._require_repo()
        tab_name = "Half\tok@users.noreply.github.com"
        placeholder_author = EMAIL_REPRESENTATIVE[EmailClass.PLACEHOLDER_T_AT_T]
        good = "gearoid@users.noreply.github.com"
        sha = self._commit(
            repo,
            "feat: tab in author name hides placeholder author email",
            author_email=placeholder_author,
            committer_email=good,
            author_name=tab_name,
        )
        self.world.range_commit_shas.append(sha)
        self.world.staged_author_email = placeholder_author

    def run_prepush_gate(self, shape: PushRangeShape) -> GateOutcome:
        """Run the real pre-push validator over the local..remote ref line.

        For ``NEW_BRANCH_ZERO_SHA`` the remote object name is the zero SHA, which
        the validator resolves to ``<local> --not --remotes`` (research §2.5).
        For ``EXISTING_UPSTREAM`` it diffs against the baseline commit.
        """
        repo = self._require_repo()
        local_sha = self._git(repo, "rev-parse", "HEAD").stdout.strip()
        if shape is PushRangeShape.NEW_BRANCH_ZERO_SHA:
            remote_sha = _ZERO_SHA
        else:
            remote_sha = (
                self._git(repo, "rev-list", "--max-parents=0", "HEAD")
                .stdout.strip()
                .splitlines()[0]
            )
        ref_line = f"refs/heads/main {local_sha} refs/heads/main {remote_sha}\n"
        result = self._run_validator(_PUSH_SCRIPT, [], repo, stdin=ref_line)
        self.world.exit_code = result.returncode
        self.world.captured_output = result.stderr
        return GateOutcome.ADMITTED if result.returncode == 0 else GateOutcome.REJECTED

    # -- CI driving port (layer 3, range over argv) -------------------------

    def run_ci_check_over_range(self) -> GateOutcome:
        """Run the authoritative CI runner over ``<baseline>..HEAD``.

        Drives the pure-Python runner directly (NOT a live Actions run) with the
        base + head SHAs on argv, returning the exit code — the gate that
        survives ``--no-verify`` and ``core.hooksPath`` injection (research §3.1).
        """
        repo = self._require_repo()
        base = (
            self._git(repo, "rev-list", "--max-parents=0", "HEAD")
            .stdout.strip()
            .splitlines()[0]
        )
        head = self._git(repo, "rev-parse", "HEAD").stdout.strip()
        result = self._run_validator(_CI_SCRIPT, ["--base", base, "--head", head], repo)
        self.world.exit_code = result.returncode
        self.world.captured_output = result.stdout + result.stderr
        return GateOutcome.ADMITTED if result.returncode == 0 else GateOutcome.REJECTED

    def run_ci_check_over_head_only(self, email_class: EmailClass) -> GateOutcome:
        """Drive the CI runner with ``--head`` only — NO ``--base`` (W1 degrade path).

        Models the GitHub Actions push-event case where no ``base..head`` range
        exists (initial push, force-push, or a HEAD whose parent is not fetched):
        the workflow invokes ``ci_author_check.main(["--head", <sha>])`` with the
        base omitted, and the runner degrades to validating the single pushed
        commit via ``git show -s`` on HEAD rather than validating nothing
        (``ci_author_check.py`` W1 branch, research §3.2). Faithful to production:
        a real placeholder/clean commit is staged on HEAD and the real runner
        runs ``git show -s`` over it — no range argument is supplied. The HEAD
        commit's SHA is recorded so the report can be asked to name the offender.
        """
        repo = self._require_repo()
        good = "gearoid@users.noreply.github.com"
        offending = EMAIL_REPRESENTATIVE[email_class]
        head_email = good if email_class in ACCEPTED_EMAIL_CLASSES else offending
        sha = self._commit(
            repo,
            "feat: pushed head commit (no range)",
            author_email=head_email,
            committer_email=head_email,
            author_name="Gearoid O'Treasaigh",
        )
        self.world.range_commit_shas = [sha]
        head = self._git(repo, "rev-parse", "HEAD").stdout.strip()
        result = self._run_validator(_CI_SCRIPT, ["--head", head], repo)
        self.world.exit_code = result.returncode
        self.world.captured_output = result.stdout + result.stderr
        return GateOutcome.ADMITTED if result.returncode == 0 else GateOutcome.REJECTED

    def run_ci_check_over_head_only_name(self, name_class: NameClass) -> GateOutcome:
        """Drive the CI runner with ``--head`` only over a placeholder-NAME commit.

        The single-commit / ``--head``-only degrade path (W1) for the NAME check
        (R3-F1): a pushed HEAD whose author NAME is a placeholder and whose email
        is clean must be flagged when no ``--base`` range is supplied. A real
        commit is staged on HEAD with the placeholder name + clean emails and the
        real runner runs ``git show -s`` over it — faithful to the push-event
        case where only HEAD is known.
        """
        repo = self._require_repo()
        good = "gearoid@users.noreply.github.com"
        offending_name = NAME_REPRESENTATIVE[name_class]
        sha = self._commit(
            repo,
            "feat: pushed head commit with placeholder name",
            author_email=good,
            committer_email=good,
            author_name=offending_name,
        )
        self.world.range_commit_shas = [sha]
        self.world.staged_author_name = offending_name
        head = self._git(repo, "rev-parse", "HEAD").stdout.strip()
        result = self._run_validator(_CI_SCRIPT, ["--head", head], repo)
        self.world.exit_code = result.returncode
        self.world.captured_output = result.stdout + result.stderr
        return GateOutcome.ADMITTED if result.returncode == 0 else GateOutcome.REJECTED

    def run_prepush_gate_with_no_resolvable_default_base(self) -> GateOutcome:
        """Run the pre-push gate on a new-branch push where NO ``origin/*`` ref resolves.

        Exercises the fail-closed ``_resolve_default_base() -> None`` fallback
        (R3-F4): the isolated repo has NO remote-tracking refs at all, so none of
        ``origin/HEAD`` / ``origin/master`` / ``origin/main`` resolve. On a
        new-branch (zero-SHA) push the runner must then validate the WHOLE
        reachable set from the pushed tip rather than skipping — a placeholder
        commit anywhere in that history must still be refused. A placeholder-
        authored commit is staged on the pushable history; nothing creates a
        remote ref, so the None-fallback is the only path that can catch it.
        """
        self.add_range_commit(
            EmailClass.PLACEHOLDER_TEST_EXAMPLE,
            IdentityRole.AUTHOR,
            CommitBypass.NO_VERIFY,
        )
        return self.run_prepush_gate(PushRangeShape.NEW_BRANCH_ZERO_SHA)

    def run_ci_check_over_pr42_equivalent_range(self) -> GateOutcome:
        """Build a range equivalent to PR #42 (8 commits authored test@example.com).

        Encodes the real failing instance the whole feature exists to catch
        (``plan.md`` regression anchor). All 8 commits carry the placeholder
        author; the CI runner must flag the range.
        """
        repo = self._require_repo()
        base = self._git(repo, "rev-parse", "HEAD").stdout.strip()
        self.world.range_commit_shas = []
        for i in range(8):
            sha = self._commit(
                repo,
                f"fix: pr42 commit {i}",
                author_email="test@example.com",
                committer_email="gearoid@users.noreply.github.com",
                author_name="Real Contributor",
            )
            self.world.range_commit_shas.append(sha)
        head = self._git(repo, "rev-parse", "HEAD").stdout.strip()
        result = self._run_validator(_CI_SCRIPT, ["--base", base, "--head", head], repo)
        self.world.exit_code = result.returncode
        self.world.captured_output = result.stdout + result.stderr
        return GateOutcome.ADMITTED if result.returncode == 0 else GateOutcome.REJECTED

    def run_ci_check_over_clean_first_then_placeholder_range(self) -> GateOutcome:
        """Build a range whose FIRST commit is clean and a LATER one is placeholder.

        Guards against a ``rows[:1]``-style regression (adversarial review H1):
        a runner that only inspected the first commit would clear this range. The
        clean baseline commit comes first; a placeholder-authored commit is added
        afterwards. Only the placeholder commit's SHA is recorded as the one the
        gate must flag.
        """
        repo = self._require_repo()
        base = self._git(repo, "rev-parse", "HEAD").stdout.strip()
        good = "gearoid@users.noreply.github.com"
        self._commit(
            repo,
            "feat: clean first commit in range",
            author_email=good,
            committer_email=good,
            author_name="Gearoid O'Treasaigh",
        )
        placeholder_sha = self._commit(
            repo,
            "feat: placeholder author later in range",
            author_email="test@example.com",
            committer_email=good,
            author_name="Real Contributor",
        )
        self.world.range_commit_shas = [placeholder_sha]
        head = self._git(repo, "rev-parse", "HEAD").stdout.strip()
        result = self._run_validator(_CI_SCRIPT, ["--base", base, "--head", head], repo)
        self.world.exit_code = result.returncode
        self.world.captured_output = result.stdout + result.stderr
        return GateOutcome.ADMITTED if result.returncode == 0 else GateOutcome.REJECTED

    # -- internal helpers ---------------------------------------------------

    def _require_repo(self) -> Path:
        assert self.world.repo is not None, "repo not initialised — Given step missing"
        return self.world.repo

    def _run_validator(
        self,
        script: Path,
        args: list[str],
        repo: Path,
        stdin: str | None = None,
        strip_identity: bool = False,
        identity: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        """Run a validator entry as a real subprocess inside the isolated repo.

        With ``identity`` supplied, the four ``GIT_AUTHOR_*`` / ``GIT_COMMITTER_*``
        vars are injected so the validator's ``git var`` resolves the prospective
        commit identity (the pre-commit path — research §2.4). With
        ``strip_identity`` set, those same vars are removed so git (with
        ``user.useConfigOnly true``) can resolve no identity — the
        degraded-environment path. The two are mutually exclusive; ``identity``
        is ignored when ``strip_identity`` is set.
        """
        env = _isolated_git_env(repo)
        env["PYTHONPATH"] = str(_REPO_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
        if strip_identity:
            for var in (
                "GIT_AUTHOR_NAME",
                "GIT_AUTHOR_EMAIL",
                "GIT_COMMITTER_NAME",
                "GIT_COMMITTER_EMAIL",
            ):
                env.pop(var, None)
        elif identity is not None:
            env.update(identity)
        return subprocess.run(
            [sys.executable, str(script), *args],
            cwd=str(repo),
            env=env,
            input=stdin,
            capture_output=True,
            text=True,
            check=False,
        )

    def _git(self, repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            ["git", *args],
            cwd=str(repo),
            env=_isolated_git_env(repo),
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f"git {args} failed: {result.stderr}")
        return result

    def _commit(
        self,
        repo: Path,
        message: str,
        *,
        author_email: str,
        author_name: str,
        committer_email: str | None = None,
        committer_name: str | None = None,
    ) -> str:
        """Create a commit with explicit author/committer identity; return its SHA.

        ``committer_name`` / ``committer_email`` default to the author's so the
        common case stays terse; a caller isolating the COMMITTER field (NAME or
        email) supplies them independently, exactly as ``git commit --author`` /
        ``git cherry-pick`` produce diverging author/committer pairs (research
        §2.2).
        """
        marker = repo / "file.txt"
        marker.write_text(message + "\n")
        env = _isolated_git_env(repo)
        env["GIT_AUTHOR_NAME"] = author_name
        env["GIT_AUTHOR_EMAIL"] = author_email
        env["GIT_COMMITTER_NAME"] = committer_name or author_name
        env["GIT_COMMITTER_EMAIL"] = committer_email or author_email
        subprocess.run(
            ["git", "add", "-A"],
            cwd=str(repo),
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "commit", "-q", "--no-verify", "-m", message],
            cwd=str(repo),
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo),
            env=env,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
