"""
BackupManager - Infrastructure adapter for backup creation.

HEXAGONAL ARCHITECTURE:
This is an infrastructure adapter (DRIVEN PORT implementation).
Provides backup creation capabilities for nWave updates.
"""

import shutil
from datetime import datetime
from pathlib import Path


class BackupManager:
    """
    Manages backup creation for nWave safe updates.

    Creates backups with naming format: .claude_bck_YYYYMMDD
    Handles sequence numbers for multiple backups on same day.
    """

    def __init__(self, home_dir: Path):
        """
        Initialize BackupManager with home directory.

        Args:
            home_dir: Parent directory where backups will be created
        """
        self.home_dir = Path(home_dir)

    def create_backup(self, source_dir: Path) -> Path:
        """
        Create backup of source directory.

        Args:
            source_dir: Directory to backup (e.g., ~/.claude/)

        Returns:
            Path to created backup directory

        Raises:
            FileNotFoundError: If source directory does not exist
        """
        source_dir = Path(source_dir)

        if not source_dir.exists():
            raise FileNotFoundError(f"Source directory does not exist: {source_dir}")

        backup_path = self._generate_backup_path()

        # Copy entire directory tree preserving metadata
        shutil.copytree(source_dir, backup_path, dirs_exist_ok=False)

        return backup_path

    def _generate_backup_path(self) -> Path:
        """
        Generate unique backup path with date and optional sequence number.

        Returns:
            Path for new backup directory
        """
        today = datetime.now().strftime("%Y%m%d")
        base_name = f".claude_bck_{today}"
        backup_path = self.home_dir / base_name

        # If base path doesn't exist, use it
        if not backup_path.exists():
            return backup_path

        # Otherwise, add sequence numbers
        sequence = 1
        while True:
            sequence_name = f"{base_name}_{sequence:02d}"
            backup_path = self.home_dir / sequence_name
            if not backup_path.exists():
                return backup_path
            sequence += 1
