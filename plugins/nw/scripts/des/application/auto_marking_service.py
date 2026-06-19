"""Silent auto-marking application service (ADR-AG-003).

Reads the per-project marker via ``DESConfig``; if ``enabled_for_repo`` is
explicitly present (true OR false) it is a no-op (sticky in both directions);
else if the trigger's evidence predicate holds it writes
``{"enabled_for_repo": true}`` then fixes both gitignore layers. Bounded-change
mutation set: ``{.nwave/local-config.json, .nwave/.gitignore, <root>/.gitignore}``.
Fail-open: a read-only / unwritable filesystem never raises.

The return value is the production-side ``AdoptionOutcome`` enum. The acceptance
composition adapts it to the test-domain ``AdoptionResult`` at the boundary
(production never imports test types).
"""

from __future__ import annotations

import json
import os
from enum import Enum
from pathlib import Path


class AdoptionTrigger(Enum):
    """Which auto-marking trigger fired (DDD-7)."""

    PRIOR_USE = "prior-use"  # Trigger 1, SessionStart
    REAL_FEATURE_USE = "real-feature-use"  # Trigger 2, pre-task nw-* dispatch


class AdoptionOutcome(Enum):
    """Outcome of ``adopt_if_warranted`` (ADR-AG-003)."""

    ADOPTED = "adopted"  # marker written
    NOT_WARRANTED = "not-warranted"  # no evidence -> no write
    NO_OP_STICKY = "no-op-sticky"  # marker already present (any value) -> no write


_MARKER_RELATIVE = Path(".nwave") / "local-config.json"


class AutoMarkingService:
    """Writes the marker + fixes gitignore behind a sticky guard."""

    def __init__(self, *, read_only: bool = False) -> None:
        self._read_only = read_only

    def adopt_if_warranted(
        self, *, project_root: Path, trigger: AdoptionTrigger
    ) -> AdoptionOutcome:
        """Adopt the project if the trigger's evidence warrants it.

        Returns ADOPTED / NOT_WARRANTED / NO_OP_STICKY. Never raises on a
        read-only filesystem (fail-open).
        """
        if self._marker_present(project_root):
            return AdoptionOutcome.NO_OP_STICKY
        if not self._evidence_warrants(project_root, trigger):
            return AdoptionOutcome.NOT_WARRANTED
        if not self._write_marker(project_root):
            return AdoptionOutcome.NOT_WARRANTED
        self.fix_gitignore(project_root=project_root)
        return AdoptionOutcome.ADOPTED

    def fix_gitignore(self, *, project_root: Path) -> None:
        """Apply the dual-layer gitignore fix idempotently (ADR-AG-004)."""
        if self._read_only:
            return
        self._fix_root_gitignore(project_root)
        self._fix_nested_gitignore(project_root)

    # ---- guards + evidence ----

    def _marker_present(self, project_root: Path) -> bool:
        """Whether ``enabled_for_repo`` is explicitly present (sticky guard)."""
        from des.adapters.driven.config.des_config import DESConfig

        return DESConfig(cwd=project_root).enabled_for_repo is not None

    def _evidence_warrants(self, project_root: Path, trigger: AdoptionTrigger) -> bool:
        if trigger is AdoptionTrigger.REAL_FEATURE_USE:
            return True
        return self._has_prior_use(project_root)

    def _has_prior_use(self, project_root: Path) -> bool:
        """Trigger-1 prior-use predicate (DDD-8; OQ-3 corrected audit-log path)."""
        if self._audit_log_nonempty(project_root):
            return True
        feature_dir = project_root / "docs" / "feature"
        return (
            any(feature_dir.glob("*/execution-log.json"))
            or any(feature_dir.glob("*/feature-delta.md"))
            or any(p.is_dir() for p in feature_dir.glob("*/deliver"))
        )

    def _audit_log_nonempty(self, project_root: Path) -> bool:
        """Non-empty ``<audit_dir>/audit-*.log`` (honors env / des-config override)."""
        for logs_dir in self._audit_log_dirs(project_root):
            for log in logs_dir.glob("audit-*.log"):
                try:
                    if log.stat().st_size > 0:
                        return True
                except OSError:
                    continue
        return False

    def _audit_log_dirs(self, project_root: Path) -> list[Path]:
        """Candidate audit-log dirs: env override, des-config override, default."""

        candidates: list[Path] = []
        env_dir = os.environ.get("DES_AUDIT_LOG_DIR")
        if env_dir:
            candidates.append(Path(env_dir))
        configured = self._configured_audit_dir(project_root)
        if configured is not None:
            candidates.append(configured)
        candidates.append(project_root / ".nwave" / "des" / "logs")
        return candidates

    def _configured_audit_dir(self, project_root: Path) -> Path | None:
        des_config = project_root / ".nwave" / "des-config.json"
        try:
            data = json.loads(des_config.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
        # Valid non-dict JSON (``null``, ``[]``, ``123``) would crash ``.get``;
        # its ``except`` only catches parse/IO errors, not a wrong-shaped value.
        if not isinstance(data, dict):
            return None
        configured = data.get("audit_log_dir")
        if not configured:
            return None
        path = Path(configured)
        return path if path.is_absolute() else project_root / path

    # ---- writes (fail-open) ----

    def _write_marker(self, project_root: Path) -> bool:
        """Write the trackable marker; return False on a write failure (fail-open)."""
        if self._read_only:
            return False
        marker = project_root / _MARKER_RELATIVE
        try:
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.write_text(
                json.dumps({"enabled_for_repo": True}, indent=2) + "\n",
                encoding="utf-8",
            )
        except OSError:
            return False
        return True

    def _fix_root_gitignore(self, project_root: Path) -> None:
        from des.domain.root_gitignore_fix import fix_root_gitignore

        path = project_root / ".gitignore"
        try:
            current = path.read_text(encoding="utf-8") if path.exists() else ""
            fixed = fix_root_gitignore(current)
            if fixed != current:
                path.write_text(fixed, encoding="utf-8")
        except OSError:
            return

    def _fix_nested_gitignore(self, project_root: Path) -> None:
        """Repair the nested ignore via the shared single-source-of-truth helper.

        Delegates to ``ensure_nwave_gitignore`` (the EXTEND verdict): both nested
        writers now emit identical canonical content (banner + ``*`` +
        ``!local-config.json``), so a later runtime ``ensure_nwave_gitignore`` call can
        never re-ignore the marker. User-customized (non-banner) files are left
        untouched by the shared helper.
        """
        from des.domain.nwave_dir_gitignore import ensure_nwave_gitignore

        nested = project_root / ".nwave"
        ensure_nwave_gitignore(nested)
