"""SessionStart hook handler for nWave update checks and housekeeping.

Reads hook input JSON from stdin, runs housekeeping, invokes UpdateCheckService,
and writes the update notice JSON to stdout when UPDATE_AVAILABLE.

Fail-open: any exception exits 0 so session is never blocked.
Housekeeping and update check run in independent try/except blocks.
Housekeeping runs before update check; DESConfig is shared between both.

Output format when UPDATE_AVAILABLE (see ``_build_update_output``):
    {
      "systemMessage": "nWave update available: {local} → {latest}. Run /nw-update to update.",
      "hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": "nWave update available: {local} → {latest}. Changes: {changelog_or_empty}"
      }
    }

``systemMessage`` is shown to the user; ``additionalContext`` is injected into
the model context. The wrapped ``hookSpecificOutput`` form is required -- the
bare ``{"additionalContext": ...}`` form is not honored by current Claude Code.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from des.adapters.drivers.hooks.substrate_probe import run_probe


if TYPE_CHECKING:
    from des.adapters.driven.config.des_config import DESConfig
    from des.application.update_check_service import UpdateCheckService
    from des.ports.driven_ports.package_manager_port import PackageManagerPort


def _get_local_version() -> str:
    """Return installed nwave-ai version, or '0.0.0' if unavailable."""
    from des.application.update_check_service import _detect_local_version

    return _detect_local_version()


def _select_package_manager_adapter(pm: str) -> PackageManagerPort:
    """Return the adapter for the given package manager name.

    For ``pm == "unknown"`` returns a ``NullPackageManager`` no-op adapter; the
    service exits via its own ``flag.pm == "unknown"`` branch before invoking
    ``upgrade()`` on it. Always returning a real ``PackageManagerPort`` keeps
    the type contract honest and removes the need for ``# type: ignore`` at
    the call site.
    """
    if pm == "pipx":
        from des.adapters.driven.package_managers.pipx_package_manager_adapter import (
            PipxPackageManagerAdapter,
        )

        return PipxPackageManagerAdapter()
    if pm == "uv":
        from des.adapters.driven.package_managers.uv_package_manager_adapter import (
            UvPackageManagerAdapter,
        )

        return UvPackageManagerAdapter()
    # pm == "unknown": service handles via its existing branch.
    from des.adapters.driven.package_managers.null_package_manager import (
        NullPackageManager,
    )

    return NullPackageManager()


def _apply_pending_update_if_any(des_config: DESConfig, current_version: str) -> None:
    """Early-phase apply of any pending deferred nWave self-update.

    Reads the pending-update flag via DESConfig; when present, composes a
    PendingUpdateService with the adapter matching ``flag.pm`` and invokes
    ``apply()``. For ``flag.pm == "unknown"`` the service handles the branch
    internally (no adapter invoked) and emits a warning banner.

    Fail-open: all exceptions are swallowed so the session is never blocked.
    """
    try:
        flag = des_config.read_pending_update()
        if flag is None:
            return

        from des.application.pending_update_service import PendingUpdateService

        adapter = _select_package_manager_adapter(flag.pm)

        service = PendingUpdateService(
            config=des_config,
            pm=adapter,
            current_version=current_version,
        )
        service.apply()
    except Exception as e:
        sys.stderr.write(f"[nwave] pending-update apply error (fail-open): {e}\n")


def _adopt_prior_use_if_warranted(stdin_text: str) -> None:
    """Trigger-1: silently adopt a prior-use project at SessionStart (DDD-7).

    SessionStart is gate-exempt (always runs), so this is the wiring point for
    prior-use adoption. Resolves the project root from the hook stdin ``cwd``
    (same envelope shape every handler reads), then asks ``AutoMarkingService``
    to write the marker IFF prior-use evidence warrants it. Silent and fail-open:
    any parse/IO error is swallowed so SessionStart's update-notice and
    housekeeping are never disturbed.
    """
    try:
        project_root = _parse_cwd(stdin_text)
        if project_root is None:
            return
        from des.application.auto_marking_service import (
            AdoptionTrigger,
            AutoMarkingService,
        )

        AutoMarkingService().adopt_if_warranted(
            project_root=project_root, trigger=AdoptionTrigger.PRIOR_USE
        )
    except Exception as e:
        sys.stderr.write(f"[nwave] prior-use adoption error (fail-open): {e}\n")


def _parse_cwd(stdin_text: str) -> Path | None:
    """Resolve the project root from the hook stdin envelope's ``cwd`` field."""
    try:
        data = json.loads(stdin_text)
    except (json.JSONDecodeError, TypeError):
        return None
    cwd = data.get("cwd") if isinstance(data, dict) else None
    return Path(cwd) if cwd else None


