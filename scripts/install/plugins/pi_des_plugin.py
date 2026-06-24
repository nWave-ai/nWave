"""Plugin for installing the nWave DES TypeScript extension into the pi agent.

pi (pi.dev, the @earendil-works/pi-coding-agent) loads extensions from a config
dir (default ``~/.pi/agent``, overridable via ``PI_CONFIG_DIR``). This plugin
renders ``nWave/templates/pi-des-extension.ts.template`` (placeholders ->
resolved python + DES lib path via ``install_paths`` resolvers) into that dir and
writes ``.nwave-des-manifest.json`` for clean uninstall. All enforcement logic
lives in the reused Python DES engine (``src/des/**``) -- this extension is a
protocol translator only (zero adapter fork; mirrors the OpenCode shim, ADR-PI-002 /
D11). Contract shape: bounded-change -- declared mutation set = rendered extension
file + manifest.

A3 (pi skill-dir + ``resources_discover`` shape, confirmed against pi 0.79.9 types
at ``@earendil-works/pi-coding-agent/dist/core/extensions/types.d.ts``): pi exposes
skill directories to an extension through the ``resources_discover`` event. The
handler returns a ``ResourcesDiscoverResult`` whose relevant field is
``skillPaths?: string[]`` (siblings ``promptPaths?``, ``themePaths?``) -- an array
of absolute directory paths pi loads skills from. ``resources_discover`` fires
after ``session_start`` with ``reason: "startup" | "reload"``.

Step 01-03 (pi-kata-tdd-flow, ADR-PKT-001) EXTENDS this plugin's render path:
1. A third placeholder ``{{KATA_PYTHONPATH}}`` is resolved so the extension's
   ``kata`` command / commit-context branch can ``python -c "from pi_kata...."``
   (KD3 -- reuses the same ``install_paths`` spawn-resolver discipline as the DES
   lib path). It resolves to the parent dir of the importable ``pi_kata`` package.
2. The crafter-skill pi-runnable cycle+recording section (ADR-PI-003 / D9) is
   placed alongside the extension as ``software-crafter/SKILL.md`` so a pi
   ``resources_discover`` handler can surface it in ``skillPaths``. The section
   states the self-driven 3-phase RED->GREEN->COMMIT loop and the per-phase
   ``des-log-phase`` recording the kata harness relies on. Canonical crafter
   content is reused (no new authored skill); the section is the pi-runnable
   adaptation of the ``nw-execute`` OUTCOME_RECORDING pattern.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path

from scripts.install.plugins.base import (
    InstallationPlugin,
    InstallContext,
    PluginResult,
)
from scripts.shared.install_paths import (
    resolve_des_lib_path_for_spawn,
    resolve_python_command_for_spawn,
)


_EXTENSION_FILENAME = "nwave-des.ts"
_MANIFEST_FILENAME = ".nwave-des-manifest.json"
_TEMPLATE_FILENAME = "pi-des-extension.ts.template"

# Crafter-skill pi-runnable section placement (ADR-PI-003 / D9). A single skill
# dir alongside the extension; the extension's resources_discover handler surfaces
# it in skillPaths. Reuses canonical crafter content (no new authored skill).
_SKILL_DIRNAME = "software-crafter"
_SKILL_FILENAME = "SKILL.md"


def _resolve_kata_pythonpath() -> str:
    """Return an absolute forward-slash path that makes ``pi_kata`` importable.

    Mirrors ``install_paths.resolve_*_for_spawn`` discipline (KD3): consumers
    pass this to a non-shell ``python -c`` spawn where ``$HOME`` is NOT expanded,
    so it must be resolved at install time. Resolves to the parent of the
    importable ``pi_kata`` package for the running interpreter -- which is the
    repo's ``scripts/install`` dir in the dev tree and the installed scripts dir
    post-install -- falling back to ``~/.claude/scripts``.
    """
    spec = importlib.util.find_spec("scripts.install.pi_kata")
    if spec is not None and spec.submodule_search_locations:
        # pi_kata package dir -> its parent (scripts/install) makes
        # ``from pi_kata....`` importable.
        return str(Path(spec.submodule_search_locations[0]).parent.as_posix())
    return (Path.home() / ".claude" / "scripts").as_posix()


# pi-runnable crafter cycle+recording section (ADR-PI-003 / D9). The pi-runnable
# adaptation of the nw-execute OUTCOME_RECORDING pattern: self-decompose a kata
# into NN-NN steps, drive RED->GREEN->COMMIT per tiny test, and record each phase
# via the install-resolved des-log-phase. ``{python}`` / ``{lib}`` are rendered
# with the same spawn resolvers as the extension.
_CRAFTER_SKILL_SECTION = """\
---
name: software-crafter
description: Self-driven kata TDD crafter for pi -- drives RED->GREEN->COMMIT and \
records each phase via DES.
---

