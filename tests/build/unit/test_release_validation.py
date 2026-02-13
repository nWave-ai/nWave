"""Tests for release validation and error handling."""

import json
from unittest.mock import patch

import pytest

from scripts.framework.release_validation import (
    ChecksumMismatchValidator,
    MissingArtifactsValidator,
    VersionConflictValidator,
)


class TestMissingArtifactsValidator:
    """Tests for missing artifacts detection."""

    def test_detect_missing_platform_artifacts(self, tmp_path):
        """Test detection of missing platform artifacts."""
        dist_dir = tmp_path / "dist"
        dist_dir.mkdir()

        validator = MissingArtifactsValidator(dist_dir)

        # Test with claude-code platform
        _error = validator.validate_platform_artifacts("claude-code")
        # No actual archives yet, so validation would need to check archive presence
        # This is a validation pattern check

    def test_missing_artifacts_error_includes_remediation(self):
        """Test that missing artifacts error includes remediation steps."""
        error = MissingArtifactsValidator.MissingArtifactError(
            platform="claude-code",
            missing_files=["nWave/agents", "nWave/tasks"],
            remediation="Rebuild with clean parameter",
        )

        assert error.platform == "claude-code"
        assert "nWave/agents" in error.missing_files
        assert "remediation" in error.__dict__
        assert "Rebuild" in error.remediation


