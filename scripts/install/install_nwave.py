#!/usr/bin/env python3
"""
nWave Framework Installation Script

Cross-platform installer for the nWave methodology framework.
Installs specialized agents and commands to global Claude config directory.

Usage: python install_nwave.py [--backup-only] [--restore] [--dry-run] [--help]
"""

import argparse
import ast
import hashlib
import json
import os
import shlex
import sys
from pathlib import Path
from typing import NamedTuple

from scripts.install.plugins.base import PluginResult


_HASH_CHUNK_BYTES = 65536  # 64 KiB chunked read keeps SKILL.md etc. memory-bounded
_LEGACY_CODEX_AGENT_ALIASES = {"nw-architect", "nw-crafter"}
# The interpreter floor nWave supports: the minimum of pyproject requires-python.
# The OMP hooks probe and every message that names the floor read these names.
PYTHON_FLOOR: tuple[int, int] = (3, 11)
PYTHON_FLOOR_TEXT = ".".join(str(part) for part in PYTHON_FLOOR)

# HOW remedies for the Codex ownership preflight (see
# NWaveInstaller.validate_codex_ownership_preflight /
# _report_ownership_preflight_errors). Keyed by the ``kind`` tag attached to
# each collected error: distinct kinds need DISTINCT fixes -- relocating an
# untracked collision is the right remedy, but the wrong one for a corrupted
# manifest -- so this is a lookup table, never one generic line reused for
# every failure shape.
_OWNERSHIP_PREFLIGHT_UNTRACKED_COLLISION_HOW = (
    "If this is legacy nWave dev state, relocating it is a manual one-off "
    "step: move it into a backup folder yourself, then re-run install. If it "
    "is NOT nWave state, remove or relocate it yourself, then re-run install."
)
_OWNERSHIP_PREFLIGHT_REMEDIES: dict[str, str] = {
    # Skill and agent collisions are split into two kinds -- not one -- purely
    # so the aggregate report in _report_ownership_preflight_errors names BOTH
    # host roots (skills dir, agents dir) and samples from each, instead of one
    # alphabetically-dominant root hiding the other.
    "foreign-collision-skill": _OWNERSHIP_PREFLIGHT_UNTRACKED_COLLISION_HOW,
    "foreign-collision-agent": _OWNERSHIP_PREFLIGHT_UNTRACKED_COLLISION_HOW,
    "foreign-collision-manual": (
        "The installer does not move this for you. Back it up if you need it, "
        "remove it yourself, then re-run install so nWave writes its own trusted "
        "copy."
    ),
    "missing-owned-asset": (
        "nWave's own manifest says it owns this asset, but the file is "
        "gone. Re-run install to recreate it, or restore it from an nWave "
        "backup if you need the exact prior version."
    ),
    "unsafe-path": (
        "This path is a symlink, or the wrong type where nWave expects a "
        "plain file or directory. Inspect it, replace it with the expected "
        "type (or remove it), then re-run install."
    ),
    "corrupt-file": (
        "This file could not be read or parsed. Restore it from an nWave "
        "backup, or delete it and re-run install so nWave regenerates it."
    ),
    "untrusted-content": (
        "This file's content does not match what nWave generates or "
        "expects (hand-edited or incompatible). Back it up if you need it, "
        "delete it, then re-run install so nWave regenerates its own "
        "trusted copy."
    ),
}

# Ruling B: the legacy dev quarantine flag is retired. Its refusal recommends no
# flag and states that relocating legacy dev assets is a manual one-off step.
_LEGACY_CODEX_DEV_FLAG_REFUSAL = (
    "WHAT: the legacy dev quarantine flag --adopt-legacy-codex-dev is refused; "
    "no file was written.\n"
    "WHY: the flag is retired, so the installer no longer moves legacy Codex dev "
    "assets; relocating them is a manual one-off step.\n"
    "HOW: the flag is retired. Relocating the legacy nWave dev assets is a "
    "manual one-off step: move each nw-* skill folder under ~/.agents/skills "
    "and each nw-*.toml agent under ~/.codex/agents that no nWave manifest "
    "lists into a backup folder you keep, then re-run the install without the "
    "flag."
)


def _file_sha256(path: Path) -> str | None:
    """Compute SHA-256 of *path* in chunks; return None on read error.

    Returning ``None`` (vs. raising) lets the verifier treat "unreadable" the
    same as "drifted" — both reach the operator via the same diagnostic line
    naming the file, instead of crashing the verifier mid-walk.
    """
    try:
        digest = hashlib.sha256()
        with path.open("rb") as fh:
            while True:
                chunk = fh.read(_HASH_CHUNK_BYTES)
                if not chunk:
                    break
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return None


def _files_content_equal(source: Path, target: Path) -> bool:
    """Return True only when both files exist AND their SHA-256 digests match.

    Used by the verifier to detect content drift between an installer source
    file and its installed counterpart. Existence check alone misses the
    silent-template-skip bug class (RCA fix-installer-silent-template-skip).
    """
    if not target.exists():
        return False
    return _file_sha256(source) == _file_sha256(target)


def verify_directory_content(
    source_dir: Path, target_dir: Path
) -> tuple[int, list[str]]:
    """Partition a source directory's files by whether the target matches them.

    Returns ``(matched, drifted)``: how many source files have byte-identical
    counterparts under ``target_dir``, and the sorted names of those that do
    not. A file missing from the target counts as drifted, not as absent --
    `_files_content_equal` already collapses missing and different into the
    same "not synced" answer, because both reach the operator as the same
    stale-install symptom.

    Pure over the two directories: no logging, no verdict, no installer state.
    That is the point. The law it makes testable is decomposition ---
    ``matched + len(drifted) == number of source files``, and ``drifted`` is
    exactly the set failing `_files_content_equal` --- which previously could
    only be observed by driving the whole verifier, and therefore only by first
    satisfying every unrelated component it also checks.
    """
    source_files = sorted(f for f in source_dir.iterdir() if f.is_file())
    drifted = [
        f.name for f in source_files if not _files_content_equal(f, target_dir / f.name)
    ]
    return len(source_files) - len(drifted), drifted


# Bootstrap sys.path BEFORE the import block below, so the `scripts.install.*`
# package imports resolve identically whether this file is run as a bare script
# (`python scripts/install/install_nwave.py`) or as a module
# (`python -m scripts.install.install_nwave`).
#
# `.resolve()` is load-bearing: in bare-script mode `__file__` is a *relative*
# path, so `Path(__file__).parent.parent.parent` without resolution collapses to
# a relative `.` that does not place the repo root ahead of any stale `scripts/`
# package shadowing it on sys.path. Resolving first yields the absolute repo
# root; inserting it at index 0 makes the repo's `scripts` win namespace-package
# resolution (F-05 dogfood friction regression).
#
# Move-to-FRONT unconditionally (not `if not in sys.path`): an editable-install
# `.pth` appends the repo root AFTER site-packages, so a presence-only guard
# leaves site-packages' stale wheel snapshot of `scripts/` FIRST in the PEP 420
# namespace-portion order — the running plugin code silently rots to the last
# `uv sync` (fix-dispatch-ssot slice-01: `dispatch` never shipped because the
# stale site-packages `des_plugin.py` predated the constant change).
_project_root = Path(__file__).resolve().parent.parent.parent
_project_root_entry = str(_project_root)
if _project_root_entry in sys.path:
    sys.path.remove(_project_root_entry)
sys.path.insert(0, _project_root_entry)
_source_root = _project_root / "src"
if _source_root.is_dir():
    sys.path.insert(0, str(_source_root))


# Support both standalone execution and package import
try:
    from nwave_ai.platform.locations import NWaveLocations
    from nwave_ai.platform.result import Failure
    from nwave_ai.upgrade_shell import cleanup as run_legacy_cleanup
    from nwave_ai.upgrade_shell import real_port
    from scripts.install.context_detector import detect_target_platforms
    from scripts.install.host_attribution import HostAttributionPolicy
    from scripts.install.install_lock import (
        EXIT_INSTALL_LOCK_HELD,
        InstallLockHeld,
        install_lock,
    )
    from scripts.install.install_utils import (
        BackupManager,
        Logger,
        ManifestWriter,
        PathUtils,
    )
    from scripts.install.installation_verifier import InstallationVerifier
    from scripts.install.output_formatter import format_error
    from scripts.install.plugins.agents_plugin import AgentsPlugin
    from scripts.install.plugins.attribution_plugin import AttributionPlugin
    from scripts.install.plugins.base import InstallContext
    from scripts.install.plugins.codex_agents_plugin import (
        _CODEX_LEGACY_WITNESS_KEY,
        CodexAgentsPlugin,
    )
    from scripts.install.plugins.codex_skills_plugin import (
        _ATTESTED_LEGACY_SKILLS_METADATA_KEY,
        CodexSkillsPlugin,
    )
    from scripts.install.plugins.commands_plugin import CommandsPlugin
    from scripts.install.plugins.dev_launchers_plugin import DevLaunchersPlugin
    from scripts.install.plugins.devin_skills_plugin import DevinSkillsPlugin
    from scripts.install.plugins.nwave_hooks_plugin import HooksPlugin
    from scripts.install.plugins.nwdes_plugin import NwdesPlugin
    from scripts.install.plugins.omp_agents_plugin import OmpAgentsPlugin
    from scripts.install.plugins.omp_commands_plugin import OmpCommandsPlugin
    from scripts.install.plugins.omp_skills_plugin import OmpSkillsPlugin
    from scripts.install.plugins.opencode_agents_plugin import OpenCodeAgentsPlugin
    from scripts.install.plugins.opencode_commands_plugin import OpenCodeCommandsPlugin
    from scripts.install.plugins.opencode_skills_plugin import OpenCodeSkillsPlugin
    from scripts.install.plugins.registry import PluginRegistry
    from scripts.install.plugins.skills_plugin import SkillsPlugin
    from scripts.install.plugins.templates_plugin import TemplatesPlugin
    from scripts.install.plugins.utilities_plugin import UtilitiesPlugin
    from scripts.install.preflight_checker import PreflightChecker
    from scripts.shared.agent_catalog import is_public_agent, load_public_agents
    from scripts.shared.install_paths import agents_home, codex_config_dir, env_or_none
    from scripts.shared.version import resolve_product_version
except ImportError:
    # Safety-net fallback. With the sys.path bootstrap above the package
    # imports in the `try` block resolve in BOTH invocation modes, so this
    # branch is normally unreachable. It is retained as a defensive net and
    # MUST stay import-correct: bare `scripts/install` directory imports plus
    # an explicit re-bootstrap of the repo root for the `scripts.shared`
    # package (which lives one level up from `scripts/install`, so a bare
    # `from shared...` would fail — F-05 latent fallback bug).
    if _project_root_entry in sys.path:
        sys.path.remove(_project_root_entry)
    sys.path.insert(0, _project_root_entry)
    from context_detector import detect_target_platforms
    from host_attribution import HostAttributionPolicy
    from install_lock import (
        EXIT_INSTALL_LOCK_HELD,
        InstallLockHeld,
        install_lock,
    )
    from install_utils import (
        BackupManager,
        Logger,
        ManifestWriter,
        PathUtils,
    )
    from installation_verifier import InstallationVerifier
    from output_formatter import format_error
    from plugins.agents_plugin import AgentsPlugin
    from plugins.attribution_plugin import AttributionPlugin
    from plugins.base import InstallContext
    from plugins.codex_agents_plugin import (
        _CODEX_LEGACY_WITNESS_KEY,
        CodexAgentsPlugin,
    )
    from plugins.codex_skills_plugin import (
        _ATTESTED_LEGACY_SKILLS_METADATA_KEY,
        CodexSkillsPlugin,
    )
    from plugins.commands_plugin import CommandsPlugin
    from plugins.dev_launchers_plugin import DevLaunchersPlugin
    from plugins.devin_skills_plugin import DevinSkillsPlugin
    from plugins.nwave_hooks_plugin import HooksPlugin
    from plugins.nwdes_plugin import NwdesPlugin
    from plugins.omp_agents_plugin import OmpAgentsPlugin
    from plugins.omp_commands_plugin import OmpCommandsPlugin
    from plugins.omp_skills_plugin import OmpSkillsPlugin
    from plugins.opencode_agents_plugin import OpenCodeAgentsPlugin
    from plugins.opencode_commands_plugin import OpenCodeCommandsPlugin
    from plugins.opencode_skills_plugin import OpenCodeSkillsPlugin
    from plugins.registry import PluginRegistry
    from plugins.skills_plugin import SkillsPlugin
    from plugins.templates_plugin import TemplatesPlugin
    from plugins.utilities_plugin import UtilitiesPlugin
    from preflight_checker import PreflightChecker

    import scripts.shared.install_paths as _install_paths
    from scripts.shared.agent_catalog import is_public_agent, load_public_agents
    from scripts.shared.version import resolve_product_version

    # Keep the bare-script namespace identical to the package branch while
    # importing the canonical module once; only codex_config_dir is consumed
    # by this module's implementation.
    agents_home = _install_paths.agents_home
    codex_config_dir = _install_paths.codex_config_dir
    env_or_none = _install_paths.env_or_none

