"""
Unit tests for UpdateOrchestrator.

Tests the orchestration of backup creation before update and complete
update workflow coordination.

These tests follow Outside-In TDD - they are written BEFORE implementation
and should FAIL until UpdateOrchestrator is implemented.
"""

from pathlib import Path
from unittest.mock import Mock

import pytest


class TestUpdateOrchestrator:
    """Unit tests for UpdateOrchestrator coordination logic."""

    def test_orchestrator_creates_backup_before_update(self, tmp_path):
        """
        GIVEN an UpdateOrchestrator with BackupManager dependency
        WHEN execute_update is called
        THEN BackupManager.create_backup is called before update proceeds
        """
        # Arrange
        from scripts.update.backup_manager import BackupManager
        from scripts.update.update_orchestrator import UpdateOrchestrator

        mock_backup_manager = Mock(spec=BackupManager)
        mock_backup_path = tmp_path / ".claude_bck_20260126"
        mock_backup_manager.create_backup.return_value = mock_backup_path

        orchestrator = UpdateOrchestrator(backup_manager=mock_backup_manager)

        # Act
        orchestrator.execute_update()

        # Assert
        mock_backup_manager.create_backup.assert_called_once()

    def test_orchestrator_outputs_backup_creation_message(self, tmp_path, capsys):
        """
        GIVEN an UpdateOrchestrator that successfully creates backup
        WHEN execute_update is called
        THEN output contains "Backup created at ~/.claude_bck_"
        """
        # Arrange
        from scripts.update.backup_manager import BackupManager
        from scripts.update.update_orchestrator import UpdateOrchestrator

        mock_backup_manager = Mock(spec=BackupManager)
        backup_path = tmp_path / ".claude_bck_20260126"
        mock_backup_manager.create_backup.return_value = backup_path

        orchestrator = UpdateOrchestrator(backup_manager=mock_backup_manager)

        # Act
        orchestrator.execute_update()
        captured = capsys.readouterr()

        # Assert
        assert "Backup created at" in captured.out
        assert ".claude_bck_" in captured.out

    def test_orchestrator_handles_backup_failure_gracefully(self, tmp_path):
        """
        GIVEN BackupManager.create_backup raises an error
        WHEN execute_update is called
        THEN orchestrator raises appropriate error with context
        """
        # Arrange
        from scripts.update.backup_manager import BackupManager
        from scripts.update.update_orchestrator import UpdateOrchestrator

        mock_backup_manager = Mock(spec=BackupManager)
        mock_backup_manager.create_backup.side_effect = FileNotFoundError(
            "Source directory does not exist: /path/to/source"
        )

        orchestrator = UpdateOrchestrator(backup_manager=mock_backup_manager)

        # Act & Assert
        with pytest.raises(FileNotFoundError) as exc_info:
            orchestrator.execute_update()

        assert "Source directory does not exist" in str(exc_info.value)

    def test_orchestrator_accepts_backup_manager_dependency_injection(self, tmp_path):
        """
        GIVEN a BackupManager instance
        WHEN UpdateOrchestrator is instantiated with backup_manager parameter
        THEN orchestrator stores the dependency correctly
        """
        # Arrange
        from scripts.update.backup_manager import BackupManager
        from scripts.update.update_orchestrator import UpdateOrchestrator

        mock_backup_manager = Mock(spec=BackupManager)

        # Act
        orchestrator = UpdateOrchestrator(backup_manager=mock_backup_manager)

        # Assert
        assert orchestrator.backup_manager == mock_backup_manager

    def test_orchestrator_coordinates_complete_update_flow(self, tmp_path):
        """
        GIVEN an UpdateOrchestrator with all dependencies
        WHEN execute_update is called
        THEN backup is created, update proceeds, and version is updated
        """
        # Arrange
        from scripts.update.backup_manager import BackupManager
        from scripts.update.update_orchestrator import UpdateOrchestrator

        mock_backup_manager = Mock(spec=BackupManager)
        backup_path = tmp_path / ".claude_bck_20260126"
        mock_backup_manager.create_backup.return_value = backup_path

        orchestrator = UpdateOrchestrator(backup_manager=mock_backup_manager)

        # Act
        result = orchestrator.execute_update()

        # Assert
        assert result is not None
        assert result.get("backup_created") is True
        assert result.get("backup_path") == backup_path
        mock_backup_manager.create_backup.assert_called_once()

    def test_orchestrator_passes_correct_source_directory_to_backup_manager(
        self, tmp_path
    ):
        """
        GIVEN an UpdateOrchestrator with BackupManager
        WHEN execute_update is called
        THEN BackupManager.create_backup receives correct source directory path
        """
        # Arrange
        from scripts.update.backup_manager import BackupManager
        from scripts.update.update_orchestrator import UpdateOrchestrator

        mock_backup_manager = Mock(spec=BackupManager)
        backup_path = tmp_path / ".claude_bck_20260126"
        mock_backup_manager.create_backup.return_value = backup_path

        orchestrator = UpdateOrchestrator(backup_manager=mock_backup_manager)

        # Act
        orchestrator.execute_update()

        # Assert
        # Verify create_backup was called with a Path argument
        call_args = mock_backup_manager.create_backup.call_args
        assert call_args is not None
        source_path = call_args[0][0]
        assert isinstance(source_path, Path)
        # Should be ~/.claude or equivalent
        assert source_path.name in [".claude", "nWave"]
