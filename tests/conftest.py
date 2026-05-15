"""Root conftest.py for all tests - ensures test isolation."""

from __future__ import annotations

import os
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Project root (single source of truth for autouse fixtures below).
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).parent.parent


@pytest.fixture(autouse=True)
def restore_working_directory():
    """
    Automatically restore the working directory after each test.

    This fixture ensures that tests which change the working directory
    (e.g., using os.chdir()) don't affect subsequent tests.

    The working directory is restored to the project root, which is
    determined by finding the directory containing pytest.ini.
    """
    # Save original working directory
    original_cwd = os.getcwd()

    # Ensure we're in the project root (directory containing pytest.ini)
    os.chdir(_PROJECT_ROOT)

    yield

    # Restore original working directory after test
    os.chdir(original_cwd)


# ---------------------------------------------------------------------------
# Class B regression guard — editable install health check (RCA 2026-05-13).
#
# Symptom: subprocess-based tests fail with
# `ModuleNotFoundError: No module named 'nwave_ai'` when run from a sandboxed
# cwd, because Python's `sys.path` no longer contains `''` and the editable
# install .pth file is missing/corrupted. Catching this at session start
# gives a clear actionable message instead of dozens of identical cryptic
# failures across `tests/outcomes/acceptance/`, `tests/feature_delta/...`.
#
# RCA: docs/feature/fix-outcomes-acceptance/discuss/rca.md.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session", autouse=True)
def _verify_nwave_ai_subprocess_importable():
    """Fast-fail if nwave_ai cannot be imported from a clean-cwd subprocess."""
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-c", "import nwave_ai"],
        cwd="/tmp",
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode != 0:
        pytest.exit(
            "FATAL: nwave_ai not importable from a clean-cwd subprocess. "
            "Class B regression — editable install .pth missing or corrupted.\n"
            f"  python: {sys.executable}\n"
            f"  stderr: {result.stderr.strip()}\n"
            "Fix: `pipenv install -e .` (or run `nwave-doctor` if available).",
            returncode=1,
        )


