"""
Unit tests for BackupManager.

Tests backup creation functionality that will be reused from
scripts/install/install_utils.py.

These tests follow Outside-In TDD - they are written BEFORE implementation
and should FAIL until BackupManager is implemented.

State-delta migration summary
------------------------------
CONVERTED (3 tests) — assert_state_delta + implicit-unchanged invariant:
  - test_create_backup_creates_directory_with_correct_name_format:
    filesystem multi-slot (backup.exists, source.exists, source_file.exists);
    implicit-unchanged enforces source directory is not touched during backup.
  - test_create_backup_copies_all_files_from_source:
    multi-slot (4 backup content slots + 4 source content slots);
    implicit-unchanged on source slots catches any accidental mutation to the
    original files during the copy (classic "preserve source" invariant).
  - test_create_backup_handles_sequence_numbers_for_multiple_backups_same_day:
    multi-slot (3 backup.exists slots + source_file.exists);
    implicit-unchanged guards that multiple backup calls don't corrupt the
    source directory or its contents between calls.

KEPT as-is (2 tests) — no state-delta benefit:
  - test_create_backup_raises_error_when_source_does_not_exist: exception
    path; no filesystem mutation occurs; result-assertion style is correct as-is.
  - test_create_backup_returns_backup_path: return-value contract (isinstance,
    is_dir, parent); primary assertion is on the function's return value, not
    filesystem state mutation; state-delta adds ceremony without gain.

Hidden mutations found: NONE detected. Source directory contents are untouched
across all scenarios — shutil.copytree does not mutate source. The implicit-
unchanged invariant is now enforced explicitly, making the "clean copy" contract
machine-checkable going forward.
"""

from datetime import datetime
from pathlib import Path

import pytest
from nwave_ai.state_delta import assert_state_delta, set_to


# ---------------------------------------------------------------------------
# State-delta helpers
# ---------------------------------------------------------------------------


def _backup_filesystem_state(
    home_dir: Path,
    backup_name: str,
    track: frozenset[str] | None = None,
) -> dict[str, object]:
    """Return a flat state dict for backup directory existence.

    Slots: "<label>.exists" — bool whether the path exists.

    When ``track`` is provided every name in the set is always emitted,
    even when the path is absent (emits False). Without ``track``, only
    existing paths are emitted.

    Args:
        home_dir: Parent directory containing source and backup directories.
        backup_name: Name of the backup directory (e.g. ".claude_bck_20240101").
        track: Optional explicit set of slot names to always emit.
    """
    state: dict[str, object] = {}
    if track is not None:
        for slot in track:
            # Slot format: "<name>.exists" where name is relative to home_dir
            name = slot.removesuffix(".exists")
            state[slot] = (home_dir / name).exists()
    return state


def _source_content_state(
    source_dir: Path, filenames: list[tuple[str, ...]]
) -> dict[str, object]:
    """Return a flat state dict for source file content.

    Slots: "source.<rel_path>.content" — str content of each file.
    Returns empty string for absent files.

    Args:
        source_dir: Root of source directory.
        filenames: List of path tuples relative to source_dir (e.g. ("file1.txt",)).
    """
    state: dict[str, object] = {}
    for parts in filenames:
        path = source_dir.joinpath(*parts)
        slot = "source." + "/".join(parts) + ".content"
        state[slot] = path.read_text() if path.exists() else ""
    return state


