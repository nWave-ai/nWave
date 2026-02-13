"""
UpdateOrchestrator - Coordinates backup and update workflow.

HEXAGONAL ARCHITECTURE:
This is an application service that orchestrates the update workflow.
Coordinates backup creation before update proceeds.
"""

from pathlib import Path
from typing import Any


class UpdateOrchestrator:
    """
    Orchestrates the nWave update workflow.

    Coordinates:
    - Backup creation before update
    - Update execution
    - Rollback on failure
    """

    def __init__(self, backup_manager: Any):
        """
        Initialize UpdateOrchestrator with dependencies.

        Args:
            backup_manager: BackupManager instance for backup operations
        """
        self.backup_manager = backup_manager

    def execute_update(self) -> dict:
        """
        Execute the complete update workflow.

        1. Creates backup of current installation
        2. Outputs confirmation message
        3. Returns result with backup information

        Returns:
            dict with:
                - backup_created: bool indicating backup success
                - backup_path: Path to backup directory

        Raises:
            FileNotFoundError: If source directory does not exist
        """
        # Determine source directory (default to ~/.claude or nWave)
        source_dir = self._get_source_directory()

        # Create backup before update
        backup_path = self.backup_manager.create_backup(source_dir)

        # Output confirmation message
        print(f"Backup created at {backup_path}")

        return {
            "backup_created": True,
            "backup_path": backup_path,
        }

    def _get_source_directory(self) -> Path:
        """
        Determine the source directory to backup.

        Returns:
            Path to the nWave/claude installation directory
        """
        # Check for ~/.claude first, then nWave
        home = Path.home()
        claude_dir = home / ".claude"

        if claude_dir.exists():
            return claude_dir

        # Fallback to nWave in current directory structure
        nwave_dir = Path(__file__).parent.parent.parent / "nWave"
        if nwave_dir.exists():
            return nwave_dir

        # Return .claude as expected path even if not existing
        # (will trigger FileNotFoundError in backup_manager)
        return claude_dir
