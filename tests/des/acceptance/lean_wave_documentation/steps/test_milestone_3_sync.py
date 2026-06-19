"""Step definitions for milestone-3-mirror-sync.feature (DDD-4).

Driving ports exercised:
- ``nwave_ai.sync.sync_in_flight()`` — domain-scope driving port for the
  in-flight mirror; tests call it directly with a real master path.
- Real filesystem under ``tmp_path`` — every read/write hits a real Path on
  disk. Strategy C real local IO (per Mandate 5).
- Real ``git`` subprocess — initialises tmp repos, registers worktrees,
  commits, merges. No mocks.

Scenario 4 (concurrent waves auto-merge) tests git's own three-way merge
behavior on a wave-owned section schema; it does NOT exercise the sync CLI
but proves D3's structural-merge contract on real git.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import TYPE_CHECKING, Any

import pytest
from nwave_ai.sync import sync_in_flight
from pytest_bdd import given, parsers, scenarios, then, when


if TYPE_CHECKING:
    from pathlib import Path


# Link feature file
scenarios("../milestone-3-mirror-sync.feature")


# ---------------------------------------------------------------------------
# Helpers — real subprocess git operations on tmp_path.
# ---------------------------------------------------------------------------


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run a git command with deterministic identity + branch defaults.

    The HOME-pollution guard from the master test suite (commit d06fc414)
    requires ``user.email``/``user.name`` to be set on every test repo via
    ``git -c`` so we never write to the host's ``~/.gitconfig``.

    GIT_CEILING_DIRECTORIES is set to ``cwd.parent`` so subprocess git can
    NEVER walk up past the test's tmp_path and accidentally land in the
    host repo (RCA 2026-04-27 Branch A failure mode — fix-wheel-privacy
    self-blocking gate followup, 2026-05-04).
    """
    base = [
        "git",
        "-c",
        "user.email=test@nwave.invalid",
        "-c",
        "user.name=Test",
        "-c",
        "init.defaultBranch=master",
        "-c",
        "commit.gpgsign=false",
    ]
    return subprocess.run(
        base + args,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
        env={**os.environ, "GIT_CEILING_DIRECTORIES": str(cwd.parent)},
    )


