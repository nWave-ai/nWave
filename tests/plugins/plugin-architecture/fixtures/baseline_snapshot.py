"""
Baseline Snapshot Utilities for Behavioral Equivalence Testing.

Step 02-02: Behavioral Equivalence Validation

This module provides utilities to capture and compare installation snapshots,
validating that plugin-based installation produces identical results to
the expected baseline.

Domain: Plugin Infrastructure - Behavioral Equivalence
"""

import hashlib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FileSnapshot:
    """Represents a snapshot of a single file."""

    relative_path: str
    content_hash: str
    size_bytes: int

    @classmethod
    def from_file(cls, file_path: Path, base_dir: Path) -> "FileSnapshot":
        """Create a FileSnapshot from an actual file.

        Args:
            file_path: Absolute path to the file.
            base_dir: Base directory for calculating relative paths.

        Returns:
            FileSnapshot with path, hash, and size.
        """
        relative = str(file_path.relative_to(base_dir))
        content = file_path.read_bytes()
        content_hash = hashlib.sha256(content).hexdigest()
        return cls(
            relative_path=relative,
            content_hash=content_hash,
            size_bytes=len(content),
        )


@dataclass
class InstallationSnapshot:
    """Represents a complete installation snapshot."""

    files: dict[str, FileSnapshot] = field(default_factory=dict)
    total_file_count: int = 0
    total_size_bytes: int = 0

    @classmethod
    def capture(cls, install_dir: Path) -> "InstallationSnapshot":
        """Capture a snapshot of an installation directory.

        Args:
            install_dir: The directory to capture (e.g., ~/.claude).

        Returns:
            InstallationSnapshot containing all files.
        """
        snapshot = cls()

        if not install_dir.exists():
            return snapshot

        for file_path in install_dir.rglob("*"):
            if file_path.is_file():
                file_snapshot = FileSnapshot.from_file(file_path, install_dir)
                snapshot.files[file_snapshot.relative_path] = file_snapshot
                snapshot.total_file_count += 1
                snapshot.total_size_bytes += file_snapshot.size_bytes

        return snapshot


@dataclass
class ComparisonResult:
    """Result of comparing two installation snapshots."""

    identical: bool
    files_match: bool
    content_match: bool
    missing_files: list[str] = field(default_factory=list)
    extra_files: list[str] = field(default_factory=list)
    content_mismatches: list[str] = field(default_factory=list)
    message: str = ""


def compare_snapshots(
    baseline: InstallationSnapshot,
    actual: InstallationSnapshot,
) -> ComparisonResult:
    """Compare two installation snapshots.

    Args:
        baseline: The expected installation snapshot.
        actual: The actual installation snapshot to verify.

    Returns:
        ComparisonResult with detailed comparison information.
    """
    baseline_paths = set(baseline.files.keys())
    actual_paths = set(actual.files.keys())

    missing_files = list(baseline_paths - actual_paths)
    extra_files = list(actual_paths - baseline_paths)
    content_mismatches = []

    for path in baseline_paths & actual_paths:
        if baseline.files[path].content_hash != actual.files[path].content_hash:
            content_mismatches.append(path)

    files_match = len(missing_files) == 0 and len(extra_files) == 0
    content_match = len(content_mismatches) == 0
    identical = files_match and content_match

    if identical:
        message = "Installation is identical to baseline"
    else:
        issues = []
        if missing_files:
            issues.append(f"{len(missing_files)} missing files")
        if extra_files:
            issues.append(f"{len(extra_files)} extra files")
        if content_mismatches:
            issues.append(f"{len(content_mismatches)} content mismatches")
        message = "Differences found: " + ", ".join(issues)

    return ComparisonResult(
        identical=identical,
        files_match=files_match,
        content_match=content_match,
        missing_files=missing_files,
        extra_files=extra_files,
        content_mismatches=content_mismatches,
        message=message,
    )


# Expected file structure for a valid nWave installation
# This defines the minimum required files for behavioral equivalence
EXPECTED_INSTALLATION_STRUCTURE = {
    "agents": {
        "subdirectory": "nw",
        "file_pattern": "*.md",
        "minimum_count": 10,
    },
    "commands": {
        "subdirectory": "nw",
        "file_pattern": "*.md",
        "minimum_count": 1,
    },
    "templates": {
        "subdirectory": None,
        "file_pattern": "*.json",
        "minimum_count": 1,
    },
}


def validate_installation_structure(install_dir: Path) -> tuple[bool, list[str]]:
    """Validate that an installation has the expected structure.

    Args:
        install_dir: The installation directory to validate.

    Returns:
        Tuple of (is_valid, list_of_issues).
    """
    issues = []

    for component, spec in EXPECTED_INSTALLATION_STRUCTURE.items():
        if spec["subdirectory"]:
            component_dir = install_dir / component / spec["subdirectory"]
        else:
            component_dir = install_dir / component

        if not component_dir.exists():
            issues.append(f"Missing directory: {component_dir}")
            continue

        file_count = len(list(component_dir.glob(spec["file_pattern"])))
        if file_count < spec["minimum_count"]:
            issues.append(
                f"{component}: expected >= {spec['minimum_count']} files, found {file_count}"
            )

    return len(issues) == 0, issues
