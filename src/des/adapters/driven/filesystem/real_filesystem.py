"""Production implementation of filesystem adapter."""

import json
from pathlib import Path

from des.ports.driven_ports.filesystem_port import FileSystemPort


class RealFileSystem(FileSystemPort):
    """Production implementation of file system operations.

    Wraps standard Python file I/O operations for JSON files.
    """

    def read_json(self, path: Path) -> dict:
        """Read and parse JSON file.

        Args:
            path: Absolute path to JSON file

        Returns:
            Parsed JSON data as dictionary

        Raises:
            FileNotFoundError: If file doesn't exist
            JSONDecodeError: If file is not valid JSON
        """
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def write_json(self, path: Path, data: dict) -> None:
        """Write data as formatted JSON file.

        Args:
            path: Absolute path to target JSON file
            data: Dictionary to write as JSON
        """
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def exists(self, path: Path) -> bool:
        """Check if path exists.

        Args:
            path: Path to check

        Returns:
            True if path exists
        """
        return path.exists()
