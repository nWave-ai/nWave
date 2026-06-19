"""Composition root for installer-orphan-sweep slice-02 acceptance tests.

Drives the REAL plugin pipeline for the asset families that share a target
directory under ``~/.claude`` — ``PluginRegistry.install_all(InstallContext)``
with the three family-owner plugins registered (templates, utilities, des) in
production dependency order (Driving-Port-Only Boundary mandate; Pillar 3:
only the diagnostics logger is captured, every filesystem effect is real).

Era state machine (C2a — drives the slice-02 contract per family):

- family MANIFEST-TRACKED  → tracked names absent from the new source are
  swept; anything the family's manifest does not record is preserved.
- family PRE-RECORD        → adoption run: nothing foreign is deleted, the
  user is warned about preserved unrecorded files, records start being kept.
- family NEVER-INSTALLED   → fresh target: install + record, zero warnings.

All slice business logic (seeding, expected-delta computation, universe
capture) lives HERE as the single source of truth; step bodies in
``test_runtime_asset_sweep.py`` delegate one call each
(SSOT-via-Types-Services-DSL mandate, criterion 3).

Universe (Mandate 8, layer 3 — port-exposed observables only):

- ``runtime_assets.entries``    — top-level non-hidden names in the target
  templates directory (the runtime-asset family)
- ``runtime_assets.tracked``    — names tracked by the family manifest
  (shared ``.nwave-manifest.json`` mechanism), or None
- ``user_template.content``     — content of the user's own template, or None
- ``scripts.files``             — non-hidden file names in the target scripts dir
- ``scripts.tracked``           — names tracked by the scripts-dir manifest, or None
- ``personal_script.content``   — content of the user's personal script, or None
- ``preserve_warnings.count``   — diagnostics-port warnings about preserved /
  unrecorded files (logger records + plugin result messages)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from nwave_ai.state_delta import assert_state_delta, set_to

from scripts.install.plugins.base import InstallContext
from scripts.install.plugins.des_plugin import DESPlugin
from scripts.install.plugins.registry import PluginRegistry
from scripts.install.plugins.templates_plugin import TemplatesPlugin
from scripts.install.plugins.utilities_plugin import UtilitiesPlugin
from scripts.shared.skill_distribution import read_manifest, write_manifest

from .composition import at_least
from .domain_types import (
    CURRENT_ASSET_DIR,
    UTILITY_SCRIPTS,
    ScriptName,
    TargetEra,
    TemplateName,
)


_UNIVERSE = {
    "runtime_assets.entries",
    "runtime_assets.tracked",
    "user_template.content",
    "scripts.files",
    "scripts.tracked",
    "personal_script.content",
    "preserve_warnings.count",
}

#: The shared record file (one manifest format per feature constraint) is
#: bookkeeping, never an asset — mirrors skill_distribution._MANIFEST_FILENAME.
_MANIFEST_BOOKKEEPING_FILE = ".nwave-manifest.json"

_USER_TEMPLATE_CONTENT = (
    "# the team's own template — the installer must never touch this\n"
)
_PERSONAL_SCRIPT_CONTENT = "# personal tool — the installer must never touch this\n"


class _CapturingHandler(logging.Handler):
    """Captures log records emitted through the injected diagnostics logger."""

    def __init__(self) -> None:
        super().__init__(level=logging.DEBUG)
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


class FamiliesUpgradeJourney:
    """One user journey: a target machine, one run of the real plugin pipeline.

    Duck-type contract with the slice-01 step vocabulary
    (``test_des_script_manifest.py`` imports re-bound here): implements
    ``given_target``, ``given_personal_script``, ``run_installer``,
    ``assert_personal_script_preserved``, ``assert_preserve_warning_surfaced``.
    """

    def __init__(self, tmp_path: Path) -> None:
        self._tmp = tmp_path
        self._framework_source = self._build_current_version_source(tmp_path)
        self._claude_dir = tmp_path / ".claude"
        self._claude_dir.mkdir(parents=True, exist_ok=True)
        self._scripts_target = self._claude_dir / "scripts"
        self._templates_target = self._claude_dir / "templates"
        self._log_capture = _CapturingHandler()
        self._logger = logging.getLogger(f"at.installer-orphan-sweep.s02.{id(self)}")
        self._logger.setLevel(logging.DEBUG)
        self._logger.handlers = [self._log_capture]
        self._logger.propagate = False
        self._seeded_assets: list[TemplateName] = []
        self._personal_script: ScriptName | None = None
        self._user_template: TemplateName | None = None
        self._before: dict[str, Any] | None = None
        self._after: dict[str, Any] | None = None
        self._results: dict[str, Any] | None = None

    # -- Given services --------------------------------------------------------

    def given_target(self, era: TargetEra) -> None:
        """Shape the pre-existing scripts-family target per the declared era.

        ``MANIFEST_TRACKED`` reproduces the realistic prior-version state the
        shipped slice-01 production leaves behind: DES scripts recorded under
        the ``installed_scripts`` family key, utility scripts on disk but not
        yet recorded by any family.
        """
        if era is TargetEra.NEVER_INSTALLED:
            return
        self._scripts_target.mkdir(parents=True, exist_ok=True)
        for name in [*DESPlugin.DES_SCRIPTS, *UTILITY_SCRIPTS]:
            (self._scripts_target / name).write_text(
                "# shipped by the previous version\n"
            )
        if era is TargetEra.MANIFEST_TRACKED:
            write_manifest(
                self._scripts_target,
                list(DESPlugin.DES_SCRIPTS),
                key="installed_scripts",
            )

    def given_personal_script(self, name: ScriptName) -> None:
        """A user-created script the framework never installed nor tracked."""
        self._scripts_target.mkdir(parents=True, exist_ok=True)
        (self._scripts_target / name).write_text(_PERSONAL_SCRIPT_CONTENT)
        self._personal_script = name

    def given_runtime_assets_tracked(self) -> None:
        """The previous version installed the runtime assets, with a manifest.

        Seeds the current-version asset set (the upgrade re-ships it) and a
        family manifest written through the shared mechanism. Seeding uses the
        default v1.0 manifest key, so the backward-compatible key-agnostic
        read constraint is exercised, not just documented (slice-01 precedent).
        """
        self._templates_target.mkdir(parents=True, exist_ok=True)
        for name in DESPlugin.DES_TEMPLATES:
            (self._templates_target / name).write_text(
                "# shipped by the previous version\n"
            )
            self._record_seeded_asset(TemplateName(name))
        self._seed_asset_dir(TemplateName(CURRENT_ASSET_DIR))
        write_manifest(self._templates_target, list(self._seeded_assets))

    def given_retired_asset_dir(self, name: TemplateName) -> None:
        """A runtime-asset folder the previous version installed and tracked."""
        self._seed_asset_dir(name)
        write_manifest(self._templates_target, list(self._seeded_assets))

    def given_user_template(self, name: TemplateName) -> None:
        """A user-created template the framework never installed nor tracked."""
        self._templates_target.mkdir(parents=True, exist_ok=True)
        (self._templates_target / name).write_text(_USER_TEMPLATE_CONTENT)
        self._user_template = name

    # -- When service ------------------------------------------------------------

    def run_installer(self) -> None:
        """Drive the real driving port: the plugin pipeline in registry order."""
        registry = PluginRegistry(logger=self._logger)
        registry.register(TemplatesPlugin())
        registry.register(UtilitiesPlugin())
        registry.register(DESPlugin())
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
        self._results = registry.install_all(context)
        self._after = self._capture_universe()
        failed = {
            name: result.message
            for name, result in self._results.items()
            if not result.success
        }
        assert not failed, f"the installer pipeline reported failures: {failed}"

    # -- Then services -----------------------------------------------------------

    def assert_retired_asset_swept(self, name: TemplateName) -> None:
        assert name not in self._after["runtime_assets.entries"], (
            f"runtime asset {name!r} was retired from the source but still "
            f"exists in the target after upgrade (orphan) — installed assets: "
            f"{sorted(self._after['runtime_assets.entries'])}"
        )

    def assert_current_assets_installed(self) -> None:
        missing = self._current_assets() - self._after["runtime_assets.entries"]
        assert not missing, (
            f"current-version runtime assets missing after install: "
            f"{sorted(missing)}; present: "
            f"{sorted(self._after['runtime_assets.entries'])}"
        )

    def assert_user_template_preserved(self) -> None:
        assert self._after["user_template.content"] == _USER_TEMPLATE_CONTENT, (
            f"user-created template {self._user_template!r} was deleted or "
            f"modified by the upgrade — preserve-by-default is a hard contract"
        )

    def assert_personal_script_preserved(self) -> None:
        assert self._after["personal_script.content"] == _PERSONAL_SCRIPT_CONTENT, (
            f"personal script {self._personal_script!r} was deleted or modified "
            f"by the upgrade — preserve-by-default is a hard contract"
        )

    def assert_preserve_warning_surfaced(self) -> None:
        assert self._after["preserve_warnings.count"] >= 1, (
            "no warning surfaced about preserving unrecorded files — the user "
            "must be told, not left guessing"
        )

    def assert_contract_holds(self) -> None:
        """Universe-bound contract: exactly the declared delta, nothing else."""
        assert_state_delta(
            before=self._before,
            after=self._after,
            universe=_UNIVERSE,
            expected=self._expected_delta(),
        )

    # -- internals ----------------------------------------------------------------

    @staticmethod
    def _current_assets() -> frozenset[str]:
        return frozenset({*DESPlugin.DES_TEMPLATES, CURRENT_ASSET_DIR})

    @staticmethod
    def _framework_scripts() -> frozenset[str]:
        return frozenset(DESPlugin.DES_SCRIPTS) | frozenset(UTILITY_SCRIPTS)

    def _expected_delta(self) -> dict[str, Any]:
        before = self._before
        preserved_assets = self._preserved(
            before["runtime_assets.entries"], before["runtime_assets.tracked"]
        )
        preserved_scripts = self._preserved(
            before["scripts.files"], before["scripts.tracked"]
        )
        expected: dict[str, Any] = {
            "runtime_assets.entries": set_to(self._current_assets() | preserved_assets),
            "runtime_assets.tracked": set_to(self._current_assets()),
            "scripts.files": set_to(self._framework_scripts() | preserved_scripts),
            "scripts.tracked": set_to(self._framework_scripts()),
        }
        foreign_scripts = preserved_scripts - self._framework_scripts()
        if foreign_scripts:
            # Family-adoption run with unrecorded user files: preserve + warn
            # (the slice-01 fail-safe contract, applied per family).
            expected["preserve_warnings.count"] = at_least(1)
        # user_template.content / personal_script.content carry no predicate:
        # implicit-unchanged, fail-closed (Mandate 8) — any mutation of a
        # user's file is a violation. preserve_warnings stays 0 (fail-closed)
        # whenever every file on disk is accounted for.
        return expected

    @staticmethod
    def _preserved(
        before_names: frozenset[str], tracked: frozenset[str] | None
    ) -> frozenset[str]:
        if tracked is None:
            # Preserve-by-default: without a record nothing may be deleted.
            return before_names
        return before_names - tracked

    def _capture_universe(self) -> dict[str, Any]:
        return {
            "runtime_assets.entries": self._visible_entries(self._templates_target),
            "runtime_assets.tracked": self._tracked_names(self._templates_target),
            "user_template.content": self._content(
                self._templates_target, self._user_template
            ),
            "scripts.files": self._visible_entries(self._scripts_target),
            "scripts.tracked": self._tracked_names(self._scripts_target),
            "personal_script.content": self._content(
                self._scripts_target, self._personal_script
            ),
            "preserve_warnings.count": self._count_preserve_warnings(),
        }

    @staticmethod
    def _visible_entries(target: Path) -> frozenset[str]:
        """Asset names in the target dir — everything except the record file.

        Dot-prefixed FRAMEWORK assets count (two DES templates are dotfiles);
        only the manifest bookkeeping file itself is not an asset.
        """
        if not target.exists():
            return frozenset()
        return frozenset(
            p.name for p in target.iterdir() if p.name != _MANIFEST_BOOKKEEPING_FILE
        )

    @staticmethod
    def _tracked_names(target: Path) -> frozenset[str] | None:
        """All names tracked by the directory's manifest, key-name agnostic.

        ONE manifest format (shared ``.nwave-manifest.json`` mechanism); the
        concrete family keys are a GREEN-phase design decision, so the oracle
        accepts every list-of-strings value in the manifest document.
        """
        manifest = read_manifest(target)
        if not manifest:
            return None
        names: set[str] = set()
        for value in manifest.values():
            if isinstance(value, list):
                names.update(v for v in value if isinstance(v, str))
        return frozenset(names)

    @staticmethod
    def _content(target: Path, name: str | None) -> str | None:
        if name is None:
            return None
        path = target / name
        return path.read_text() if path.exists() else None

    def _count_preserve_warnings(self) -> int:
        def _matches(text: str) -> bool:
            lower = text.lower()
            return ("preserv" in lower or "unrecorded" in lower) or (
                "manifest" in lower and "no" in lower
            )

        count = sum(
            1
            for record in self._log_capture.records
            if record.levelno >= logging.WARNING and _matches(record.getMessage())
        )
        if self._results:
            count += sum(
                1 for result in self._results.values() if _matches(result.message)
            )
        return count

    def _record_seeded_asset(self, name: TemplateName) -> None:
        if name not in self._seeded_assets:
            self._seeded_assets.append(name)

    def _seed_asset_dir(self, name: TemplateName) -> None:
        asset_dir = self._templates_target / name
        asset_dir.mkdir(parents=True, exist_ok=True)
        (asset_dir / "asset.json").write_text("{}\n")
        self._record_seeded_asset(name)

    def _build_current_version_source(self, tmp_path: Path) -> Path:
        """Fabricate the current-version framework source tree in tmp_path.

        Extends the slice-01 recipe with the utilities-family script sources
        and the current runtime-asset folder, so the whole three-plugin
        pipeline runs without touching the repo tree.
        """
        framework = tmp_path / "nWave"
        des_scripts = framework / "scripts" / "des"
        des_scripts.mkdir(parents=True)
        for script in DESPlugin.DES_SCRIPTS:
            (des_scripts / script).write_text("#!/usr/bin/env python3\n# current\n")
        for shim in DESPlugin.DES_SHIMS:
            (des_scripts / shim).write_text("#!/bin/sh\n")
        for utility in UTILITY_SCRIPTS:
            (framework / "scripts" / utility).write_text('__version__ = "99.0.0"\n')
        templates = framework / "templates"
        templates.mkdir(parents=True)
        for template in DESPlugin.DES_TEMPLATES:
            (templates / template).write_text("# template\n")
        current_asset = templates / CURRENT_ASSET_DIR
        current_asset.mkdir(parents=True)
        (current_asset / "asset.json").write_text("{}\n")
        prebuilt = framework / "lib" / "python" / "des"
        prebuilt.mkdir(parents=True)
        (prebuilt / "__init__.py").write_text("")
        return framework
