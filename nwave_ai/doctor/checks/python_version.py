"""PythonVersionCheck — verifies the interpreter is Python >= 3.11."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from nwave_ai.common.check_result import CheckResult


if TYPE_CHECKING:
    from nwave_ai.doctor.context import DoctorContext


class PythonVersionCheck:
    """Check that the active Python interpreter is >= 3.11."""

    name: str = "python_version"
    description: str = "Python interpreter version is 3.11 or newer"

    def run(self, context: DoctorContext) -> CheckResult:
        """Return passed=True when sys.version_info >= (3, 11).

        Args:
            context: Filesystem roots (unused — interpreter check is in-process).

        Returns:
            CheckResult with version details in message.
        """
        major, minor = sys.version_info[:2]
        version_string = f"{major}.{minor}.{sys.version_info[2]}"
        if (major, minor) >= (3, 11):
            return CheckResult(
                passed=True,
                error_code=None,
                message=f"Python {version_string} — OK",
                remediation=None,
            )
        return CheckResult(
            passed=False,
            error_code="PYTHON_VERSION_TOO_OLD",
            message=f"Python {version_string} is below the required minimum",
            remediation=(
                "Upgrade to Python 3.11 or newer. "
                "Visit https://www.python.org/downloads/ for installers."
            ),
        )
