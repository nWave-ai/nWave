"""ConfigSsotCheck -- reports the merged canonical configuration.

This thin doctor shell delegates resolution to ``NWaveConfig.effective_config``.
Legacy filenames are intentionally absent: migration is ConfigWriter's
one-shot responsibility, and ordinary consumers must not inspect retired
configuration files after cutover.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from nwave_ai.common.check_result import CheckResult
from nwave_ai.platform.config import NWaveConfig


if TYPE_CHECKING:
    from nwave_ai.doctor.context import DoctorContext


class ConfigSsotCheck:
    """Surface the merged canonical config."""

    name: str = "config_ssot"
    description: str = "Unified config.json cascade (ADR-CFG-001 Slice 2)"

    def run(self, context: DoctorContext) -> CheckResult:
        """Report the effective enabled/verbosity/attribution values.

        Missing canonical files are resolved through ``merge_config`` defaults.
        This check deliberately does not inspect legacy filenames: install and
        explicit config mutation route their one-shot migration through
        ``ConfigWriter`` before this regular consumer is invoked.
        """
        config = NWaveConfig(
            cwd=context.project_root, global_config_path=context.global_config_path
        )
        effective = config.effective_config()

        return CheckResult(
            passed=True,
            error_code=None,
            message=(
                f"Effective config: enabled={effective['enabled']}, "
                f"verbosity={effective['verbosity']!r}, "
                f"attribution={effective['attribution']}"
            ),
            remediation=None,
        )
