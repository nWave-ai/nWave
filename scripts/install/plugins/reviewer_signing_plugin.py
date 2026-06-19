"""Reviewer signing-key provisioning plugin (friction-fix F-01).

docs/analysis/atdd-pure-dogfooding-friction-2026-05-20.md F-01: the ATDD-pure
AT-review HMAC signing key (``NWAVE_REVIEWER_SIGNING_KEY`` env /
``.nwave/secrets/reviewer-signing.key`` file) had no provisioning path. This
plugin provisions a per-project key at install time -- idempotent (never
overwrites an existing key), skipped when the env var is set, mode 0600 on
POSIX. The ``.nwave/`` directory is already gitignored, so the key never
enters version control.
"""

from __future__ import annotations

import os
import secrets
from pathlib import Path

from scripts.install.plugins.base import (
    InstallationPlugin,
    InstallContext,
    PluginResult,
)


_SIGNING_KEY_ENV = "NWAVE_REVIEWER_SIGNING_KEY"
_KEY_RELPATH = Path(".nwave") / "secrets" / "reviewer-signing.key"
_KEY_MODE = 0o600


class ReviewerSigningPlugin(InstallationPlugin):
    """Provisions the per-project AT-review reviewer signing key."""

    def __init__(self) -> None:
        super().__init__(name="reviewer_signing", priority=110)

    def _key_file(self, context: InstallContext) -> Path:
        root = context.project_root or Path.cwd()
        return root / _KEY_RELPATH

    def install(self, context: InstallContext) -> PluginResult:
        """Provision the reviewer signing key when absent.

        Idempotent: an existing key file is never overwritten. When
        ``NWAVE_REVIEWER_SIGNING_KEY`` is set, no file is provisioned -- the
        env var takes precedence as the key source.
        """
        key_file = self._key_file(context)

        if os.environ.get(_SIGNING_KEY_ENV):
            return PluginResult(
                success=True,
                plugin_name=self.name,
                message=(
                    "Reviewer signing key sourced from "
                    f"{_SIGNING_KEY_ENV}; no key file provisioned."
                ),
            )

        if key_file.is_file():
            return PluginResult(
                success=True,
                plugin_name=self.name,
                message=(
                    "Reviewer signing key already present at "
                    f"{_KEY_RELPATH}; left unchanged."
                ),
            )

        try:
            key_file.parent.mkdir(parents=True, exist_ok=True)
            key_file.write_text(secrets.token_hex(32), encoding="utf-8")
            if os.name == "posix":
                key_file.chmod(_KEY_MODE)
        except OSError as e:
            # EROFS, EACCES, ENOSPC, etc. — project dir not writable.
            # Mirrors DES config plugin (des_plugin.py:754) soft-skip: the
            # installer succeeds; operator can later set NWAVE_REVIEWER_SIGNING_KEY
            # env var or provision the file when the dir is writable. Without
            # this fallback the install hard-errors (issue surfaced by v3.16.0rc4
            # e2e validation on read-only /src container mount).
            return PluginResult(
                success=True,
                plugin_name=self.name,
                message=(
                    f"Reviewer signing key skipped (read-only project dir): {e}. "
                    f"Set {_SIGNING_KEY_ENV} env var, or provision "
                    f"{_KEY_RELPATH} when the project dir is writable."
                ),
            )
        return PluginResult(
            success=True,
            plugin_name=self.name,
            message=f"Reviewer signing key generated at {_KEY_RELPATH}.",
            installed_files=[key_file],
        )

    def verify(self, context: InstallContext) -> PluginResult:
        """Report the provisioned/present/env state of the signing key."""
        if os.environ.get(_SIGNING_KEY_ENV):
            return PluginResult(
                success=True,
                plugin_name=self.name,
                message=(f"Reviewer signing key provided via {_SIGNING_KEY_ENV}."),
            )
        key_file = self._key_file(context)
        if key_file.is_file():
            return PluginResult(
                success=True,
                plugin_name=self.name,
                message=f"Reviewer signing key present at {_KEY_RELPATH}.",
            )
        return PluginResult(
            success=True,
            plugin_name=self.name,
            message="Reviewer signing key not configured (optional).",
        )
