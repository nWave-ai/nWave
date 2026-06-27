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

It never mutates settings.json. It is a diagnostic, not a gate: it always
reports passed=True so a clean install still shows all checks green. The signal
lives in the message body.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from nwave_ai.common.check_result import CheckResult


if TYPE_CHECKING:
    from pathlib import Path

    from nwave_ai.doctor.context import DoctorContext


_LEGACY_RUNTIME = "nwave_attribution_hook.py"
_HOOK_MARKER = "pre-commit-attribution"


class AttributionCheck:
    """Read-only diagnostic: 4-line activation-aware attribution report (AB-9)."""

    name: str = "attribution"
    description: str = (
        "Reports hook registration, this repo's activation state, legacy "
        "settings residue, and the deprecated includeCoAuthoredBy state"
    )

    def run(self, context: DoctorContext) -> CheckResult:
        """Return a read-only attribution diagnostic — never mutates."""
        settings = self._read_settings(context.settings_path)

        hook_present = self._hook_registered(settings)
        hook_line = (
            f"attribution commit hook: "
            f"{'registered' if hook_present else 'not registered'}"
        )

        active = self._repo_is_active(context)
        activation_line = f"this repo activation: {'active' if active else 'inactive'}"

        residue_present = self._legacy_residue_present(context, settings)
        residue_line = (
            f"legacy settings residue: {'present' if residue_present else 'absent'}"
        )

        deprecated = settings.get("includeCoAuthoredBy")
        deprecated_state = "unset" if deprecated is None else str(deprecated).lower()
        deprecated_line = f"deprecated includeCoAuthoredBy: {deprecated_state}"

        message = "\n".join([hook_line, activation_line, residue_line, deprecated_line])
        return CheckResult(
            passed=True,
            error_code=None,
            message=message,
            remediation=None,
        )

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
            _HOOK_MARKER in hook.get("command", "")
            for entry in entries
            if isinstance(entry, dict)
            for hook in entry.get("hooks", [])
            if isinstance(hook, dict)
        )

    @staticmethod
    def _repo_is_active(context: DoctorContext) -> bool:
        """Resolve THIS repo's activation, failing to INACTIVE on a read error.

        Reuses the canonical ``resolve_activation`` policy over the two scalars
        the ``DESConfig`` reader exposes (marker ``enabled_for_repo`` + global
        ``activation.mode``) — the policy is NOT re-derived here.

        On a config-read exception we fail to INACTIVE (return False), matching
        the activation gate's fail-to-inactive-under-opt-in semantics: a
        diagnostic must never be more optimistic than the enforcement gate.
        """
        try:
            from des.adapters.driven.config.des_config import DESConfig
            from des.domain.activation_policy import resolve_activation

            config = DESConfig(
                cwd=context.project_root,
                global_config_path=context.global_config_path,
            )
            return resolve_activation(config.enabled_for_repo, config.activation_mode)
        except Exception:
            return False

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
        return cls._legacy_hook_present(context.home_dir)

    @staticmethod
    def _managed_baseline(context: DoctorContext) -> str | None:
        try:
            data = json.loads(context.global_config_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
        return (data.get("attribution") or {}).get("last_written_value")

    @staticmethod
    def _legacy_hook_present(home_dir: Path) -> bool:
        return (home_dir / ".nwave" / "hooks" / _LEGACY_RUNTIME).exists()