# software-crafter (pi-runnable kata cycle)

Reuses the canonical nWave crafter 3-phase TDD canon (ADR-025) adapted to run \
inside pi with zero orchestrator. After `/kata <kata-id>` bootstraps the session \
(manifest at `docs/feature/<kata-id>/deliver/kata-manifest.json`), drive the kata \
one tiny test at a time.

## Self-decomposition (before the first RED)
Decompose the kata into an ordered step plan -- each step one observable behavior, \
~<=20 lines, semantically independent -- and record it. Step ids follow the `NN-NN` \
convention: a single slice `01`, incrementing the second field per tiny test \
(`01-01`, `01-02`, ...). Read the current step id from the manifest; increment it \
at each new RED. Never reuse a step id across cycles.

## Per-test cycle
1. **RED** -- write one failing test for the next increment; confirm it fails for \
the right reason. Record:

   `{python} -m des.cli.log_phase --project-dir docs/feature/<kata-id>/deliver \
--step-id <NN-NN> --phase RED --status EXECUTED --data PASS`

2. **GREEN** -- write the minimum production code to pass; run the suite. Record \
the `GREEN` phase the same way.
3. **COMMIT** -- refactor if it adds value (suite stays green), then commit with \
`Step-Id: <NN-NN>` and `Task-Id: <kata-id>` trailers. Record the `COMMIT` phase. \
The commit boundary is verified by the shipped DES gate (synthesized transcript + \
GitCommitVerifier): an incomplete cycle or a stale manifest step-id surfaces as a \
blocked commit (`COMMIT_NOT_VERIFIED`), never a silent allow.

