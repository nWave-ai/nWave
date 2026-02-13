"""Schema version detection for TDD step files.

Detects schema_version field in step files to determine which TDD phase cycle
is being used (v1.0 = 14 phases, v2.0 = 8 phases).
"""

from pathlib import Path

from des.ports.driven_ports.filesystem_port import FileSystemPort


class SchemaVersionDetector:
    """Detects and interprets schema versions from step files."""

    def __init__(self, filesystem: FileSystemPort):
        """Initialize with injected filesystem port.

        Args:
            filesystem: File I/O operations
        """
        self._filesystem = filesystem

    def detect_version(self, step_file_path: Path) -> str:
        """Detect schema version from step file.

        Reads the step file and extracts schema_version field to determine
        which TDD phase cycle it uses (v1.0 = 14 phases, v2.0 = 8 phases).

        Args:
            step_file_path: Path to step JSON file

        Returns:
            Schema version string (e.g., "1.0", "2.0", "unknown")

        Raises:
            FileNotFoundError: If step file does not exist
            json.JSONDecodeError: If step file is not valid JSON
        """
        step_data = self._filesystem.read_json(step_file_path)

        # Check multiple possible locations for schema_version
        schema_version = (
            step_data.get("schema_version")
            or step_data.get("tdd_cycle", {}).get("schema_version")
            or "1.0"  # Default to v1.0 if not found (14-phase legacy)
        )

        return schema_version

    def get_phase_count(self, schema_version: str) -> int:
        """Get expected phase count for schema version.

        Args:
            schema_version: Schema version (e.g., "1.0", "2.0")

        Returns:
            Expected number of phases (14 for v1.0, 8 for v2.0)
        """
        if schema_version == "2.0":
            return 8
        else:
            return 14  # Default to 14 for v1.0 and unknown versions