_SNAPSHOT_PREFIX = "nwave-"
_HOLD_PREFIX = "legacy-hold-"
_LISTED_PREFIXES = (_SNAPSHOT_PREFIX, f"{_HOLD_PREFIX}{_SNAPSHOT_PREFIX}")
_LEGACY_COPY_NAME = "legacy-codex-dev"
_RESTORE_CLAUDE_LINE = (
    "     Claude root: --restore reads the last one in name order and replaces the current agents "
    "and commands with what it holds."
)
_RESTORE_CODEX_LINE = "     Codex root: --restore does not read this directory."
_DELETE_BY_HAND_LINE = "     This run does not use them. Delete the others by hand only when you no longer need them."


def _legacy_copy_present(snapshot: Path) -> bool:
    """True while the snapshot's legacy-codex-dev entry exists, of any kind or unreadable."""
    try:
        os.lstat(snapshot / _LEGACY_COPY_NAME)
    except FileNotFoundError:
        return False
    except OSError:
        return True
    return True


def _kept_marker(name: str, root: Path, this_run: str) -> str:
    """The F484 marker that follows a kept snapshot's name in the listing."""
    if name == this_run:
        return "  (this run)"
    if name.startswith(_HOLD_PREFIX):
        return (
            "  (held: its legacy Codex dev copy is its only copy; retire the copy with "
            f"verify_nwave.py --retire-legacy-copy {root}/{name}/{_LEGACY_COPY_NAME} --against DIR "
            f"after verify_nwave.py --verify-legacy-copy {root}/{name}/{_LEGACY_COPY_NAME} "
            "--against DIR passes)"
        )
    return ""


# ANSI color codes for --help output (only consumer)
_ANSI_BLUE = "\033[0;34m"
_ANSI_NC = "\033[0m"  # No Color


def _get_version() -> str:
    """Resolve the live product version through the strict producer.

    Delegates to :func:`resolve_product_version` -- installed metadata wins
    over the adjacent dev-checkout ``pyproject.toml``; ambiguous, missing, or
    malformed identity raises ``VersionResolutionError`` (WHAT/WHY/HOW)
    instead of a ``"0.0.0"`` sentinel. Called only at the point of use, never
    at import time.
    """
    return resolve_product_version(_project_root).version


def __getattr__(name: str) -> str:
    """Lazy external access to ``__version__``: no identity lookup at import.

    Only resolves (and may raise ``VersionResolutionError``) when a consumer
    actually asks for the module's ``__version__`` attribute.
    """
    if name == "__version__":
        return _get_version()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _detect_installed_version() -> str | None:
    """Return the live ``nwave-ai`` package version, or None when unavailable.

    Metadata-only (no pyproject fallback): the recorded value must match what
    the doctor reads at runtime via ``importlib.metadata`` so a dev/editable
    checkout (no installed distribution) records nothing rather than a pyproject
    version that would read as spurious drift.
    """
    from importlib.metadata import PackageNotFoundError, version

    try:
        return version("nwave-ai")
    except PackageNotFoundError:
        return None


class InstallProvenance(NamedTuple):
    """The selected hosts, mode, and destinations of one validated install."""

    target_platforms: frozenset[str]
    dev_mode: bool
    host_paths: dict[str, str]


def record_install_metadata(
    global_config_path: Path,
    installed_version: str | None,
    *,
    repo_root: Path | None = None,
    provenance: InstallProvenance | None = None,
) -> None:
    """Record install provenance through the sole atomic config writer.

    Version metadata is diagnostic. The selected hosts, mode, and destinations
    are update safety provenance and must persist after a validated install.
    """
    try:
        from nwave_ai.platform.config_writer import ConfigWriter

        writer = ConfigWriter(
            home_dir=global_config_path.parent.parent,
            repo_root=repo_root or Path.cwd(),
        )

        def record(document: dict) -> None:
            existing_install = document.get("install")
            install_block = (
                dict(existing_install) if isinstance(existing_install, dict) else {}
            )
            if installed_version is not None:
                install_block["installed_version"] = installed_version
            elif provenance is not None and provenance.dev_mode:
                install_block.pop("installed_version", None)
            if provenance is not None:
                install_block["target_platforms"] = sorted(provenance.target_platforms)
                install_block["dev_mode"] = provenance.dev_mode
                install_block["host_paths"] = dict(provenance.host_paths)
            document["install"] = install_block

        writer.update_global(record)
    except Exception:
        # Existing version-only callers retain their best-effort diagnostic
        # metadata contract. A selected host/mode is safety-critical update
        # provenance: an install cannot report success if it failed to record it.
        if provenance is not None:
            raise


# OMP's tool_call guard ceiling: what the kept nWave hooks extension can and
# cannot block on the OMP host. Same categories the kept template enforces.
OMP_GUARD_CEILING = (
    "OMP nWave: tool_call can block task, bash, write and edit calls "
    "(path, hashline and apply_patch file headers, including move targets). "
    "Not enforced: unrecognized edit formats, internal URI writes, eval/workpool spawns, "
    "SendMessage and TaskCreate/TaskUpdate (no equivalent tools), "
    "SubagentStop transcript-based checks (no Claude transcript). "
    "Session lifecycle/update admission guards are not enforced by this extension."
)

_OMP_HOOKS_TEMPLATE = "omp-nwave-hooks-extension.ts.template"
_OMP_HOOKS_SHIM = "nwave-hooks.ts"
_OMP_HOOKS_MANIFEST = ".nwave-des-manifest.json"


