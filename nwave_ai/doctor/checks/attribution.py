"""AttributionCheck — read-only activation-aware attribution report (AB-9).

DESIGN ADR-CA-007. The check is read-only (Principle 12 pure-read): it reads
``~/.claude/settings.json`` and the activation config via the injected
DoctorContext and reports four diagnostic lines so a user can answer "why did
this commit (not) get the credit?":

  1. is the activation-gated attribution commit hook registered?
  2. is THIS repo activation-resolved active? (reuses the canonical
     ``resolve_activation`` policy over the marker + global mode — no
     re-derivation here, DDD discipline)
  3. is there leftover nWave-managed legacy ``settings.json`` residue?
  4. the deprecated ``includeCoAuthoredBy`` flag, read from its correct
     TOP-LEVEL location (DDD-7 bug fix — it was previously read nested under
     ``attribution``).

It never mutates settings.json.

Three-valued verdict (ADR-CFG-003 correction 2, CONTESTED_LAW): the check
observes TWO axes (GDP-8 witness corollary) -- (a) is the hook registered in
settings.json, (b) does the producing-tool resolver (the SAME resolution
``attribute_commit_message`` performs: activation AND ``attribution.enabled``)
now attribute for this repo. The verdict is the IMPLICATION
``would_attribute -> hook_present``, NOT equality: ``hook_present`` means
"nWave installed," not "attribution on," so an installed machine with
attribution off everywhere (hook_present=True, would_attribute=False) is a
vacuously-true implication, not a disagreement. AGREED (the implication
holds) -> passed=True. DISAGREED (would_attribute is True but hook_present is
False) -> passed=False, ``ATTRIBUTION_DISAGREEMENT``, remediation naming the
real producing-tool command ``nwave-ai attribution on``. COULD_NOT_VERIFY
(the resolution itself raises) -> passed=False, ``ATTRIBUTION_UNVERIFIABLE``
-- its own third state reaching the aggregate rather than being silently
folded into AGREED.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from nwave_ai.common.check_result import CheckResult


if TYPE_CHECKING:
    from nwave_ai.doctor.context import DoctorContext
    from scripts.install.host_attribution import (
        HostAttributionPolicy,
        InstalledHookPort,
    )
    from scripts.install.plugins.base import InstallContext, PluginResult


_LEGACY_RUNTIME = "nwave_attribution_hook.py"

# Current registration shape (ADR-CA-006/007): the universal PreToolUse
# adapter observes attribution.enabled at invocation time -- there is no
# dedicated attribution hook entry anymore. `_HOOK_MARKER` below matched the
# retired independent `pre-commit-attribution` action
# (scripts/install/attribution_utils.py:_attribution_hook_command, tombstoned
# as the cleanup-only removal baseline); real installs have never written
# that shape since ADR-CA-006. `_hook_registered` must key on the module +
# action actually installed by scripts/install/plugins/nwave_hooks_plugin.py
# (HOOK_COMMAND_TEMPLATE): "...-m nwave_ai.hooks pre-tool-use".
_HOOK_MODULE = "nwave_ai.hooks"
_HOOK_ACTION = "PreToolUse"
_OMP_HOOKS_SHIM = "nwave-hooks.ts"
_OMP_HOOKS_MANIFEST = ".nwave-des-manifest.json"


class InstalledHookVerifier:
    """Map policy-owned verification ports to their installing adapters."""

    def __init__(self, context: DoctorContext):
        from scripts.install.host_attribution import InstalledHookPort

        self._context = context
        self._verify_by_port = {
            InstalledHookPort.CODEX_HOOKS: self._codex_hooks,
            InstalledHookPort.OMP_EXTENSION: self._omp_extension,
        }

    def verify(self, port: InstalledHookPort) -> str | None:
        return self._verify_by_port[port]()

    def _install_context(self, platforms: set[str]) -> InstallContext:
        from scripts.install.plugins.base import InstallContext

        return InstallContext(
            claude_dir=self._context.claude_dir,
            scripts_dir=self._context.home_dir,
            templates_dir=self._context.home_dir,
            logger=logging.getLogger(__name__),
            target_platforms=platforms,
        )

    def _codex_hooks(self) -> str | None:
        from scripts.install.plugins.nwave_hooks_plugin import HooksPlugin

        result = HooksPlugin().verify(self._install_context({"codex"}))
        return self._failure_reason(result)

    def _omp_extension(self) -> str | None:
        """The OMP hook shim exists and matches the sha256 its manifest records."""
        from scripts.shared.install_paths import omp_extensions_dir

        directory = omp_extensions_dir(self._context.home_dir)
        shim = directory / _OMP_HOOKS_SHIM
        manifest = directory / _OMP_HOOKS_MANIFEST
        try:
            rendered = shim.read_bytes()
            recorded = json.loads(manifest.read_text(encoding="utf-8"))["sha256"]
        except (OSError, ValueError, KeyError, TypeError) as error:
            return (
                f"WHAT: kept OMP nWave hooks extension not verified at {shim}. "
                f"WHY: {error}. HOW: rerun the installer."
            )
        if hashlib.sha256(rendered).hexdigest() != recorded:
            return (
                f"WHAT: kept OMP nWave hooks extension at {shim} is stale. "
                "WHY: its bytes differ from the manifest. HOW: rerun the installer."
            )
        return None

    @staticmethod
    def _failure_reason(result: PluginResult) -> str | None:
        return None if result.success else "; ".join(result.errors) or result.message


class AttributionCheck:
    """Read-only diagnostic: 4-line activation-aware attribution report (AB-9)."""

    name: str = "attribution"
    description: str = (
        "Reports hook registration, this repo's activation state, legacy "
        "settings residue, and the deprecated includeCoAuthoredBy state"
    )

    def run(self, context: DoctorContext) -> CheckResult:
        """Return a read-only attribution diagnostic — never mutates.

        See the module docstring for the three-valued AGREED / DISAGREED /
        COULD_NOT_VERIFY verdict this returns.
        """
        from scripts.install.attribution_utils import UnreadableAttributionPreference
        from scripts.install.host_attribution import (
            AttributionPreference,
            HostAttributionPolicy,
        )

        preference = AttributionPreference.read(context.global_config_path.parent)
        policy = HostAttributionPolicy.from_install_record(
            context.global_config_path.parent
        )
        settings = self._read_settings(context.settings_path)

        hook_present = self._hook_registered(settings)
        hook_line = (
            f"attribution commit hook: "
            f"{'registered' if hook_present else 'not registered'}"
        )

        active, attribution_enabled, resolution_error = self._resolve_attribution_state(
            context
        )
        activation_line = f"this repo activation: {'active' if active else 'inactive'}"

        residue_present = self._legacy_residue_present(context, settings)
        residue_line = (
            f"legacy settings residue: {'present' if residue_present else 'absent'}"
        )

        deprecated = settings.get("includeCoAuthoredBy")
        deprecated_state = "unset" if deprecated is None else str(deprecated).lower()
        deprecated_line = f"deprecated includeCoAuthoredBy: {deprecated_state}"

        host_lines, host_remediations = self._host_attribution(
            context,
            attribution_enabled,
            resolution_error,
            policy,
        )
        message = "\n".join(
            [hook_line, activation_line, residue_line, deprecated_line, *host_lines]
        )

        if isinstance(preference, UnreadableAttributionPreference):
            return CheckResult(
                passed=False,
                error_code="ATTRIBUTION_UNVERIFIABLE",
                message=f"{message}\n{preference.warning()}",
                remediation=(
                    "Restore a readable config file, then run "
                    "`nwave-ai attribution on` or `nwave-ai attribution off` "
                    "and re-run `nwave-ai doctor`."
                ),
            )

        if resolution_error is not None:
            return CheckResult(
                passed=False,
                error_code="ATTRIBUTION_UNVERIFIABLE",
                message=message,
                remediation=(
                    "Could not resolve the attribution configuration "
                    f"({resolution_error}). Fix the underlying config read, "
                    "then re-run `nwave-ai doctor`."
                ),
            )

        would_attribute = active and attribution_enabled
        disagreed = would_attribute and not hook_present and policy.claude_expected
        if not disagreed and not host_remediations:
            return CheckResult(
                passed=True,
                error_code=None,
                message=message,
                remediation=None,
            )

        remediation = [
            *(
                [
                    "The attribution commit hook registration and the resolved "
                    "attribution state disagree. Run `nwave-ai attribution on` "
                    "to re-register the hook and align both."
                ]
                if disagreed
                else []
            ),
            *host_remediations,
        ]
        return CheckResult(
            passed=False,
            error_code=(
                "ATTRIBUTION_DISAGREEMENT"
                if disagreed
                else "ATTRIBUTION_HOST_UNAVAILABLE"
            ),
            message=message,
            remediation="\n".join(remediation),
        )

    @staticmethod
    def _host_attribution(
        context: DoctorContext,
        attribution_enabled: bool,
        resolution_error: Exception | None,
        policy: HostAttributionPolicy,
    ) -> tuple[list[str], list[str]]:
        """Report each detected non-Claude host's mechanism, as found on disk.

        Returns ``(report lines, remediations)``; a host whose mechanism is
        unavailable while attribution is enabled contributes a remediation and
        fails the check. Nothing is reported while attribution is disabled.
        """
        if (
            not attribution_enabled
            or resolution_error is not None
            or not policy.has_hosts
        ):
            return [], []
        lines: list[str] = []
        remediations: list[str] = []
        verifier = InstalledHookVerifier(context)
        for mechanism in policy.mechanisms_in(context.project_root):
            found = mechanism.inspect(verifier)
            lines.append(found.describe())
            if not found.works:
                remediations.append(f"{found.label}: {found.remediation}.")
        return lines, remediations

    @staticmethod
    def _read_settings(settings_path: Path) -> dict:
        if not settings_path.exists():
            return {}
        try:
            return json.loads(settings_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    @staticmethod
    def _hook_registered(settings: dict) -> bool:
        entries = settings.get("hooks", {}).get("PreToolUse", [])
        return any(
            _HOOK_MODULE in (command := hook.get("command", ""))
            and _HOOK_ACTION in command
            for entry in entries
            if isinstance(entry, dict)
            for hook in entry.get("hooks", [])
            if isinstance(hook, dict)
        )

    @staticmethod
    def _resolve_attribution_state(
        context: DoctorContext,
    ) -> tuple[bool, bool, Exception | None]:
        """Resolve ``(active, attribution_enabled, resolution_error)``.

        Reuses the SAME resolution
        ``nwave_ai.hooks.attribution.attribute_commit_message``
        performs (the canonical ``resolve_activation`` policy over the two
        scalars ``DESConfig`` exposes -- marker ``enabled_for_repo`` + global
        ``activation.mode`` -- AND ``DESConfig.attribution_enabled``) — the
        policy is NOT re-derived here.

        On a config-read exception, returns ``(False, False, exc)`` rather
        than raising: ``active=False`` lets the diagnostic message still fail
        OPEN to "inactive" (never more optimistic than the enforcement gate),
        while the returned exception lets the caller surface its own
        COULD_NOT_VERIFY third state instead of silently folding the failure
        into AGREED.
        """
        try:
            from nwave_ai.platform.activation import resolve_activation
            from nwave_ai.platform.config import NWaveConfig

            config = NWaveConfig(
                cwd=context.project_root,
                global_config_path=context.global_config_path,
            )
            active = resolve_activation(config.enabled_for_repo, config.activation_mode)
            return active, config.attribution_enabled, None
        except Exception as exc:
            return False, False, exc

    @classmethod
    def _legacy_residue_present(cls, context: DoctorContext, settings: dict) -> bool:
        """Report leftover nWave-managed legacy residue.

        Residue is the ``settings.json attribution.commit`` block still set AND
        recognised as nWave-managed (its value matches the global-config
        ``last_written_value`` baseline that 01-03's migration cleans), or a
        legacy on-disk attribution runtime hook.
        """
        attribution = settings.get("attribution") or {}
        commit = attribution.get("commit")
        if commit and commit == cls._managed_baseline(context):
            return True
        return cls._legacy_hook_present(context)

    @staticmethod
    def _managed_baseline(context: DoctorContext) -> str | None:
        try:
            data = json.loads(context.global_config_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
        return (data.get("attribution") or {}).get("last_written_value")

    @staticmethod
    def _legacy_hook_present(context: DoctorContext) -> bool:
        """A runtime hook copy is legacy unless a current fallback shim runs it."""
        from scripts.install.attribution_utils import has_current_fallback

        runtime = context.home_dir / ".nwave" / "hooks" / _LEGACY_RUNTIME
        if not runtime.exists():
            return False
        try:
            config = json.loads(context.global_config_path.read_text(encoding="utf-8"))
            recorded = (config.get("attribution") or {}).get("hooks_dir")
        except (json.JSONDecodeError, OSError, AttributeError):
            recorded = None
        return not (recorded and has_current_fallback(Path(recorded)))
