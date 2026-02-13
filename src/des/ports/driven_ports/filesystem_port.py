from abc import ABC, abstractmethod
from pathlib import Path


class FileSystemPort(ABC):
    """Port for file system operations."""

    @abstractmethod
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
        pass

    @abstractmethod
    def write_json(self, path: Path, data: dict) -> None:
        """Write data as formatted JSON file.

        Args:
            path: Absolute path to target JSON file
            data: Dictionary to write as JSON
        """
        pass

    @abstractmethod
    def exists(self, path: Path) -> bool:
        """Check if path exists.

        Args:
            path: Path to check

        Returns:
            True if path exists
        """
        pass