def _install_omp_hooks_extension(context) -> "PluginResult":
    """Install the kept nWave guard extension for OMP from its kept template.

    The retired OMP plugin owned this surface; the kept guard comes from
    nWave/templates/omp-nwave-hooks-extension.ts.template, rendered with the
    resolved interpreter and the host-neutral runtime PYTHONPATH. Writes the
    rendered extension and a sha256 manifest under omp_extensions_dir();
    honours context.dry_run.
    """
    import hashlib
    import subprocess

    from scripts.shared.install_paths import (
        omp_extensions_dir,
        resolve_python_command_for_spawn,
    )

    name = "omp-nwave-hooks"
    try:
        from scripts.install.plugins.omp_common import require_default_profile
    except ImportError:
        from omp_common import require_default_profile  # type: ignore[no-redef]

    require_default_profile()
    try:
        probe_result = subprocess.run(
            [
                resolve_python_command_for_spawn(),
                "-c",
                f"import sys; assert sys.version_info >= {PYTHON_FLOOR}; print(sys.executable)",
            ],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        python = probe_result.stdout.strip()
    except (OSError, subprocess.SubprocessError) as error:
        message = (
            f"WHAT: Python >={PYTHON_FLOOR_TEXT} could not be resolved for the OMP hooks extension. "
            f"WHY: {error}. HOW: install Python >={PYTHON_FLOOR_TEXT}, put it on PATH, and rerun "
            "the installer with that interpreter."
        )
        return PluginResult(False, name, message, errors=[str(error)])
    import nwave_ai

    # The directory that makes the kept nwave_ai importable: the extension must
    # resolve the same package this installer runs from.
    runtime = str(Path(nwave_ai.__file__).resolve().parent.parent)
    template = context.framework_source / "templates" / _OMP_HOOKS_TEMPLATE
    if not template.is_file():
        template = context.project_root / "nWave/templates" / _OMP_HOOKS_TEMPLATE
    rendered = (
        template.read_text(encoding="utf-8")
        .replace("{{PYTHON_PATH_JSON}}", json.dumps(python))
        .replace("{{PYTHONPATH_JSON}}", json.dumps(runtime))
    )
    directory = omp_extensions_dir()
    shim = directory / _OMP_HOOKS_SHIM
    manifest_path = directory / _OMP_HOOKS_MANIFEST
    if directory.is_symlink() or shim.is_symlink() or manifest_path.is_symlink():
        message = f"Unsafe OMP extension path: {directory}; remove symlinks and rerun install."
        return PluginResult(False, name, message, errors=[message])
    if shim.exists() and not manifest_path.is_file():
        message = (
            f"Foreign OMP extension collision: {shim}; back up and remove it "
            "before reinstalling."
        )
        return PluginResult(False, name, message, errors=[message])
    if not context.dry_run:
        if runtime and Path(runtime) not in sys.path:
            probe = subprocess.run(
                [python, "-c", "import nwave_ai.hooks"],
                env={**os.environ, "PYTHONPATH": runtime},
                cwd=Path.home(),
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=15,
            )
            if probe.returncode:
                message = (
                    f"WHAT: nwave_ai.hooks import failed with PYTHONPATH={runtime}. "
                    f"WHY: {probe.stderr.strip()}. HOW: rerun the installer with "
                    f"Python >={PYTHON_FLOOR_TEXT} and its required dependencies installed."
                )
                return PluginResult(False, name, message, errors=[message])
        directory.mkdir(parents=True, exist_ok=True)
        shim.write_text(rendered, encoding="utf-8")
        manifest_path.write_text(
            json.dumps(
                {
                    "installed_extensions": [_OMP_HOOKS_SHIM],
                    "sha256": hashlib.sha256(rendered.encode()).hexdigest(),
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    message = (
        f"{'Would install' if context.dry_run else 'Installed'} OMP nWave hooks "
        f"extension at {shim}; Python: {python}; runtime: {runtime}. "
        f"{OMP_GUARD_CEILING}"
    )
    context.logger.info(message)
    return PluginResult(True, name, message, installed_files=[shim])


def _component_synced(matched: int, expected: int) -> bool:
    """Return True iff a verifier component is synced.

    Pure equality predicate: a component is synced when the count of
    files present in the target equals the count expected from the
    source. The "no work needed" state (matched == 0 AND expected == 0)
    is success, NOT failure.

    Earlier inline expressions added a defensive `and expected > 0`
    clause that turned legitimate zero-expected states into hard fails
    (v3.12.1 install regression, RCA Bugs #2 and #5). The verifier's
    job is to assert that everything-expected is present — it does not
    decide what counts as suspicious.
    """
    return matched == expected


class ComponentResult(NamedTuple):
    """Per-component sync verification result.

    Carries the four facts the failure aggregator needs:
    - name      : human-readable component name (agents/commands/...)
    - matched   : count of files found in the target
    - expected  : count of files declared by the source
    - ok        : whether matched == expected (cached for clarity)
    """

    name: str
    matched: int
    expected: int
    ok: bool


def _format_sync_mismatch(components: list[ComponentResult]) -> str:
    """Format a per-component sync-mismatch failure message.

    Pure data transformation: take the list of component results, keep
    only the failures, render each as ``<name> (<matched>/<expected>)``,
    and join them under the prefix ``sync mismatch: ``.

    Replaces the legacy literal ``"agent/command sync mismatch"`` which
    blamed agents/commands regardless of which component actually failed
    (v3.12.1 install regression, RCA Bug #3). Mentioning only the failing
    components avoids contradiction with the per-component checkmarks
    printed above the aggregate failure line.
    """
    failing = [c for c in components if not c.ok]
    if not failing:
        # Defensive: caller should not invoke us when all components are
        # green, but if it does we still want a sensible non-empty token.
        return "sync mismatch: unknown"
    parts = [f"{c.name} ({c.matched}/{c.expected})" for c in failing]
    return f"sync mismatch: {', '.join(parts)}"


# ASCII art logo (raw text, no Rich markup)
_LOGO_ART = [
    "        \u2584\u2584\u2584\u2584  \u2584\u2584\u2584  \u2584\u2584\u2584\u2584",
    "        \u2580\u2588\u2588\u2588  \u2588\u2588\u2588  \u2588\u2588\u2588\u2580",
    "  \u2588\u2588\u2588\u2588\u2584  \u2588\u2588\u2588  \u2588\u2588\u2588  \u2588\u2588\u2588  \u2580\u2580\u2588\u2584 \u2588\u2588 \u2588\u2588 \u2584\u2588\u2580\u2588\u2584",
    "  \u2588\u2588 \u2588\u2588  \u2588\u2588\u2588\u2584\u2584\u2588\u2588\u2588\u2584\u2584\u2588\u2588\u2588 \u2584\u2588\u2580\u2588\u2588 \u2588\u2588\u2584\u2588\u2588 \u2588\u2588\u2584\u2588\u2580",
    "  \u2588\u2588 \u2588\u2588   \u2580\u2588\u2588\u2588\u2588\u2580\u2588\u2588\u2588\u2588\u2580  \u2580\u2588\u2584\u2588\u2588  \u2580\u2588\u2580  \u2580\u2588\u2584\u2584\u2584\u2584\u2582\u2582\u2581\u2581",
]
_TAGLINES = [
    " Orchestrated Agentic-AI code assistant for crafters.",
    " Modern Software Engineering at scale. Confidence at speed.",
]


class NWaveInstaller:
    """nWave framework installer."""

    # None until the legacy cleanup records its Codex witness (F516). A class default
    # keeps an installer built without __init__ on the disk-witness fallback.
    _codex_legacy_witness: bool | None = None

    def __init__(
        self,
        dry_run: bool = False,
        platform_override: set[str] | None = None,
        dev_mode: bool = False,
    ):
        """Initialize installer.

        Args:
            dry_run: When True, show what would be done without making changes.
            platform_override: Override auto-detected platforms. None means auto-detect.
            dev_mode: When True, install ALL agents/skills (not just public).
        """
        self.dry_run = dry_run
        self.dev_mode = dev_mode
        self._platform_override = platform_override
        # The install must have one target truth.  In particular, auto mode
        # cannot install a detected Codex target and later reconstruct a
        # Claude-only validation set from the original CLI override.  Resolved
        # HERE rather than at first use, so the ambient read happens where the
        # caller still controls the environment.
        self._effective_target_platforms: set[str] = self._resolve_target_platforms()
        self.script_dir = Path(__file__).parent
        self.project_root = PathUtils.get_project_root(self.script_dir)
        declared_user_root = os.environ.get("NWAVE_PROJECT_ROOT")
        self.user_project_root = (
            Path(declared_user_root).resolve()
            if declared_user_root is not None
            else Path.cwd().resolve()
        )
        # Source-first: use nWave/ when in dev repo, dist/ only for distribution
        source_dir = self.project_root / "nWave"
        dist_dir = self.project_root / "dist"
        if source_dir.exists():
            self.framework_source = source_dir
        elif (dist_dir / "MANIFEST.json").exists():
            self.framework_source = dist_dir
        else:
            self.framework_source = source_dir  # fall through for error reporting

        # ONE construction site for every write/read destination this
        # invocation shares (NWaveLocations.resolve): refuses a relative
        # NWAVE_AGENTS_HOME / CLAUDE_CONFIG_DIR / CODEX_HOME before any
        # attribute below is derived from it, and before any public method
        # can run -- closing the double-blind-spot where the five ad hoc
        # agents_home()/codex_config_dir() call sites this replaces could
        # each independently re-read a changed environment mid-install.
        locations_result = NWaveLocations.resolve(
            home=Path.home(),
            repo_root=self.project_root,
            agents_home_override=env_or_none("NWAVE_AGENTS_HOME"),
            claude_config_override=env_or_none("CLAUDE_CONFIG_DIR"),
            codex_config_override=env_or_none("CODEX_HOME"),
        )
        if isinstance(locations_result, Failure):
            raise ValueError(
                "nWave installer refuses a relative install-root override "
                f"before any write: {locations_result.error}"
            )
        self._locations: NWaveLocations = locations_result.unwrap()
        # Keep the Claude target on the same immutable location result as the
        # selected nWave home.  Deriving it independently would re-read the
        # environment and permit the installer to split its destinations.
        self.claude_config_dir = self._locations.claude_config_dir

        # Persistent logging starts only after Codex ownership preflight.  A
        # refusal must leave every user-controlled byte untouched, including
        # an unrelated pre-existing Claude log.
        self._install_log_file = self.claude_config_dir / "nwave-install.log"
        self.logger = Logger(None)
        self.backup_manager = BackupManager(self.logger, "install")
        # Public observability contract for restore_backup: after a successful
        # restore, this attribute exposes the path of the backup that was
        # selected. Acceptance tests inspect this to verify selection without
        # re-running glob/sort logic in the test step (see DWD-09).
        self.last_restored_from: Path | None = None
        self._codex_backup_dir: Path | None = None
        self._attested_legacy_codex_skill_names: frozenset[str] = frozenset()

    def enable_install_logging(self) -> None:
        """Enable persistent logging after the no-write ownership preflight."""
        if not self.dry_run:
            self.logger.log_file = self._install_log_file

    @property
    def effective_target_platforms(self) -> frozenset[str]:
        """Return the authoritative targets for this installer invocation.

        Resolved once, AT CONSTRUCTION (`_resolve_target_platforms`), so every
        downstream stage consumes the same set and the caller can see the
        decision being made. Reading it here is a plain lookup with no fallback.
        """
        return frozenset(self._effective_target_platforms)

    def _resolve_target_platforms(self) -> set[str]:
        """Decide the target set: the caller's declaration, else the environment.

        Deliberately eager. This used to resolve lazily at first use, which put
        the ambient read deep inside `validate_installation()` -- OUTSIDE the
        window in which a caller, or a test, controls the environment. A caller
        that wanted to declare the platform could still be overtaken by
        detection, and three test suites passed only because a sibling had
        created a host directory first (2026-08-06).

        Construction stays free of SIDE EFFECTS: this reads the environment, it
        writes nothing. Reading at construction is the point -- it is where the
        caller is still in charge. See `contract:declared-inputs-not-ambient-reads`
        (`nw-cross-cutting-invariants`): the ambient lookup is the default the
        caller may state, never the only source.
        """
        if self._platform_override is not None:
            return set(self._platform_override)
        return {platform.value for platform in detect_target_platforms()}

    def create_backup(self) -> None:
        """Create backup of existing installation, then enforce retention.

        Wires backup creation and retention pruning into a single seam so
        ``main()`` and any other caller automatically gets retention without
        having to remember to call ``apply_retention`` themselves.

        Retention is intentionally NOT applied in dry-run mode: dry-run must
        not delete anything from disk. In live runs, retention runs even when
        ``create_backup`` returns ``None`` (no prior install) — older
        accumulated backups from previous runs may still need pruning, and
        ``apply_retention`` is a no-op when the cap is not exceeded.

        Raises:
            ConfigValidationError: when ``~/.nwave/config.json``
                provides an invalid ``backups.max_count`` value. Bubbled up
                so ``main()`` aborts the install BEFORE ``install_framework``
                runs — see scope.md S9 ("no backup is touched if config is
                invalid"); equivalently, no install proceeds either.
        """
        # Read-only, but still an isolation boundary: `apply_retention` below
        # reads `config.json`'s `backups.max_count` regardless of
        # platform, and a sentinel byte-diff test cannot observe a READ the
        # way it observes a write. Computed once, for both branches.
        install_root = self._locations.agents_home
        target_platforms = self.effective_target_platforms

        # Each selected platform gets its own snapshot at its own existing
        # supported location -- Claude under claude_config_dir/backups, Codex
        # under install_root/.nwave/backups. A combined selection must run
        # BOTH, not just whichever branch a prior single-target `if/else`
        # happened to test first (that earlier shape silently dropped the
        # Claude snapshot whenever Codex was also selected). Codex-only
        # isolation is preserved: the Claude branch below only runs when
        # "claude_code" is actually selected, so a Codex-only invocation
        # still never touches claude_config_dir.
        #
        # `backup_manager` is one shared, mutable object reused across calls
        # (and across both branches of a single call). Its `backup_root`/
        # `backup_dir` are therefore rebound EXPLICITLY, from this
        # invocation's own locations, immediately before each store's use --
        # never left to whatever a previous call or branch last set. Two
        # defects this closes: (1) a combined run used to prune retention
        # only on whichever store the manager's fields pointed to LAST
        # (Codex, since that branch mutated them after Claude's); (2) a
        # second `create_backup()` call reusing the same installer used to
        # find `backup_dir` still redirected to the Codex store by the
        # previous call, so a Claude-only follow-up call wrote Claude bytes
        # into the Codex backup tree.
        backup_type = self.backup_manager.backup_type
        timestamp = self.backup_manager.timestamp
        claude_backup_root = self.claude_config_dir / "backups"
        codex_backup_root = install_root / ".nwave" / "backups"

        if "claude_code" in target_platforms:
            self.backup_manager.backup_root = claude_backup_root
            self.backup_manager.backup_dir = (
                claude_backup_root / f"nwave-{backup_type}-{timestamp}"
            )
            self.backup_manager.create_backup(dry_run=self.dry_run)
            if not self.dry_run:
                self.backup_manager.apply_retention(
                    max_count=None, nwave_config_dir=install_root / ".nwave"
                )

        if "codex" in target_platforms:
            codex_dir = self._locations.codex_config_dir
            self.backup_manager.backup_root = codex_backup_root
            self.backup_manager.backup_dir = (
                codex_backup_root / f"nwave-{backup_type}-{timestamp}"
            )
            self._codex_backup_dir = self.backup_manager.create_codex_backup(
                skills_dir=install_root / ".agents" / "skills",
                agents_dir=codex_dir / "agents",
                codex_dir=codex_dir,
                dry_run=self.dry_run,
            )
            if not self.dry_run:
                holds_complete = self._release_and_hold_codex_snapshots(
                    codex_backup_root
                )
                if holds_complete:
                    self.backup_manager.apply_retention(
                        max_count=None, nwave_config_dir=install_root / ".nwave"
                    )

    def _release_and_hold_codex_snapshots(self, backup_root: Path) -> bool:
        """Release retired legacy holds, then hold snapshots that carry a legacy Codex copy.

        A hold is a snapshot renamed to legacy-hold-<name> while its legacy-codex-dev copy
        is its only copy. Holds sit outside the nwave-* retention pool, so retention never
        prunes them. Returns False when a rename failed; the caller then skips retention
        for this root.
        """
        try:
            entries = sorted(backup_root.iterdir()) if backup_root.is_dir() else []
        except OSError as error:
            self.logger.error(
                f"WHAT: the Codex backup root {backup_root} could not be listed. "
                f"WHY: {error}. HOW: fix its permissions and rerun the install; "
                "retention is skipped for this root."
            )
            return False
        complete = True
        for entry in entries:
            if (
                entry.name.startswith(_HOLD_PREFIX)
                and entry.is_dir()
                and not _legacy_copy_present(entry)
            ):
                complete &= self._rename_snapshot(
                    entry, entry.name[len(_HOLD_PREFIX) :], held=False
                )
        for entry in entries:
            if (
                entry.name.startswith(_SNAPSHOT_PREFIX)
                and entry.is_dir()
                and _legacy_copy_present(entry)
            ):
                complete &= self._rename_snapshot(
                    entry, f"{_HOLD_PREFIX}{entry.name}", held=True
                )
        return complete

    def _rename_snapshot(self, source: Path, target_name: str, *, held: bool) -> bool:
        """Rename one snapshot inside its backup root; False reports the failure by name."""
        target = source.parent / target_name
        try:
            if os.path.lexists(target):
                raise FileExistsError(f"{target_name} already exists")
            source.rename(target)
        except OSError as error:
            self.logger.error(
                f"WHAT: the legacy Codex copy snapshot {source.name} could not be renamed to "
                f"{target_name}. WHY: {error}. HOW: resolve the named problem and rerun the "
                f"install; nothing was deleted and retention is skipped for {source.parent}."
            )
            return False
        if held:
            self.logger.info(
                f"  legacy Codex copy snapshot renamed to {target_name}; kept until retired "
                "with --retire-legacy-copy after --verify-legacy-copy passes."
            )
        return True

    def report_kept_snapshots(self) -> None:
        """Print the kept-snapshot listing (F484) for each backup root that holds snapshots.

        Runs after validation passes on a successful install, whatever the target platforms.
        """
        this_run = (
            f"{_SNAPSHOT_PREFIX}{self.backup_manager.backup_type}"
            f"-{self.backup_manager.timestamp}"
        )
        roots = (
            (self.claude_config_dir / "backups", _RESTORE_CLAUDE_LINE),
            (self._locations.agents_home / ".nwave" / "backups", _RESTORE_CODEX_LINE),
        )
        for root, restore_line in roots:
            if not root.is_dir():
                continue
            names = sorted(
                entry.name
                for entry in root.iterdir()
                if entry.is_dir() and entry.name.startswith(_LISTED_PREFIXES)
            )
            if not names:
                continue
            print(
                f"  \u26a0\ufe0f {len(names)} nWave backup snapshot(s) kept under {root}:"
            )
            for name in names:
                print(f"     {name}{_kept_marker(name, root, this_run)}")
            print(_DELETE_BY_HAND_LINE)
            print(restore_line)

    def validate_codex_ownership_preflight(self) -> bool:
        """Reject ambiguous Codex ownership before the installer writes.

        Codex plugins intentionally preserve user configuration, but cannot
        safely decide whether an existing reserved nWave path is theirs without
        a well-formed, contained manifest.  This check runs before backup,
        target-directory creation, and plugin dispatch so a refusal leaves the
        complete user state untouched.
        """
        # The capability is per preflight pass.  A failed or later unrelated
        # preflight must never leave a previous discovery available to install.
        self._attested_legacy_codex_skill_names = frozenset()
        if "codex" not in self.effective_target_platforms:
            return True

        install_root = self._locations.agents_home
        skills_dir = install_root / ".agents" / "skills"
        codex_dir = self._locations.codex_config_dir
        agents_dir = codex_dir / "agents"
        # Each entry is (kind, line) rather than a bare string: ``kind`` keys
        # the aggregation + HOW-remedy lookup at the bottom of this method,
        # so a flood of same-shape collisions collapses to one header + one
        # remedy instead of N repeated, HOW-less log lines (see
        # _OWNERSHIP_PREFLIGHT_REMEDIES for the fixed set of kinds and why
        # each maps to a DIFFERENT fix, never one generic HOW for all).
        errors: list[tuple[str, str]] = []
        public_agents = load_public_agents(self.project_root / "nWave")
        legacy_agent_names = {
            source.stem
            for source in (self.framework_source / "agents").glob("nw-*.md")
            if is_public_agent(source.name, public_agents)
        } | _LEGACY_CODEX_AGENT_ALIASES
        hooks_path = codex_dir / "hooks.json"
        des_manifest_path = codex_dir / ".nwave-des-manifest.json"
        launcher_path = codex_dir / "nwave_claude_code_hook_adapter_launcher.py"

        def regular_file(path: Path) -> bool:
            return not path.is_symlink() and path.is_file()

        def safe_directory(path: Path) -> bool:
            return not path.is_symlink() and path.is_dir()

        def safe_skill_tree(path: Path) -> bool:
            if not safe_directory(path):
                return False
            try:
                skill = path / "SKILL.md"
                return regular_file(skill) and all(
                    not child.is_symlink() and (child.is_dir() or child.is_file())
                    for child in path.rglob("*")
                )
            except OSError:
                return False

        skills_dir_safe = not (
            skills_dir.exists() or skills_dir.is_symlink()
        ) or safe_directory(skills_dir)
        agents_dir_safe = not (
            agents_dir.exists() or agents_dir.is_symlink()
        ) or safe_directory(agents_dir)
        for label, path in (
            ("Codex skills directory", skills_dir),
            ("Codex agents directory", agents_dir),
            ("Codex hooks configuration", hooks_path),
            ("nWave DES manifest", des_manifest_path),
            ("nWave DES launcher", launcher_path),
        ):
            if (path.exists() or path.is_symlink()) and (
                (path in {skills_dir, agents_dir} and not safe_directory(path))
                or (path not in {skills_dir, agents_dir} and not regular_file(path))
            ):
                errors.append(("unsafe-path", f"unsafe {label}: {path}"))

        legacy_direct_command: str | None = None
        legacy_launcher_witness = False
        legacy_direct_hook_witness = False
        orphan_launcher_witness = False
        if regular_file(des_manifest_path) and regular_file(hooks_path):
            try:
                from nwave_ai.upgrade_shell import (
                    _codex_legacy_direct_des_command,
                    _codex_v1_launcher_source,
                )

                legacy_manifest = json.loads(
                    des_manifest_path.read_text(encoding="utf-8")
                )
                legacy_hooks = json.loads(hooks_path.read_text(encoding="utf-8"))
                legacy_direct_command = _codex_legacy_direct_des_command(
                    legacy_manifest, hooks_path, legacy_hooks
                )
                expected_legacy_launcher_command = shlex.join(
                    [
                        legacy_manifest["python_path"],
                        str(launcher_path),
                        "pre-tool-use",
                    ]
                )
                legacy_pretool = (
                    legacy_hooks.get("hooks", {}).get("PreToolUse", [])
                    if isinstance(legacy_hooks, dict)
                    and isinstance(legacy_hooks.get("hooks"), dict)
                    else []
                )
                launcher_hook_present = any(
                    isinstance(group, dict)
                    and isinstance(group.get("hooks"), list)
                    and any(
                        isinstance(handler, dict)
                        and handler.get("command") == expected_legacy_launcher_command
                        for handler in group["hooks"]
                    )
                    for group in legacy_pretool
                )
                if (
                    isinstance(legacy_manifest, dict)
                    and set(legacy_manifest)
                    == {"hooks_file", "python_path", "pythonpath"}
                    and legacy_manifest.get("hooks_file") == str(hooks_path)
                    and isinstance(legacy_manifest.get("python_path"), str)
                    and legacy_manifest["python_path"]
                    and isinstance(legacy_manifest.get("pythonpath"), str)
                    and legacy_manifest["pythonpath"]
                    and regular_file(launcher_path)
                    and launcher_path.read_text(encoding="utf-8")
                    == _codex_v1_launcher_source(
                        legacy_manifest["python_path"], legacy_manifest["pythonpath"]
                    )
                    and launcher_hook_present
                ):
                    legacy_launcher_witness = True
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                pass

        def manifest_names(path: Path, key: str) -> set[str] | None:
            if not (path.exists() or path.is_symlink()):
                return None
            if not regular_file(path):
                errors.append(("unsafe-path", f"unsafe nWave manifest {path}"))
                return set()
            try:
                document = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(
                    ("corrupt-file", f"unreadable nWave manifest {path}: {exc}")
                )
                return set()
            names = document.get(key) if isinstance(document, dict) else None
            if (
                not isinstance(document, dict)
                or document.get("version") != "1.0"
                or not isinstance(names, list)
                or any(
                    not isinstance(name, str)
                    or not name.startswith("nw-")
                    or Path(name).name != name
                    for name in names
                )
                or len(names) != len(set(names))
            ):
                errors.append(("untrusted-content", f"untrusted nWave manifest {path}"))
                return set()
            return set(names)

        skill_manifest = (
            manifest_names(skills_dir / ".nwave-manifest.json", "installed_skills")
            if skills_dir_safe
            else None
        )
        agent_manifest = (
            manifest_names(
                agents_dir / ".nwave-agents-manifest.json", "installed_agents"
            )
            if agents_dir_safe
            else None
        )
        # This is deliberately separate from the manifest catalogue.  It can
        # contain only the closed set returned by the byte-level v1 witness;
        # no directory discovery result is ever promoted to ownership here.
        attested_legacy_skills: set[str] = set()

        # A v1 public Codex manifest historically omitted a closed pair of
        # command skills.  Its DES witness corroborates that this is the
        # bootstrap shape, while the skill helper proves every omitted tree
        # byte-for-byte.  No current command discovery participates here:
        # future nw-* directories remain foreign until a manifest records
        # them explicitly.
        if skills_dir_safe and skills_dir.exists() and skill_manifest is not None:
            try:
                from scripts.install.plugins.codex_skills_plugin import (
                    legacy_v1_omitted_command_skills,
                )

                skill_document = json.loads(
                    (skills_dir / ".nwave-manifest.json").read_text(encoding="utf-8")
                )
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                skill_document = None
            unlisted_skills = {
                path.name
                for path in skills_dir.glob("nw-*")
                if path.name not in skill_manifest
            }
            if unlisted_skills:
                omissions = (
                    legacy_v1_omitted_command_skills(skills_dir, skill_document)
                    if (legacy_direct_command is not None or legacy_launcher_witness)
                    else None
                )
                if omissions is not None and omissions == unlisted_skills:
                    attested_legacy_skills = omissions
                else:
                    errors.extend(
                        (
                            "foreign-collision-skill",
                            f"foreign or untracked Codex skill collision: {skills_dir / name}",
                        )
                        for name in sorted(unlisted_skills)
                    )

        # A reserved nWave name without a manifest is never trusted: it could
        # be a foreign file and the plugin would otherwise replace it.
        if skills_dir_safe and skills_dir.exists() and skill_manifest is None:
            for path in skills_dir.glob("nw-*"):
                errors.append(
                    (
                        "foreign-collision-skill",
                        f"foreign or untracked Codex skill collision: {path}",
                    )
                )
        if agents_dir_safe and agents_dir.exists() and agent_manifest is None:
            for path in agents_dir.glob("nw-*.toml"):
                if not (
                    legacy_direct_command is not None
                    and path.stem in legacy_agent_names
                ):
                    errors.append(
                        (
                            "foreign-collision-agent",
                            f"foreign or untracked Codex agent collision: {path}",
                        )
                    )

        if skill_manifest is not None:
            owned_skill_names = skill_manifest | attested_legacy_skills
            for name in owned_skill_names:
                if not safe_skill_tree(skills_dir / name):
                    errors.append(
                        (
                            "missing-owned-asset",
                            f"manifest-owned Codex skill is missing: {name}",
                        )
                    )
            for path in skills_dir.glob("nw-*"):
                if path.name not in owned_skill_names:
                    errors.append(
                        (
                            "foreign-collision-skill",
                            f"foreign or untracked Codex skill collision: {path}",
                        )
                    )
        if agent_manifest is not None:
            for name in agent_manifest:
                if not regular_file(agents_dir / f"{name}.toml"):
                    errors.append(
                        (
                            "missing-owned-asset",
                            f"manifest-owned Codex agent is missing: {name}",
                        )
                    )
            for path in agents_dir.glob("nw-*.toml"):
                if path.stem not in agent_manifest:
                    errors.append(
                        (
                            "foreign-collision-agent",
                            f"foreign or untracked Codex agent collision: {path}",
                        )
                    )

        hooks: object = None
        if regular_file(hooks_path):
            try:
                hooks_document = json.loads(hooks_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(
                    (
                        "corrupt-file",
                        f"malformed Codex hooks configuration {hooks_path}: {exc}",
                    )
                )
            else:
                hooks = (
                    hooks_document.get("hooks")
                    if isinstance(hooks_document, dict)
                    else None
                )
                if not isinstance(hooks, dict) or any(
                    not isinstance(entries, list) for entries in hooks.values()
                ):
                    errors.append(
                        (
                            "untrusted-content",
                            f"ambiguous Codex hooks configuration {hooks_path}",
                        )
                    )

        if regular_file(des_manifest_path):
            try:
                des_manifest = json.loads(des_manifest_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(
                    (
                        "corrupt-file",
                        f"unreadable nWave DES manifest {des_manifest_path}: {exc}",
                    )
                )
            else:
                if legacy_direct_command is not None:
                    # A public direct-hook bootstrap could leave behind the
                    # newer canonical launcher without recording it in its
                    # three-field manifest.  Adopt that orphan only when the
                    # direct hook is exact and the launcher round-trips to the
                    # fixed generated template with both embedded paths under
                    # this user's historical .nwave runtime root.
                    try:
                        from nwave_ai.upgrade_shell import (
                            _codex_build_hook_entry,
                            _codex_launcher_source,
                        )

                        expected_direct = _codex_build_hook_entry(
                            des_manifest["python_path"], des_manifest["pythonpath"]
                        )["hooks"][0]["command"]
                        legacy_direct_hook_witness = (
                            legacy_direct_command == expected_direct
                        )
                        launcher_source = launcher_path.read_text(encoding="utf-8")
                        launcher_tree = ast.parse(launcher_source)
                        launcher_values = {
                            node.targets[0].id: node.value.value
                            for node in launcher_tree.body
                            if isinstance(node, ast.Assign)
                            and len(node.targets) == 1
                            and isinstance(node.targets[0], ast.Name)
                            and isinstance(node.value, ast.Constant)
                            and isinstance(node.value.value, str)
                            and node.targets[0].id in {"PYTHON_PATH", "PYTHONPATH"}
                        }
                        launcher_python = launcher_values["PYTHON_PATH"]
                        launcher_pythonpath = launcher_values["PYTHONPATH"]
                        legacy_runtime_dir = install_root / ".nwave"
                        runtime_root_is_safe = (
                            not legacy_runtime_dir.is_symlink()
                            and legacy_runtime_dir.is_dir()
                        )
                        legacy_runtime_root = legacy_runtime_dir.resolve(strict=False)
                        lexical_runtime_root = Path(
                            os.path.normpath(str(legacy_runtime_dir))
                        )
                        lexical_python = Path(os.path.normpath(launcher_python))
                        pythonpath_is_contained = Path(
                            launcher_pythonpath
                        ).is_absolute() and Path(launcher_pythonpath).resolve(
                            strict=False
                        ).is_relative_to(legacy_runtime_root)
                        # The candidate venv's terminal interpreter is often
                        # a symlink to the host Python.  Its pathname and its
                        # parent must still be inside .nwave; only that final
                        # interpreter link may leave the runtime root.
                        python_is_contained = (
                            lexical_python.is_absolute()
                            and lexical_python.is_relative_to(lexical_runtime_root)
                            and lexical_python.parent.resolve(
                                strict=False
                            ).is_relative_to(legacy_runtime_root)
                        )
                        orphan_launcher_witness = (
                            legacy_direct_hook_witness
                            and regular_file(launcher_path)
                            and runtime_root_is_safe
                            and pythonpath_is_contained
                            and python_is_contained
                            and launcher_source
                            == _codex_launcher_source(
                                launcher_python, launcher_pythonpath
                            )
                        )
                    except (
                        KeyError,
                        OSError,
                        UnicodeDecodeError,
                        SyntaxError,
                        TypeError,
                        ValueError,
                    ):
                        orphan_launcher_witness = False
                    if launcher_path.exists() and not (
                        legacy_launcher_witness or orphan_launcher_witness
                    ):
                        errors.append(
                            (
                                "foreign-collision-manual",
                                f"untracked nWave DES launcher collision: {launcher_path}",
                            )
                        )
                elif not (
                    isinstance(des_manifest, dict)
                    and des_manifest.get("hooks_file") == str(hooks_path)
                    and des_manifest.get("launcher_file") == str(launcher_path)
                    and isinstance(des_manifest.get("python_path"), str)
                    and isinstance(des_manifest.get("pythonpath"), str)
                    and set(des_manifest)
                    in (
                        {
                            "hooks_file",
                            "python_path",
                            "pythonpath",
                            "launcher_file",
                        },
                        {
                            "hooks_file",
                            "python_path",
                            "pythonpath",
                            "launcher_file",
                            "session_start_launcher_file",
                            "resolver_script_file",
                        },
                    )
                ):
                    errors.append(
                        (
                            "untrusted-content",
                            f"untrusted nWave DES manifest {des_manifest_path}",
                        )
                    )
                else:
                    from nwave_ai.upgrade_shell import (
                        _codex_command_owns_launcher,
                        _codex_launcher_source,
                    )

                    try:
                        launcher_source = launcher_path.read_text(encoding="utf-8")
                    except OSError as exc:
                        errors.append(
                            (
                                "corrupt-file",
                                f"unreadable nWave DES launcher {launcher_path}: {exc}",
                            )
                        )
                    else:
                        if launcher_source != _codex_launcher_source(
                            des_manifest["python_path"], des_manifest["pythonpath"]
                        ):
                            errors.append(
                                (
                                    "untrusted-content",
                                    f"untrusted nWave DES launcher {launcher_path}",
                                )
                            )
                    has_owned_launcher_hook = isinstance(hooks, dict) and any(
                        isinstance(group, dict)
                        and any(
                            isinstance(handler, dict)
                            and _codex_command_owns_launcher(
                                handler.get("command", ""), launcher_path
                            )
                            for handler in group.get("hooks", [])
                            if isinstance(group.get("hooks", []), list)
                        )
                        for groups in hooks.values()
                        for group in groups
                    )
                    if not has_owned_launcher_hook:
                        errors.append(
                            (
                                "untrusted-content",
                                f"untrusted nWave DES hook {hooks_path}",
                            )
                        )
        elif launcher_path.exists():
            errors.append(
                (
                    "foreign-collision-manual",
                    f"untracked nWave DES launcher collision: {launcher_path}",
                )
            )

        self._report_ownership_preflight_errors(errors)
        if errors:
            return False
        self._attested_legacy_codex_skill_names = frozenset(attested_legacy_skills)
        return True

    _OWNERSHIP_PREFLIGHT_SAMPLE_LIMIT = 5

    def _report_ownership_preflight_errors(self, errors: list[tuple[str, str]]) -> None:
        """Emit the Codex ownership preflight refusal, aggregated with a HOW.

        A same-shape flood (e.g. one line per legacy Codex skill directory)
        must not become one near-identical, HOW-less log line per collision
        -- that buries the one fact the operator needs under noise (GDP-3)
        and forces them to read installer source to find the fix (GDP-4).
        Errors are grouped by ``kind``; each group prints a bounded sample
        (house style shared with e.g. check_trailing_whitespace.py's
        "... and N more") followed by the ONE remedy that fits that kind --
        never a single generic remedy reused across kinds that need
        different fixes. The method ends on an explicit verdict line so the
        log never simply stops on the last collision with the outcome left
        to be inferred.
        """
        if not errors:
            return
        by_kind: dict[str, list[str]] = {}
        for kind, line in errors:
            by_kind.setdefault(kind, []).append(line)
        for kind, lines in sorted(by_kind.items()):
            lines = sorted(lines)
            limit = self._OWNERSHIP_PREFLIGHT_SAMPLE_LIMIT
            for line in lines[:limit]:
                self.logger.error(f"  ❌ Ownership preflight: {line}")
            if len(lines) > limit:
                self.logger.error(f"       ... and {len(lines) - limit} more")
            how = _OWNERSHIP_PREFLIGHT_REMEDIES.get(kind)
            if how:
                self.logger.error(f"       HOW: {how}")
        self.logger.error(
            f"  ❌ Installation refused: {len(errors)} Codex ownership "
            f"collision(s) across {len(by_kind)} failure kind(s) -- "
            "0 files written, nothing changed."
        )

    def restore_backup(self) -> bool:
        """Restore from most recent backup.

        Returns True on success, False on failure. On success, the selected
        backup path is also exposed via ``self.last_restored_from`` (public
        observability contract — see ``__init__``). Bool return is preserved
        for the existing caller in ``main()``.
        """
        self.logger.info("  🔍 Looking for backups to restore...")

        backup_root = self.claude_config_dir / "backups"
        if not backup_root.exists():
            self.logger.error(f"  ❌ No backups found in {backup_root}")
            return False

        # Find latest backup
        backups = sorted(backup_root.glob("nwave-*"))
        if not backups:
            self.logger.error("  ❌ No nWave backups found")
            return False

        latest_backup = backups[-1]
        self.last_restored_from = latest_backup

        # dry_run must remain non-mutating, symmetrically with
        # BackupManager.create_backup's own dry_run branch: report the
        # backup that WOULD be restored from (selection is observable,
        # `last_restored_from` above is already set) without touching
        # agents_dir/commands_dir/skills_dir, and without the "complete"
        # verdict below, which would otherwise claim an actual restoration
        # never performed.
        if self.dry_run:
            self.logger.info(f"  🚨 [DRY RUN] Would restore from {latest_backup}")
            return True

        self.logger.info(f"  ⏳ Restoring from {latest_backup}")

        # Remove current installation
        agents_dir = self.claude_config_dir / "agents"
        commands_dir = self.claude_config_dir / "commands"

        if agents_dir.exists():
            import shutil

            shutil.rmtree(agents_dir)
        if commands_dir.exists():
            import shutil

            shutil.rmtree(commands_dir)

        # Restore from backup
        backup_agents = latest_backup / "agents"
        backup_commands = latest_backup / "commands"

        if backup_agents.exists():
            import shutil

            shutil.copytree(backup_agents, agents_dir)
            self.logger.info("  ✅ Agents restored")

        if backup_commands.exists():
            import shutil

            shutil.copytree(backup_commands, commands_dir)
            self.logger.info("  ✅ Commands restored")

        # Restore skills as an overlay, never a blanket delete: a legacy
        # backup predating skills/ capture must leave currently-installed
        # skills untouched, and a skill added independently after the
        # snapshot (absent from it) must survive restore too.
        backup_skills = latest_backup / "skills"
        if backup_skills.exists():
            import shutil

            skills_dir = self.claude_config_dir / "skills"
            skills_dir.mkdir(parents=True, exist_ok=True)
            shutil.copytree(backup_skills, skills_dir, dirs_exist_ok=True)
            self.logger.info("  ✅ Skills restored")

        self.logger.info(f"  🍾 Restoration complete from {latest_backup}")
        return True

    def _create_plugin_registry(
        self, silent: bool = False, target_platforms: set[str] | None = None
    ) -> PluginRegistry:
        """Create and configure the plugin registry with all installation plugins.

        Args:
            silent: When True, pass logger=None to suppress registration log messages.
            target_platforms: Set of platform strings to install for.
                When None or contains "claude_code", registers Claude Code plugins.
                When contains "opencode", also registers OpenCode plugins.

        Returns:
            PluginRegistry configured with plugins for the target platforms.
        """
        registry = PluginRegistry(logger=None if silent else self.logger)
        requested_platforms = target_platforms or {"claude_code"}

        # The hooks runtime is host-neutral; the kept hook set registers for
        # every target.  Every other shared plugin writes a Claude discovery
        # surface and is therefore registered only for Claude.
        registry.register(HooksPlugin())
        if "claude_code" in requested_platforms:
            registry.register(TemplatesPlugin())
            registry.register(UtilitiesPlugin())
            registry.register(AgentsPlugin())
            registry.register(CommandsPlugin())
            registry.register(SkillsPlugin())
        # Attribution is host-neutral; its execution boundary consumes the
        # immutable locations from InstallContext rather than resolving roots
        # while this registry only selects plugins.
        # NWAVE_AGENTS_HOME must come from that same location snapshot: falling
        # back to Path.home() here would put an isolated install's attribution
        # preference and hook runtime in the operator's real home.
        attribution_policy = HostAttributionPolicy.for_platforms(requested_platforms)
        if attribution_policy.claude_expected or attribution_policy.has_hosts:
            registry.register(
                AttributionPlugin(
                    policy=attribution_policy,
                )
            )
        # OpenCode plugins (registered when opencode detected)
        if target_platforms and "opencode" in target_platforms:
            opencode_skills = OpenCodeSkillsPlugin()
            opencode_agents = OpenCodeAgentsPlugin()
            opencode_commands = OpenCodeCommandsPlugin()
            registry.register(opencode_skills)
            registry.register(opencode_agents)
            registry.register(opencode_commands)
            opencode_agents.set_dependencies(["opencode-skills"])
            opencode_commands.set_dependencies(["opencode-skills"])
        # Codex CLI plugins (registered when codex detected)
        if target_platforms and "codex" in target_platforms:
            codex_skills = CodexSkillsPlugin()
            registry.register(codex_skills)
            codex_agents = CodexAgentsPlugin()
            codex_agents.set_dependencies(["codex-skills"])
            registry.register(codex_agents)
        # OMP's tool_call event accepts returned refusals; Python owns decisions.
        if target_platforms and "omp" in target_platforms:
            omp_skills = OmpSkillsPlugin()
            registry.register(omp_skills)
            omp_agents = OmpAgentsPlugin()
            omp_agents.set_dependencies(["omp-skills"])
            registry.register(omp_agents)
            registry.register(OmpCommandsPlugin())
        # Devin CLI plugins. Every public skill is installed, including the
        # user-invocable command-skills (equivalent to Claude Code commands).
        # Skills are discovered as /devin:nw-* slash commands (confirmed via
        # `devin skills list` on Devin 3000.6.14, 2026-10-11).
        # S4 CLOSED (A — platform limitation): Devin 3000.6.14 has no hook
        # subcommand and no hooks key in config.json. Probe confirmed via
        # `devin --help` and `devin config show` on 2026-10-11. Devin uses a
        # permissions model (Exec allow-lists in config.json) rather than
        # pre-tool-use hooks. DES enforcement is not possible on Devin.
        # S5 CONFIRMED GAP: `des` is not in PATH after a Devin install. The
        # DES runtime lands at ~/.claude/lib/python/des/ (not on PATH), so
        # `des design ...` invocations inside skill bodies cannot execute in
        # Devin's shell environment. Skills work as LLM methodology guidance;
        # DES step EXECUTION requires `PYTHONPATH=~/.claude/lib/python` or a
        # `des` shim on PATH. Probe confirmed on 2026-10-11.
        if target_platforms and "devin" in target_platforms:
            registry.register(DevinSkillsPlugin())
        registry.register(NwdesPlugin())
        if self.dev_mode and not self.dry_run:
            registry.register(DevLaunchersPlugin())
        return registry

    def record_codex_legacy_witness(self, present: bool) -> None:
        """Record whether the legacy cleanup found the Codex DES witness (F510).

        The Codex plugin adopts the legacy aliases only on a recorded True. The
        recorded value reaches the plugin context metadata in install_framework.
        """
        self._codex_legacy_witness = present

    def install_framework(self) -> bool:
        """Install framework files using plugin-based orchestration.

        Uses PluginRegistry to orchestrate installation of all components:
        - agents (priority 10)
        - commands (priority 20)
        - templates (priority 30)
        - skills (priority 35)
        - utilities (priority 40)

        Returns:
            True if all plugins installed successfully, False otherwise.
        """
        target_platforms = self.effective_target_platforms
        if self.dry_run:
            if target_platforms == frozenset({"codex"}):
                from scripts.install.plugins.codex_agents_plugin import (
                    _codex_agents_dir,
                )
                from scripts.install.plugins.codex_skills_plugin import (
                    _codex_skills_dir,
                )
                from scripts.shared.agent_catalog import (
                    build_ownership_map,
                    detect_command_skills,
                )
                from scripts.shared.skill_distribution import (
                    enumerate_skills,
                    filter_public_skills,
                )

                agents_source = self.framework_source / "agents"
                public_agents = (
                    set()
                    if self.dev_mode
                    else load_public_agents(self.project_root / "nWave")
                )
                agent_count = sum(
                    is_public_agent(source.name, public_agents)
                    for source in agents_source.glob("nw-*.md")
                )
                skills_source = self.framework_source / "skills"
                skill_entries = enumerate_skills(skills_source)
                if not self.dev_mode:
                    skill_entries = filter_public_skills(
                        skill_entries,
                        public_agents,
                        build_ownership_map(agents_source),
                        detect_command_skills(skills_source),
                    )
                self.logger.info(
                    f"  🚨 [DRY RUN] Would install {len(skill_entries)} Codex skills to "
                    f"{_codex_skills_dir()}"
                )
                self.logger.info(
                    f"  🚨 [DRY RUN] Would install {agent_count} Codex agents to "
                    f"{_codex_agents_dir()}"
                )
                self.logger.info(
                    "  🚨 [DRY RUN] Would install Codex DES hook to "
                    f"{self._locations.codex_config_dir / 'hooks.json'}"
                )
                return True
            # A non-Claude target must not have a Claude directory announced as
            # the install destination -- naming a path the run will never touch
            # is a silent-wrong (the user reads a location and finds it bare).
            if "claude_code" in target_platforms:
                self.logger.info(
                    f"  🚨 [DRY RUN] Would install nWave framework to: {self.claude_config_dir}"
                )
                self.logger.info(
                    f"  🚨 [DRY RUN] Would create target directory: {self.claude_config_dir}"
                )

            # Show what would be installed from nWave/ source
            agents_dir = self.project_root / "nWave" / "agents"
            commands_dir = self.project_root / "nWave" / "tasks" / "nw"

            if agents_dir.exists() and "claude_code" in target_platforms:
                agent_count = PathUtils.count_files(agents_dir, "nw-*.md")
                self.logger.info(
                    f"  🚨 [DRY RUN] Would install {agent_count} agent files"
                )

            if commands_dir.exists() and "claude_code" in target_platforms:
                command_count = PathUtils.count_files(commands_dir, "*.md")
                self.logger.info(
                    f"  🚨 [DRY RUN] Would install {command_count} command files"
                )

            if "omp" in target_platforms:
                from scripts.install.plugins.omp_agents_plugin import (
                    _find_agents_source,
                )
                from scripts.install.plugins.omp_skills_plugin import (
                    _find_skills_source,
                )
                from scripts.shared.agent_catalog import (
                    build_ownership_map,
                    detect_command_skills,
                    load_private_skills,
                )
                from scripts.shared.install_paths import omp_agents_dir, omp_skills_dir
                from scripts.shared.skill_distribution import (
                    enumerate_skills,
                    filter_public_skills,
                )

                omp_context = InstallContext(
                    claude_dir=self.claude_config_dir,
                    scripts_dir=self.project_root / "scripts" / "install",
                    templates_dir=self.framework_source / "templates",
                    logger=self.logger,
                    project_root=self.project_root,
                    framework_source=self.framework_source,
                    dev_mode=self.dev_mode,
                    dry_run=True,
                    target_platforms=set(target_platforms),
                )
                omp_public_agents = (
                    set()
                    if self.dev_mode
                    else load_public_agents(self.project_root / "nWave")
                )
                omp_agents_source = _find_agents_source(omp_context)
                omp_agent_count = 0
                if omp_agents_source is not None:
                    omp_agent_count = sum(
                        is_public_agent(f.name, omp_public_agents)
                        for f in omp_agents_source.glob("nw-*.md")
                    )
                omp_skills_source = _find_skills_source(omp_context)
                omp_skill_count = 0
                if omp_skills_source is not None:
                    omp_entries = enumerate_skills(omp_skills_source)
                    if not self.dev_mode:
                        omp_entries = filter_public_skills(
                            omp_entries,
                            omp_public_agents,
                            build_ownership_map(self.project_root / "nWave" / "agents"),
                            detect_command_skills(omp_skills_source),
                            load_private_skills(self.project_root / "nWave"),
                        )
                    omp_skill_count = len(omp_entries)
                self.logger.info(
                    f"  🚨 [DRY RUN] Would install {omp_skill_count} OMP skills to "
                    f"{omp_skills_dir()}"
                )
                self.logger.info(
                    f"  🚨 [DRY RUN] Would install {omp_agent_count} OMP agents to "
                    f"{omp_agents_dir()}"
                )
                commands_plan = OmpCommandsPlugin().install(omp_context)
                extension_plan = _install_omp_hooks_extension(omp_context)
                for plan in (commands_plan, extension_plan):
                    if not plan.success:
                        self.logger.error(plan.message)
                        return False

            if "devin" in target_platforms:
                from scripts.install.plugins.devin_skills_plugin import (
                    _find_skills_source as _find_devin_skills_source,
                )
                from scripts.shared.agent_catalog import (
                    build_ownership_map,
                    detect_command_skills,
                    load_private_skills,
                )
                from scripts.shared.install_paths import devin_skills_dir
                from scripts.shared.skill_distribution import (
                    enumerate_skills,
                    filter_public_skills,
                )

                devin_context = InstallContext(
                    claude_dir=self.claude_config_dir,
                    scripts_dir=self.project_root / "scripts" / "install",
                    templates_dir=self.framework_source / "templates",
                    logger=self.logger,
                    project_root=self.project_root,
                    framework_source=self.framework_source,
                    dev_mode=self.dev_mode,
                    dry_run=True,
                    target_platforms=set(target_platforms),
                )
                devin_skills_source = _find_devin_skills_source(devin_context)
                devin_skill_count = 0
                if devin_skills_source is not None:
                    devin_public_agents = (
                        set()
                        if self.dev_mode
                        else load_public_agents(self.project_root / "nWave")
                    )
                    devin_entries = enumerate_skills(devin_skills_source)
                    if not self.dev_mode:
                        devin_entries = filter_public_skills(
                            devin_entries,
                            devin_public_agents,
                            build_ownership_map(self.project_root / "nWave" / "agents"),
                            detect_command_skills(devin_skills_source),
                            load_private_skills(self.project_root / "nWave"),
                        )
                    devin_skill_count = len(devin_entries)
                self.logger.info(
                    f"  🚨 [DRY RUN] Would install {devin_skill_count} Devin skills to "
                    f"{devin_skills_dir()}"
                )

            return True

        self.logger.info("")
        # Announce the Claude directory ONLY when Claude Code is a target.  A
        # Codex/OpenCode/Copilot-only run writes nothing there, and naming a
        # path the run will never touch is a silent-wrong: the user reads a
        # location, follows the closing "reopen Claude Code" line, and finds an
        # empty directory.
        if "claude_code" in target_platforms:
            self.logger.info(f"  💿 Installing nWave → {self.claude_config_dir}")
        else:
            hosts = ", ".join(sorted(target_platforms))
            self.logger.info(f"  💿 Installing nWave → {hosts}")

        # Codex has no Claude activation surface.  Do not create an empty
        # ~/.claude directory merely because the installer knows its legacy
        # location.
        if "claude_code" in target_platforms:
            self.claude_config_dir.mkdir(parents=True, exist_ok=True)

        # Create plugin registry and install all components
        registry = self._create_plugin_registry(target_platforms=target_platforms)

        metadata = {
            _ATTESTED_LEGACY_SKILLS_METADATA_KEY: self._attested_legacy_codex_skill_names
        }
        if self._codex_legacy_witness is not None:
            metadata[_CODEX_LEGACY_WITNESS_KEY] = self._codex_legacy_witness

        # Create installation context with all required utilities
        context = InstallContext(
            claude_dir=self.claude_config_dir,
            scripts_dir=self.project_root / "scripts" / "install",
            templates_dir=self.framework_source / "templates",
            logger=self.logger,
            project_root=self.project_root,
            user_project_root=self.user_project_root,
            locations=self._locations,
            framework_source=self.framework_source,
            dry_run=self.dry_run,
            dev_mode=self.dev_mode,
            target_platforms=target_platforms,
            metadata=metadata,
        )

        self.logger.info("  📑 Installing Context...")
        with self.logger.progress_spinner("  🚧 Work in progress..."):
            # Execute all plugins through registry
            results = registry.install_all(context)

        # The OMP guard extension is installed outside the registry: its kept
        # template needs the resolved interpreter and host-neutral runtime.
        if "omp" in target_platforms:
            omp_result = _install_omp_hooks_extension(context)
            results["omp-nwave-hooks"] = omp_result

        # Check if any plugin failed
        for plugin_name, result in results.items():
            if not result.success:
                self.logger.error(
                    f"  ❌ Plugin '{plugin_name}' failed: {result.message}"
                )
                return False

        # Close on the PROPERTY, not on "the branch was taken": an announced
        # Claude target that is still empty here means the run would otherwise
        # report success over a directory the user will find bare.  Degrade
        # LOUD rather than let the declared fact and the disk diverge.
        if "claude_code" in target_platforms and not any(
            self.claude_config_dir.iterdir()
        ):
            self.logger.error(
                f"  ❌ WHAT: nothing was installed into {self.claude_config_dir}, "
                "yet it was announced as the install target."
            )
            self.logger.error(
                "  WHY: the Claude Code plugins produced no files, so Claude Code "
                "would start with no nWave agents, skills or commands."
            )
            self.logger.error(
                "  HOW: re-run the installer with the target made explicit -- "
                f"CLAUDE_CONFIG_DIR={self.claude_config_dir} "
                "python -m nwave_ai.cli install"
            )
            return False

        return True

    def validate_installation(self) -> bool:
        """Validate installation using shared InstallationVerifier.

        Uses the InstallationVerifier module for consistent verification logic
        between standalone verification and post-build verification.

        Returns:
            True if verification passed, False otherwise.
        """
        target_platforms = self.effective_target_platforms
        codex_valid = True
        if "codex" in target_platforms:
            codex_only = target_platforms == {"codex"}
            codex_valid = self._validate_codex_installation(verify_plugins=codex_only)
            if codex_only:
                return codex_valid

        self.logger.info("")
        self.logger.info("  🔎 Validate Installation...")
        with self.logger.progress_spinner("  🚧 Work in progress..."):
            # Use shared InstallationVerifier for consistent verification
            verifier = InstallationVerifier(
                claude_config_dir=self.claude_config_dir,
                use_host_neutral_runtime="claude_code" not in target_platforms,
                check_essential_commands="claude_code" in target_platforms,
                check_manifest="claude_code" in target_platforms,
                require_runtime_package=False,
            )
            result = verifier.run_verification()

        # Plugin verification via registry.verify_all()
        plugin_registry = self._create_plugin_registry(
            silent=True, target_platforms=target_platforms
        )
        plugin_context = InstallContext(
            claude_dir=self.claude_config_dir,
            scripts_dir=self.project_root / "scripts" / "install",
            templates_dir=self.framework_source / "templates",
            logger=self.logger,
            project_root=self.project_root,
            user_project_root=self.user_project_root,
            locations=self._locations,
            framework_source=self.framework_source,
            dry_run=self.dry_run,
            dev_mode=self.dev_mode,
            target_platforms=target_platforms,
        )
        plugin_results = plugin_registry.verify_all(plugin_context)
        plugin_failures = {
            name: r for name, r in plugin_results.items() if not r.success
        }

        # Verify components: compare source files vs installed target
        # Supports both dist/ layout (agents/nw/, commands/nw/) and
        # nWave/ source layout (agents/nw-*.md, tasks/nw/*.md)
        #
        # Agents/Commands/Templates/Scripts are all shipped by plugins that
        # _create_plugin_registry registers ONLY when "claude_code" is in the
        # requested platforms (TemplatesPlugin, UtilitiesPlugin, AgentsPlugin,
        # CommandsPlugin, SkillsPlugin -- "every other shared plugin writes a
        # Claude discovery surface"). A Copilot/OpenCode-only target never
        # gets those plugins, so judging it against these components' source
        # counts fails validation unconditionally, regardless of whether the
        # install the target actually owns succeeded.
        all_synced = True
        components: list[ComponentResult] = []

        if "claude_code" in target_platforms:
            # Agents: dist/agents/nw/ or nWave/agents/
            # In dev_mode, all agents are installed; otherwise only public
            dist_agents = self.framework_source / "agents" / "nw"
            if dist_agents.exists():
                agents_source = dist_agents
            else:
                agents_source = self.project_root / "nWave" / "agents"
            agents_target = self.claude_config_dir / "agents" / "nw"
            if agents_source.exists():
                public_agents = (
                    set()
                    if self.dev_mode
                    else load_public_agents(self.project_root / "nWave")
                )
                agent_source_files = sorted(
                    f
                    for f in agents_source.glob("nw-*.md")
                    if is_public_agent(f.name, public_agents)
                )
                agent_matched = sum(
                    1 for f in agent_source_files if (agents_target / f.name).exists()
                )
                agent_expected = len(agent_source_files)
                agent_ok = agent_matched == agent_expected and agent_expected > 0
                if not agent_ok:
                    all_synced = False
                components.append(
                    ComponentResult("agents", agent_matched, agent_expected, agent_ok)
                )
                self.logger.info(
                    f"    {'✅' if agent_ok else '❌'} Agents verified ({agent_matched}/{agent_expected})"
                )

            # Commands: now installed as skills (nw-{name}/SKILL.md with user-invocable)
            skills_target = self.claude_config_dir / "skills"
            essential_commands = [
                "nw-deliver",
                "nw-design",
                "nw-discuss",
                "nw-distill",
                "nw-devops",
                "nw-review",
            ]
            cmd_matched = sum(
                1
                for name in essential_commands
                if (skills_target / name / "SKILL.md").exists()
            )
            cmd_expected = len(essential_commands)
            cmd_ok = cmd_matched == cmd_expected
            if not cmd_ok:
                all_synced = False
            components.append(
                ComponentResult("commands", cmd_matched, cmd_expected, cmd_ok)
            )
            self.logger.info(
                f"    {'✅' if cmd_ok else '❌'} Commands verified ({cmd_matched}/{cmd_expected})"
            )

            # Templates from framework_source/templates/
            #
            # Content-aware verify (M1 fix-installer-silent-template-skip): replace
            # the existence-only check with a SHA-256 compare so a stale target that
            # diverges from source is reported as drift instead of "verified".
            templates_source = self.framework_source / "templates"
            templates_target = self.claude_config_dir / "templates"
            if templates_source.exists():
                tmpl_matched, tmpl_drifted = verify_directory_content(
                    templates_source, templates_target
                )
                tmpl_expected = tmpl_matched + len(tmpl_drifted)
                tmpl_ok = _component_synced(tmpl_matched, tmpl_expected)
                if not tmpl_ok:
                    all_synced = False
                components.append(
                    ComponentResult("templates", tmpl_matched, tmpl_expected, tmpl_ok)
                )
                self.logger.info(
                    f"    {'✅' if tmpl_ok else '❌'} Templates verified ({tmpl_matched}/{tmpl_expected})"
                )
                for drifted in tmpl_drifted:
                    self.logger.error(
                        f"      ❌ Content drift: templates/{drifted} differs from source "
                        f"(re-run `python -m nwave_ai.cli install` to refresh)"
                    )

            # Scripts: dist/scripts/ or project_root/scripts/
            dist_scripts = self.framework_source / "scripts"
            if (
                dist_scripts.exists()
                and (dist_scripts / "install_nwave_target_hooks.py").exists()
            ):
                scripts_source = dist_scripts
            else:
                scripts_source = self.project_root / "scripts"
            scripts_target = self.claude_config_dir / "scripts"
            utility_scripts = ["install_nwave_target_hooks.py", "validate_step_file.py"]
            script_files = [s for s in utility_scripts if (scripts_source / s).exists()]
            script_matched = sum(
                1 for s in script_files if (scripts_target / s).exists()
            )
            script_expected = len(script_files)
            script_ok = _component_synced(script_matched, script_expected)
            if not script_ok:
                all_synced = False
            components.append(
                ComponentResult("scripts", script_matched, script_expected, script_ok)
            )
            self.logger.info(
                f"    {'✅' if script_ok else '❌'} Scripts verified ({script_matched}/{script_expected})"
            )

        self.logger.info(
            f"    {'✅' if result.manifest_exists else '❌'} Manifest created"
        )

        # Report missing essential files
        if result.missing_essential_files:
            for missing_file in result.missing_essential_files:
                self.logger.error(f"    ❌ Missing essential: {missing_file}")

        # Report plugin verification results
        if plugin_failures:
            for name, r in plugin_failures.items():
                self.logger.error(
                    f"    ❌ {name} plugin verification failed: {r.message}"
                )
                for err in r.errors:
                    self.logger.error(f"      ❌ {err}")
        else:
            self.logger.info("    ✅ All plugins verified")

        # Determine overall success
        overall_success = (
            result.success and all_synced and not plugin_failures and codex_valid
        )

        if overall_success:
            self.logger.info("  🍾 Deployment validated")
            return True
        else:
            # Identify every failing condition for clear diagnostics
            failures: list[str] = []
            if not result.success:
                failures.append("essential files missing")
            if not all_synced:
                failures.append(_format_sync_mismatch(components))
            if plugin_failures:
                failures.append(
                    f"plugin verification failed: {', '.join(plugin_failures)}"
                )
            if not codex_valid:
                failures.append("Codex validation failed")
            if not result.manifest_exists:
                failures.append("manifest not created")
            detail = "; ".join(failures) if failures else "unknown condition"
            self.logger.error(
                f"  ❌ Validation failed ({len(failures)} issues: {detail})"
            )
            return False

    def _validate_codex_installation(self, *, verify_plugins: bool = True) -> bool:
        """Validate the Codex-native discovery surfaces selected for this install.

        The Codex skill manifest is the ownership oracle: a public release may
        legitimately omit skills that are private or unavailable for that host.
        Requiring a separate hard-coded command list here would turn that
        policy into a false deployment failure.  The Codex plugin verifies every
        manifest-declared skill; the all-target registry below independently
        verifies the Copilot and OpenCode surfaces.

        Args:
            verify_plugins: run the Codex-scoped plugin registry check here.
                False when the caller is about to run the full all-target
                registry check right after -- that check already covers the
                Codex plugin, and running both double-invokes the same
                registry.verify_all() for no additional signal.
        """
        self.logger.info("")
        self.logger.info("  🔎 Validate Codex Installation...")

        install_root = self._locations.agents_home
        skills_dir = install_root / ".agents" / "skills"
        codex_home = self._locations.codex_config_dir
        native_artifacts = [
            skills_dir / ".nwave-manifest.json",
            codex_home / "agents" / ".nwave-agents-manifest.json",
            codex_home / "hooks.json",
        ]
        missing = [path for path in native_artifacts if not path.exists()]

        plugin_failures: dict[str, object] = {}
        if verify_plugins:
            registry = self._create_plugin_registry(
                silent=True, target_platforms={"codex"}
            )
            context = InstallContext(
                claude_dir=self.claude_config_dir,
                scripts_dir=self.project_root / "scripts" / "install",
                templates_dir=self.framework_source / "templates",
                logger=self.logger,
                project_root=self.project_root,
                user_project_root=self.user_project_root,
                locations=self._locations,
                framework_source=self.framework_source,
                dry_run=self.dry_run,
                dev_mode=self.dev_mode,
                target_platforms={"codex"},
            )
            plugin_failures = {
                name: result
                for name, result in registry.verify_all(context).items()
                if not result.success
            }
        for path in missing:
            self.logger.error(f"    ❌ Missing Codex artifact: {path}")
        for name, result in plugin_failures.items():
            self.logger.error(
                f"    ❌ {name} plugin verification failed: {result.message}"
            )

        if missing or plugin_failures:
            self.logger.error("  ❌ Codex deployment validation failed")
            return False
        self.logger.info("  🍾 Codex deployment validated")
        return True

    def create_manifest(self) -> None:
        """Create installation manifest."""
        if self.dry_run:
            self.logger.info("  🚨 [DRY RUN] Would create installation manifest")
            return

        ManifestWriter.write_install_manifest(
            self.claude_config_dir,
            self.backup_manager.backup_dir,
            self.script_dir,
            target_platforms=self.effective_target_platforms,
        )

        self.logger.info(
            f"  📄 Installation manifest created: {self.claude_config_dir / 'nwave-manifest.txt'}"
        )


def _force_utf8_console() -> None:
    """Make stdout/stderr able to carry the installer's non-ASCII output.

    The logo's block glyphs and the wave/siren emoji are unrepresentable in
    cp1252, still the default console encoding on a non-UTF-8 Windows box. The
    logo prints before any real work, so an encode error there is a hard install
    failure at the first line of output -- for decoration.

    ``errors="replace"`` is the second belt: if the encoding cannot be changed
    the output degrades to replacement characters instead of raising. A stream
    that cannot reconfigure at all is left alone rather than crashing the
    installer over cosmetics.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            try:
                reconfigure(errors="replace")
            except (ValueError, OSError):
                pass


def print_logo(logger: Logger | None = None) -> None:
    """Print the nWave ASCII art logo with version and taglines.

    Uses Rich markup via logger when available, ANSI fallback otherwise.
    """
    if logger:
        out = logger.print_styled
        wrap = lambda line: f"[cyan]{line}[/cyan]"  # noqa: E731
    else:
        out = print
        wrap = lambda line: f"{_ANSI_BLUE}{line}{_ANSI_NC}"  # noqa: E731

    out("")
    for line in _LOGO_ART[:-1]:
        out(wrap(line))
    out(f"{wrap(_LOGO_ART[-1])}  \U0001f30a \U0001f30a \U0001f30a  v{_get_version()}")
    out("")
    for tagline in _TAGLINES:
        out(tagline)


def show_title_panel(logger: Logger, dry_run: bool = False) -> None:
    """Display styled title panel when installer starts."""
    print_logo(logger)

    if dry_run:
        logger.print_styled(" 🚨 \\[DRY RUN]")

    logger.print_styled("")


def show_installation_summary(
    logger: Logger,
    target_dir: Path | None = None,
    target_platforms: set[str] | None = None,
) -> None:
    """Display installation summary panel at end of successful install."""
    codex_only = target_platforms == {"codex"}
    logger.info("")
    logger.info(f"  🎉 nWave v{_get_version()} installed and healthy!")
    if target_dir is not None and (
        target_platforms is None or target_platforms == {"claude_code"}
    ):
        logger.info(f"  📂 Installed to: {target_dir}")
    logger.info("")
    logger.info("  📖 Quick start")
    command_prefix = "$" if codex_only else "/"
    commands = [
        (f"{command_prefix}nw-discover", "Evidence-based product discovery"),
        (
            f"{command_prefix}nw-discuss",
            "Requirements gathering and business analysis",
        ),
        (
            f"{command_prefix}nw-design",
            "Architecture design with visual representation",
        ),
        (
            f"{command_prefix}nw-distill",
            "Acceptance test creation and business validation",
        ),
        (
            f"{command_prefix}nw-deliver",
            "Outside-In TDD implementation with refactoring",
        ),
    ]
    for cmd, desc in commands:
        logger.info(f"    {cmd:<16} {desc}")
    mixed_hosts = bool(
        target_platforms and {"claude_code", "codex"}.issubset(target_platforms)
    )
    if mixed_hosts:
        logger.info(
            "    $nw-design       Architecture design with visual representation"
        )
    cli_entry = Path(sys.executable).with_name("nwave-ai")
    project_cli = shlex.quote(str(cli_entry)) if cli_entry.is_file() else "nwave-ai"
    logger.info(f"  💡 In the target Git project, run: {project_cli} project enable")
    logger.info(f"  💡 Check activation: {project_cli} project status")
    omp_selected = bool(target_platforms and "omp" in target_platforms)
    if codex_only:
        logger.info("  ⚠️  Quit and reopen Codex to load the new agents and skills.")
        logger.info("  💡 In the activated project, ask $nw-buddy what to do first.")
    elif mixed_hosts:
        logger.info(
            "  ⚠️  Quit and reopen Claude Code to load the new agents, skills, and commands."
        )
        logger.info("  ⚠️  Quit and reopen Codex to load the new agents and skills.")
        logger.info(
            "  💡 In the activated project, ask /nw-buddy in Claude Code or $nw-buddy in Codex."
        )
    elif omp_selected and target_platforms == frozenset({"omp"}):
        logger.info("  💡 In the activated project, ask /nw-buddy what to do first.")
    else:
        logger.info(
            "  ⚠️  Quit and reopen Claude Code to load the new agents, skills, and commands."
        )
        logger.info("  💡 In the activated project, ask /nw-buddy what to do first.")
    if omp_selected:
        logger.info(
            "  ⚠️  Quit and reopen OMP to load agents, skills, commands and the tool_call guard extension."
        )
        logger.info(
            "  💡 In OMP, dispatch nw-* task agents via Task, or invoke /skill:nw-<name>."
        )
        logger.info(f"  ⚠️  {OMP_GUARD_CEILING}")
    logger.info("  📚 Docs: https://github.com/nWave-ai/nWave")


# Single source of truth for --platform: argparse choices, the target set each choice
# resolves to, the no-host refusal and the help listing all read this table.
# Row: (flag, target platform or None for auto-detect, what that choice installs).
_HOST_PLATFORMS: tuple[tuple[str, str, str], ...] = (
    (
        "claude-code",
        "claude_code",
        "agents, /nw-* commands, skills, templates and hooks",
    ),
    ("opencode", "opencode", "agents, /nw-* commands and skills"),
    ("codex", "codex", "skills, TOML agents and hooks"),
    ("cursor", "cursor", "hooks only"),
    ("copilot", "copilot", "hooks only"),
    ("omp", "omp", "agents, skills, /nw-* commands and the tool_call guard extension"),
    ("devin", "devin", "skills only"),
)
_PLATFORM_CHOICES: tuple[tuple[str, frozenset[str] | None, str], ...] = (
    ("auto", None, "detect installed hosts; refuses when none is found"),
    *(
        (flag, frozenset({platform}), meaning)
        for flag, platform, meaning in _HOST_PLATFORMS
    ),
    (
        "all",
        frozenset(platform for _flag, platform, _meaning in _HOST_PLATFORMS),
        "every host above",
    ),
)


def _platform_help_lines() -> str:
    """One help line per --platform choice, rendered from ``_PLATFORM_CHOICES``."""
    return "\n".join(
        f"      {flag:<12} {meaning}" for flag, _targets, meaning in _PLATFORM_CHOICES
    )


def _explicit_platform_names() -> str:
    """Comma-separated --platform names that name a target; auto-detect excluded."""
    return ", ".join(
        flag for flag, targets, _meaning in _PLATFORM_CHOICES if targets is not None
    )


def show_help():
    """Show help message."""
    B, N = _ANSI_BLUE, _ANSI_NC

    print()
    for line in _LOGO_ART[:-1]:
        print(f"{B}{line}{N}")
    print(f"{B}{_LOGO_ART[-1]}{N}  \U0001f30a \U0001f30a \U0001f30a  v{_get_version()}")
    print()
    for tagline in _TAGLINES:
        print(tagline)

    help_text = f"""
{B}DESCRIPTION:{N}
    Installs the nWave methodology framework to your global AI coding host
    config directory (Claude Code, OpenCode, Codex, Cursor, Copilot, OMP, Devin).
    This makes all specialized agents and commands available across all projects.

{B}USAGE:{N}
    nwave-ai install [OPTIONS]

{B}OPTIONS:{N}
    --platform <name>  Target host (default: auto). One of:
{_platform_help_lines()}
    --backup-only      Create backup of existing nWave installation without installing
    --restore          Restore from the most recent backup
    --dry-run          Show what would be installed without making any changes.
                       Also surfaces Codex ownership-collision refusals safely,
                       before a real install -- run this first if unsure.
    --dev              Install ALL agents, skills and OMP commands (including private)
    --help             Show this help message

{B}EXAMPLES:{N}
    nwave-ai install --platform claude-code      # Install for Claude Code
    nwave-ai install --platform codex --dry-run  # Preview a Codex install
    nwave-ai install --backup-only               # Create backup only
    nwave-ai install --restore                   # Restore from latest backup

{B}WHAT GETS INSTALLED:{N}
    - nWave agents, skills and /nw-* commands for the methodology waves
      (DISCOVER\u2192DISCUSS\u2192DESIGN\u2192DEVOP\u2192DISTILL\u2192DELIVER), per host
    - nWave hook registrations for claude-code, codex, cursor and copilot
    - nwdes is not installed: the installer checks that `python -m nwdes --help` runs

{B}INSTALLATION LOCATION:{N}
    ~/.claude/agents/nw/    # nWave agent specifications
    ~/.claude/commands/nw/  # nWave command integrations
    ~/.claude/templates/    # nWave authoring templates
    ~/.omp/agent/agents/    # OMP: nWave task agents (native)
    ~/.omp/agent/skills/    # OMP: nWave skills (native; PI_CONFIG_DIR renames .omp)
    ~/.omp/agent/commands/  # OMP: /nw-* slash commands
    # OMP commands project nWave/tasks/nw/*.md through the public catalog.
    ~/.omp/agent/extensions/nwave-hooks.ts  # OMP: nWave tool_call guard
    PI_CODING_AGENT_DIR relocates OMP skills, commands and extensions.
    {OMP_GUARD_CEILING}
    # OMP installs no hooks: OMP extension events differ from Claude Code
    # hooks, so nWave guard enforcement is not projected onto OMP.
    ~/.codex/hooks.json      # Codex PreToolUse hook configuration (if codex enabled)
    ~/.agents/skills/        # Codex SKILL.md registry (if codex enabled)
    ~/.codex/agents/         # Codex TOML agents (if codex enabled)
    ~/.cursor/hooks.json     # Cursor preToolUse hook configuration (if cursor enabled)

For more information: https://github.com/nWave-ai/nWave
"""
    print(help_text)


def _resolve_platform_override(platform_flag: str) -> set[str] | None:
    """Resolve CLI --platform flag to a platform override set.

    Args:
        platform_flag: One of the flags in ``_PLATFORM_CHOICES``.

    Returns:
        None for auto-detect, or a set of platform string values.
    """
    targets = {flag: platforms for flag, platforms, _meaning in _PLATFORM_CHOICES}
    selected = targets[platform_flag]
    return None if selected is None else set(selected)


def main():
    """Main entry point."""
    _force_utf8_console()
    parser = argparse.ArgumentParser(
        description="Install nWave framework", add_help=False
    )
    parser.add_argument("--backup-only", action="store_true", help="Create backup only")
    parser.add_argument("--restore", action="store_true", help="Restore from backup")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be done"
    )
    parser.add_argument("--help", "-h", action="store_true", help="Show help")
    parser.add_argument(
        "--platform",
        choices=[flag for flag, _targets, _meaning in _PLATFORM_CHOICES],
        default="auto",
        help="Target platform (default: auto-detect)",
    )
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Install ALL agents and skills (not just public). For local dev only.",
    )
    # Retired (Ruling B): accepted only so that a run passing it is refused with
    # a WHAT/WHY/HOW report. Hidden from --help.
    parser.add_argument(
        "--adopt-legacy-codex-dev",
        action="store_true",
        help=argparse.SUPPRESS,
    )

    args = parser.parse_args()

    if args.help:
        show_help()
        return 0

    # Ruling B: the retired legacy dev quarantine flag is refused before the
    # installer is built, before the install lock and before any write.
    if args.adopt_legacy_codex_dev:
        print(_LEGACY_CODEX_DEV_FLAG_REFUSAL, file=sys.stderr)
        return 2

    # Resolve platform override from CLI flag
    platform_override = _resolve_platform_override(args.platform)

    installer = NWaveInstaller(
        dry_run=args.dry_run,
        platform_override=platform_override,
        dev_mode=args.dev,
    )

    # Auto-detection must never guess a host.  In particular, defaulting an
    # empty result to Claude mutates a configuration the operator may not use.
    # Refuse before title/preflight/backup/install surfaces so this path has no
    # filesystem write effect; an explicit --platform remains authoritative.
    if not installer.effective_target_platforms:
        print(
            "No supported AI coding host was detected; rerun with "
            f"--platform one of {_explicit_platform_names()}.",
            file=sys.stderr,
        )
        return 2

    # A native-only target (no claude_code selected) has no Claude backup or
    # restore surface -- restore must stay a no-op without consulting or
    # naming a Claude directory it would never have written.
    if args.restore and "claude_code" not in installer.effective_target_platforms:
        return 0

    # ONE install at a time, per destination (GDP-0: make the torn state
    # unrepresentable instead of asking the operator to remember a rule).
    # Two concurrent installs into the same root leave a half-written runtime,
    # a roster that briefly vanishes and private agents rewritten by the other
    # run's asset set -- observed twice on 2026-08-21/22, minutes apart.
    #
    # Taken HERE: after the no-write refusal paths above (an unsupported host,
    # a Codex restore no-op) so a refusal still touches nothing, and BEFORE the
    # title panel, preflight, backup and install so no effort is spent on a run
    # that cannot proceed (GDP-1).
    if args.dry_run:
        # A dry run writes nothing, so it has nothing to serialize -- and it
        # must stay usable for inspecting an install that is running RIGHT NOW.
        return _run_install(args, installer)

    try:
        with install_lock(
            target_platforms=",".join(sorted(installer.effective_target_platforms))
        ):
            return _run_install(args, installer)
    except InstallLockHeld as held:
        print(str(held), file=sys.stderr)
        return EXIT_INSTALL_LOCK_HELD


def _run_install(args: argparse.Namespace, installer: "NWaveInstaller") -> int:
    """Run the install stages that WRITE, under the caller's install lock.

    Split out of ``main()`` so the lock wraps every write-bearing stage in one
    ``with`` block: backup, install, manifest and validation all
    release the lock on the way out, including on an exception or a Ctrl-C.
    ``main()`` keeps only argument parsing and the no-write refusal paths.
    """
    # Show title panel at startup
    show_title_panel(installer.logger, dry_run=args.dry_run)

    # Run preflight checks BEFORE any build or installation actions
    preflight = PreflightChecker()
    preflight_results = preflight.run_all_checks()

    # Display preflight results in TUI format
    installer.logger.info("  \U0001f50d Pre-flight checks")
    for result in preflight_results:
        if result.passed:
            installer.logger.info(f"  \u2705 {result.message}")
        else:
            installer.logger.error(f"  \u274c {result.message}")

    if preflight.has_blocking_failures(preflight_results):
        for failed_check in preflight.get_failed_checks(preflight_results):
            error_message = format_error(
                error_code=failed_check.error_code,
                message=failed_check.message,
                remediation=failed_check.remediation or "No remediation available.",
                recoverable=False,
            )
            installer.logger.error(error_message)
        return 1

    installer.logger.info("  \u2705 Pre-flight passed")
    installer.logger.info("")

    if args.dry_run:
        installer.logger.warn("  🚨 DRY RUN MODE - No changes will be made")

    # Handle backup-only mode
    if args.backup_only:
        # A native-only target (Codex, Copilot, OpenCode, or any combination
        # of them without Claude) has no Claude backup surface at all -- do
        # not enable Claude install logging or touch claude_config_dir for it.
        if "claude_code" not in installer.effective_target_platforms:
            return 0
        installer.enable_install_logging()
        installer.create_backup()
        installer.logger.info("  🍾 Backup completed successfully")
        return 0

    # Handle restore mode
    if args.restore:
        if installer.restore_backup():
            if args.dry_run:
                installer.logger.info(
                    "  🚨 [DRY RUN] Restoration preview complete -- no files changed"
                )
            else:
                installer.logger.info("  🍾 Restoration completed successfully")
            return 0
        else:
            return 1

    # Normal installation
    # validate_codex_ownership_preflight already emits a full WHAT/WHY/HOW
    # report plus a "0 files written" verdict line for every collision when
    # it refuses (see _report_ownership_preflight_errors) -- no separate
    # generic message here, or the operator sees a redundant, less useful
    # second verdict on top of the specific one.
    if not installer.validate_codex_ownership_preflight():
        return 1

    if args.dry_run:
        return 0 if installer.install_framework() else 1

    # A native-only target (Codex, Copilot, OpenCode, or any combination of
    # them without Claude) has no Claude activation surface -- persistent
    # install logging must never create or write under claude_config_dir for
    # it. create_backup() is safe to call unconditionally: its Codex branch
    # never touches claude_config_dir, and its default (Claude) branch is a
    # no-op unless a prior Claude installation already exists on disk.
    if "claude_code" in installer.effective_target_platforms:
        installer.enable_install_logging()
    installer.create_backup()

    # Upgrade cleanup runs after the ownership preflight and the backup, and before
    # the new install writes. A refusal stops the run before anything is installed.
    # Its Codex witness decides the Codex alias adoption in this same install (F510).
    outcome = run_legacy_cleanup(str(Path.home()), sys.stdout, sys.stderr, real_port())
    if outcome.exit_code != 0:
        return 1

    installer.record_codex_legacy_witness(outcome.codex_witness is not None)
    if not installer.install_framework():
        return 1

    # Create manifest after installation but before validation
    # This prevents circular dependency where validation fails because
    # manifest doesn't exist yet. Only "claude_code" targets get a Claude
    # discovery surface (claude_config_dir) for the manifest to live in --
    # a native-only target (single or combined) must not create one.
    if "claude_code" in installer.effective_target_platforms:
        installer.create_manifest()

    # Dry-run preview: install_framework + create_manifest already returned
    # without side effects (each plugin honors context.dry_run). Skip the
    # post-install verifier — it asserts real installation state which by
    # definition does not exist in a dry-run preview. Fix for v1.1.14+
    # regression where --dry-run exited 1 with "DES config not found".
    if installer.dry_run:
        installer.logger.info("")
        installer.logger.info(
            "  🍾 Dry-run preview complete (no changes made, verifier skipped)"
        )
        return 0

    if installer.validate_installation():
        installer.report_kept_snapshots()
        # Record install provenance (machine-scoped ~/.nwave by default) so
        # the doctor VersionSyncCheck can later detect a package upgraded
        # without re-running install. Best-effort; never fails the run.
        #
        # NWAVE_AGENTS_HOME honored here too (same override every other
        # ~/.nwave-rooted read/write in this file already honors -- see
        # create_backup,
        # validate_codex_ownership_preflight, show_installation_summary's
        # helper): an isolated caller (e.g. a K4 harness campaign arm) that
        # pins it must never have this write land in the operator's real
        # home instead. Default is unchanged when unset.
        #
        # Known limitation: the record is keyed to the machine, NOT the install
        # target. A `--target` install shares this single ~/.nwave record with
        # the default install, so maintaining two targets backed by different
        # venvs could surface a spurious drift warning on the target not last
        # installed. Single-target is the norm; left as-is deliberately.
        installed_version = _detect_installed_version()
        from scripts.shared.install_paths import omp_agent_dir, omp_skills_dir

        try:
            record_install_metadata(
                installer._locations.agents_home / ".nwave" / "config.json",
                installed_version=installed_version,
                repo_root=installer.user_project_root,
                provenance=InstallProvenance(
                    target_platforms=installer.effective_target_platforms,
                    dev_mode=args.dev,
                    host_paths={
                        "agents_home": str(installer._locations.agents_home),
                        "claude_config_dir": str(
                            installer._locations.claude_config_dir
                        ),
                        "codex_config_dir": str(installer._locations.codex_config_dir),
                        **(
                            {
                                "omp_agent_dir": str(omp_agent_dir()),
                                "omp_skills_dir": str(omp_skills_dir()),
                            }
                            if "omp" in installer.effective_target_platforms
                            else {}
                        ),
                    },
                ),
            )
        except Exception as exc:
            installer.logger.error(
                "WHAT: the validated install did not persist its selected host "
                f"and mode. WHY: {exc}. HOW: repair the global config writer "
                "and rerun the same install command; do not attempt automatic "
                "updates until provenance is recorded."
            )
            return 1

        installer.logger.info("")
        show_installation_summary(
            installer.logger,
            installer.claude_config_dir,
            target_platforms=installer.effective_target_platforms,
        )

        return 0
    else:
        installer.logger.error("  ❌ Installation failed validation")
        installer.logger.warn("  ⚠️ Restore with: nwave-ai install --restore")
        return 1


if __name__ == "__main__":
    sys.exit(main())
