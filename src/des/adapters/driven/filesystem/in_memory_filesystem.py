"""Test implementation of filesystem adapter."""

from pathlib import Path

from des.ports.driven_ports.filesystem_port import FileSystemPort


class InMemoryFileSystem(FileSystemPort):
    """In-memory filesystem for testing.

    Provides fast, deterministic file operations without touching disk.
    Files are stored in memory dictionary keyed by absolute path.
    """

    def __init__(self):
        """Initialize empty in-memory filesystem."""
        self._files: dict[Path, dict] = {}

    def read_json(self, path: Path) -> dict:
        """Read JSON from in-memory storage.

        Args:
            path: Absolute path to JSON file

        Returns:
            Parsed JSON data as dictionary

        Raises:
            FileNotFoundError: If file doesn't exist in memory
        """
        if path not in self._files:
            raise FileNotFoundError(f"File not found: {path}")
        return self._files[path]

    def write_json(self, path: Path, data: dict) -> None:
        """Write JSON to in-memory storage.

        Args:
            path: Absolute path to target JSON file
            data: Dictionary to store
        """
        self._files[path] = data

    def exists(self, path: Path) -> bool:
        """Check if path exists in memory.

        Args:
            path: Path to check

        Returns:
            True if path exists in in-memory filesystem
        """
        return path in self._files

    def seed_file(self, path: Path, data: dict) -> None:
        """Seed in-memory filesystem with test data.

        Convenience method for test setup.

        Args:
            path: Absolute path where file should exist
            data: JSON data to store at that path
        """
        self._files[path] = data

    def clear(self) -> None:
        """Clear all files from in-memory filesystem.

        Convenience method for test teardown.
        """
        self._files.clear()

    def get_all_paths(self) -> list[Path]:
        """Get all file paths in memory.

        Convenience method for test assertions.

        Returns:
            List of all paths currently stored
        """
        return list(self._files.keys())