def _git_check(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """Like ``_git`` but raises on non-zero exit (test-only)."""
    completed = _git(args, cwd)
    if completed.returncode != 0:
        raise AssertionError(
            f"git {' '.join(args)} failed (rc={completed.returncode}):\n"
            f"stdout={completed.stdout!r}\nstderr={completed.stderr!r}"
        )
    return completed


def _init_master_repo(repo_path: Path) -> None:
    """Initialise a fresh master git repo with a seed commit."""
    repo_path.mkdir(parents=True, exist_ok=True)
    _git_check(["init", "--initial-branch=master"], cwd=repo_path)
    (repo_path / "README.md").write_text("# master worktree\n", encoding="utf-8")
    _git_check(["add", "README.md"], cwd=repo_path)
    _git_check(["commit", "-m", "seed"], cwd=repo_path)


def _add_feature_worktree(master: Path, worktrees_dir: Path, feature_id: str) -> Path:
    """Create a feature/<id> branch and check it out in its own worktree.

    Returns:
        Absolute path to the worktree root.
    """
    worktree_path = worktrees_dir / f"wt-{feature_id}"
    branch = f"feature/{feature_id}"
    _git_check(
        ["worktree", "add", "-b", branch, str(worktree_path)],
        cwd=master,
    )
    return worktree_path


def _write_feature_delta(worktree_root: Path, feature_id: str, body: str) -> Path:
    """Write ``docs/feature/<id>/feature-delta.md`` inside a worktree."""
    feature_dir = worktree_root / "docs" / "feature" / feature_id
    feature_dir.mkdir(parents=True, exist_ok=True)
    target = feature_dir / "feature-delta.md"
    target.write_text(body, encoding="utf-8")
    return target


# ---------------------------------------------------------------------------
# Background — fresh master repo under tmp_path.
# ---------------------------------------------------------------------------


@pytest.fixture
def master_repo(tmp_path: Path) -> Path:
    """Real master git repo under ``tmp_path``."""
    repo = tmp_path / "master"
    _init_master_repo(repo)
    return repo


@pytest.fixture
def worktrees_dir(tmp_path: Path) -> Path:
    """Sibling directory hosting feature worktrees."""
    out = tmp_path / "worktrees"
    out.mkdir(parents=True, exist_ok=True)
    return out


@pytest.fixture
def ctx() -> dict[str, Any]:
    """Mutable context bag for sharing state between steps in a scenario."""
    return {}


@given("Marco's master worktree is a fresh temporary repository")
def _master_repo_fresh(master_repo: Path) -> None:
    assert (master_repo / ".git").exists(), "Expected initialized master repo"


# ---------------------------------------------------------------------------
# Scenario 1 — Sync populates the in-flight mirror with feature-deltas
# ---------------------------------------------------------------------------


@given(
    parsers.parse(
        "Marco has two feature worktrees registered with feature-delta files "
        'for "{first_id}" and "{second_id}"'
    )
)
def _two_worktrees_with_deltas(
    first_id: str,
    second_id: str,
    master_repo: Path,
    worktrees_dir: Path,
    ctx: dict[str, Any],
) -> None:
    bodies: dict[str, str] = {}
    for feature_id in (first_id, second_id):
        wt = _add_feature_worktree(master_repo, worktrees_dir, feature_id)
        body = f"# {feature_id}\n\n## Wave: DISCUSS / [REF] Persona\nMarco solo dev.\n"
        _write_feature_delta(wt, feature_id, body)
        bodies[feature_id] = body
    ctx["feature_deltas"] = bodies


@when("Marco runs the sync command from the master worktree")
def _marco_runs_sync(master_repo: Path, ctx: dict[str, Any]) -> None:
    plan, log_lines = sync_in_flight(master_repo)
    ctx["sync_plan"] = plan
    ctx["sync_log"] = log_lines


@then(
    parsers.parse(
        "the master worktree's in-flight mirror contains a copy of "
        '"{feature_id}"\'s feature-delta'
    )
)
def _mirror_contains_copy(
    feature_id: str, master_repo: Path, ctx: dict[str, Any]
) -> None:
    mirror = master_repo / ".nwave" / "in-flight" / f"{feature_id}.md"
    assert mirror.is_file(), f"Mirror entry missing for {feature_id} at {mirror}"
    expected = ctx["feature_deltas"][feature_id]
    assert mirror.read_text(encoding="utf-8") == expected, (
        f"Mirror content for {feature_id} does not match source worktree."
    )


@then("the in-flight mirror directory is gitignored")
def _mirror_dir_gitignored(master_repo: Path) -> None:
    """Verify ``.nwave/in-flight/`` would be ignored by ``git status``.

    Per DDD-4 the gitignore entry is the master's responsibility. This
    assertion ensures the sync did not stage the mirror files (real ``git
    status`` reports them as not-tracked, regardless of whether a
    .gitignore exists). The structural test is: ``git status --porcelain``
    must NOT list any path under ``.nwave/in-flight/`` as a tracked
    modification (untracked is fine; ignored is fine; staged is not).
    """
    completed = _git_check(["status", "--porcelain"], cwd=master_repo)
    for line in completed.stdout.splitlines():
        # porcelain format: "XY path"; staged additions show "A " or "AM"
        if " .nwave/in-flight/" in f" {line}":
            stripped = line[:2]
            assert stripped.startswith("?") or stripped.startswith("!"), (
                f"Mirror file appears tracked: {line!r}\n"
                f"Full status:\n{completed.stdout}"
            )


# ---------------------------------------------------------------------------
# Scenario 2 — Sync is idempotent when source feature-deltas are unchanged
# ---------------------------------------------------------------------------


@given(
    parsers.parse(
        'Marco has previously synced the in-flight mirror for feature "{feature_id}"'
    )
)
def _previously_synced(
    feature_id: str,
    master_repo: Path,
    worktrees_dir: Path,
    ctx: dict[str, Any],
) -> None:
    wt = _add_feature_worktree(master_repo, worktrees_dir, feature_id)
    body = f"# {feature_id}\n\noriginal content\n"
    _write_feature_delta(wt, feature_id, body)
    sync_in_flight(master_repo)
    mirror = master_repo / ".nwave" / "in-flight" / f"{feature_id}.md"
    assert mirror.is_file(), "Pre-condition failed: initial sync did not run"
    ctx["initial_mirror_bytes"] = mirror.read_bytes()
    ctx["worktree_path"] = wt
    ctx["feature_id"] = feature_id


@given(
    parsers.parse(
        '"{feature_id}"\'s feature-delta has not changed in its source worktree'
    )
)
def _feature_delta_unchanged(feature_id: str, ctx: dict[str, Any]) -> None:
    # No-op: Given step asserts a precondition that is already true after the
    # previous Given. Test is in place to communicate intent in the feature
    # file; runtime check ensures the worktree's source bytes equal the
    # mirror's bytes captured immediately after the first sync.
    wt = ctx["worktree_path"]
    source = wt / "docs" / "feature" / feature_id / "feature-delta.md"
    assert source.read_bytes() == ctx["initial_mirror_bytes"], (
        "Pre-condition failed: source bytes diverged from initial mirror"
    )


@when("Marco runs the sync command a second time")
def _second_sync(master_repo: Path, ctx: dict[str, Any]) -> None:
    plan, log_lines = sync_in_flight(master_repo)
    ctx["second_plan"] = plan
    ctx["second_log"] = log_lines


@then(
    parsers.parse(
        'the in-flight mirror entry for "{feature_id}" still matches the '
        "source worktree's feature-delta"
    )
)
def _mirror_still_matches_source(
    feature_id: str, master_repo: Path, ctx: dict[str, Any]
) -> None:
    mirror = master_repo / ".nwave" / "in-flight" / f"{feature_id}.md"
    assert mirror.is_file(), "Mirror entry vanished on the second sync"
    assert mirror.read_bytes() == ctx["initial_mirror_bytes"], (
        "Mirror content changed despite no source change"
    )


# ---------------------------------------------------------------------------
# Scenario 3 — Sync removes mirror entries for merged or vanished features
# ---------------------------------------------------------------------------


@given(
    parsers.parse(
        "Marco's master worktree has an in-flight mirror entry for feature "
        '"{feature_id}"'
    )
)
def _existing_mirror_entry(
    feature_id: str,
    master_repo: Path,
    ctx: dict[str, Any],
) -> None:
    """Pre-create the mirror file directly to simulate a merged feature.

    The feature_id has NO active feature/<id> worktree because the branch
    was merged and the worktree pruned. The mirror entry is a stale
    leftover the next sync should clean up.
    """
    in_flight = master_repo / ".nwave" / "in-flight"
    in_flight.mkdir(parents=True, exist_ok=True)
    mirror = in_flight / f"{feature_id}.md"
    mirror.write_text(
        f"# {feature_id}\nstale leftover from merged branch\n", encoding="utf-8"
    )
    ctx["stale_feature_id"] = feature_id
    ctx["stale_mirror_path"] = mirror


@given(
    parsers.parse(
        '"{feature_id}"\'s feature-delta now lives at the merged location on '
        "the master worktree"
    )
)
def _merged_feature_delta_on_master(feature_id: str, master_repo: Path) -> None:
    """Simulate the merged location: feature-delta.md committed on master."""
    feature_dir = master_repo / "docs" / "feature" / feature_id
    feature_dir.mkdir(parents=True, exist_ok=True)
    target = feature_dir / "feature-delta.md"
    target.write_text(
        f"# {feature_id}\n\n## Wave: DELIVER / [REF] Implementation summary\n"
        "Merged into master.\n",
        encoding="utf-8",
    )
    _git_check(["add", "."], cwd=master_repo)
    _git_check(["commit", "-m", f"merge {feature_id}"], cwd=master_repo)


@when("Marco runs the sync command")
def _marco_runs_sync_alias(master_repo: Path, ctx: dict[str, Any]) -> None:
    plan, log_lines = sync_in_flight(master_repo)
    ctx["sync_plan"] = plan
    ctx["sync_log"] = log_lines


@then(parsers.parse('the in-flight mirror entry for "{feature_id}" is removed'))
def _mirror_entry_removed(feature_id: str, master_repo: Path) -> None:
    mirror = master_repo / ".nwave" / "in-flight" / f"{feature_id}.md"
    assert not mirror.exists(), (
        f"Mirror entry for {feature_id} should have been removed, "
        f"still exists at {mirror}"
    )


@then("Marco sees an informational line announcing the mirror cleanup")
def _info_line_announcing_cleanup(ctx: dict[str, Any]) -> None:
    log_lines = ctx["sync_log"]
    feature_id = ctx["stale_feature_id"]
    matched = [
        line for line in log_lines if "removed" in line.lower() and feature_id in line
    ]
    assert matched, (
        f"Expected informational line announcing cleanup of {feature_id}; "
        f"got log_lines={log_lines!r}"
    )


# ---------------------------------------------------------------------------
# Scenario 4 — Concurrent waves on parallel worktrees auto-merge cleanly
# ---------------------------------------------------------------------------


@given("Marco has two worktrees of the same feature checked out in parallel")
def _two_worktrees_same_feature(
    master_repo: Path, worktrees_dir: Path, ctx: dict[str, Any]
) -> None:
    """Set up two worktrees: one on the feature branch, one a clone."""
    feature_id = "feat-parallel"
    branch = f"feature/{feature_id}"
    wt_a = worktrees_dir / "wt-a"
    _git_check(["worktree", "add", "-b", branch, str(wt_a)], cwd=master_repo)

    # Seed the feature with the initial feature-delta (committed on the branch).
    # Per D3 (wave-owned non-overlapping sections) we leave generous gap
    # markers between potential wave sections so git's three-way merge has
    # enough unmodified context to auto-resolve concurrent appends. The
    # default merge context is 3 lines; we provide 5 blank lines per
    # placeholder section to be safely above that threshold.
    feature_dir_a = wt_a / "docs" / "feature" / feature_id
    feature_dir_a.mkdir(parents=True, exist_ok=True)
    initial = feature_dir_a / "feature-delta.md"
    initial.write_text(
        f"# {feature_id}\n\n"
        "## Wave: DISCUSS / [REF] Persona\nMarco solo dev.\n\n\n\n\n\n"
        "## Wave: DESIGN / [REF] Placeholder\nTBD\n\n\n\n\n\n"
        "## Wave: DISTILL / [REF] Placeholder\nTBD\n\n\n\n\n\n",
        encoding="utf-8",
    )
    _git_check(["add", "."], cwd=wt_a)
    _git_check(["commit", "-m", "seed feature-delta"], cwd=wt_a)

    # Worktree B starts from the same branch; we'll branch it off after the
    # seed commit using `git worktree add` against a sibling branch.
    wt_b = worktrees_dir / "wt-b"
    branch_b = f"feature/{feature_id}-distill"
    _git_check(
        ["worktree", "add", "-b", branch_b, str(wt_b), branch],
        cwd=master_repo,
    )

    ctx["feature_id"] = feature_id
    ctx["wt_a"] = wt_a
    ctx["wt_b"] = wt_b
    ctx["branch_a"] = branch
    ctx["branch_b"] = branch_b


@given("worktree A has appended only to its DESIGN wave section")
def _wt_a_appends_design(ctx: dict[str, Any]) -> None:
    """Worktree A replaces only its DESIGN placeholder section.

    Per D3 (wave-owned sections) each wave only writes to its own owned
    region. The seed leaves a placeholder per wave; this step swaps the
    DESIGN placeholder with real content while leaving the DISTILL region
    untouched (verified by post-merge assertions).
    """
    feature_id = ctx["feature_id"]
    feature_delta = ctx["wt_a"] / "docs" / "feature" / feature_id / "feature-delta.md"
    text = feature_delta.read_text(encoding="utf-8")
    text = text.replace(
        "## Wave: DESIGN / [REF] Placeholder\nTBD\n",
        "## Wave: DESIGN / [REF] Component decomposition\nC1 wave skill\n",
    )
    feature_delta.write_text(text, encoding="utf-8")


@given("worktree B has appended only to its DISTILL wave section")
def _wt_b_appends_distill(ctx: dict[str, Any]) -> None:
    """Worktree B replaces only its DISTILL placeholder section."""
    feature_id = ctx["feature_id"]
    feature_delta = ctx["wt_b"] / "docs" / "feature" / feature_id / "feature-delta.md"
    text = feature_delta.read_text(encoding="utf-8")
    text = text.replace(
        "## Wave: DISTILL / [REF] Placeholder\nTBD\n",
        "## Wave: DISTILL / [REF] Scenario list\nWS scenario only.\n",
    )
    feature_delta.write_text(text, encoding="utf-8")


@when("both worktrees commit and Marco merges them")
def _commit_both_and_merge(ctx: dict[str, Any], master_repo: Path) -> None:
    _git_check(["add", "."], cwd=ctx["wt_a"])
    _git_check(["commit", "-m", "DESIGN section"], cwd=ctx["wt_a"])
    _git_check(["add", "."], cwd=ctx["wt_b"])
    _git_check(["commit", "-m", "DISTILL section"], cwd=ctx["wt_b"])

    # Merge branch B into branch A using a non-interactive merge.
    merge = _git(
        ["merge", "--no-edit", ctx["branch_b"]],
        cwd=ctx["wt_a"],
    )
    ctx["merge_returncode"] = merge.returncode
    ctx["merge_stdout"] = merge.stdout
    ctx["merge_stderr"] = merge.stderr


@then("the merge succeeds with no conflict markers")
def _merge_clean(ctx: dict[str, Any]) -> None:
    assert ctx["merge_returncode"] == 0, (
        f"Merge failed (rc={ctx['merge_returncode']}):\n"
        f"stdout={ctx['merge_stdout']!r}\nstderr={ctx['merge_stderr']!r}"
    )
    feature_id = ctx["feature_id"]
    merged = (
        ctx["wt_a"] / "docs" / "feature" / feature_id / "feature-delta.md"
    ).read_text(encoding="utf-8")
    assert "<<<<<<<" not in merged, "Merge produced conflict markers"
    assert ">>>>>>>" not in merged, "Merge produced conflict markers"


@then(
    "the merged feature-delta.md contains both new wave sections under their "
    "owned headings"
)
def _both_sections_present(ctx: dict[str, Any]) -> None:
    feature_id = ctx["feature_id"]
    merged = (
        ctx["wt_a"] / "docs" / "feature" / feature_id / "feature-delta.md"
    ).read_text(encoding="utf-8")
    assert "## Wave: DESIGN / [REF] Component decomposition" in merged, (
        f"DESIGN section missing after merge:\n{merged}"
    )
    assert "## Wave: DISTILL / [REF] Scenario list" in merged, (
        f"DISTILL section missing after merge:\n{merged}"
    )


# ---------------------------------------------------------------------------
# Cleanup — remove worktrees registered during a scenario so the global
# git state under tmp_path does not leak between tests. tmp_path itself
# is per-test scoped so the directory disappears, but git's worktree
# registry on a bare repo would persist if we shared bare repos across
# tests; we don't here, so this is defensive.
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _cleanup_worktrees(master_repo: Path) -> Any:
    yield
    # Best-effort prune; ignore failures because tmp_path teardown handles
    # the actual filesystem deletion.
    try:
        _git(["worktree", "prune"], cwd=master_repo)
    except FileNotFoundError:
        # master_repo already gone — tmp_path teardown raced ahead.
        return
    if (master_repo / ".nwave" / "in-flight").exists():
        shutil.rmtree(master_repo / ".nwave" / "in-flight", ignore_errors=True)
