"""HooksRegisteredCheck — verifies all required hook types are in settings.json."""

from __future__ import annotations

from typing import TYPE_CHECKING

from nwave_ai.common.check_result import CheckResult
from nwave_ai.doctor.checks._settings import read_settings
from nwave_ai.hooks.registration import HOOK_EVENT_TYPES


if TYPE_CHECKING:
    from nwave_ai.doctor.context import DoctorContext


# Derived from HOOK_EVENT_TYPES (scripts/shared/hook_definitions.py) -- the SSOT
# for which hook events DES actually registers -- rather than hand-restating the
# set a third place. Sorted for a deterministic message/count independent of
# frozenset iteration order.
REQUIRED_HOOK_TYPES: tuple[str, ...] = tuple(sorted(HOOK_EVENT_TYPES))


class HooksRegisteredCheck:
    """Check that settings.json contains all required hook type entries."""

    name: str = "hooks_registered"
    description: str = "All required hook types are registered in settings.json"

    def run(self, context: DoctorContext) -> CheckResult:
        """Return passed=True when all required hook type keys are present.

        Args:
            context: Filesystem roots — reads context.settings_path.

        Returns:
            CheckResult listing any missing hook types in message.
        """
        data, error = read_settings(context.settings_path)
        if error is not None:
            return error

        registered = set(data.get("hooks", {}).keys())
        missing = [h for h in REQUIRED_HOOK_TYPES if h not in registered]

        if not missing:
            total = sum(len(data["hooks"].get(h, [])) for h in REQUIRED_HOOK_TYPES)
            return CheckResult(
                passed=True,
                error_code=None,
                message=(
                    f"All {len(REQUIRED_HOOK_TYPES)} hook types registered "
                    f"({total} total entries)"
                ),
                remediation=None,
            )

        missing_str = ", ".join(missing)
        return CheckResult(
            passed=False,
            error_code="HOOKS_MISSING",
            message=f"Missing hook types: {missing_str}",
            remediation="Run `nwave-ai install` to register the missing hook entries.",
        )
