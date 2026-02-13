"""Unit tests for error_codes module.

Tests validate that error codes are consistently defined, unique,
and properly structured for use across installer components.
"""


class TestErrorCodesUniqueness:
    """Verify all error codes have unique values."""

    def test_error_codes_are_unique(self):
        """All error code values must be unique to prevent confusion."""
        from scripts.install.error_codes import (
            BUILD_FAILED,
            DEP_MISSING,
            ENV_NO_PIPENV,
            ENV_NO_VENV,
            VERIFY_FAILED,
        )

        codes = [ENV_NO_VENV, ENV_NO_PIPENV, DEP_MISSING, BUILD_FAILED, VERIFY_FAILED]
        assert len(codes) == len(set(codes)), "Error codes must be unique"


class TestErrorCodesTypes:
    """Verify error codes are string types for JSON serialization."""

    def test_error_codes_are_strings(self):
        """Error codes must be strings for machine-readable JSON output."""
        from scripts.install.error_codes import (
            BUILD_FAILED,
            DEP_MISSING,
            ENV_NO_PIPENV,
            ENV_NO_VENV,
            VERIFY_FAILED,
        )

        codes = [ENV_NO_VENV, ENV_NO_PIPENV, DEP_MISSING, BUILD_FAILED, VERIFY_FAILED]
        for code in codes:
            assert isinstance(code, str), f"Error code {code} must be a string"


class TestErrorCodesDefinitions:
    """Verify all required error codes are defined."""

    def test_all_error_codes_defined(self):
        """All expected error codes must be importable from the module."""
        from scripts.install import error_codes

        required_codes = [
            "ENV_NO_VENV",
            "ENV_NO_PIPENV",
            "DEP_MISSING",
            "BUILD_FAILED",
            "VERIFY_FAILED",
        ]

        for code_name in required_codes:
            assert hasattr(error_codes, code_name), (
                f"Error code {code_name} must be defined"
            )

    def test_error_codes_not_empty(self):
        """Error code values must not be empty strings."""
        from scripts.install.error_codes import (
            BUILD_FAILED,
            DEP_MISSING,
            ENV_NO_PIPENV,
            ENV_NO_VENV,
            VERIFY_FAILED,
        )

        codes = {
            "ENV_NO_VENV": ENV_NO_VENV,
            "ENV_NO_PIPENV": ENV_NO_PIPENV,
            "DEP_MISSING": DEP_MISSING,
            "BUILD_FAILED": BUILD_FAILED,
            "VERIFY_FAILED": VERIFY_FAILED,
        }

        for name, value in codes.items():
            assert value, f"Error code {name} must not be empty"

    def test_error_codes_have_consistent_naming(self):
        """Error codes should follow consistent naming convention."""
        from scripts.install.error_codes import (
            BUILD_FAILED,
            DEP_MISSING,
            ENV_NO_PIPENV,
            ENV_NO_VENV,
            VERIFY_FAILED,
        )

        codes = {
            "ENV_NO_VENV": ENV_NO_VENV,
            "ENV_NO_PIPENV": ENV_NO_PIPENV,
            "DEP_MISSING": DEP_MISSING,
            "BUILD_FAILED": BUILD_FAILED,
            "VERIFY_FAILED": VERIFY_FAILED,
        }

        for name, value in codes.items():
            # Value should be uppercase with underscores (snake_case)
            assert value == value.upper(), (
                f"Error code {name} value should be uppercase"
            )
            assert " " not in value, f"Error code {name} should not contain spaces"
