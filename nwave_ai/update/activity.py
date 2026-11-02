"""Exclusive update lease and global-idle policy before replacement.

The registry itself (``nwave_ai.platform.session_registry``) lives
in the installed runtime so the installed lifecycle hooks can always import it. This
module holds only the update-side decision taken immediately before the first
mutating stage: take the exclusive update lock (every update), and, for an
automatic startup installation, prove global idle while holding it.

The lock is taken lazily, after every read-only preflight, so a refusal such
as an unknown package owner or a Windows platform writes nothing at all.
"""

from __future__ import annotations

from contextlib import ExitStack
from pathlib import Path

from nwave_ai.platform.session_registry import (
    Idle,
    SessionActivityRegistry,
)
from nwave_ai.update.package_activity import PackageActivityLease
from nwave_ai.update.service import UpdateResult


#: How long an updater waits for a concurrent registration to release the lock.
UPDATE_LOCK_WAIT_SECONDS = 5.0

_NO_CHANGE = "no package or host change started"


def _refusal(
    cause: str, recovery: str, stage: str = "activity-registry"
) -> UpdateResult:
    return UpdateResult(
        state="refused",
        version=None,
        failed_stage=stage,
        cause=cause,
        recovery=recovery,
    )


class ReplacementLease:
    """Hold the exclusive update lock from the pre-replacement check to ``close``.

    Automatic installation requires the in-memory capability of a controlled
    prelaunch session. Public arguments or environment variables cannot grant it.
    """

    def __init__(
        self,
        automatic_session=None,
        *,
        interpreter: Path | None = None,
        check_only: bool = False,
    ) -> None:
        self._automatic_session = automatic_session
        self._package = PackageActivityLease.for_interpreter(interpreter)
        self._stack = ExitStack()
        self._check_only = check_only
        self._ready = False

    def close(self) -> None:
        self._stack.close()
        self._ready = False

    def before_replacement(self, platform: str) -> UpdateResult | None:
        if self._check_only:
            return _refusal(
                "a check-only lease cannot replace a package",
                "grant installation separately and start a new controlled session",
            )
        return self._acquire(platform)

    def before_check(self) -> UpdateResult | None:
        return self._acquire("")

    def _acquire(self, platform: str) -> UpdateResult | None:
        """Keep both release discovery and replacement outside active work."""
        from nwave_ai.update.managed import WrapperRegistration
        from nwave_ai.update.permissions import (
            controlled_launch_permission,
            update_permissions,
        )

        automatic = self._automatic_session is not None
        check, install = update_permissions()
        if automatic and (
            not isinstance(self._automatic_session, WrapperRegistration)
            or not check
            or (
                not self._check_only
                and (not install or not controlled_launch_permission())
            )
        ):
            return _refusal(
                "controlled-launch capability or current consent is absent",
                "use nwave-ai run HOST -- ARGS after explicitly granting check, install and controlled-launch consent",
            )
        if automatic and self._package is None:
            return _refusal(
                "the running package has no verified, stable cross-home coordination location",
                "use a supported owned virtual environment; no automatic replacement started",
            )
        if self._ready:
            return None
        registry = SessionActivityRegistry.selected()
        if registry is None:
            return _refusal(
                "the selected agents home is invalid, so the global update lock cannot be located",
                (
                    "set NWAVE_AGENTS_HOME, CLAUDE_CONFIG_DIR and CODEX_HOME to absolute "
                    f"paths or unset them, then retry; {_NO_CHANGE}"
                ),
                stage="update-lock",
            )
        try:
            if self._package is not None:
                if not self._package.acquire(exclusive=True):
                    return _refusal(
                        "another controlled host or updater is using this package",
                        "close active host sessions and retry; no package change started",
                        stage="update-lock",
                    )
                self._stack.callback(self._package.close)
            acquired = self._stack.enter_context(
                registry.exclusive(UPDATE_LOCK_WAIT_SECONDS)
            )
        except OSError as exc:
            return _refusal(
                f"the global update lock {registry.lock_file} cannot be opened: {exc}",
                f"repair the selected agents home's .nwave/activity directory, then retry; {_NO_CHANGE}",
                stage="update-lock",
            )
        if not acquired:
            return _refusal(
                f"another update or a session registration holds {registry.lock_file}",
                (
                    "wait for the other update to finish, then retry; the OS releases the "
                    f"lock when its holder exits; {_NO_CHANGE}"
                ),
                stage="update-lock",
            )
        if self._automatic_session is None:
            self._ready = True
            return None
        registration = self._automatic_session
        registries = (registry, self._package.registry)
        for current in registries:
            if not registration.belongs_to(current):
                return _refusal(
                    "the controlled caller does not own its registered identity",
                    "restart using nwave-ai run HOST -- ARGS",
                )
            verdict = current.evaluate_idle(
                own_key=registration.key,
                require_legacy_confirmation=current is registry
                and not self._check_only,
            )
            if not isinstance(verdict, Idle):
                return _refusal(
                    f"global idle is not established: {verdict.reason}",
                    f"{verdict.recovery}; {_NO_CHANGE}",
                )
        from nwave_ai.update.startup import _idle_root

        root, reason = _idle_root(Path.cwd())
        if root is None:
            return _refusal(
                f"the project idle state is not established: {reason}",
                "finish or recover its work before automatic installation",
            )
        self._ready = True
        return None
