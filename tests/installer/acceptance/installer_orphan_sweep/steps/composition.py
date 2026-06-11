"""Composition root for installer-orphan-sweep slice-01 acceptance tests.

Drives the REAL public install path for the DES scripts family —
``DESPlugin.install(InstallContext)`` — against a fabricated current-version
framework source and a real target filesystem under ``tmp_path``
(Driving-Port-Only Boundary mandate; Pillar 3: only the diagnostics logger is
captured, every filesystem effect is real).

All slice business logic (expected-delta computation, universe capture) lives
HERE as the single source of truth; step bodies in
``test_des_script_manifest.py`` delegate one call each
(SSOT-via-Types-Services-DSL mandate, criterion 3).

Universe (Mandate 8, layer 3 — port-exposed observables only):

- ``scripts.files``             — non-hidden file names in the target scripts dir
- ``manifest.tracked_scripts``  — names tracked by the shared manifest
  mechanism (``scripts.shared.skill_distribution.read_manifest``), or None
- ``personal_script.content``   — content of the user's personal script, or None
- ``preserve_warnings.count``   — diagnostics-port warnings about preserved /
  unrecorded scripts (logger records + plugin result message)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from nwave_ai.state_delta import assert_state_delta, set_to

from scripts.install.plugins.base import InstallContext
from scripts.install.plugins.des_plugin import DESPlugin
from scripts.shared.skill_distribution import read_manifest, write_manifest

from .domain_types import ScriptName, TargetEra


_UNIVERSE = {
    "scripts.files",
    "manifest.tracked_scripts",
    "personal_script.content",
    "preserve_warnings.count",
}


def at_least(n: int):
    """State-delta predicate: the new value is >= n (old value ignored)."""

    def _predicate(old: Any, new: Any) -> bool:
        return isinstance(new, int) and new >= n

    return _predicate


class _CapturingHandler(logging.Handler):
    """Captures log records emitted through the injected diagnostics logger."""

    def __init__(self) -> None:
        super().__init__(level=logging.DEBUG)
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


class ScriptsUpgradeJourney:
    """One user journey: a target machine, one run of the real installer."""

    def __init__(self, tmp_path: Path) -> None:
        self._tmp = tmp_path
        self._framework_source = self._build_current_version_source(tmp_path)
        self._claude_dir = tmp_path / ".claude"
        self._claude_dir.mkdir(parents=True, exist_ok=True)
        self._scripts_target = self._claude_dir / "scripts"
        self._log_capture = _CapturingHandler()
        self._logger = logging.getLogger(f"at.installer-orphan-sweep.{id(self)}")
        self._logger.setLevel(logging.DEBUG)
        self._logger.handlers = [self._log_capture]
        self._logger.propagate = False
        self._seeded_scripts: list[ScriptName] = []
        self._personal_script: ScriptName | None = None
        self._before: dict[str, Any] | None = None
        self._after: dict[str, Any] | None = None
        self._result = None

    # -- Given services ------------------------------------------------------

    def given_target(self, era: TargetEra) -> None:
        """Shape the pre-existing target installation per the declared era."""
        if era is TargetEra.NEVER_INSTALLED:
            return
        self._scripts_target.mkdir(parents=True, exist_ok=True)
        for name in DESPlugin.DES_SCRIPTS:
            self._write_script(ScriptName(name), "# shipped by the previous version\n")
        if era is TargetEra.MANIFEST_TRACKED:
            write_manifest(self._scripts_target, list(self._seeded_scripts))

    def given_previously_installed_script(self, name: ScriptName) -> None:
        """A script the PREVIOUS version installed and tracked in its manifest."""
        self._write_script(name, "# retired: shipped only by the previous version\n")
        write_manifest(self._scripts_target, list(self._seeded_scripts))

    def given_personal_script(self, name: ScriptName) -> None:
        """A user-created script the framework never installed nor tracked."""
        self._scripts_target.mkdir(parents=True, exist_ok=True)
        path = self._scripts_target / name
        path.write_text("# personal tool — the installer must never touch this\n")
        self._personal_script = name

    # -- When service ----------------------------------------------------------

    def run_installer(self) -> None:
        """Drive the real driving port: DESPlugin.install(InstallContext)."""
        context = InstallContext(
            claude_dir=self._claude_dir,
            scripts_dir=Path("scripts/install"),
            templates_dir=self._framework_source / "templates",
            logger=self._logger,
            project_root=self._tmp,
            framework_source=self._framework_source,
            dry_run=False,
            dev_mode=True,
        )
        self._before = self._capture_universe()
        self._result = DESPlugin().install(context)
        self._after = self._capture_universe()
        assert self._result.success, (
            f"the installer reported failure: {self._result.message} "
            f"(errors: {self._result.errors})"
        )

    # -- Then services ---------------------------------------------------------

    def assert_current_scripts_installed(self) -> None:
        missing = set(DESPlugin.DES_SCRIPTS) - self._after["scripts.files"]
        assert not missing, (
            f"current-version DES scripts missing after install: {sorted(missing)}; "
            f"present: {sorted(self._after['scripts.files'])}"
        )

    def assert_script_absent(self, name: ScriptName) -> None:
        assert name not in self._after["scripts.files"], (
            f"script {name!r} was retired from the source but still exists in "
            f"the target after upgrade (orphan) — installed files: "
            f"{sorted(self._after['scripts.files'])}"
        )

    def assert_personal_script_preserved(self) -> None:
        assert self._after["personal_script.content"] == (
            "# personal tool — the installer must never touch this\n"
        ), (
            f"personal script {self._personal_script!r} was deleted or modified "
            f"by the upgrade — preserve-by-default is a hard contract"
        )

    def assert_preserve_warning_surfaced(self) -> None:
        assert self._after["preserve_warnings.count"] >= 1, (
            "no warning surfaced about preserving scripts from a manifest-less "
            "(pre-record) installation — the user must be told, not left guessing"
        )

    def assert_contract_holds(self) -> None:
        """Universe-bound contract: exactly the declared delta, nothing else."""
        assert_state_delta(
            before=self._before,
            after=self._after,
            universe=_UNIVERSE,
            expected=self._expected_delta(),
        )

    # -- internals -------------------------------------------------------------

    def _expected_delta(self) -> dict[str, Any]:
        before_files: frozenset[str] = self._before["scripts.files"]
        before_tracked = self._before["manifest.tracked_scripts"]
        if before_tracked is None:
            # Preserve-by-default: without a manifest nothing may be deleted.
            preserved = before_files
        else:
            preserved = before_files - before_tracked
        expected: dict[str, Any] = {
            "scripts.files": set_to(frozenset(DESPlugin.DES_SCRIPTS) | preserved),
            "manifest.tracked_scripts": set_to(frozenset(DESPlugin.DES_SCRIPTS)),
        }
        if before_files and before_tracked is None:
            expected["preserve_warnings.count"] = at_least(1)
        # personal_script.content carries no predicate: implicit-unchanged,
        # fail-closed (Mandate 8) — any mutation of the user's file is a violation.
        return expected

    def _capture_universe(self) -> dict[str, Any]:
        if self._scripts_target.exists():
            files = frozenset(
                p.name
                for p in self._scripts_target.iterdir()
                if p.is_file() and not p.name.startswith(".")
            )
        else:
            files = frozenset()
        manifest = read_manifest(self._scripts_target)
        tracked = self._tracked_names(manifest) if manifest else None
        personal = None
        if self._personal_script is not None:
            path = self._scripts_target / self._personal_script
            personal = path.read_text() if path.exists() else None
        return {
            "scripts.files": files,
            "manifest.tracked_scripts": tracked,
            "personal_script.content": personal,
            "preserve_warnings.count": self._count_preserve_warnings(),
        }

    @staticmethod
    def _tracked_names(manifest: dict) -> frozenset[str]:
        """All names tracked by the manifest, key-name agnostic.

        The slice constraint is ONE manifest format (the shared
        ``.nwave-manifest.json`` mechanism); the concrete list key for the
        scripts family is a GREEN-phase design decision, so the oracle
        accepts any list-of-strings value in the manifest document.
        """
        names: set[str] = set()
        for value in manifest.values():
            if isinstance(value, list):
                names.update(v for v in value if isinstance(v, str))
        return frozenset(names)

    def _count_preserve_warnings(self) -> int:
        def _matches(text: str) -> bool:
            lower = text.lower()
            return "script" in lower and ("preserv" in lower or "manifest" in lower)

        count = sum(
            1
            for record in self._log_capture.records
            if record.levelno >= logging.WARNING and _matches(record.getMessage())
        )
        if self._result is not None and _matches(self._result.message):
            count += 1
        return count

    def _write_script(self, name: ScriptName, content: str) -> None:
        self._scripts_target.mkdir(parents=True, exist_ok=True)
        (self._scripts_target / name).write_text(content)
        if name not in self._seeded_scripts:
            self._seeded_scripts.append(name)

    def _build_current_version_source(self, tmp_path: Path) -> Path:
        """Fabricate the current-version framework source tree in tmp_path.

        Satisfies DESPlugin.validate_prerequisites (scripts + shims +
        templates) and provides a pre-built lib/python/des module so the
        whole public install path runs without touching the repo tree.
        """
        framework = tmp_path / "nWave"
        des_scripts = framework / "scripts" / "des"
        des_scripts.mkdir(parents=True)
        for script in DESPlugin.DES_SCRIPTS:
            (des_scripts / script).write_text("#!/usr/bin/env python3\n# current\n")
        for shim in DESPlugin.DES_SHIMS:
            (des_scripts / shim).write_text("#!/bin/sh\n")
        templates = framework / "templates"
        templates.mkdir(parents=True)
        for template in DESPlugin.DES_TEMPLATES:
            (templates / template).write_text("# template\n")
        prebuilt = framework / "lib" / "python" / "des"
        prebuilt.mkdir(parents=True)
        (prebuilt / "__init__.py").write_text("")
        return framework
