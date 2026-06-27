"""Doctor runner — orchestrates all diagnostic checks.

Step 01-01: stub returning empty list.
Step 01-03: wire 7 checks in fixed order; annotate results with check_name.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from nwave_ai.doctor.checks.attribution import AttributionCheck
from nwave_ai.doctor.checks.density import DensityCheck
from nwave_ai.doctor.checks.des_module import DesModuleCheck
from nwave_ai.doctor.checks.framework_files import FrameworkFilesCheck
from nwave_ai.doctor.checks.hook_python_path import HookPythonPathCheck
from nwave_ai.doctor.checks.hooks_registered import HooksRegisteredCheck
from nwave_ai.doctor.checks.path_env import PathEnvCheck
from nwave_ai.doctor.checks.python_version import PythonVersionCheck
from nwave_ai.doctor.checks.shims_deployed import ShimsDeployedCheck


if TYPE_CHECKING:
    from nwave_ai.common.check_result import CheckResult
    from nwave_ai.doctor.context import DoctorContext


class _DiagnosticCheck(Protocol):
    """Structural type for all diagnostic check classes."""

    name: str

    def run(self, context: DoctorContext) -> CheckResult: ...


_CHECKS: list[_DiagnosticCheck] = [
    PythonVersionCheck(),
    DesModuleCheck(),
    HooksRegisteredCheck(),
    HookPythonPathCheck(),
    ShimsDeployedCheck(),
    PathEnvCheck(),
    FrameworkFilesCheck(),
    DensityCheck(),
    AttributionCheck(),
]


def run_doctor(context: DoctorContext) -> list[CheckResult]:
    """Run all doctor checks and return results in registration order.

    Each CheckResult is annotated with the originating check's name attribute.

    Args:
        context: Filesystem roots for this run (injected for testability).

    Returns:
        Ordered list of CheckResult objects, one per check.
    """
    results: list[CheckResult] = []
    for check in _CHECKS:
        result = check.run(context)
        result.check_name = check.name
        results.append(result)
    return results
