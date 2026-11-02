"""Run diagnostic checks independently, preserving failures in the report."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from nwave_ai.common.check_result import CheckResult
from nwave_ai.doctor.checks.attribution import AttributionCheck
from nwave_ai.doctor.checks.config_ssot import ConfigSsotCheck
from nwave_ai.doctor.checks.framework_files import FrameworkFilesCheck
from nwave_ai.doctor.checks.hook_python_path import HookPythonPathCheck
from nwave_ai.doctor.checks.hooks_registered import HooksRegisteredCheck
from nwave_ai.doctor.checks.python_version import PythonVersionCheck
from nwave_ai.doctor.checks.version_sync import VersionSyncCheck


if TYPE_CHECKING:
    from nwave_ai.doctor.context import DoctorContext


class _DiagnosticCheck(Protocol):
    """Structural type for all diagnostic check classes."""

    name: str

    def run(self, context: DoctorContext) -> CheckResult: ...


_CHECKS: list[_DiagnosticCheck] = [
    PythonVersionCheck(),
    HooksRegisteredCheck(),
    HookPythonPathCheck(),
    FrameworkFilesCheck(),
    AttributionCheck(),
    VersionSyncCheck(),
    ConfigSsotCheck(),
]


def run_doctor(context: DoctorContext) -> list[CheckResult]:
    """Run all doctor checks and return results in registration order.

    Each result retains its check's name. An unexpected exception becomes an
    unverifiable result without preventing the remaining checks from running.

    Args:
        context: Filesystem roots for this run (injected for testability).

    Returns:
        Ordered list of CheckResult objects, one per check.
    """
    results: list[CheckResult] = []
    for check in _CHECKS:
        try:
            result = check.run(context)
        except Exception as error:
            result = CheckResult.could_not_verify(
                error_code="DOCTOR_CHECK_EXCEPTION",
                message=(
                    f"WHAT: doctor check '{check.name}' could not be verified. "
                    f"WHY: {type(error).__name__}: {error}"
                ),
                remediation=(
                    "HOW: Reinstall nWave with `nwave-ai install` so the CLI and "
                    "installer components match, then rerun `nwave-ai doctor`."
                ),
            )
        result.check_name = check.name
        results.append(result)
    return results
