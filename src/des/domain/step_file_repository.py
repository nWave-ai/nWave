"""Step file repository for loading and persisting step data.

Provides centralized step file operations with path resolution,
JSON parsing, and current phase extraction.
"""

from pathlib import Path

from des.ports.driven_ports.filesystem_port import FileSystemPort


class StepFileRepository:
    """Repository for step file operations."""

    def __init__(self, filesystem: FileSystemPort):
        """Initialize with injected filesystem port.

        Args:
            filesystem: File I/O operations
        """
        self._filesystem = filesystem

    def resolve_path(self, project_root: Path | str, step_file: str) -> Path:
        """Convert project_root and step_file to absolute path.

        Args:
            project_root: Project root directory
            step_file: Relative path to step file

        Returns:
            Absolute Path to step file
        """
        if isinstance(project_root, str):
            project_root = Path(project_root)
        return project_root / step_file

    def load(self, step_file_path: Path) -> dict:
        """Load and parse step file JSON.

        Args:
            step_file_path: Path to step JSON file

        Returns:
            Parsed step data dictionary

        Raises:
            FileNotFoundError: If step file does not exist
            json.JSONDecodeError: If step file is not valid JSON
        """
        return self._filesystem.read_json(step_file_path)

    def save(self, step_file_path: Path, step_data: dict) -> None:
        """Persist step data to file.

        Args:
            step_file_path: Path to step file
            step_data: Complete step data dictionary to persist
        """
        self._filesystem.write_json(step_file_path, step_data)

    def get_current_phase(self, step_data: dict) -> dict:
        """Get current phase from step data and mark as IN_PROGRESS if needed.

        Args:
            step_data: Parsed step data dictionary

        Returns:
            Current phase dictionary with status potentially updated to IN_PROGRESS
        """
        phase_log = step_data["tdd_cycle"]["phase_execution_log"]
        current_phase = phase_log[0]  # For now, use first phase

        if current_phase["status"] == "NOT_EXECUTED":
            current_phase["status"] = "IN_PROGRESS"

        return current_phase
