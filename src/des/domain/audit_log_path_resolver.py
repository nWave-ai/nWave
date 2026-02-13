"""AuditLogPathResolver - shared path resolution for audit logs.

Single source of truth for audit log directory resolution, used by both
JsonlAuditLogWriter and JsonlAuditLogReader to prevent path divergence.

Priority (highest to lowest):
1. Explicit log_dir parameter
2. DES_AUDIT_LOG_DIR environment variable
3. .nwave/des-config.json audit_log_dir field
4. Project-local .nwave/des/logs/ (using cwd or Path.cwd())
5. Global ~/.claude/des/logs/ (fallback)
"""

from __future__ import annotations

import json
import os
from pathlib import Path


class AuditLogPathResolver:
    """Resolves audit log directory path deterministically."""

    def __init__(
        self,
        log_dir: str | Path | None = None,
        cwd: str | Path | None = None,
    ) -> None:
        """Initialize resolver.

        Args:
            log_dir: Explicit log directory (highest priority)
            cwd: Working directory override (for hook context where
                 Path.cwd() may be non-deterministic)
        """
        self._explicit_dir = Path(log_dir) if log_dir else None
        self._cwd = Path(cwd) if cwd else None

    def resolve(self) -> Path:
        """Resolve audit log directory path.

        Returns:
            Path to audit log directory
        """
        # Priority 1: Explicit parameter
        if self._explicit_dir:
            return self._explicit_dir

        # Priority 2: Environment variable
        env_dir = os.environ.get("DES_AUDIT_LOG_DIR")
        if env_dir:
            return Path(env_dir)

        # Priority 3: Config file
        effective_cwd = self._cwd or Path.cwd()
        config_dir = self._resolve_config_dir(effective_cwd)
        if config_dir:
            return config_dir

        # Priority 4: Project-local
        home = Path.home()
        if effective_cwd != home and str(effective_cwd) not in (
            "/",
            "/usr",
            "/bin",
            "/etc",
            "/var",
            "/tmp",
        ):
            return effective_cwd / ".nwave" / "des" / "logs"

        # Priority 5: Global fallback
        return home / ".claude" / "des" / "logs"

    @staticmethod
    def _resolve_config_dir(cwd: Path) -> Path | None:
        """Read audit_log_dir from .nwave/des-config.json if it exists."""
        config_file = cwd / ".nwave" / "des-config.json"
        if config_file.exists():
            try:
                config = json.loads(config_file.read_text(encoding="utf-8"))
                audit_dir = config.get("audit_log_dir")
                if audit_dir:
                    return Path(audit_dir)
            except (json.JSONDecodeError, OSError):
                pass
        return None
