"""Standardized error codes for the nWave installer system.

This module provides consistent error identification across all installer
components. Error codes are used by preflight_checker, output_formatter,
and other modules for machine-readable error reporting in Claude Code
JSON output.

Each error code is a unique uppercase string identifier that enables:
- Consistent error handling across installer components
- Machine-readable error identification for automation
- Clear categorization of error types (environment, dependency, build, verify)

Usage:
    from scripts.install.error_codes import ENV_NO_VENV, DEP_MISSING

    if not venv_exists:
        return {"error_code": ENV_NO_VENV, "message": "No virtual environment found"}
"""

# Environment-related error codes
ENV_NO_VENV: str = "ENV_NO_VENV"
"""No virtual environment detected. The installer requires a Python virtual
environment to be active for safe package installation."""

ENV_NO_PIPENV: str = "ENV_NO_PIPENV"
"""Pipenv is not available. The installer requires pipenv for dependency
management and lock file handling."""

# Dependency-related error codes
DEP_MISSING: str = "DEP_MISSING"
"""A required dependency is missing. This indicates that a package required
by nWave is not installed or cannot be imported."""

# Build-related error codes
BUILD_FAILED: str = "BUILD_FAILED"
"""The build process failed. This can occur during package compilation,
asset generation, or other build steps."""

# Verification-related error codes
VERIFY_FAILED: str = "VERIFY_FAILED"
"""Verification failed. Post-installation checks did not pass, indicating
the installation may be incomplete or corrupted."""