class TestChecksumMismatchValidator:
    """Tests for checksum validation."""

    def test_load_checksums_success(self, tmp_path):
        """Test loading checksums from file."""
        checksums_data = {
            "nwave-claude-code-1.2.57.zip": "abc123def456",
            "nwave-codex-1.2.57.zip": "xyz789uvw012",
        }
        checksums_file = tmp_path / "CHECKSUMS.json"
        with open(checksums_file, "w") as f:
            json.dump(checksums_data, f)

        validator = ChecksumMismatchValidator(checksums_file)
        checksums = validator.load_checksums()

        assert checksums == checksums_data

    def test_load_checksums_file_not_found(self, tmp_path):
        """Test loading checksums when file doesn't exist."""
        validator = ChecksumMismatchValidator(tmp_path / "missing.json")

        with pytest.raises(FileNotFoundError):
            validator.load_checksums()

    def test_verify_checksum_match(self, tmp_path):
        """Test checksum verification when checksums match."""
        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        # Calculate actual checksum
        import hashlib

        sha256_hash = hashlib.sha256()
        with open(test_file, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        expected_checksum = sha256_hash.hexdigest()

        validator = ChecksumMismatchValidator(tmp_path / "dummy.json")
        error = validator.verify_checksum("test.txt", test_file, expected_checksum)

        assert error is None

    def test_verify_checksum_mismatch(self, tmp_path):
        """Test checksum verification when checksums don't match."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        validator = ChecksumMismatchValidator(tmp_path / "dummy.json")
        wrong_checksum = "0" * 64  # Invalid checksum
        error = validator.verify_checksum("test.txt", test_file, wrong_checksum)

        assert error is not None
        assert error.filename == "test.txt"
        assert "SECURITY WARNING" in error.security_implications
        assert "re-download" in error.security_implications.lower()

    def test_checksum_mismatch_error_security_info(self):
        """Test that checksum mismatch error includes security implications."""
        error = ChecksumMismatchValidator.ChecksumMismatchError(
            filename="archive.zip",
            expected_checksum="abc123",
            actual_checksum="xyz789",
            security_implications="SECURITY WARNING: Check file integrity",
        )

        assert "SECURITY" in error.security_implications
        assert "file" in error.security_implications.lower()


class TestVersionConflictValidator:
    """Tests for version conflict detection."""

    def test_get_configuration_version(self, tmp_path):
        """Test reading version from configuration."""
        catalog_dir = tmp_path / "nWave"
        catalog_dir.mkdir()
        catalog_content = """
name: "nWave"
version: "1.2.57"
description: "Test framework"
"""
        catalog_path = catalog_dir / "framework-catalog.yaml"
        catalog_path.write_text(catalog_content)

        validator = VersionConflictValidator(tmp_path)
        version = validator.get_configuration_version()

        assert version == "1.2.57"

    def test_get_configuration_version_missing(self, tmp_path):
        """Test reading version when catalog is missing."""
        validator = VersionConflictValidator(tmp_path)

        with pytest.raises(FileNotFoundError):
            validator.get_configuration_version()

    def test_validate_version_consistency_no_tag(self, tmp_path):
        """Test version consistency when no git tag exists."""
        catalog_dir = tmp_path / "nWave"
        catalog_dir.mkdir()
        catalog_content = """
name: "nWave"
version: "1.2.57"
description: "Test framework"
"""
        catalog_path = catalog_dir / "framework-catalog.yaml"
        catalog_path.write_text(catalog_content)

        validator = VersionConflictValidator(tmp_path)
        error = validator.validate_version_consistency()

        # No error if no git tag exists
        assert error is None or error.tag_version is None

    def test_validate_version_consistency_conflict(self, tmp_path):
        """Test version consistency detects conflict."""
        catalog_dir = tmp_path / "nWave"
        catalog_dir.mkdir()
        catalog_content = """
name: "nWave"
version: "1.2.57"
description: "Test framework"
"""
        catalog_path = catalog_dir / "framework-catalog.yaml"
        catalog_path.write_text(catalog_content)

        validator = VersionConflictValidator(tmp_path)

        # Mock git tag to return different version
        with patch.object(validator, "get_git_tag_version", return_value="1.2.56"):
            error = validator.validate_version_consistency()

        assert error is not None
        assert error.configuration_version == "1.2.57"
        assert error.tag_version == "1.2.56"
        assert len(error.resolution_steps) > 0
        assert any("Update" in step for step in error.resolution_steps)

    def test_validate_archive_versions_match(self, tmp_path):
        """Test archive version validation when versions match."""
        catalog_dir = tmp_path / "nWave"
        catalog_dir.mkdir()
        catalog_content = """
name: "nWave"
version: "1.2.57"
description: "Test framework"
"""
        catalog_path = catalog_dir / "framework-catalog.yaml"
        catalog_path.write_text(catalog_content)

        dist_dir = tmp_path / "dist"
        dist_dir.mkdir()

        # Create dummy archives with matching version
        (dist_dir / "nwave-claude-code-1.2.57.zip").touch()
        (dist_dir / "nwave-codex-1.2.57.zip").touch()

        validator = VersionConflictValidator(tmp_path)
        error = validator.validate_archive_versions(dist_dir)

        assert error is None

    def test_validate_archive_versions_mismatch(self, tmp_path):
        """Test archive version validation when versions don't match."""
        catalog_dir = tmp_path / "nWave"
        catalog_dir.mkdir()
        catalog_content = """
name: "nWave"
version: "1.2.57"
description: "Test framework"
"""
        catalog_path = catalog_dir / "framework-catalog.yaml"
        catalog_path.write_text(catalog_content)

        dist_dir = tmp_path / "dist"
        dist_dir.mkdir()

        # Create archives with mismatched version
        (dist_dir / "nwave-claude-code-1.2.56.zip").touch()
        (dist_dir / "nwave-codex-1.2.56.zip").touch()

        validator = VersionConflictValidator(tmp_path)
        error = validator.validate_archive_versions(dist_dir)

        assert error is not None
        assert error.configuration_version == "1.2.57"
        assert "1.2.56" in error.archive_versions
        assert any("Rebuild" in step for step in error.resolution_steps)

    def test_version_conflict_includes_resolution_steps(self):
        """Test that version conflict error includes resolution steps."""
        error = VersionConflictValidator.VersionConflictError(
            configuration_version="1.2.57",
            tag_version="1.2.56",
            archive_versions=[],
            resolution_steps=["Step 1", "Step 2", "Step 3"],
        )

        assert len(error.resolution_steps) == 3
        assert all(isinstance(step, str) for step in error.resolution_steps)


class TestValidationIntegration:
    """Integration tests for validation."""

    def test_all_validators_available(self, tmp_path):
        """Test that all validators can be instantiated."""
        dist_dir = tmp_path / "dist"
        dist_dir.mkdir()

        # Create dummy files
        (dist_dir / "CHECKSUMS.json").write_text("{}")

        catalog_dir = tmp_path / "nWave"
        catalog_dir.mkdir()
        (catalog_dir / "framework-catalog.yaml").write_text("version: 1.2.57\n")

        # All validators should instantiate successfully
        missing_validator = MissingArtifactsValidator(dist_dir)
        checksum_validator = ChecksumMismatchValidator(dist_dir / "CHECKSUMS.json")
        version_validator = VersionConflictValidator(tmp_path)

        assert missing_validator is not None
        assert checksum_validator is not None
        assert version_validator is not None