def _backup_content_state(
    backup_dir: Path, filenames: list[tuple[str, ...]]
) -> dict[str, object]:
    """Return a flat state dict for backup file content.

    Slots: "backup.<rel_path>.content" — str content of each file.
    Returns empty string for absent files.

    Args:
        backup_dir: Root of backup directory.
        filenames: List of path tuples relative to backup_dir.
    """
    state: dict[str, object] = {}
    for parts in filenames:
        path = backup_dir.joinpath(*parts)
        slot = "backup." + "/".join(parts) + ".content"
        state[slot] = path.read_text() if path.exists() else ""
    return state


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBackupManager:
    """Unit tests for BackupManager backup creation."""

    def test_create_backup_creates_directory_with_correct_name_format(self, tmp_path):
        """
        GIVEN a source directory exists
        WHEN create_backup is called
        THEN a backup directory is created with .claude_bck_YYYYMMDD format
             AND the source directory and its contents are not touched

        State-delta: backup.exists transitions False→True; source.exists and
        source_test_file.txt.exists stay True (implicit-unchanged invariant
        guards against accidental source mutation).
        """
        from scripts.update.backup_manager import BackupManager

        source_dir = tmp_path / ".claude"
        source_dir.mkdir()
        (source_dir / "test_file.txt").write_text("test content")

        manager = BackupManager(home_dir=tmp_path)

        today = datetime.now().strftime("%Y%m%d")
        expected_backup_name = f".claude_bck_{today}"

        # Build tracked universe: backup dir + source dir + source file
        tracked = frozenset(
            [
                f"{expected_backup_name}.exists",
                ".claude.exists",
                ".claude/test_file.txt.exists",
            ]
        )
        before = _backup_filesystem_state(tmp_path, expected_backup_name, track=tracked)

        backup_path = manager.create_backup(source_dir)

        after = _backup_filesystem_state(tmp_path, expected_backup_name, track=tracked)

        # Verify date format contract before asserting state
        date_part = backup_path.name.replace(".claude_bck_", "")
        assert len(date_part) == 8
        assert date_part.isdigit()
        assert date_part == today

        assert_state_delta(
            before=before,
            after=after,
            universe=set(tracked),
            expected={
                # Backup directory created
                f"{expected_backup_name}.exists": set_to(True),
                # Source directory and file: implicit-unchanged (not in expected)
            },
        )

    def test_create_backup_copies_all_files_from_source(self, tmp_path):
        """
        GIVEN a source directory with multiple files and subdirectories
        WHEN create_backup is called
        THEN all files and directory structure are copied to backup
             AND the source files remain byte-identical to before the call

        State-delta: 4 backup content slots transition ""→expected_content;
        4 source content slots remain unchanged (implicit-unchanged invariant).
        The source-unchanged slots make the "non-destructive copy" contract
        machine-checkable: if copytree ever mutated source, the test fails.
        """
        from scripts.update.backup_manager import BackupManager

        source_dir = tmp_path / ".claude"
        source_dir.mkdir()
        (source_dir / "file1.txt").write_text("content1")
        (source_dir / "file2.txt").write_text("content2")
        subdir = source_dir / "subdir"
        subdir.mkdir()
        (subdir / "file3.txt").write_text("content3")

        manager = BackupManager(home_dir=tmp_path)

        # All relative paths tracked in both source and backup universes
        file_paths: list[tuple[str, ...]] = [
            ("file1.txt",),
            ("file2.txt",),
            ("subdir", "file3.txt"),
        ]

        before_source = _source_content_state(source_dir, file_paths)

        backup_path = manager.create_backup(source_dir)

        after_source = _source_content_state(source_dir, file_paths)
        after_backup = _backup_content_state(backup_path, file_paths)

        # Source content must be identical after backup (implicit-unchanged)
        source_universe = set(before_source.keys())
        assert_state_delta(
            before=before_source,
            after=after_source,
            universe=source_universe,
            expected={},  # nothing should change — all slots implicit-unchanged
        )

        # Backup content slots must match expected file contents
        backup_universe = set(after_backup.keys())
        assert_state_delta(
            before=dict.fromkeys(backup_universe, ""),  # all absent before backup
            after=after_backup,
            universe=backup_universe,
            expected={
                "backup.file1.txt.content": set_to("content1"),
                "backup.file2.txt.content": set_to("content2"),
                "backup.subdir/file3.txt.content": set_to("content3"),
            },
        )

    def test_create_backup_raises_error_when_source_does_not_exist(self, tmp_path):
        """
        GIVEN a source directory that does not exist
        WHEN create_backup is called
        THEN FileNotFoundError is raised with clear message

        KEPT as-is: exception path; no filesystem mutation occurs.
        State-delta adds ceremony without gain on error paths.
        """
        from scripts.update.backup_manager import BackupManager

        source_dir = tmp_path / ".claude"
        # Do NOT create source_dir - it should not exist

        manager = BackupManager(home_dir=tmp_path)

        with pytest.raises(FileNotFoundError) as exc_info:
            manager.create_backup(source_dir)

        assert "Source directory does not exist" in str(exc_info.value)
        assert str(source_dir) in str(exc_info.value)

    def test_create_backup_returns_backup_path(self, tmp_path):
        """
        GIVEN a source directory exists
        WHEN create_backup is called
        THEN the Path to the created backup directory is returned

        KEPT as-is: return-value contract (isinstance, is_dir, parent).
        Primary assertion is on the function return value, not filesystem
        state mutation. State-delta adds ceremony without gain here.
        """
        from scripts.update.backup_manager import BackupManager

        source_dir = tmp_path / ".claude"
        source_dir.mkdir()

        manager = BackupManager(home_dir=tmp_path)

        backup_path = manager.create_backup(source_dir)

        assert isinstance(backup_path, Path)
        assert backup_path.exists()
        assert backup_path.is_dir()
        assert backup_path.parent == tmp_path

    def test_create_backup_handles_sequence_numbers_for_multiple_backups_same_day(
        self, tmp_path
    ):
        """
        GIVEN multiple backups are created on the same day
        WHEN create_backup is called multiple times
        THEN each backup gets a unique sequence number (_01, _02, etc.)
             AND the source directory and its file are not modified between calls

        State-delta: 3 backup.exists slots all transition False→True; source
        file slot stays True across all 3 calls (implicit-unchanged).
        """
        from scripts.update.backup_manager import BackupManager

        source_dir = tmp_path / ".claude"
        source_dir.mkdir()
        (source_dir / "file.txt").write_text("content")

        manager = BackupManager(home_dir=tmp_path)

        today = datetime.now().strftime("%Y%m%d")
        base_name = f".claude_bck_{today}"

        # Track the 3 anticipated backup names + the source file
        tracked = frozenset(
            [
                f"{base_name}.exists",
                f"{base_name}_01.exists",
                f"{base_name}_02.exists",
                ".claude/file.txt.exists",
            ]
        )
        before = _backup_filesystem_state(tmp_path, base_name, track=tracked)

        backup1 = manager.create_backup(source_dir)
        backup2 = manager.create_backup(source_dir)
        backup3 = manager.create_backup(source_dir)

        after = _backup_filesystem_state(tmp_path, base_name, track=tracked)

        # All 3 backups must have been created and be distinct paths
        assert backup1 != backup2
        assert backup2 != backup3
        assert backup1 != backup3

        assert_state_delta(
            before=before,
            after=after,
            universe=set(tracked),
            expected={
                # All 3 backup slots created
                f"{base_name}.exists": set_to(True),
                f"{base_name}_01.exists": set_to(True),
                f"{base_name}_02.exists": set_to(True),
                # source file: implicit-unchanged (not in expected)
            },
        )