Recording uses the install-resolved interpreter + DES lib on `PYTHONPATH={lib}` \
(the same spawn path the extension uses). Repeat until the kata is solved with a \
strict, fully recorded RED->GREEN->COMMIT trail in plan order.
"""


def _pi_config_dir() -> Path:
    """Return the pi configuration directory.

    Honors the ``PI_CONFIG_DIR`` env override (used by acceptance tests against a
    tmp dir); otherwise the default pi location (R1).
    """
    override = os.environ.get("PI_CONFIG_DIR")
    return Path(override) if override else Path.home() / ".pi" / "agent"


def _get_framework_version(context: InstallContext) -> str:
    """Read the framework version from VERSION file or fallback."""
    version_file = context.framework_source / "VERSION"
    if version_file.exists():
        return version_file.read_text(encoding="utf-8").strip()
    return "0.0.0"


class PiDESPlugin(InstallationPlugin):
    """Installs the nWave DES TS extension into the pi agent config dir."""

    def __init__(self) -> None:
        super().__init__(name="pi-des", priority=55)
        self.dependencies = ["des"]

    def validate_prerequisites(self, context: InstallContext) -> PluginResult:
        """Validate that pi and DES prerequisites exist.

        Checks:
        1. pi config directory exists (``PI_CONFIG_DIR`` or ``~/.pi/agent``)
        2. DES Python module is installed (``~/.claude/lib/python/des/``)
        3. TS template exists in framework source

        If pi is not detected, returns success with a skip message (R1).
        """
        pi_dir = _pi_config_dir()

        # pi not detected: skip silently (not an error) -- R1 non-fatal warning.
        if not pi_dir.exists():
            context.logger.warn(
                "  pi not detected, skipping DES extension installation"
            )
            return PluginResult(
                success=True,
                plugin_name=self.name,
                message="pi not detected, skipping DES extension installation",
            )

        # DES module must be installed.
        des_module = context.claude_dir / "lib" / "python" / "des"
        if not des_module.exists():
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message=(
                    f"DES Python library not found at {des_module}. Install DES first."
                ),
                errors=["DES library must be installed before pi DES extension"],
            )

        # TS template must exist.
        template_path = self._find_template(context)
        if template_path is None:
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message=f"TS template {_TEMPLATE_FILENAME} not found",
                errors=[f"Template {_TEMPLATE_FILENAME} missing from framework source"],
            )

        return PluginResult(
            success=True,
            plugin_name=self.name,
            message="pi DES prerequisites validated",
        )

    def install(self, context: InstallContext) -> PluginResult:
        """Render the DES extension into the pi config dir and write a manifest.

        Steps:
        1. Validate prerequisites (skips with success if pi not detected).
        2. Read the TS template.
        3. Resolve the python interpreter + DES lib path.
        4. Replace ``{{PYTHON_PATH}}`` / ``{{PYTHONPATH}}`` placeholders.
        5. Write the rendered extension to ``<pi_dir>/nwave-des.ts``.
        6. Write the manifest with version + content hash.
        """
        try:
            prereq_result = self.validate_prerequisites(context)
            if not prereq_result.success:
                return prereq_result

            pi_dir = _pi_config_dir()
            if not pi_dir.exists():
                return prereq_result  # success=True with skip message

            template_path = self._find_template(context)
            template_content = template_path.read_text(encoding="utf-8")

            python_path = resolve_python_command_for_spawn()
            des_lib_path = resolve_des_lib_path_for_spawn()
            rendered = template_content.replace("{{PYTHON_PATH}}", python_path)
            rendered = rendered.replace("{{PYTHONPATH}}", des_lib_path)
            # KD3: make the pi_kata bootstrap/transcript helpers importable from
            # the extension's `python -c` spawns (kata command + commit-context).
            rendered = rendered.replace(
                "{{KATA_PYTHONPATH}}", _resolve_kata_pythonpath()
            )

            extension_path = pi_dir / _EXTENSION_FILENAME
            if not context.dry_run:
                extension_path.write_text(rendered, encoding="utf-8")

            # Place the crafter-skill pi-runnable cycle+recording section
            # (ADR-PI-003 / D9). Rendered with the same resolved python + DES lib
            # path so the recorded des-log-phase invocations are reachable.
            skill_path = pi_dir / _SKILL_DIRNAME / _SKILL_FILENAME
            skill_content = _CRAFTER_SKILL_SECTION.format(
                python=python_path, lib=des_lib_path
            )
            if not context.dry_run:
                skill_path.parent.mkdir(parents=True, exist_ok=True)
                skill_path.write_text(skill_content, encoding="utf-8")

            content_hash = hashlib.sha256(rendered.encode("utf-8")).hexdigest()
            manifest = {
                "extension_file": str(extension_path),
                "skill_file": str(skill_path),
                "version": _get_framework_version(context),
                "sha256": content_hash,
            }
            manifest_path = pi_dir / _MANIFEST_FILENAME
            if not context.dry_run:
                manifest_path.write_text(
                    json.dumps(manifest, indent=2) + "\n",
                    encoding="utf-8",
                )

            context.logger.info(f"  pi DES extension installed: {extension_path}")
            context.logger.info(f"  pi crafter skill installed: {skill_path}")

            return PluginResult(
                success=True,
                plugin_name=self.name,
                message="pi DES extension installed successfully",
                installed_files=[extension_path, skill_path],
            )

        except Exception as e:
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message=f"pi DES extension installation failed: {e}",
                errors=[str(e)],
            )

    def verify(self, context: InstallContext) -> PluginResult:
        """Verify the DES extension and manifest are present in the pi config dir.

        If pi is not detected, verification is skipped with success.
        """
        try:
            pi_dir = _pi_config_dir()

            if not pi_dir.exists():
                return PluginResult(
                    success=True,
                    plugin_name=self.name,
                    message="pi not detected, verification skipped",
                )

            errors = []

            extension_path = pi_dir / _EXTENSION_FILENAME
            if not extension_path.exists():
                errors.append(f"pi DES extension not found: {extension_path}")

            skill_path = pi_dir / _SKILL_DIRNAME / _SKILL_FILENAME
            if not skill_path.exists():
                errors.append(f"pi crafter skill not found: {skill_path}")

            # The skill being on disk is necessary but NOT sufficient: pi only
            # loads it if the extension surfaces its dir via a resources_discover
            # handler (ADR-PI-003). Verify the wire, not just file presence --
            # otherwise the recording contract never reaches the model and the
            # kata's execution-log.json stays empty (the defect this guards).
            if extension_path.exists():
                rendered = extension_path.read_text(encoding="utf-8")
                if 'pi.on("resources_discover"' not in rendered:
                    errors.append(
                        "pi DES extension does not register a resources_discover "
                        f"handler; the crafter skill at {skill_path} is on disk but "
                        "not discoverable by pi (ADR-PI-003)"
                    )
                elif _SKILL_DIRNAME not in rendered:
                    errors.append(
                        f"pi DES extension does not surface the '{_SKILL_DIRNAME}' "
                        "skill dir in resources_discover skillPaths; the crafter "
                        "skill is on disk but not discoverable by pi (ADR-PI-003)"
                    )

            manifest_path = pi_dir / _MANIFEST_FILENAME
            if not manifest_path.exists():
                errors.append(f"pi DES manifest not found: {manifest_path}")

            if errors:
                return PluginResult(
                    success=False,
                    plugin_name=self.name,
                    message=(
                        f"pi DES verification failed: {_EXTENSION_FILENAME} missing"
                    ),
                    errors=errors,
                )

            context.logger.info("  pi DES extension verified")

            return PluginResult(
                success=True,
                plugin_name=self.name,
                message="pi DES extension verification passed",
            )

        except Exception as e:
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message=f"pi DES extension verification failed: {e}",
                errors=[str(e)],
            )

    def uninstall(self, context: InstallContext) -> PluginResult:
        """Remove the DES extension file and manifest.

        Only removes ``nwave-des.ts`` and the manifest. Operator files in the pi
        config dir are untouched.
        """
        try:
            pi_dir = _pi_config_dir()

            extension_path = pi_dir / _EXTENSION_FILENAME
            if extension_path.exists():
                extension_path.unlink()
                context.logger.info(f"  Removed pi DES extension: {extension_path}")

            skill_path = pi_dir / _SKILL_DIRNAME / _SKILL_FILENAME
            if skill_path.exists():
                skill_path.unlink()
                context.logger.info(f"  Removed pi crafter skill: {skill_path}")
                # Remove the skill dir if now empty (operator files untouched).
                skill_dir = skill_path.parent
                if skill_dir.exists() and not any(skill_dir.iterdir()):
                    skill_dir.rmdir()

            manifest_path = pi_dir / _MANIFEST_FILENAME
            if manifest_path.exists():
                manifest_path.unlink()
                context.logger.info(f"  Removed pi DES manifest: {manifest_path}")

            return PluginResult(
                success=True,
                plugin_name=self.name,
                message="pi DES extension uninstalled",
            )

        except Exception as e:
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message=f"pi DES extension uninstall failed: {e}",
                errors=[str(e)],
            )

    def _find_template(self, context: InstallContext) -> Path | None:
        """Locate the TS extension template file.

        Checks ``framework_source/templates/`` first, then
        ``project_root/nWave/templates/``.
        """
        if context.framework_source:
            template = context.framework_source / "templates" / _TEMPLATE_FILENAME
            if template.exists():
                return template

        if context.project_root:
            template = context.project_root / "nWave" / "templates" / _TEMPLATE_FILENAME
            if template.exists():
                return template

        return None
