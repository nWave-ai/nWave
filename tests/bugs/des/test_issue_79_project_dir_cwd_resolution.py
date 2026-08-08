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
- WHEN ``des-verify-integrity`` finds no ``execution-log.json`` at the resolved
  project directory, the system SHALL name the log(s) that exist elsewhere under
  the git worktree root, and SHALL report a scan that could not run.
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

from des.cli import init_log, log_phase, verify_deliver_integrity


FEATURE_ID = "brand-visual-system"


def _git_repo(root: Path) -> None:
    """Initialise a git repo that ignores the developer's global git config.

    The discovery helper enumerates candidates with ``git ls-files
    --exclude-standard``, which honours ``core.excludesFile`` — so on a machine
    whose global gitignore happens to exclude ``docs/``, ``apps/`` or
    ``*.json``, these fixtures would produce different results than on CI. The
    people most likely to run this suite are exactly the ones with elaborate
    global ignores, so the fixture repo pins the setting to an empty file.
    """
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    empty_ignore = root / ".git" / "empty-global-ignore"
    empty_ignore.write_text("")
    subprocess.run(
        ["git", "-C", str(root), "config", "core.excludesFile", str(empty_ignore)],
        check=True,
    )


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
    # Diagnostics go to stderr, matching des-init-log and the other DES CLIs.
    captured = capsys.readouterr()
    output = captured.err
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


# ---------------------------------------------------------------------------
# Failure paths of the discovery helper.
#
# The whole point of #79 is that a silent failure hid a real problem, so the
# helper must not fail silently either: "found nothing" and "could not look"
# have to reach the operator as different messages.
# ---------------------------------------------------------------------------


def test_scan_failure_is_reported_rather_than_read_as_no_siblings(
    tmp_path: Path, capsys, monkeypatch
) -> None:
    """WHEN the sibling scan cannot run, the system SHALL say so.

    Outside a git worktree the scan is impossible. Printing nothing would be
    indistinguishable from "no other log exists" — the exact confusion this
    change removes.
    """
    project_dir = tmp_path / "not-a-repo" / "deliver"
    project_dir.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)

    exit_code = log_phase.main(
        [
            "--project-dir",
            str(project_dir),
            "--step-id",
            "01-01",
            "--phase",
            "GREEN",
            "--status",
            "EXECUTED",
            "--data",
            "PASS",
        ]
    )

    message = capsys.readouterr().err
    assert exit_code == 1
    assert "could not scan for other execution logs" in message, (
        "a scan that could not run must be reported, not rendered as silence"
    )


def test_corrupt_sibling_log_is_reported_not_silently_filtered(
    worktree: Path, capsys, monkeypatch
) -> None:
    """WHEN a sibling log cannot be parsed, the system SHALL still report it.

    A corrupt audit trail is a louder problem than a missing one. Treating an
    unreadable log as "some other feature's log" would drop the strongest
    evidence that something is wrong.
    """
    stray = worktree / "apps" / "website" / "deliver"
    stray.mkdir(parents=True)
    (stray / "execution-log.json").write_text('{"feature_id": "brand-visual')

    missing = worktree / "docs" / "feature" / "other-feature" / "deliver"
    missing.mkdir(parents=True)
    monkeypatch.chdir(worktree)

    log_phase.main(
        [
            "--project-dir",
            str(missing),
            "--step-id",
            "01-01",
            "--phase",
            "GREEN",
            "--status",
            "EXECUTED",
            "--data",
            "PASS",
        ]
    )

    message = capsys.readouterr().err
    assert str(stray / "execution-log.json") in message, (
        "an unparseable sibling log must still be named"
    )
    assert "WARNING" in message and "not valid JSON" in message, (
        "the operator must be told the log is corrupt, and why"
    )


def test_a_file_merely_ending_in_the_log_name_is_not_a_sibling(
    worktree: Path, capsys, monkeypatch
) -> None:
    """A suffix match is not a filename match.

    ``my-execution-log.json`` is a different file. A git pathspec without
    ``:(glob)`` magic would select it, because ``*`` there matches across path
    separators as a plain suffix.
    """
    decoy_dir = worktree / "apps" / "website"
    decoy_dir.mkdir(parents=True, exist_ok=True)
    (decoy_dir / "my-execution-log.json").write_text("{}")

    missing = worktree / "docs" / "feature" / "other-feature" / "deliver"
    missing.mkdir(parents=True)
    monkeypatch.chdir(worktree)

    log_phase.main(
        [
            "--project-dir",
            str(missing),
            "--step-id",
            "01-01",
            "--phase",
            "GREEN",
            "--status",
            "EXECUTED",
            "--data",
            "PASS",
        ]
    )

    message = capsys.readouterr().err
    assert "my-execution-log.json" not in message, (
        "a file whose name merely ends in the log name is not an execution log"
    )


# ---------------------------------------------------------------------------
# des-verify-integrity shares the same missing-log branch.
#
# The Phase 6 closure gate is where a forked log does the most damage: it
# reports an incomplete trace for a directory that is not the one the run
# actually wrote to. Its diagnostic must carry the same evidence as
# des-log-phase's, so both CLIs are exercised, not just the two that write.
# ---------------------------------------------------------------------------


def _roadmap(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "roadmap": {
                    "project_id": FEATURE_ID,
                    "created_at": "2026-01-01T00:00:00Z",
                    "total_steps": 1,
                },
                "phases": [
                    {
                        "id": "01",
                        "name": "Phase One",
                        "steps": [
                            {
                                "id": "01-01",
                                "name": "First",
                                "criteria": ["the first step is done"],
                            }
                        ],
                    }
                ],
            },
            indent=2,
        )
    )


def test_verify_integrity_names_the_existing_log_when_relative_dir_misses(
    worktree: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The closure gate must name the log that DOES exist, not a bare miss."""
    canonical_log = (
        worktree / "docs" / "feature" / FEATURE_ID / "deliver" / "execution-log.json"
    )
    subdir_deliver = (
        worktree / "apps" / "website" / "docs" / "feature" / FEATURE_ID / "deliver"
    )
    _roadmap(subdir_deliver / "roadmap.json")
    monkeypatch.chdir(worktree / "apps" / "website")

    exit_code = verify_deliver_integrity.main([f"docs/feature/{FEATURE_ID}/deliver"])

    assert exit_code == 2
    output = capsys.readouterr().err
    assert str(canonical_log) in output, (
        "the closure gate must name the existing canonical log, not only the miss"
    )


def test_verify_integrity_reports_a_scan_that_could_not_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """WHEN the scan cannot run, the closure gate SHALL say so, not stay silent."""
    project_dir = tmp_path / "not-a-repo" / "deliver"
    project_dir.mkdir(parents=True)
    _roadmap(project_dir / "roadmap.json")
    monkeypatch.chdir(tmp_path)

    exit_code = verify_deliver_integrity.main([str(project_dir)])

    assert exit_code == 2
    message = capsys.readouterr().err
    assert "could not scan for other execution logs" in message, (
        "a scan that could not run must be reported, not rendered as silence"
    )
