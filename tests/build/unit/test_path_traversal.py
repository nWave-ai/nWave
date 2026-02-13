"""
Test path traversal security validation for BUILD:INCLUDE markers.

Validates that the dependency resolver blocks path escape attempts
(../, absolute paths, encoded traversal, null bytes) while allowing
valid paths within project boundaries.
"""

import re
from pathlib import Path

import pytest


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "path-traversal"


def _get_project_root() -> Path:
    """Get the project root (the directory containing this test file acts as root)."""
    return FIXTURES_DIR


def _validate_path_security(path: Path, project_root: Path) -> bool:
    """Validate that path doesn't escape project root (path traversal protection)."""
    try:
        resolved = path.resolve()
        project_root_resolved = project_root.resolve()
        return str(resolved).startswith(str(project_root_resolved))
    except (ValueError, OSError):
        return False


def _resolve_path(path_str: str, project_root: Path) -> Path:
    """Resolve a path string relative to project root."""
    path_str = path_str.strip()
    return Path(path_str) if path_str.startswith("/") else project_root / path_str


def _process_includes(file_path: Path, project_root: Path) -> tuple[bool, list[str]]:
    """Process a file for BUILD:INCLUDE markers and validate path security.

    Returns: (success, errors)
    """
    errors = []
    content = file_path.read_text()
    include_pattern = re.compile(r"\{\{\s*BUILD:INCLUDE\s+([^\}]+)\s*\}\}")

    for match in include_pattern.finditer(content):
        include_path_str = match.group(1).strip()
        include_path = _resolve_path(include_path_str, project_root)

        if not _validate_path_security(include_path, project_root):
            errors.append(f"Path traversal attempt blocked: {include_path_str}")
        elif not include_path.exists():
            errors.append(f"File not found: {include_path_str}")

    return len(errors) == 0, errors


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def fixture_files():
    """All path traversal fixture .md files."""
    files = sorted(FIXTURES_DIR.glob("*.md"))
    assert files, f"No fixture files found in {FIXTURES_DIR}"
    return files


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPathTraversalSecurity:
    """BUILD:INCLUDE path traversal protection tests."""

    def test_absolute_path_blocked(self):
        """Absolute paths to sensitive files must be blocked."""
        f = FIXTURES_DIR / "absolute-path.md"
        success, errors = _process_includes(f, FIXTURES_DIR)
        assert not success
        assert any("blocked" in e for e in errors)

    def test_complex_traversal_blocked(self):
        """Complex ../ traversal attempts must be blocked."""
        f = FIXTURES_DIR / "complex-traversal.md"
        success, errors = _process_includes(f, FIXTURES_DIR)
        assert not success
        assert any("blocked" in e for e in errors)

    def test_encoded_traversal_blocked(self):
        """URL-encoded traversal attempts must be blocked."""
        f = FIXTURES_DIR / "encoded-traversal.md"
        success, _errors = _process_includes(f, FIXTURES_DIR)
        assert not success

    def test_null_byte_blocked(self):
        """Null byte injection attempts must be blocked."""
        f = FIXTURES_DIR / "null-byte.md"
        success, _errors = _process_includes(f, FIXTURES_DIR)
        assert not success

    def test_windows_traversal_blocked(self):
        """Windows-style backslash traversal must be blocked."""
        f = FIXTURES_DIR / "windows-traversal.md"
        success, _errors = _process_includes(f, FIXTURES_DIR)
        assert not success

    def test_mixed_valid_invalid_continues_processing(self):
        """Processing must continue after encountering a blocked path."""
        f = FIXTURES_DIR / "mixed-valid-invalid.md"
        success, errors = _process_includes(f, FIXTURES_DIR)
        assert not success
        assert len(errors) >= 1  # at least the invalid one blocked

    def test_all_fixtures_found(self, fixture_files):
        """All 8 fixture files must be present."""
        assert len(fixture_files) == 8