# ---------------------------------------------------------------------------
# Layer 1 — repo-wide GIT_CEILING_DIRECTORIES (Fix 1 from RCA).
# Function-scoped so pytest-xdist workers each get their own env, and so the
# var is cleaned up after every test (no global env mutation).
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _git_ceiling(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stop subprocess git from walking up into the host repo.

    Sets ``GIT_CEILING_DIRECTORIES`` to the parent of the project root for
    every test. If a subprocess git invocation has its cwd resolve above
    its tmp_path (race / inode reuse / chdir interaction), git will fail
    to find a parent ``.git`` instead of mutating the host repo.

    Pairs with ``_git_pollution_guard`` below: env stops the leak, the
    detective guard catches it if env is bypassed (some tests build their
    own subprocess env dict and inherit only ``os.environ`` selectively).
    """
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(_PROJECT_ROOT.parent))


# ---------------------------------------------------------------------------
# Git hooks guard — prevents any test from corrupting .git/hooks/
# ---------------------------------------------------------------------------


def _snapshot_hooks_dir(hooks_dir: Path) -> dict[str, bytes]:
    """Return a filename -> full-bytes mapping for all files in hooks_dir.

    Returns an empty dict when the directory does not exist. Pure function.
    Content is captured in full (not hashed) so the guard can restore the
    pre-session state in teardown — detection alone leaves corruption
    between sessions and blocks manual commits.
    """
    if not hooks_dir.is_dir():
        return {}
    return {
        entry.name: entry.read_bytes()
        for entry in sorted(hooks_dir.iterdir())
        if entry.is_file()
    }


def _restore_hooks_dir(hooks_dir: Path, snapshot: dict[str, bytes]) -> None:
    """Restore hooks_dir to match the captured snapshot exactly.

    Writes every file in the snapshot back to disk with its pre-session
    content + 0o755 permissions (hooks must be executable). Deletes any
    files that appeared during the session (and are not in the snapshot).
    Idempotent: calling twice with the same snapshot is a no-op.
    """
    if not hooks_dir.is_dir():
        return
    current_names = {entry.name for entry in hooks_dir.iterdir() if entry.is_file()}
    # Delete files that appeared during the session
    for name in current_names - set(snapshot):
        (hooks_dir / name).unlink(missing_ok=True)
    # Restore original content for everything that was in the snapshot
    for name, content in snapshot.items():
        path = hooks_dir / name
        path.write_bytes(content)
        path.chmod(0o755)


def _locate_git_hooks_dir() -> Path:
    """Resolve the real .git/hooks directory, following worktree indirection.

    For a normal clone: <project_root>/.git/hooks/
    For a worktree:    the common .git/hooks/ of the main worktree.
    """
    project_root = Path(__file__).parent.parent
    git_path = project_root / ".git"
    if git_path.is_dir():
        return git_path / "hooks"
    # Worktree: .git is a file containing "gitdir: <path>"
    gitdir_line = git_path.read_text().strip()
    if gitdir_line.startswith("gitdir:"):
        worktree_git = Path(gitdir_line[len("gitdir:") :].strip())
        # Walk up to the common dir (two levels up from worktrees/<name>)
        common_git = worktree_git.parent.parent
        return common_git / "hooks"
    return git_path / "hooks"


@pytest.fixture(scope="session", autouse=True)
def guard_git_hooks():
    """Session-scoped guard that RESTORES and fails if tests corrupt .git/hooks/.

    Definitive fix for hook corruption: detection alone is insufficient —
    corrupted state survives the pytest session and blocks manual commits
    (e.g. plugin-installer tests calling install_attribution_hook without
    proper isolation can overwrite prepare-commit-msg). This fixture:

    1. Snapshots the hooks directory BEFORE the session (full bytes + perms).
    2. YIELDS — tests run and may corrupt hooks.
    3. UNCONDITIONALLY RESTORES the pre-session state in teardown,
       regardless of whether violations were detected.
    4. Computes the diff AFTER restore and fails loudly if any test
       touched the hooks directory, so the regression is still visible
       in CI/local output.

    Restore runs before the fail assertion so even a failing session
    leaves the hooks dir clean for the next commit attempt.
    """
    hooks_dir = _locate_git_hooks_dir()
    before = _snapshot_hooks_dir(hooks_dir)

    yield

    after = _snapshot_hooks_dir(hooks_dir)

    created = sorted(set(after) - set(before))
    deleted = sorted(set(before) - set(after))
    modified = sorted(
        name for name in set(before) & set(after) if before[name] != after[name]
    )

    # UNCONDITIONAL RESTORE first — even on detection failure, the next
    # commit must not be blocked by leftover corruption.
    if created or deleted or modified:
        _restore_hooks_dir(hooks_dir, before)

    violations: list[str] = []
    if created:
        violations.append(f"Created: {created}")
    if deleted:
        violations.append(f"Deleted: {deleted}")
    if modified:
        violations.append(f"Modified: {modified}")

    if violations:
        # Surface as a warning rather than a teardown failure: the unconditional
        # restore above is the safety net — we do not want to block pre-commit
        # runs when a test touches hooks, we want the hooks left intact.
        import sys as _sys

        _sys.stderr.write(
            "\nHOOK-GUARD: test session corrupted .git/hooks/ — "
            + "; ".join(violations)
            + f"\n  hooks dir: {hooks_dir}"
            + "\n  (hooks dir has been RESTORED to the pre-session snapshot)\n"
        )


# ---------------------------------------------------------------------------
# Layer 2 — Detective guard: snapshot+diff+restore .git/{config,HEAD,refs/}.
#
# Two pure helpers form the API contract that tests/test_guard_fixtures.py
# locks (Step 01-01): _compute_git_state_snapshot and _diff_git_state. The
# autouse fixture _git_pollution_guard wraps them.
#
# Unlike `guard_git_hooks` (which warns), this fixture uses pytest.fail()
# because config/HEAD/refs corruption — unlike hooks corruption — is
# immediately repo-breaking and must halt the suite.
# ---------------------------------------------------------------------------


def _resolve_git_common_dir(project_root: Path) -> Path:
    """Resolve the git common dir, following worktree indirection.

    For a normal clone: ``<project_root>/.git`` (a directory).
    For a worktree: ``<project_root>/.git`` is a file containing
    ``gitdir: <path>/<common>/worktrees/<name>``; the common dir is two
    levels up.

    Pure: only reads filesystem state. No subprocess (deliberate — the
    guard runs per-test in worker scope; a `git rev-parse` would itself
    walk up and could trigger the very corruption we are trying to detect
    on a misconfigured repo).
    """
    git_path = project_root / ".git"
    if git_path.is_dir():
        return git_path
    if git_path.is_file():
        gitdir_line = git_path.read_text().strip()
        if gitdir_line.startswith("gitdir:"):
            worktree_git = Path(gitdir_line[len("gitdir:") :].strip())
            # <common>/worktrees/<name> -> <common>
            return worktree_git.parent.parent
    return git_path


def _resolve_head_path(project_root: Path) -> Path:
    """Return the path to the HEAD that this worktree owns.

    Normal clone: ``<common>/HEAD``.
    Worktree: ``<common>/worktrees/<name>/HEAD`` (per-worktree HEAD).
    """
    git_path = project_root / ".git"
    if git_path.is_dir():
        return git_path / "HEAD"
    if git_path.is_file():
        gitdir_line = git_path.read_text().strip()
        if gitdir_line.startswith("gitdir:"):
            return Path(gitdir_line[len("gitdir:") :].strip()) / "HEAD"
    return git_path / "HEAD"


def _read_packed_refs(common_dir: Path) -> dict[str, str]:
    """Parse ``<common_dir>/packed-refs`` into a ``{ref_name: sha}`` map.

    Pure function. Returns ``{}`` if the file does not exist or is empty —
    a freshly-initialised repo has no packed-refs file at all, and a repo
    with all refs unpacked has only loose files.

    File format (``man git-pack-refs``)::

        # pack-refs with: peeled fully-peeled sorted
        <sha> <ref-name>
        ^<peeled-sha>            (annotation for the previous annotated tag)

    Comment lines (start with ``#``) and peeled-tag annotation lines
    (start with ``^``) are skipped — they are not refs themselves.

    Used by ``_compute_git_state_snapshot`` to distinguish
    routine-housekeeping promotions (loose ref appears with same SHA as
    an existing packed entry — ignore) from genuine ref creation (loose
    ref appears with a SHA never seen in packed-refs — flag).
    """
    packed_path = common_dir / "packed-refs"
    if not packed_path.is_file():
        return {}
    result: dict[str, str] = {}
    for line in packed_path.read_text().splitlines():
        if not line or line.startswith("#") or line.startswith("^"):
            continue
        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            continue
        sha, name = parts
        result[name.strip()] = sha.strip()
    return result


def _resolve_head_target(head_path: Path, common_dir: Path) -> bytes | None:
    """Return the SHA HEAD currently resolves to, or the raw HEAD bytes.

    Pure function. Reads ``HEAD`` directly; if it is a symbolic ref of the
    shape ``ref: refs/heads/<branch>\\n``, follows the pointer once to the
    target ref file and returns its bytes (the commit SHA). For detached
    HEAD (raw 40-char SHA in the file) returns the file bytes directly.

    When the symbolic-ref target has no loose file (``git pack-refs --all``
    deleted it), falls back to the SHA in ``packed-refs``. Only when both
    are absent (unborn branch, freshly-cloned bare ref) does it return the
    literal HEAD bytes — which would otherwise spuriously diff as ``HEAD``
    on a packed-only repo. Returns ``None`` if HEAD is absent.

    The reason we resolve the target rather than only snapshot the HEAD
    file: ``git commit`` does NOT touch HEAD when on a branch — it
    mutates ``refs/heads/<branch>``. The user-visible "HEAD moved"
    symptom of the RCA Branch A pollution therefore manifests as a
    change in the resolved target, not in HEAD's symbolic-ref text.
    Snapshotting only the literal bytes would miss that exact failure.
    """
    if not head_path.is_file():
        return None
    raw = head_path.read_bytes()
    text = raw.decode("utf-8", errors="replace").strip()
    if text.startswith("ref:"):
        ref_name = text[len("ref:") :].strip()
        target = common_dir / ref_name
        if target.is_file():
            return target.read_bytes()
        # Loose file absent — try packed-refs (housekeeping after pack).
        packed = _read_packed_refs(common_dir)
        packed_sha = packed.get(ref_name)
        if packed_sha is not None:
            # Match git's loose-ref on-disk shape: 40 hex + LF.
            return (packed_sha + "\n").encode("ascii")
    return raw


def _compute_git_state_snapshot(project_root: Path) -> dict[str, object]:
    """Return a byte-level snapshot of the load-bearing host git state.

    Pure function. The snapshot covers the four artifacts whose mutation
    constitutes pollution: ``config`` (shared across worktrees),
    ``HEAD`` (per-worktree), the union of loose ``refs/heads/`` and
    ``refs/tags/``, and the ``packed-refs`` map.

    Returns a dict with the contract:
        {
            "config":       <bytes | None>,      # raw .git/config bytes
            "HEAD_raw":     <bytes | None>,      # literal HEAD file bytes
            "HEAD_resolved":<bytes | None>,      # SHA target of HEAD, or
                                                 #   the raw bytes if HEAD
                                                 #   is detached / target
                                                 #   ref missing
            "refs":         <list[(str, bytes)]> # sorted (refname, sha-bytes)
            "packed_refs":  <dict[str, str]>     # ref_name -> sha hex map
        }

    Two HEAD fields exist by design (adversarial review D1 fix):
    ``HEAD_raw`` is what restore writes back so a symbolic-ref HEAD
    (``ref: refs/heads/<branch>\\n``) is preserved across restores —
    writing the resolved SHA would leave the worktree in detached-HEAD
    state. ``HEAD_resolved`` is what diff compares so ``git commit``
    (which only mutates ``refs/heads/<branch>``, not HEAD itself) is
    detected as a corruption: the resolved target advances even though
    HEAD's literal bytes are unchanged.

    The ``packed_refs`` field exists by design (Step 01-02 fix for the
    residual-RCA false-positive). It lets ``_diff_git_state`` distinguish
    routine git housekeeping (a packed ref gets promoted to a loose file
    with the same SHA — ignore) from genuine pollution (a brand-new ref
    appears with a SHA never seen in packed-refs — flag).

    Designed for ``_diff_git_state`` (returns subset of {"config","HEAD","refs"}
    naming what changed). Worktree gitdir indirection is resolved via
    ``_resolve_git_common_dir`` and ``_resolve_head_path``.

    Returns ``None`` for missing files instead of raising — a non-existent
    repo is still a deterministic state to diff against.
    """
    common_dir = _resolve_git_common_dir(project_root)
    config_path = common_dir / "config"
    head_path = _resolve_head_path(project_root)

    config_bytes = config_path.read_bytes() if config_path.is_file() else None

    # HEAD_raw: literal file bytes — used by restore to preserve the
    # symbolic-ref form (`ref: refs/heads/<branch>\n`).
    head_raw = head_path.read_bytes() if head_path.is_file() else None

    # HEAD_resolved: target SHA via _resolve_head_target. Used by diff so
    # `git commit` (which advances refs/heads/<branch> but leaves HEAD's
    # literal bytes unchanged) is detected as a HEAD corruption — that IS
    # the user-visible symptom of the RCA Branch A pollution.
    head_resolved = _resolve_head_target(head_path, common_dir)

    # refs: glob refs/heads/* and refs/tags/* under the common dir.
    refs: list[tuple[str, bytes]] = []
    for category in ("heads", "tags"):
        refs_dir = common_dir / "refs" / category
        if not refs_dir.is_dir():
            continue
        for ref_file in sorted(refs_dir.rglob("*")):
            if not ref_file.is_file():
                continue
            ref_name = f"refs/{category}/" + str(
                ref_file.relative_to(refs_dir)
            ).replace(os.sep, "/")
            refs.append((ref_name, ref_file.read_bytes()))

    return {
        "config": config_bytes,
        "HEAD_raw": head_raw,
        "HEAD_resolved": head_resolved,
        "refs": sorted(refs),
        "packed_refs": _read_packed_refs(common_dir),
    }


def _refs_diff_is_pollution(
    before_refs: list[tuple[str, bytes]],
    after_refs: list[tuple[str, bytes]],
    before_packed: dict[str, str],
) -> bool:
    """Return True iff the loose-refs change is real pollution.

    Pure function. Decomposes the previous all-or-nothing list-compare
    into three independent questions:

    1. New loose ref in ``after`` that was not in ``before``: is its SHA
       already in ``before``'s ``packed-refs``? If yes -> housekeeping
       promotion (ignore). If no -> creation (pollution).
    2. Loose ref in ``before`` that disappeared in ``after``: was its SHA
       in ``before``'s ``packed-refs``? If yes -> the ref was collapsed
       back into pack (housekeeping; ignore). If no -> deletion
       (pollution).
    3. SHA changed for a ref that exists in both ``before`` and ``after``:
       always pollution (the ref moved to a different commit).
    """
    before_map = dict(before_refs)
    after_map = dict(after_refs)

    # 1. Created loose refs.
    for name, sha_bytes in after_map.items():
        if name in before_map:
            continue
        sha = sha_bytes.decode("ascii", errors="replace").strip()
        if before_packed.get(name) == sha:
            continue  # promotion — housekeeping, ignore.
        return True  # genuine creation — pollution.

    # 2. Disappeared loose refs.
    for name, sha_bytes in before_map.items():
        if name in after_map:
            continue
        sha = sha_bytes.decode("ascii", errors="replace").strip()
        if before_packed.get(name) == sha:
            continue  # collapsed back into pack — housekeeping, ignore.
        return True  # genuine deletion — pollution.

    # 3. SHA changed on existing loose ref.
    for name, sha_bytes in after_map.items():
        if name in before_map and before_map[name] != sha_bytes:
            return True

    return False


def _diff_git_state(before: dict[str, object], after: dict[str, object]) -> list[str]:
    """Return subset of {"config", "HEAD", "refs"} listing what changed.

    Pure function. Empty list = no corruption. Used by the autouse guard
    to drive ``pytest.fail()`` with a precise corruption-type list, and
    by ``tests/test_guard_fixtures.py`` to verify the predicate detects
    the exact failure modes of the 2026-04-27 incident.

    Refs comparison is promotion-aware (Step 01-02 fix): a new loose ref
    whose SHA already lives in ``before["packed_refs"]`` is housekeeping
    (the ref was promoted from pack to loose by ``git fetch`` / etc.) and
    must NOT be flagged. A new loose ref whose SHA is NOT in the packed
    map IS pollution — the legitimate-creation contract from
    ``test_guard_detects_refs_corruption`` is preserved.

    Symmetric in argument order modulo set semantics for config/HEAD; the
    refs branch is asymmetric by design (the ``before`` packed-refs map
    is the housekeeping witness, not the ``after`` one).
    """
    diff: list[str] = []
    if before.get("config") != after.get("config"):
        diff.append("config")
    # Compare HEAD_resolved (the SHA target) so `git commit` — which only
    # advances refs/heads/<branch> while leaving HEAD's literal bytes
    # unchanged — is still flagged. Adversarial review D1: HEAD_raw is the
    # restore field; HEAD_resolved is the diff field.
    if before.get("HEAD_resolved") != after.get("HEAD_resolved"):
        diff.append("HEAD")

    before_refs_obj = before.get("refs")
    after_refs_obj = after.get("refs")
    before_packed_obj = before.get("packed_refs")
    if (
        isinstance(before_refs_obj, list)
        and isinstance(after_refs_obj, list)
        and isinstance(before_packed_obj, dict)
    ):
        if _refs_diff_is_pollution(before_refs_obj, after_refs_obj, before_packed_obj):
            diff.append("refs")
    elif before_refs_obj != after_refs_obj:
        # Fallback for snapshots produced before packed_refs was added —
        # preserve the old whole-list comparison so legacy callers still
        # see refs corruption.
        diff.append("refs")
    return diff


# Recursion-safety flag: while we are mid-restore, the guard MUST NOT
# re-enter (e.g. if a finalizer somehow re-invokes the snapshot path).
_GUARD_RESTORE_IN_PROGRESS = False


def _atomic_restore_git_state(project_root: Path, before: dict[str, object]) -> None:
    """Restore .git/{config,HEAD,refs/heads,refs/tags} from a snapshot.

    Direct file writes only — never invokes ``git`` as a subprocess
    because that is the exact escape vector this guard exists to defend
    against. Idempotent: calling twice with the same snapshot is a no-op.

    HEAD restore uses ``HEAD_raw`` (literal file bytes), NOT
    ``HEAD_resolved`` (the SHA target). Writing the SHA back would leave
    the worktree in detached-HEAD state — the original HEAD contained
    ``ref: refs/heads/<branch>\\n`` (a symbolic ref), and that text must
    be preserved verbatim. Adversarial review D1.

    Refs restore performs TWO passes (adversarial review D2): first
    writes back snapshot-before entries, then deletes any refs that
    appeared during the test (i.e. files under refs/heads or refs/tags
    that are not in ``refs_before``). Mirrors ``_restore_hooks_dir``'s
    pattern (lines 96-99). Detection alone is insufficient when the
    autouse guard wants the next test to start from a CLEAN snapshot —
    leftover refs would themselves be picked up as a corruption signal
    on the very next test, masking the true offender.

    Pass 2 is promotion-aware (Step 01-02): a loose ref absent from
    ``refs_before`` whose SHA matches an entry in
    ``before["packed_refs"]`` is left in place. It was promoted from
    pack to loose by routine git housekeeping (``git fetch``, etc.) —
    deleting it would destroy a legitimate ref the user owns.

    Sets the recursion flag so any concurrent guard invocation skips its
    snapshot phase while the restore is in flight.
    """
    global _GUARD_RESTORE_IN_PROGRESS
    _GUARD_RESTORE_IN_PROGRESS = True
    try:
        common_dir = _resolve_git_common_dir(project_root)
        config_path = common_dir / "config"
        head_path = _resolve_head_path(project_root)

        config_before = before.get("config")
        if isinstance(config_before, bytes):
            config_path.write_bytes(config_before)

        # D1: write HEAD_raw (the literal file bytes), not HEAD_resolved.
        # Preserves the `ref: refs/heads/<branch>\n` text so the worktree
        # stays attached.
        head_raw = before.get("HEAD_raw")
        if isinstance(head_raw, bytes):
            head_path.write_bytes(head_raw)

        refs_before = before.get("refs")
        packed_before_obj = before.get("packed_refs")
        packed_before: dict[str, str] = (
            packed_before_obj if isinstance(packed_before_obj, dict) else {}
        )
        if isinstance(refs_before, list):
            # Pass 1: write back every snapshot-before ref.
            ref_names_before: set[str] = set()
            for ref_name, ref_bytes in refs_before:
                if not isinstance(ref_name, str) or not isinstance(ref_bytes, bytes):
                    continue
                ref_names_before.add(ref_name)
                ref_path = common_dir / ref_name
                ref_path.parent.mkdir(parents=True, exist_ok=True)
                ref_path.write_bytes(ref_bytes)

            # Pass 2 (D2): delete refs that appeared during the test.
            # Walk current refs/heads and refs/tags; anything not in
            # ref_names_before is post-snapshot pollution and must go —
            # UNLESS its SHA was already in packed-refs at snapshot time
            # (Step 01-02: housekeeping promotion, not pollution).
            for category in ("heads", "tags"):
                refs_dir = common_dir / "refs" / category
                if not refs_dir.is_dir():
                    continue
                for ref_file in refs_dir.rglob("*"):
                    if not ref_file.is_file():
                        continue
                    ref_name = f"refs/{category}/" + str(
                        ref_file.relative_to(refs_dir)
                    ).replace(os.sep, "/")
                    if ref_name in ref_names_before:
                        continue
                    # Step 01-02: skip if this is a packed-to-loose
                    # promotion (SHA matches the packed-refs entry from
                    # the BEFORE snapshot). Don't destroy the legitimate
                    # ref the user owns.
                    current_sha = (
                        ref_file.read_bytes().decode("ascii", errors="replace").strip()
                    )
                    if packed_before.get(ref_name) == current_sha:
                        continue
                    ref_file.unlink(missing_ok=True)
    finally:
        _GUARD_RESTORE_IN_PROGRESS = False


@pytest.fixture(autouse=True)
def _git_pollution_guard():
    """Fail-fast if a test mutates host .git/{config,HEAD,refs/}.

    Snapshots before yield, snapshots after, computes the diff. On any
    non-empty diff: ATOMICALLY restore the snapshot (so the next test
    starts from a clean state) and THEN ``pytest.fail()`` naming the
    corruption type ("config", "HEAD", "refs"). Restore happens inside a
    try/finally so even if it raises, the test still fails with the
    original corruption message.

    Unlike ``guard_git_hooks`` which warns, this fixture uses
    ``pytest.fail()`` because config/HEAD/refs corruption — unlike hooks
    corruption — is immediately repo-breaking and must halt the suite.
    """
    if _GUARD_RESTORE_IN_PROGRESS:
        # Re-entry safety: never snapshot during a restore in flight.
        yield
        return

    before = _compute_git_state_snapshot(_PROJECT_ROOT)
    diff: list[str] = []
    try:
        yield
    finally:
        after = _compute_git_state_snapshot(_PROJECT_ROOT)
        diff = _diff_git_state(before, after)
        if diff:
            try:
                _atomic_restore_git_state(_PROJECT_ROOT, before)
            finally:
                pytest.fail(
                    f"Test corrupted host git state: {diff}. "
                    "See docs/analysis/rca-test-git-pollution-2026-04-27.md "
                    "for the failure-mode lineage."
                )


# ---------------------------------------------------------------------------
# 3a: HTML report branding (pytest-html hooks)
# ---------------------------------------------------------------------------


def pytest_html_report_title(report):
    """Set branded title for pytest-html report."""
    report.title = "nWave Test Report"


def pytest_configure(config):
    """Add project metadata to HTML report header."""
    if hasattr(config, "_metadata"):
        config._metadata["Project"] = "nwave"
        config._metadata["Framework"] = "nWave"


def pytest_html_results_summary(prefix, summary, postfix):
    """Inject domain legend into HTML report summary."""
    prefix.extend(
        [
            "<h3>Test Domains</h3>",
            "<ul>",
            "<li><strong>DES</strong> — Developer Experience System</li>",
            "<li><strong>Installer</strong> — CLI installer and acceptance</li>",
            "<li><strong>Plugins</strong> — nWave plugins and install scripts</li>",
            "<li><strong>Acceptance</strong> — End-to-end acceptance tests</li>",
            "<li><strong>Bugs</strong> — Regression tests for tracked bugs</li>",
            "<li><strong>Release Train</strong> — Release pipeline script tests</li>",
            "</ul>",
        ]
    )


# ---------------------------------------------------------------------------
# 3b: Allure auto-labeling
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Tier auto-marking: maps directory prefixes to pytest markers.
# Sorted by specificity at runtime (longest prefix wins).
# ---------------------------------------------------------------------------

TIER_MAP = {
    # DES tiers
    "tests/des/unit/": "unit",
    "tests/des/acceptance/": "acceptance",
    "tests/des/integration/": "integration",
    "tests/des/e2e/": "e2e",
    # Installer tiers
    "tests/installer/unit/": "unit",
    "tests/installer/acceptance/": "acceptance",
    "tests/installer/e2e/": "e2e",
    # Plugin tiers
    "tests/plugins/plugin-architecture/unit/": "unit",
    "tests/plugins/plugin-architecture/integration/": "integration",
    "tests/plugins/plugin-architecture/acceptance/": "acceptance",
    "tests/plugins/plugin-architecture/e2e/": "e2e",
    "tests/plugins/install/": "unit",
    "tests/plugins/": "unit",  # frontmatter tests default to unit
    # Build tiers
    "tests/build/acceptance/": "acceptance",
    "tests/build/unit/": "unit",
    "tests/build/": "unit",
    # Release train tests
    "tests/release/": "unit",
    # Outcomes registry tiers
    "tests/outcomes/unit/": "unit",
    "tests/outcomes/acceptance/": "acceptance",
    # Bug regression tests
    "tests/bugs/": "acceptance",
    # Root-level tests
    "tests/validation/": "unit",
    "tests/e2e/": "e2e",  # testcontainers-driven Docker tests (post Phase 5 retirement of Dockerfiles)
    "tests/": "unit",  # catch-all default
}

DOMAIN_MAP = {
    "tests/des/unit/": ("DES", "Unit Tests"),
    "tests/des/acceptance/": ("DES", "Acceptance Tests"),
    "tests/des/integration/": ("DES", "Integration Tests"),
    "tests/des/e2e/": ("DES", "E2E Tests"),
    "tests/des/": ("DES", "DES Tests"),
    "tests/installer/unit/git_workflow/": ("Installer", "Git Workflow"),
    "tests/installer/unit/": ("Installer", "Unit Tests"),
    "tests/installer/acceptance/installation/": (
        "Installer",
        "Installation Acceptance",
    ),
    "tests/installer/acceptance/installer/": ("Installer", "Installer Acceptance"),
    "tests/installer/acceptance/uninstaller/": ("Installer", "Uninstaller Acceptance"),
    "tests/installer/acceptance/": ("Installer", "Acceptance Tests"),
    "tests/installer/e2e/": ("Installer", "E2E Tests"),
    "tests/plugins/plugin-architecture/unit/": ("Plugins", "Unit Tests"),
    "tests/plugins/plugin-architecture/integration/": ("Plugins", "Integration Tests"),
    "tests/plugins/plugin-architecture/acceptance/": ("Plugins", "Acceptance Tests"),
    "tests/plugins/plugin-architecture/e2e/": ("Plugins", "E2E Tests"),
    "tests/plugins/install/": ("Plugins", "Install Scripts"),
    "tests/plugins/": ("Plugins", "nWave Plugins"),
    "tests/build/acceptance/": ("Build", "Plugin Acceptance"),
    "tests/build/unit/": ("Build", "Unit Tests"),
    "tests/build/": ("Build", "Build Tests"),
    "tests/bugs/": ("Bugs", "Regression"),
    "tests/release/": ("Release Train", "Unit Tests"),
}


# ---------------------------------------------------------------------------
# Top-level test-module guard (RCA Branch B structural defense).
#
# Tests must live under a tier subdirectory (tests/unit/, tests/installer/,
# tests/des/, etc.). Top-level ``tests/test_*.py`` modules historically
# drifted out of sync with their canonical siblings — the attribution
# worktree-isolation bug surfaced because the stale top-level duplicate
# carried tests that no longer matched the canonical version. Once the
# duplicate is gone, this guard prevents future regressions.
#
# Allowlist holds top-level modules that already exist on master and are
# scheduled for migration in a follow-up step. Adding a NEW top-level
# test module is the violation this guard catches.
# Structural rationale: top-level ``tests/test_*.py`` modules historically
# drifted out of sync with their canonical siblings (e.g. an attribution
# test had a stale top-level copy that lacked the isolation fixture used
# by the canonical version under ``tests/installer/unit/plugins/``). The
# 5-tier taxonomy (unit/integration/acceptance/e2e/...) is descriptive
# elsewhere; this guard makes it enforced.
# ---------------------------------------------------------------------------

_TOP_LEVEL_TEST_ALLOWLIST: frozenset[str] = frozenset(
    {
        # Pre-existing top-level modules awaiting migration to a tier subdir.
        # Each of the following has a canonical sibling under tests/installer/
        # or tests/build/ — they are duplicates and will be deleted in a
        # follow-up step (out of scope for 02-01).
        "test_attribution_cli.py",
        "test_attribution_hook.py",
        "test_measure_adoption.py",
        "test_opencode_agents_skill_paths.py",
        "test_plugin_home_env_hardening.py",
        "test_python_path_resolution_in_skills.py",
        "test_reinforce_skill_loading.py",
        # No canonical sibling — keep at top level until migrated.
        "test_docgen.py",
        # Detective-guard self-validation harness (Step 01-01 of
        # fix-test-git-pollution). Lives at top level by design — it
        # validates the conftest-level autouse guard whose snapshot logic
        # is in this same file. Moving it to a subdir would obscure the
        # locality between guard implementation and its self-test.
        "test_guard_fixtures.py",
    }
)


def _is_offending_top_level_test(rel_path: str) -> bool:
    """True iff ``rel_path`` is a top-level ``test_*.py`` and not allowlisted.

    Pure function. ``rel_path`` is normalized with forward slashes,
    relative to the tests root.
    """
    parts = rel_path.split("/")
    if len(parts) != 1:
        return False
    name = parts[0]
    if not (name.startswith("test_") and name.endswith(".py")):
        return False
    return name not in _TOP_LEVEL_TEST_ALLOWLIST


def pytest_collection_modifyitems(config, items):
    """Auto-label tests with Allure labels and tier markers from file paths.

    Also enforces the top-level test-module guard (RCA Branch B): any
    ``tests/test_*.py`` not on the allowlist aborts collection with a
    descriptive error.
    """
    # --- Top-level module guard (fail-fast before any other work) ---
    tests_root = Path(__file__).parent
    offenders: list[str] = []
    for item in items:
        try:
            rel = Path(item.fspath).resolve().relative_to(tests_root.resolve())
        except ValueError:
            # Item lives outside the tests root (e.g. doctest in src/).
            continue
        rel_str = str(rel).replace(os.sep, "/")
        if _is_offending_top_level_test(rel_str):
            offenders.append(rel_str)

    if offenders:
        raise pytest.UsageError(
            "Stale top-level test module(s) detected: "
            + ", ".join(sorted(set(offenders)))
            + ". Tests must live under a tier subdirectory "
            + "(tests/unit/, tests/installer/, tests/des/, tests/build/, etc.). "
            + "Top-level modules historically drifted out of sync with their "
            + "canonical tier siblings; this guard enforces the 5-tier taxonomy."
        )

    try:
        import allure

        has_allure = True
    except ImportError:
        has_allure = False

    # Pre-sort TIER_MAP prefixes by length descending (longest/most-specific first)
    sorted_tier_prefixes = sorted(TIER_MAP.keys(), key=len, reverse=True)

    for item in items:
        rel_path = os.path.relpath(item.fspath, config.rootdir)
        rel_path = rel_path.replace(os.sep, "/")

        # --- Allure labeling (unchanged, conditional on allure) ---
        if has_allure:
            matched_epic = None
            matched_feature = None
            matched_len = 0
            for prefix, (epic, feature) in DOMAIN_MAP.items():
                if rel_path.startswith(prefix) and len(prefix) > matched_len:
                    matched_epic = epic
                    matched_feature = feature
                    matched_len = len(prefix)

            if matched_epic:
                item.add_marker(allure.epic(matched_epic))
                item.add_marker(allure.feature(matched_feature))

            if item.cls:
                item.add_marker(allure.story(item.cls.__name__))

        # --- Tier auto-marking (always runs) ---
        for prefix in sorted_tier_prefixes:
            if rel_path.startswith(prefix):
                tier = TIER_MAP[prefix]
                item.add_marker(getattr(pytest.mark, tier))
                break


# ---------------------------------------------------------------------------
# 3c: Rich terminal summary table
# ---------------------------------------------------------------------------


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Render a Rich table with pass/fail/skip/xfail counts per domain."""
    try:
        from rich.console import Console
        from rich.table import Table
    except ImportError:
        return

    domain_labels = {
        "tests/des/unit/": "DES (unit)",
        "tests/des/acceptance/": "DES (acceptance)",
        "tests/des/integration/": "DES (integration)",
        "tests/des/e2e/": "DES (e2e)",
        "tests/des/": "DES",
        "tests/installer/unit/git_workflow/": "Installer (git)",
        "tests/installer/unit/": "Installer (unit)",
        "tests/installer/acceptance/installation/": "Installer (installation)",
        "tests/installer/acceptance/installer/": "Installer (walking skeleton)",
        "tests/installer/acceptance/uninstaller/": "Installer (uninstaller)",
        "tests/installer/acceptance/": "Installer (acceptance)",
        "tests/installer/e2e/": "Installer (e2e)",
        "tests/plugins/plugin-architecture/unit/": "Plugins (unit)",
        "tests/plugins/plugin-architecture/integration/": "Plugins (integration)",
        "tests/plugins/plugin-architecture/acceptance/": "Plugins (acceptance)",
        "tests/plugins/plugin-architecture/e2e/": "Plugins (e2e)",
        "tests/plugins/install/": "Plugins (install)",
        "tests/plugins/": "Plugins",
        "tests/bugs/": "Bugs",
        "tests/release/": "Release Train",
    }

    # Sorted by specificity (longest prefix first)
    sorted_prefixes = sorted(domain_labels.keys(), key=len, reverse=True)

    stats = {}
    for label in domain_labels.values():
        stats[label] = {"passed": 0, "failed": 0, "skipped": 0, "xfailed": 0}

    category_keys = {
        "passed": "passed",
        "failed": "failed",
        "error": "failed",
        "skipped": "skipped",
        "xfailed": "xfailed",
        "xpassed": "passed",
    }

    for cat, outcome_key in category_keys.items():
        for report in terminalreporter.getreports(cat):
            if not hasattr(report, "fspath") or report.fspath is None:
                continue
            rel = os.path.relpath(str(report.fspath), str(config.rootdir))
            rel = rel.replace(os.sep, "/")

            matched_label = "Other"
            for prefix in sorted_prefixes:
                if rel.startswith(prefix):
                    matched_label = domain_labels[prefix]
                    break

            if matched_label not in stats:
                stats[matched_label] = {
                    "passed": 0,
                    "failed": 0,
                    "skipped": 0,
                    "xfailed": 0,
                }
            stats[matched_label][outcome_key] += 1

    # Remove domains with zero tests
    stats = {k: v for k, v in stats.items() if sum(v.values()) > 0}
    if not stats:
        return

    table = Table(title="Test Results by Domain", show_lines=True)
    table.add_column("Domain", style="bold")
    table.add_column("Passed", style="green", justify="right")
    table.add_column("Failed", style="red", justify="right")
    table.add_column("Skipped", style="yellow", justify="right")
    table.add_column("XFailed", style="cyan", justify="right")
    table.add_column("Total", style="bold", justify="right")

    totals = {"passed": 0, "failed": 0, "skipped": 0, "xfailed": 0}
    for domain in sorted(stats.keys()):
        counts = stats[domain]
        total = sum(counts.values())
        table.add_row(
            domain,
            str(counts["passed"]),
            str(counts["failed"]),
            str(counts["skipped"]),
            str(counts["xfailed"]),
            str(total),
        )
        for k in totals:
            totals[k] += counts[k]

    grand_total = sum(totals.values())
    table.add_row(
        "TOTAL",
        str(totals["passed"]),
        str(totals["failed"]),
        str(totals["skipped"]),
        str(totals["xfailed"]),
        str(grand_total),
        style="bold",
    )

    console = Console()
    console.print()
    console.print(table)
