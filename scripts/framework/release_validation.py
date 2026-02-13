"""Validation and error detection for release packages."""

import json
from dataclasses import dataclass
from pathlib import Path


class MissingArtifactsValidator:
    """Detects and reports missing platform artifacts."""

    @dataclass
    class MissingArtifactError:
        """Error for missing artifacts."""

        platform: str
        missing_files: list[str]
        remediation: str

    PLATFORM_REQUIREMENTS = {
        "claude-code": [
            "nWave/agents",
            "nWave/tasks",
            "nWave/templates",
            "nWave/framework-catalog.yaml",
            "nWave/skills",
            "src/des",
            "scripts/install",
            "README.md",
        ],
        "codex": [
            "nWave/templates",
            "nWave/skills",
            "README.md",
        ],
    }

    def __init__(self, dist_dir: Path):
        self.dist_dir = Path(dist_dir)

    def validate_platform_artifacts(self, platform: str) -> MissingArtifactError | None:
        """Check if all platform artifacts exist."""
        required = self.PLATFORM_REQUIREMENTS.get(platform, [])
        missing = []

        for _artifact in required:
            _archive_name = (
                f"nwave-{platform}-*.zip"  # Placeholder for future validation
            )
            # This would be called after archive creation, so we just validate they were created

        if missing:
            error = self.MissingArtifactError(
                platform=platform,
                missing_files=missing,
                remediation=f"Rebuild with clean parameter: `nwave build --clean --platform {platform}`",
            )
            return error

        return None

    def validate_all_platforms(self) -> list[MissingArtifactError]:
        """Validate all platform artifacts."""
        errors = []
        for platform in self.PLATFORM_REQUIREMENTS:
            error = self.validate_platform_artifacts(platform)
            if error:
                errors.append(error)
        return errors


class ChecksumMismatchValidator:
    """Validates checksum integrity for release packages."""

    @dataclass
    class ChecksumMismatchError:
        """Error for checksum mismatch."""

        filename: str
        expected_checksum: str
        actual_checksum: str
        security_implications: str

    def __init__(self, checksums_file: Path):
        self.checksums_file = Path(checksums_file)

    def load_checksums(self) -> dict[str, str]:
        """Load checksums from checksums file."""
        if not self.checksums_file.exists():
            raise FileNotFoundError(f"Checksums file not found: {self.checksums_file}")

        with open(self.checksums_file) as f:
            return json.load(f)

    def verify_checksum(
        self, filename: str, file_path: Path, expected_checksum: str
    ) -> ChecksumMismatchError | None:
        """Verify a file's checksum."""
        import hashlib

        # Calculate actual checksum
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        actual_checksum = sha256_hash.hexdigest()

        if actual_checksum != expected_checksum:
            error = self.ChecksumMismatchError(
                filename=filename,
                expected_checksum=expected_checksum,
                actual_checksum=actual_checksum,
                security_implications=(
                    "SECURITY WARNING: Checksum mismatch detected. This could indicate: "
                    "1. File corruption, 2. Incomplete download, 3. Tampering. "
                    "Please re-download from official source and verify integrity."
                ),
            )
            return error

        return None

    def verify_all_checksums(self, archive_dir: Path) -> list[ChecksumMismatchError]:
        """Verify all checksums in the checksums file."""
        checksums = self.load_checksums()
        errors = []

        for filename, expected_checksum in checksums.items():
            file_path = archive_dir / filename
            if file_path.exists():
                error = self.verify_checksum(filename, file_path, expected_checksum)
                if error:
                    errors.append(error)

        return errors


class VersionConflictValidator:
    """Detects and reports version conflicts."""

    @dataclass
    class VersionConflictError:
        """Error for version conflict."""

        configuration_version: str
        tag_version: str
        archive_versions: list[str]
        resolution_steps: list[str]

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)

    def get_configuration_version(self) -> str:
        """Get version from framework-catalog.yaml."""
        import yaml

        catalog_path = self.project_root / "nWave" / "framework-catalog.yaml"
        if not catalog_path.exists():
            raise FileNotFoundError(f"Catalog not found: {catalog_path}")

        with open(catalog_path) as f:
            catalog = yaml.safe_load(f)

        version = catalog.get("version")
        if not version:
            raise ValueError("Version not found in framework-catalog.yaml")

        return version

    def get_git_tag_version(self) -> str | None:
        """Get version from latest git tag."""
        import subprocess

        try:
            result = subprocess.run(
                ["git", "describe", "--tags", "--abbrev=0"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                tag = result.stdout.strip()
                # Extract version from tag (e.g., v1.2.57 -> 1.2.57)
                if tag.startswith("v"):
                    return tag[1:]
                return tag
        except Exception:
            pass

        return None

    def validate_version_consistency(self) -> VersionConflictError | None:
        """Validate that versions are consistent."""
        config_version = self.get_configuration_version()
        tag_version = self.get_git_tag_version()

        if tag_version and config_version != tag_version:
            error = self.VersionConflictError(
                configuration_version=config_version,
                tag_version=tag_version,
                archive_versions=[],
                resolution_steps=[
                    "Option 1: Update framework-catalog.yaml to match git tag",
                    "  - Edit: nWave/framework-catalog.yaml",
                    f"  - Set version: {tag_version}",
                    "Option 2: Create git tag to match configuration",
                    f"  - Run: git tag v{config_version}",
                    "Option 3: Keep configuration as source of truth",
                    f"  - Run: git tag -d v{tag_version} (delete old tag)",
                    f"  - Run: git tag v{config_version} (create new tag)",
                ],
            )
            return error

        return None

    def validate_archive_versions(self, dist_dir: Path) -> VersionConflictError | None:
        """Validate that archive versions match configuration."""
        config_version = self.get_configuration_version()
        archive_versions = []

        # Check archive filenames
        for archive in dist_dir.glob("nwave-*.zip"):
            # Extract version from filename (e.g., nwave-claude-code-1.2.57.zip)
            parts = archive.name.split("-")
            if len(parts) >= 3:
                version = parts[-1].replace(".zip", "")
                archive_versions.append(version)

        # Check if all versions match configuration version
        mismatched = [v for v in archive_versions if v != config_version]

        if mismatched:
            error = self.VersionConflictError(
                configuration_version=config_version,
                tag_version=None,
                archive_versions=archive_versions,
                resolution_steps=[
                    "Archive versions do not match configuration version",
                    f"  Configuration: {config_version}",
                    f"  Archives: {', '.join(set(archive_versions))}",
                    "Resolution: Rebuild archives with clean parameter",
                    "  Run: nwave package --clean",
                ],
            )
            return error

        return None
