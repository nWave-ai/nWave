"""Tests for install_nwave._get_version() — version resolution.

Regression: the 'nwave' fallback in _get_version() can resolve a stale
dev-repo version instead of the actual installed nwave-ai version.
"""

from unittest.mock import patch

from scripts.install.install_nwave import _get_version


class TestInstallerVersionResolution:
    """_get_version() must never fall back to 'nwave' package metadata."""

    def test_never_falls_back_to_nwave_package(self):
        """Given 'nwave-ai' lookup fails but 'nwave' is installed,
        when _get_version() is called,
        then it must NOT return the 'nwave' version.
        """
        from importlib.metadata import PackageNotFoundError

        def _version_side_effect(name):
            if name == "nwave-ai":
                raise PackageNotFoundError
            if name == "nwave":
                return "1.5.0"  # stale dev version
            raise PackageNotFoundError

        with patch("importlib.metadata.version", side_effect=_version_side_effect):
            result = _get_version()
        assert result != "1.5.0", "Must not fall back to 'nwave' package metadata"

    def test_returns_nwave_ai_metadata_when_available(self):
        """Given 'nwave-ai' is installed,
        when _get_version() is called,
        then it returns the nwave-ai metadata version.
        """
        with patch("importlib.metadata.version", return_value="2.2.0"):
            assert _get_version() == "2.2.0"
