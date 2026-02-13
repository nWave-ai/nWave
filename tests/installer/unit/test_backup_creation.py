"""
Unit tests for BackupManager.

Tests backup creation functionality that will be reused from
scripts/install/install_utils.py.

These tests follow Outside-In TDD - they are written BEFORE implementation
and should FAIL until BackupManager is implemented.
"""

from datetime import datetime
from pathlib import Path

import pytest


class TestBackupManager:
    """Unit tests for BackupManager backup creation."""

    def test_create_backup_creates_directory_with_correct_name_format(self, tmp_path):
        """
        GIVEN a source directory exists
        WHEN create_backup is called
        THEN a backup directory is created with .claude_bck_YYYYMMDD format
        """
        # Arrange
        from scripts.update.backup_manager import BackupManager

        source_dir = tmp_path / ".claude"
        source_dir.mkdir()
        (source_dir / "test_file.txt").write_text("test content")

        manager = BackupManager(home_dir=tmp_path)

        # Act
        backup_path = manager.create_backup(source_dir)

        # Assert
        assert backup_path.exists()
        assert backup_path.name.startswith(".claude_bck_")
        # Verify date format YYYYMMDD
        date_part = backup_path.name.replace(".claude_bck_", "")
        assert len(date_part) == 8
        assert date_part.isdigit()
        # Verify it's today's date
        today = datetime.now().strftime("%Y%m%d")
        assert date_part == today

    def test_create_backup_copies_all_files_from_source(self, tmp_path):
        """
        GIVEN a source directory with multiple files and subdirectories
        WHEN create_backup is called
        THEN all files and directory structure are copied to backup
        """
        # Arrange
        from scripts.update.backup_manager import BackupManager

        source_dir = tmp_path / ".claude"
        source_dir.mkdir()
        (source_dir / "file1.txt").write_text("content1")
        (source_dir / "file2.txt").write_text("content2")
        subdir = source_dir / "subdir"
        subdir.mkdir()
        (subdir / "file3.txt").write_text("content3")

        manager = BackupManager(home_dir=tmp_path)

        # Act
        backup_path = manager.create_backup(source_dir)

        # Assert
        assert (backup_path / "file1.txt").exists()
        assert (backup_path / "file1.txt").read_text() == "content1"
        assert (backup_path / "file2.txt").exists()
        assert (backup_path / "file2.txt").read_text() == "content2"
        assert (backup_path / "subdir" / "file3.txt").exists()
        assert (backup_path / "subdir" / "file3.txt").read_text() == "content3"

    def test_create_backup_raises_error_when_source_does_not_exist(self, tmp_path):
        """
        GIVEN a source directory that does not exist
        WHEN create_backup is called
        THEN FileNotFoundError is raised with clear message
        """
        # Arrange
        from scripts.update.backup_manager import BackupManager

        source_dir = tmp_path / ".claude"
        # Do NOT create source_dir - it should not exist

        manager = BackupManager(home_dir=tmp_path)

        # Act & Assert
        with pytest.raises(FileNotFoundError) as exc_info:
            manager.create_backup(source_dir)

        assert "Source directory does not exist" in str(exc_info.value)
        assert str(source_dir) in str(exc_info.value)

    def test_create_backup_returns_backup_path(self, tmp_path):
        """
        GIVEN a source directory exists
        WHEN create_backup is called
        THEN the Path to the created backup directory is returned
        """
        # Arrange
        from scripts.update.backup_manager import BackupManager

        source_dir = tmp_path / ".claude"
        source_dir.mkdir()

        manager = BackupManager(home_dir=tmp_path)

        # Act
        backup_path = manager.create_backup(source_dir)

        # Assert
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
        """
        # Arrange
        from scripts.update.backup_manager import BackupManager

        source_dir = tmp_path / ".claude"
        source_dir.mkdir()
        (source_dir / "file.txt").write_text("content")

        manager = BackupManager(home_dir=tmp_path)

        # Act
        backup1 = manager.create_backup(source_dir)
        backup2 = manager.create_backup(source_dir)
        backup3 = manager.create_backup(source_dir)

        # Assert
        assert backup1.exists()
        assert backup2.exists()
        assert backup3.exists()
        # All three should be different paths
        assert backup1 != backup2
        assert backup2 != backup3
        assert backup1 != backup3
        # Should have sequence numbers
        today = datetime.now().strftime("%Y%m%d")
        assert backup1.name == f".claude_bck_{today}" or "_01" in backup1.name
        if backup1.name == f".claude_bck_{today}":
            assert "_01" in backup2.name
            assert "_02" in backup3.name