def _run_housekeeping(des_config: DESConfig) -> None:
    """Run housekeeping using configuration from DESConfig.

    Builds HousekeepingConfig from des_config properties and delegates to
    HousekeepingService. Fail-open: caller must wrap in try/except.
    """
    from des.adapters.driven.time.system_time import SystemTimeProvider
    from des.application.housekeeping_service import (
        HousekeepingConfig,
        HousekeepingService,
    )

    config = HousekeepingConfig(
        enabled=des_config.housekeeping_enabled,
        audit_retention_days=des_config.housekeeping_audit_retention_days,
        signal_staleness_hours=des_config.housekeeping_signal_staleness_hours,
        skill_log_max_bytes=des_config.housekeeping_skill_log_max_bytes,
    )
    HousekeepingService.run_housekeeping(config, SystemTimeProvider())


def _build_update_check_service(des_config: DESConfig) -> UpdateCheckService:
    """Build UpdateCheckService with a shared DESConfig for frequency gating."""
    from des.application import update_check_service

    return update_check_service.UpdateCheckService(des_config=des_config)


def _build_update_message(local: str, latest: str, changelog: str | None) -> str:
    """Format the model-facing additionalContext message for an available update."""
    changes = changelog or ""
    return f"nWave update available: {local} \u2192 {latest}. Changes: {changes}"


def _build_visible_message(local: str, latest: str) -> str:
    """Format the user-visible systemMessage shown on screen at session start."""
    return f"nWave update available: {local} \u2192 {latest}. Run /nw-update to update."


def _build_update_output(local: str, latest: str, changelog: str | None) -> dict:
    """Build the SessionStart hook JSON payload for an available update.

    Emits BOTH:
    - ``systemMessage`` (top-level) -- rendered visibly to the user at session
      start. ``additionalContext`` alone is injected silently and never shown,
      so a visible notice requires this field.
    - ``hookSpecificOutput.additionalContext`` -- the canonical wrapped form for
      context injection. The bare ``{"additionalContext": ...}`` form is dropped
      by current Claude Code versions, so the wrapper is required for the model
      to actually receive the update context.
    """
    return {
        "systemMessage": _build_visible_message(local, latest),
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": _build_update_message(local, latest, changelog),
        },
    }


def handle_session_start() -> int:
    """Handle session-start hook: run housekeeping then check for nWave updates.

    Reads JSON from stdin (Claude Code hook protocol), runs housekeeping,
    calls UpdateCheckService, and writes additionalContext to stdout when an
    update is available. DESConfig is shared between both operations.

    Returns:
        0 always (fail-open: session must never be blocked).
    """
    stdin_text = sys.stdin.read()

    # Trigger-1 (prior-use adoption): SessionStart is gate-exempt, so this is
    # where an unmarked project with prior nWave use is silently adopted. Runs
    # first and fail-open so it never disturbs the update-notice / housekeeping.
    _adopt_prior_use_if_warranted(stdin_text)

    from des.adapters.driven.config.des_config import DESConfig

    des_config = DESConfig()

    # Early phase: apply any pending deferred self-update BEFORE housekeeping
    # and update-check. A just-upgraded session must not run update-check with
    # a stale current_version comparison.
    _apply_pending_update_if_any(des_config, _get_local_version())

    try:
        _run_housekeeping(des_config)
    except Exception:
        pass

    try:
        service = _build_update_check_service(des_config)
        result = service.check_for_updates()

        from des.application.update_check_service import UpdateStatus

        if result.status == UpdateStatus.UPDATE_AVAILABLE:
            output = _build_update_output(
                local=_get_local_version(),
                latest=result.latest or "",
                changelog=result.changelog,
            )
            print(json.dumps(output))

    except Exception:
        pass

    try:
        advisory = run_probe()
        if advisory:
            print(advisory, end="")
    except Exception:
        pass

    return 0
