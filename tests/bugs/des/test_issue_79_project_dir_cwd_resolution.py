"""Regression guard (issue #79): a mid-run ``cd`` must not silently split the
DELIVER execution log across two directories.

``des-init-log``, ``des-log-phase`` and ``des-verify-integrity`` all resolve
``--project-dir`` implicitly against the *process* CWD. When an agent ``cd``s
into a monorepo subdirectory partway through a DELIVER run, the same relative
``--project-dir`` string denotes a different absolute directory: ``des-log-phase``
fails with a bare "not found" and the recovery reflex (``des-init-log``) starts a
SECOND, divergent ``execution-log.json`` — with no signal that a canonical log
already exists elsewhere in the same worktree.

The fix is loud failure, not silent re-anchoring:

- WHEN ``des-log-phase`` targets a project directory with no ``execution-log.json``
  AND at least one ``execution-log.json`` exists elsewhere under the git worktree
  root, the system SHALL name BOTH the missing path and the existing log(s).
- WHEN ``des-init-log`` would create a log for a feature id that already has an
  ``execution-log.json`` elsewhere under the git worktree root, the system SHALL
  refuse, naming BOTH paths, and SHALL NOT write a second log.
- WHERE ``--allow-duplicate-log`` is passed, ``des-init-log`` SHALL create the log
  regardless of the sibling log (the legitimate deliberate-second-log case).

Every fixture is an isolated real git worktree under ``tmp_path``; the CLIs are
driven through their real ``main()`` entry points with a real process CWD change,
reproducing the reported cd-into-subdir scenario port-to-port.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from des.cli import init_log, log_phase


FEATURE_ID = "brand-visual-system"


def _git_repo(root: Path) -> None:
    subprocess.run(["git", "init", "-q", str(root)], check=True)


@pytest.fixture
def worktree(tmp_path: Path) -> Path:
    """A git worktree with a canonical DELIVER log and a monorepo subdirectory."""
    root = tmp_path / "repo"
    root.mkdir()
    _git_repo(root)

    deliver = root / "docs" / "feature" / FEATURE_ID / "deliver"
    deliver.mkdir(parents=True)
    (deliver / "execution-log.json").write_text(
        json.dumps(
            {"schema_version": "5.0", "feature_id": FEATURE_ID, "events": []},
            indent=2,
        )
    )

    subdir = root / "apps" / "website"
    subdir.mkdir(parents=True)
    (subdir / "docs" / "feature" / FEATURE_ID / "deliver").mkdir(parents=True)

    return root


def test_log_phase_names_the_existing_log_when_relative_dir_misses(
    worktree: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The cd-into-subdir miss must name BOTH paths, not just the missing one."""
    canonical = worktree / "docs" / "feature" / FEATURE_ID / "deliver"
    monkeypatch.chdir(worktree / "apps" / "website")

    relative = f"docs/feature/{FEATURE_ID}/deliver"
    exit_code = log_phase.main(
        [
            "--project-dir",
            relative,
            "--step-id",
            "02-03",
            "--phase",
            "GREEN",
            "--status",
            "EXECUTED",
            "--data",
            "PASS",
        ]
    )

    assert exit_code == 1
    output = capsys.readouterr().out
    assert str(canonical / "execution-log.json") in output, (
        "the diagnostic must name the existing canonical log, not only the miss"
    )


def test_init_log_refuses_a_second_log_for_the_same_feature(
    worktree: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Recovery-by-re-init must not silently fork the log for the same feature."""
    canonical_log = (
        worktree / "docs" / "feature" / FEATURE_ID / "deliver" / "execution-log.json"
    )
    subdir_deliver = (
        worktree / "apps" / "website" / "docs" / "feature" / FEATURE_ID / "deliver"
    )
    monkeypatch.chdir(worktree / "apps" / "website")

    exit_code = init_log.main(
        [
            "--project-dir",
            f"docs/feature/{FEATURE_ID}/deliver",
            "--feature-id",
            FEATURE_ID,
        ]
    )

    assert exit_code == 1
    assert not (subdir_deliver / "execution-log.json").exists(), (
        "a second divergent execution log must not be created"
    )
    combined = capsys.readouterr()
    message = combined.out + combined.err
    assert str(canonical_log) in message
    assert str(subdir_deliver / "execution-log.json") in message


def test_init_log_allow_duplicate_flag_creates_the_second_log(
    worktree: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """WHERE the second log is deliberate, the explicit opt-out SHALL permit it."""
    subdir_deliver = (
        worktree / "apps" / "website" / "docs" / "feature" / FEATURE_ID / "deliver"
    )
    monkeypatch.chdir(worktree / "apps" / "website")

    exit_code = init_log.main(
        [
            "--project-dir",
            f"docs/feature/{FEATURE_ID}/deliver",
            "--feature-id",
            FEATURE_ID,
            "--allow-duplicate-log",
        ]
    )

    assert exit_code == 0
    assert (subdir_deliver / "execution-log.json").exists()


def test_init_log_unaffected_when_no_sibling_log_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A first log in a clean worktree SHALL still be created without a flag."""
    root = tmp_path / "clean"
    root.mkdir()
    _git_repo(root)
    deliver = root / "docs" / "feature" / "fresh" / "deliver"
    deliver.mkdir(parents=True)
    monkeypatch.chdir(root)

    exit_code = init_log.main(
        ["--project-dir", "docs/feature/fresh/deliver", "--feature-id", "fresh"]
    )

    assert exit_code == 0
    assert (deliver / "execution-log.json").exists()


def test_init_log_ignores_a_log_for_a_different_feature(
    worktree: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The guard SHALL key on feature id, not on any log anywhere in the tree."""
    other = worktree / "docs" / "feature" / "other-feature" / "deliver"
    other.mkdir(parents=True)
    monkeypatch.chdir(worktree)

    exit_code = init_log.main(
        [
            "--project-dir",
            "docs/feature/other-feature/deliver",
            "--feature-id",
            "other-feature",
        ]
    )

    assert exit_code == 0
    assert (other / "execution-log.json").exists()
