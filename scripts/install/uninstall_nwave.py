#!/usr/bin/env python3
"""
nWave Framework Uninstallation Script

Cross-platform uninstaller for the nWave methodology framework.
Completely removes nWave framework from global Claude config directory.

Usage: python uninstall_nwave.py [--backup] [--force] [--dry-run] [--help]
"""

import argparse
import hashlib
import json
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path


# Prepend this checkout's own root ahead of anything already on sys.path so
# a direct `python3 scripts/install/uninstall_nwave.py` run below imports ITS
# OWN sibling `scripts.install.install_nwave`, never a same-named `scripts`
# package this interpreter's site-packages happens to also provide (e.g. a
# dev venv with `nwave-ai` installed). Without this, the dotted import below
# succeeds against the WRONG copy -- no ImportError, so the bare-name
# fallback never fires -- and that copy's own __file__-relative
# `_project_root` then resolves beside site-packages instead of the
# checkout, breaking `print_logo`'s strict version resolution. Harmless when
# genuinely installed: three parents up from an installed __file__ is
# site-packages itself, already on sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

try:
    from scripts.install.attribution_utils import (
        NWAVE_MANAGED_COMMIT,
        read_attribution_hooks_dir,
        remove_attribution_hook,
        remove_settings_attribution,
    )
    from scripts.install.install_nwave import print_logo
    from scripts.install.install_utils import (
        BackupManager,
        Logger,
        ManifestWriter,
        PathUtils,
        confirm_action,
    )
    from scripts.install.plugins.opencode_common import (
        opencode_config_dir as _opencode_config_dir,
    )
    from scripts.shared.install_paths import (
        active_runtime_pointer_path,
        host_neutral_runtime_dir,
        install_lock_path,
        nwave_config_dir,
    )
    from scripts.shared.settings import restore_todo_tools_env, todo_tools_receipt_path
    from scripts.shared.skill_distribution import (
        DATA_FAMILY_KEY,
        MANIFEST_FILENAME,
        SKILLS_FAMILY_KEY,
        TEMPLATES_FAMILY_KEY,
        UTILITIES_FAMILY_KEY,
        FamilyRemovalEvidence,
        read_family_record,
        remove_family_record,
    )
except ImportError:
    from attribution_utils import (
        NWAVE_MANAGED_COMMIT,
        read_attribution_hooks_dir,
        remove_attribution_hook,
        remove_settings_attribution,
    )
    from install_nwave import print_logo
    from install_utils import (
        BackupManager,
        Logger,
        ManifestWriter,
        PathUtils,
        confirm_action,
    )
    from plugins.opencode_common import (
        opencode_config_dir as _opencode_config_dir,
    )
    from shared.install_paths import (
        active_runtime_pointer_path,
        host_neutral_runtime_dir,
        install_lock_path,
        nwave_config_dir,
    )
    from shared.settings import restore_todo_tools_env, todo_tools_receipt_path
    from shared.skill_distribution import (
        DATA_FAMILY_KEY,
        MANIFEST_FILENAME,
        SKILLS_FAMILY_KEY,
        TEMPLATES_FAMILY_KEY,
        UTILITIES_FAMILY_KEY,
        FamilyRemovalEvidence,
        read_family_record,
        remove_family_record,
    )

# The DES manifest filename each native (non-Claude) plugin writes under its
# own host config dir -- each plugin module repeats this same literal as a
# private module-level constant, so it is repeated here rather than reaching
# into another module's private name.
_NATIVE_DES_MANIFEST_FILENAME = ".nwave-des-manifest.json"


def _copilot_config_dir() -> Path:
    """Copilot CLI configuration directory: COPILOT_HOME when set, else ~/.copilot.

    Same resolution as ``nwave_ai.upgrade_shell.copilot_config_dir``; kept as a
    no-arg local helper so the manifest discovery below reads like its Codex
    and OpenCode siblings.
    """
    override = os.environ.get("COPILOT_HOME")
    return Path(override) if override else Path.home() / ".copilot"


def _cursor_config_dir() -> Path:
    """Cursor configuration directory: CURSOR_HOME when set, else ~/.cursor."""
    override = os.environ.get("CURSOR_HOME")
    return Path(override) if override else Path.home() / ".cursor"


def _carries_kept_registration(hook_file: Path) -> bool:
    """True when a host hook file holds a kept nWave registration (``-m nwave_ai.hooks``).

    The kept hook plugin writes no manifest for these hosts, so the registration
    itself is the only install evidence the uninstaller can read.
    """
    try:
        return "-m nwave_ai.hooks " in hook_file.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return False


def _holds_no_entries(document: dict) -> bool:
    """True when a hook document has no registrations left (only its version or empty hooks)."""
    return all(
        key == "version" or (key == "hooks" and value == {})
        for key, value in document.items()
    )


def _opencode_shim_sha256_drift(shim_path: Path, manifest_path: Path) -> str | None:
    """Describe sha256 drift between the legacy OpenCode shim and its manifest.

    Returns None when either file is absent/unreadable (existence is checked
    separately by the caller) or the fresh hash matches the recorded one;
    otherwise a human-readable drift description.
    """
    if not shim_path.exists() or not manifest_path.is_file():
        return None
    try:
        recorded = json.loads(manifest_path.read_text(encoding="utf-8")).get("sha256")
        fresh = hashlib.sha256(shim_path.read_bytes()).hexdigest()
    except (OSError, json.JSONDecodeError, AttributeError):
        return None
    if not isinstance(recorded, str):
        return None
    return None if recorded == fresh else f"manifest {recorded} != disk {fresh}"


# ANSI color codes for --help output (only consumer)
_ANSI_BLUE = "\033[0;34m"
_ANSI_NC = "\033[0m"  # No Color


@dataclass(frozen=True)
class ManifestOwnedAssets:
    """One native plugin root whose manifest lists the members the installer wrote.

    Knows which of its own members are still on disk, so a removal that a
    plugin abandoned part-way can still name every installer-created file it
    left behind.
    """

    directory: Path
    manifest_filename: str
    members_key: str
    member_suffix: str

    def remaining_files(self) -> list[Path]:
        """Installer-created files still present, from the manifest left behind."""
        try:
            manifest = json.loads(
                (self.directory / self.manifest_filename).read_text(encoding="utf-8")
            )
            members = manifest.get(self.members_key, [])
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, AttributeError):
            return []
        remaining: list[Path] = []
        for member in members:
            owned = self.directory / f"{member}{self.member_suffix}"
            if owned.is_dir() and not owned.is_symlink():
                remaining.extend(path for path in owned.rglob("*") if path.is_file())
            elif owned.is_symlink() or owned.exists():
                remaining.append(owned)
        return sorted(remaining)


__version__ = "1.1.0"


@dataclass(frozen=True)
class ClaudeOwnershipInventory:
    """Positive-ownership snapshot of the Claude discovery surface.

    Produced by exactly one read-only scan (`scan_claude_ownership`), which
    both `validate_removal` and the removal methods consult instead of each
    re-deriving ownership ad hoc. Ownership is established only by manifest
    membership under the family's OWN key (never a legacy/superseded key --
    `remove_family_record` never adopts or removes those, so a scan that
    claimed them as owned would report residue nothing can ever clear), or
    an exact dedicated legacy root -- never a `nw-*` prefix/glob, which would
    misclassify a coincidentally-named user file as nWave residue.
    """

    agents_legacy_root_present: bool
    commands_legacy_root_present: bool
    skills_legacy_root_present: bool
    skills_manifest_status: str  # "absent" | "corrupt" | "present"
    skills_owned_present: frozenset[str]
    templates_manifest_status: str  # "absent" | "corrupt" | "present"
    templates_owned_present: frozenset[str]
    utilities_manifest_status: str  # "absent" | "corrupt" | "present"
    utilities_owned_present: frozenset[str]
    data_manifest_status: str  # "absent" | "corrupt" | "present"
    data_owned_present: frozenset[str]


def _scan_family_ownership(target_dir: Path, *, key: str) -> tuple[str, frozenset[str]]:
    """Read-only ownership scan for one manifest-tracked family.

    Shared by every family scanned by `scan_claude_ownership` -- a missing
    or corrupt manifest yields an empty owned set (never a guess), and a
    tracked name only counts as owned if it still exists on disk.
    """
    manifest_path = target_dir / MANIFEST_FILENAME
    if not manifest_path.exists():
        return "absent", frozenset()
    try:
        record = read_family_record(target_dir, key=key)
    except (OSError, ValueError, AttributeError):
        return "corrupt", frozenset()
    tracked = record.tracked or frozenset()
    owned = frozenset(
        name
        for name in tracked
        if (target_dir / name).exists() or (target_dir / name).is_symlink()
    )
    return "present", owned


def scan_claude_ownership(claude_config_dir: Path) -> ClaudeOwnershipInventory:
    """Read-only total scan of what nWave positively owns, once.

    Never mutates the tree and never calls `remove_family_record` -- it only
    reads the manifest (`read_family_record`) and stats dedicated paths, so
    two scans with no intervening removal return an equal (`==`) inventory.
    A missing or corrupt manifest yields an empty owned set (never a guess);
    a scan can therefore never manufacture ownership by itself.
    `adopt_legacy` is deliberately NOT passed: `remove_family_record` only
    ever reads/removes the family's own key, so honoring a legacy-adopted
    key here would claim ownership over members mutation can never clear.
    """
    skills_dir = claude_config_dir / "skills"
    templates_dir = claude_config_dir / "templates"
    scripts_dir = claude_config_dir / "scripts"
    data_dir = claude_config_dir / "data"

    skills_manifest_status, skills_owned_present = _scan_family_ownership(
        skills_dir, key=SKILLS_FAMILY_KEY
    )
    templates_manifest_status, templates_owned_present = _scan_family_ownership(
        templates_dir, key=TEMPLATES_FAMILY_KEY
    )
    utilities_manifest_status, utilities_owned_present = _scan_family_ownership(
        scripts_dir, key=UTILITIES_FAMILY_KEY
    )
    data_manifest_status, data_owned_present = _scan_family_ownership(
        data_dir, key=DATA_FAMILY_KEY
    )

    return ClaudeOwnershipInventory(
        agents_legacy_root_present=(claude_config_dir / "agents" / "nw").exists(),
        commands_legacy_root_present=(claude_config_dir / "commands" / "nw").exists(),
        skills_legacy_root_present=(skills_dir / "nw").exists(),
        skills_manifest_status=skills_manifest_status,
        skills_owned_present=skills_owned_present,
        templates_manifest_status=templates_manifest_status,
        templates_owned_present=templates_owned_present,
        utilities_manifest_status=utilities_manifest_status,
        utilities_owned_present=utilities_owned_present,
        data_manifest_status=data_manifest_status,
        data_owned_present=data_owned_present,
    )


def _is_legacy_flat_nw_symlink(entry: Path, nested_dir: Path) -> bool:
    """True if `entry` is a legacy flat symlink into the dedicated `nested_dir`.

    Positive identification only -- never name-prefix ownership. `entry` must
    itself be a symlink named `nw-*` whose RAW (unresolved) target lexically
    resolves inside `nested_dir` (the dedicated `{noun}/nw/` root this same
    family owns), dangling target included. Uses `Path.readlink` -- never
    `Path.resolve()` -- so neither the symlink itself nor any intermediate
    path component is ever followed on disk; only the link's own recorded
    text and `nested_dir` are compared lexically. A regular file, a
    directory, or a symlink pointing anywhere else is a preserved user
    sibling even when its name starts with `nw-`.
    """
    if not entry.is_symlink() or not entry.name.startswith("nw-"):
        return False
    try:
        raw_target = entry.readlink()
    except OSError:
        return False
    target = Path(raw_target)
    if not target.is_absolute():
        target = entry.parent / target
    normalized_target = Path(os.path.normpath(str(target)))
    normalized_nested = Path(os.path.normpath(str(nested_dir)))
    try:
        normalized_target.relative_to(normalized_nested)
    except ValueError:
        return False
    return True


class NWaveUninstaller:
    """nWave framework uninstaller."""

    def __init__(
        self,
        backup_before_removal: bool = False,
        force: bool = False,
        dry_run: bool = False,
    ):
        """
        Initialize uninstaller.

        Args:
            backup_before_removal: Create backup before uninstalling
            force: Skip confirmation prompts
            dry_run: Show what would be done without executing
        """
        self.backup_before_removal = backup_before_removal
        self.force = force
        self.dry_run = dry_run

        self.claude_config_dir = PathUtils.get_claude_config_dir()
        # Persistent logging (and the uninstall report) start only after
        # check_installation() confirms a genuine Claude discovery surface
        # exists -- a native-only (Codex/Copilot/OpenCode, alone or combined)
        # uninstall must never create ~/.claude merely to hold its own log or
        # report (mirrors install_nwave.py's enable_install_logging).
        self._uninstall_log_file = self.claude_config_dir / "nwave-uninstall.log"
        self.logger = Logger(None)
        self.backup_manager = BackupManager(self.logger, "uninstall")
        self.claude_installation_present = False
        # Set by remove_skills(); classified by _skills_removal_state() and
        # consulted by validate_removal() -- None means remove_skills() has
        # not run yet this instance, which validates the same as a missing
        # manifest (never a false green).
        self._skills_removal_evidence: FamilyRemovalEvidence | None = None
        # Set by remove_templates()/remove_utility_scripts()/remove_data();
        # keyed by family label, consulted by validate_removal() via
        # _family_removal_state(). A missing entry validates the same as a
        # missing manifest (never a false green).
        self._family_removal_evidence: dict[str, FamilyRemovalEvidence] = {}
        # Installer-created files a removal step could not delete; any entry
        # makes validate_removal() fail so success is never claimed.
        self._removal_failures: list[str] = []
        self._attribution_repository: Path | None = None
        self._attribution_recorded_hooks_dir: str | None = None

    def enable_uninstall_logging(self) -> None:
        """Enable persistent logging once a Claude installation is confirmed."""
        if not self.dry_run:
            self.logger.log_file = self._uninstall_log_file

    def check_installation(self) -> bool:
        """Check for existing nWave installation.

        Sets ``self.claude_installation_present`` so callers know whether a
        Claude discovery surface actually exists (and therefore whether it is
        safe to enable persistent logging / write the uninstall report under
        ``claude_config_dir``). A native-only (Codex/Copilot/OpenCode)
        installation makes this return True without setting that flag.
        """
        self.logger.info("  🔍 Checking for nWave installation...")

        installation_found = False

        agents_dir = self.claude_config_dir / "agents" / "nw"
        commands_dir = self.claude_config_dir / "commands" / "nw"
        manifest_file = self.claude_config_dir / "nwave-manifest.txt"
        install_log = self.claude_config_dir / "nwave-install.log"
        backups_dir = self.claude_config_dir / "backups"

        if agents_dir.exists():
            installation_found = True
            self.logger.info(f"    📂 Found nWave agents in: {agents_dir}")

        if commands_dir.exists():
            installation_found = True
            self.logger.info(f"    📂 Found nWave commands in: {commands_dir}")

        skills_dir = self.claude_config_dir / "skills" / "nw"
        if skills_dir.exists():
            installation_found = True
            self.logger.info(f"    📂 Found nWave skills in: {skills_dir}")

        if manifest_file.exists():
            installation_found = True
            self.logger.info("    📄 Found nWave manifest file")

        if install_log.exists():
            installation_found = True
            self.logger.info("    📄 Found nWave installation logs")

        if backups_dir.exists():
            nwave_backups = list(backups_dir.glob("nwave-*"))
            if nwave_backups:
                installation_found = True
                self.logger.info("    📦 Found nWave backup directories")

        # Check for DES hooks
        settings_file = self.claude_config_dir / "settings.json"
        if settings_file.exists():
            try:
                with open(settings_file, encoding="utf-8") as f:
                    config = json.load(f)
                    if "hooks" in config:
                        hooks_str = json.dumps(config["hooks"])
                        if (
                            "des/adapters/drivers/hooks/claude_code_hook_adapter"
                            in hooks_str
                        ):
                            installation_found = True
                            self.logger.info("    🔗 Found DES hooks in settings.json")
            except (OSError, json.JSONDecodeError):
                pass

        # This point onward: every check above is Claude-owned (all live
        # under claude_config_dir). Record that BEFORE looking at native
        # surfaces, so a pure native installation never flips this flag.
        self.claude_installation_present = installation_found

        # Native (non-Claude) DES surfaces: a Codex/Copilot/OpenCode-only
        # installation has no Claude discovery surface at all, so the checks
        # above always miss it -- without this, check_installation() would
        # wrongly report "nothing to uninstall" and silently no-op, leaving
        # the native hook/manifest and the host-neutral DES runtime behind.
        from nwave_ai.hooks.registration import HOOK_FILE
        from nwave_ai.platform.locations import NWaveLocations
        from scripts.shared.install_paths import agents_home

        locations = NWaveLocations.resolve(
            Path.home(), Path.cwd(), None, None, None
        ).unwrap()
        codex_manifest = locations.codex_config_dir / _NATIVE_DES_MANIFEST_FILENAME
        if codex_manifest.exists():
            installation_found = True
            self.logger.info(f"    📄 Found Codex DES manifest: {codex_manifest}")

        copilot_manifest = _copilot_config_dir() / _NATIVE_DES_MANIFEST_FILENAME
        if copilot_manifest.exists():
            installation_found = True
            self.logger.info(f"    📄 Found Copilot DES manifest: {copilot_manifest}")

        opencode_manifest = _opencode_config_dir() / _NATIVE_DES_MANIFEST_FILENAME
        if opencode_manifest.exists():
            installation_found = True
            self.logger.info(f"    📄 Found OpenCode DES manifest: {opencode_manifest}")

        for hook_label, hook_file in (
            ("Codex", locations.codex_config_dir / HOOK_FILE["codex"]),
            ("Cursor", _cursor_config_dir() / HOOK_FILE["cursor"]),
            ("Copilot", _copilot_config_dir() / HOOK_FILE["copilot"]),
        ):
            if _carries_kept_registration(hook_file):
                installation_found = True
                self.logger.info(
                    f"    🔗 Found {hook_label} nWave hooks in: {hook_file}"
                )

        codex_skills_manifest = (
            agents_home() / ".agents" / "skills" / ".nwave-manifest.json"
        )
        if codex_skills_manifest.exists():
            installation_found = True
            self.logger.info(
                f"    📄 Found Codex skills manifest: {codex_skills_manifest}"
            )

        for opencode_manifest in (
            _opencode_config_dir() / "agents" / ".nwave-agents-manifest.json",
            _opencode_config_dir() / "commands" / ".nwave-commands-manifest.json",
        ):
            if opencode_manifest.exists():
                installation_found = True
                self.logger.info(f"    📄 Found OpenCode manifest: {opencode_manifest}")
                break

        # OMP native assets: manifest-driven, same root the omp installer
        # plugins write through. OMP 18.5 splits roots (skills follow
        # PI_CODING_AGENT_DIR, agents follow the config root), so BOTH
        # candidate skill roots are probed -- an override-installed skills
        # tree must still be recognized when the uninstall environment lost
        # the override spelling.
        try:
            from scripts.shared.install_paths import (
                omp_agents_dir,
                omp_config_root,
                omp_skills_dir,
            )
        except ImportError:
            from shared.install_paths import (
                omp_agents_dir,
                omp_config_root,
                omp_skills_dir,
            )

        omp_agents_manifest = omp_agents_dir() / ".nwave-agents-manifest.json"
        if omp_agents_manifest.exists():
            installation_found = True
            self.logger.info(f"    📄 Found OMP agents manifest: {omp_agents_manifest}")

        omp_skill_manifest_roots = [
            omp_skills_dir(),
            omp_config_root() / "agent" / "skills",
        ]
        try:
            receipt_doc = json.loads(
                (Path.home() / ".nwave" / "config.json").read_text(encoding="utf-8")
            )
            recorded = (
                receipt_doc.get("install", {})
                .get("host_paths", {})
                .get("omp_skills_dir")
            )
            if isinstance(recorded, str) and recorded:
                omp_skill_manifest_roots.append(Path(recorded))
        except (OSError, json.JSONDecodeError):
            pass
        for candidate_root in omp_skill_manifest_roots:
            omp_skills_manifest = candidate_root / ".nwave-manifest.json"
            if omp_skills_manifest.exists():
                installation_found = True
                self.logger.info(
                    f"    📄 Found OMP skills manifest: {omp_skills_manifest}"
                )

        native_runtime_dir = host_neutral_runtime_dir() / "des"
        if native_runtime_dir.exists():
            installation_found = True
            self.logger.info(
                f"    📂 Found host-neutral DES runtime: {native_runtime_dir}"
            )

        if not installation_found:
            self.logger.info("  ⚠️ No nWave framework installation detected")
            self.logger.info("  ⚠️ Nothing to uninstall")
            return False

        return True

    def confirm_removal(self) -> bool:
        """Confirm uninstallation with user."""
        if self.force:
            return True

        self.logger.info("")
        self.logger.error(
            "  🚨 WARNING: This will completely remove the framework from your system"
        )
        self.logger.info("")
        self.logger.warn("  ⚠️ The following will be removed:")
        self.logger.warn("    🗑️ All nWave agents")
        self.logger.warn("    🗑️ All nWave commands")
        self.logger.warn("    🗑️ DES hooks from Claude Code settings")
        self.logger.warn("    🗑️ Configuration files and manifest")
        self.logger.warn("    🗑️ Installation logs and backup directories")
        self.logger.info("")

        if self.backup_before_removal:
            self.logger.info("  ✅ A backup will be created before removal at:")
            self.logger.info(f"    📦 {self.backup_manager.backup_dir}")
            self.logger.info("")
        else:
            self.logger.error(
                "  🚨 No backup will be created. This action cannot be undone"
            )
            self.logger.error(
                "  🚨 To create a backup, cancel and run with --backup option"
            )
            self.logger.info("")

        return confirm_action("Are you sure you want to proceed?")

    def check_global_config(
        self,
        global_config_path: Path | None = None,
        prompt_fn: object = None,
    ) -> None:
        """Check for global config and prompt user about handling it.

        Called between confirm_removal() and create_backup() in the
        uninstall flow. Handles keep/delete prompt in interactive mode,
        auto-preserves in force mode, and logs status in dry-run mode.

        Args:
            global_config_path: Override path to global config file.
                Defaults to ~/.nwave/config.json.
            prompt_fn: Optional callable(prompt_str) -> bool for testing.
                Defaults to confirm_action from install_utils.
        """
        path = global_config_path or (nwave_config_dir() / "config.json")

        if not path.exists():
            return

        if self.dry_run:
            self.logger.info(f"  [DRY RUN] Would prompt about global config at {path}")
            return

        if self.force:
            self.logger.info("  Preserved global config (--force: skipping prompt)")
            return

        # Interactive mode: prompt user to keep or delete
        ask = prompt_fn if prompt_fn is not None else confirm_action
        self.logger.info("")
        self.logger.info(f"  Found global configuration at {path}")
        should_delete = ask("  Delete global config? (No = keep for next install)")

        if not should_delete:
            self.logger.info(f"  Preserved global config at {path}")
            return

        path.unlink()
        self.logger.info(f"  Deleted global config at {path}")

        # Clean up empty directory
        nwave_dir = path.parent
        if nwave_dir.exists() and not any(nwave_dir.iterdir()):
            nwave_dir.rmdir()
            self.logger.info(f"  Removed empty directory {nwave_dir}")

    def create_backup(self) -> None:
        """Create backup before removal."""
        if not self.backup_before_removal:
            return

        self.backup_manager.create_backup(dry_run=self.dry_run)

    def remove_agents(self) -> None:
        """Remove nWave agents (delegates to shared nw-namespace remover)."""
        self._remove_nw_namespace_subdir("agents")
        if not self.dry_run:
            restore_todo_tools_env(
                self.claude_config_dir / "settings.json",
                todo_tools_receipt_path(self.claude_config_dir),
            )

    def remove_skills(self) -> None:
        """Remove nWave skills via manifest ownership record only.

        Flat `~/.claude/skills/nw-<name>/` directories listed in
        skills/.nwave-manifest.json are removed via remove_family_record
        (ownership tracking) -- the sole mutator, which always runs and
        revalidates safety immediately before deleting. scan_claude_ownership's
        skills_manifest_status classification picks which outcome message
        fires (a genuine decision input, not just the count it also reports).
        Legacy nested `~/.claude/skills/nw/<name>/` layout is removed
        unconditionally. User-created skills (untracked nw-*) and non-nw-*
        files are preserved. Missing/corrupt manifest preserves all
        skills/nw-* entries.
        """
        skills_dir = self.claude_config_dir / "skills"

        if self.dry_run:
            self.logger.info("  🚨 [DRY RUN] Would remove nWave skills")
            if skills_dir.exists():
                if (skills_dir / ".nwave-manifest.json").exists():
                    self.logger.info(
                        "    🚨 [DRY RUN] Would consider manifest-owned "
                        "skills/nw-* members for removal"
                    )
                else:
                    self.logger.info(
                        "    🚨 [DRY RUN] No manifest found; would preserve "
                        "all skills/nw-* entries"
                    )
                if (skills_dir / "nw").exists():
                    self.logger.info(
                        "    🚨 [DRY RUN] Would remove legacy skills/nw/ dir"
                    )
            return

        with self.logger.progress_spinner("  🚧 Removing nWave skills..."):
            if skills_dir.exists():
                # scan_claude_ownership() is the one total read-only scan;
                # its skills_manifest_status classification -- not a second
                # reading of result.status -- picks which message below
                # fires, so the scan genuinely drives what gets reported
                # instead of existing only for the count on the next line.
                # remove_family_record still runs unconditionally: it is the
                # sole mutator and the only one that revalidates safety
                # (and can detect "blocked") immediately before deleting.
                inventory = scan_claude_ownership(self.claude_config_dir)
                self.logger.info(
                    f"  🔍 {len(inventory.skills_owned_present)} manifest-owned "
                    "skills currently on disk"
                )
                result = remove_family_record(skills_dir, key=SKILLS_FAMILY_KEY)
                self._skills_removal_evidence = result

                if inventory.skills_manifest_status != "present":
                    category = (
                        "absent"
                        if inventory.skills_manifest_status == "absent"
                        else "corrupt"
                    )
                    self.logger.warn(self._skills_removal_diagnosis(category))
                elif result.status == "blocked":
                    self.logger.warn(
                        f"  ⚠️ Could not remove {len(result.blocked)} skills "
                        f"(non-success)\n{self._skills_removal_diagnosis('blocked')}"
                    )
                else:
                    self.logger.info(
                        f"  🗑️ Removed {len(result.removed)} manifest-owned "
                        "skills/nw-* members"
                    )

                legacy_nested = skills_dir / "nw"
                if legacy_nested.exists():
                    shutil.rmtree(legacy_nested)
                    self.logger.info("  🗑️ Removed legacy skills/nw directory")
            else:
                # Nothing was ever installed under skills/ -- already clean,
                # not the same state as "a manifest was expected but missing".
                self._skills_removal_evidence = FamilyRemovalEvidence(
                    "complete", frozenset(), frozenset(), frozenset()
                )

            if skills_dir.exists():
                try:
                    if not any(skills_dir.iterdir()):
                        skills_dir.rmdir()
                        self.logger.info("  🗑️ Removed empty skills directory")
                    else:
                        self.logger.info("  📂 Kept skills directory (contains files)")
                except OSError:
                    self.logger.info("  📂 Kept skills directory (contains files)")

    def _skills_removal_state(self) -> str:
        """Classify this run's skills removal into the five owed states.

        "absent-before-run" (no manifest existed) and "corrupt" (manifest
        unparsable) never validate green -- ownership was never established,
        so nothing can be honestly asserted as removed. "blocked" stays red
        (a tracked member survived). A completed run is green whether it
        actually deleted members this run ("removed-completely-this-run")
        or found the family already clean ("already-clean").

        `evidence is None` means remove_skills() has not run this instance
        (e.g. validate_removal() called standalone). That is honestly
        "already-clean" -- not "absent-before-run" -- when the skills
        directory does not currently exist on disk: a family that was never
        installed carries no manifest to be missing. When the directory DOES
        exist unread, ownership genuinely was never established, so it stays
        "absent-before-run".
        """
        evidence = self._skills_removal_evidence
        if evidence is None:
            skills_dir = self.claude_config_dir / "skills"
            return "already-clean" if not skills_dir.exists() else "absent-before-run"
        if evidence.status == "missing_manifest":
            return "absent-before-run"
        if evidence.status == "invalid_manifest":
            return "corrupt"
        if evidence.status == "blocked":
            return "blocked"
        return "removed-completely-this-run" if evidence.removed else "already-clean"

    def _skills_removal_diagnosis(self, category: str) -> str:
        """WHAT/WHY/HOW for a non-green skills outcome, with an actionable HOW.

        Shared by remove_skills() (reported as it happens) and
        validate_removal() (reported as the final verdict) so the two
        surfaces never drift into two different explanations for the same
        category. `category` is one of "absent" | "corrupt" | "blocked" |
        "residue" (the last covers a reported-clean run whose post-removal
        scan still finds owned or legacy residue).
        """
        what, why, how = {
            "absent": (
                "no skills/.nwave-manifest.json was found before this run",
                "ownership was never established, so no skills/nw-* entry "
                "could be honestly attributed to nWave and removed",
                "re-run the nWave installer to regenerate the manifest, "
                "then re-run uninstall; if skills/nw-* entries remain and "
                "you can confirm they are nWave-owned, remove them by hand",
            ),
            "corrupt": (
                "skills/.nwave-manifest.json could not be parsed",
                "ownership was never established, so no skills/nw-* entry "
                "could be honestly attributed to nWave and removed",
                "restore skills/.nwave-manifest.json from a backup or "
                "reinstall to regenerate it, then re-run uninstall; if "
                "skills/nw-* entries remain and you can confirm they are "
                "nWave-owned, remove them by hand",
            ),
            "blocked": (
                "one or more manifest-owned skills/nw-* entries could not be removed",
                "a filesystem or permission error stopped the mutation "
                "part-way through",
                "check filesystem permissions on the skills directory and "
                "re-run uninstall; if it persists, remove the reported "
                "skills/nw-* entries by hand after confirming ownership",
            ),
            "residue": (
                "a manifest-owned skill or the legacy skills/nw directory "
                "is still present on disk",
                "the removal pass reported success but a fresh scan found "
                "residue anyway",
                "inspect skills/ for leftover nw-* entries or a legacy "
                "skills/nw directory and remove them by hand, then re-run "
                "uninstall to confirm",
            ),
        }[category]
        return f"  WHAT: {what} WHY: {why} HOW: {how}"

    def remove_templates(self) -> None:
        """Remove nWave templates via manifest ownership record only."""
        self._remove_family_dir(
            subdir="templates", key=TEMPLATES_FAMILY_KEY, family_label="templates"
        )

    def remove_utility_scripts(self) -> None:
        """Remove nWave non-hook utility scripts via manifest ownership record only.

        Shares `~/.claude/scripts/` with DES hook scripts (removed separately
        by `remove_des_hook_scripts`); `remove_family_record` only ever
        touches its own `UTILITIES_FAMILY_KEY` members, so the sibling hook
        scripts and the manifest key that tracks them are untouched.
        """
        self._remove_family_dir(
            subdir="scripts", key=UTILITIES_FAMILY_KEY, family_label="utility scripts"
        )

    def remove_data(self) -> None:
        """Remove the installed nWave data tree via manifest ownership record only."""
        self._remove_family_dir(subdir="data", key=DATA_FAMILY_KEY, family_label="data")

    def _remove_family_dir(self, *, subdir: str, key: str, family_label: str) -> None:
        """Remove one manifest-tracked family from `~/.claude/{subdir}/`.

        Shared by remove_templates/remove_utility_scripts/remove_data: each
        owns a distinct manifest key inside a directory that may be shared
        with sibling families or untracked user files, so `remove_family_record`
        (the sole mutator) is the only thing that ever deletes -- it removes
        only its own key's listed members and preserves everything else,
        including sibling manifest keys and untracked siblings. The parent
        directory is removed only if it becomes fully empty.
        """
        target_dir = self.claude_config_dir / subdir

        if self.dry_run:
            self.logger.info(f"  🚨 [DRY RUN] Would remove nWave {family_label}")
            return

        with self.logger.progress_spinner(f"  🚧 Removing nWave {family_label}..."):
            if target_dir.exists():
                result = remove_family_record(target_dir, key=key)
                self._family_removal_evidence[family_label] = result

                if result.status == "blocked":
                    self.logger.warn(
                        f"  ⚠️ Could not remove {len(result.blocked)} {family_label} "
                        f"(non-success)\n{self._family_removal_diagnosis(family_label, 'blocked')}"
                    )
                elif result.status == "missing_manifest":
                    self.logger.info(
                        f"  ℹ️ No {family_label} manifest found; nothing to remove"
                    )
                elif result.status == "invalid_manifest":
                    self.logger.warn(
                        f"  ⚠️ {family_label} manifest could not be parsed"
                        f"\n{self._family_removal_diagnosis(family_label, 'corrupt')}"
                    )
                else:
                    self.logger.info(
                        f"  🗑️ Removed {len(result.removed)} manifest-owned "
                        f"{family_label}"
                    )
            else:
                self._family_removal_evidence[family_label] = FamilyRemovalEvidence(
                    "complete", frozenset(), frozenset(), frozenset()
                )

            if target_dir.exists():
                try:
                    if not any(target_dir.iterdir()):
                        target_dir.rmdir()
                        self.logger.info(f"  🗑️ Removed empty {subdir} directory")
                except OSError:
                    pass

    # family_label -> subdir name under claude_config_dir, for the
    # dir-existence check `_family_removal_state` needs when its remover
    # never ran this instance (validate_removal() called standalone).
    _FAMILY_SUBDIRS = {
        "templates": "templates",
        "utility scripts": "scripts",
        "data": "data",
    }

    def _family_removal_state(self, family_label: str) -> str:
        """Classify a family removal into the same states `_skills_removal_state` uses.

        `evidence is None` means this family's remover has not run this
        instance. That is honestly "already-clean" -- not
        "absent-before-run" -- when the family's directory does not
        currently exist on disk: a family that was never installed carries
        no manifest to be missing.
        """
        evidence = self._family_removal_evidence.get(family_label)
        if evidence is None:
            subdir = self._FAMILY_SUBDIRS[family_label]
            target_dir = self.claude_config_dir / subdir
            return "already-clean" if not target_dir.exists() else "absent-before-run"
        if evidence.status == "missing_manifest":
            return "absent-before-run"
        if evidence.status == "invalid_manifest":
            return "corrupt"
        if evidence.status == "blocked":
            return "blocked"
        return "removed-completely-this-run" if evidence.removed else "already-clean"

    def _family_removal_diagnosis(self, family_label: str, category: str) -> str:
        """WHAT/WHY/HOW for a non-green family removal outcome."""
        what, why, how = {
            "absent": (
                f"no {family_label} manifest was found before this run",
                "ownership was never established, so no entry could be "
                "honestly attributed to nWave and removed",
                "re-run the nWave installer to regenerate the manifest, "
                "then re-run uninstall",
            ),
            "corrupt": (
                f"the {family_label} manifest could not be parsed",
                "ownership was never established, so no entry could be "
                "honestly attributed to nWave and removed",
                "restore the manifest from a backup or reinstall to "
                "regenerate it, then re-run uninstall",
            ),
            "blocked": (
                f"one or more manifest-owned {family_label} could not be removed",
                "a filesystem or permission error stopped the mutation "
                "part-way through",
                f"check filesystem permissions and re-run uninstall; the "
                f"blocked {family_label} stay recorded in the manifest for retry",
            ),
            "residue": (
                f"a manifest-owned {family_label} entry is still present on disk",
                "the removal pass reported success but a fresh scan found "
                "residue anyway",
                f"inspect the {family_label} directory for leftovers and "
                "remove them by hand, then re-run uninstall to confirm",
            ),
        }[category]
        return f"  WHAT: {what} WHY: {why} HOW: {how}"

    def remove_lib_python(self) -> None:
        """Remove the legacy installed runtime library (`des/`), wherever it lives.

        The legacy installer wrote the old runtime under `lib/python/des/`
        (Claude targets) and/or `host_neutral_runtime_dir()/des/` (Codex/
        Copilot/OpenCode targets, or the mirror half of a mixed target).
        Uninstall must remove EVERY location the SAME target-platform
        detection resolves to -- not just the Claude-scoped path. The
        resolution mirrors the retired plugin's
        ``resolve_des_module_locations``: the primary dir is the shared
        host-neutral runtime unless Claude is targeted, and a mixed
        claude_code + host-neutral target needs the OTHER directory as a
        secondary. A hardcoded Claude-only path here orphaned the module on
        disk for any non-Claude-only target (the uninstall-vs-install path
        divergence bug). Sibling lib/python/ contents (non-des) are
        preserved; parent dirs are removed only if empty.
        """
        try:
            from scripts.install.context_detector import detect_target_platforms
        except ImportError:
            from context_detector import detect_target_platforms

        target_platforms = {platform.value for platform in detect_target_platforms()}
        claude_lib_python = self.claude_config_dir / "lib" / "python"
        neutral_lib_python = host_neutral_runtime_dir()
        primary = (
            claude_lib_python
            if "claude_code" in target_platforms
            else neutral_lib_python
        )
        des_module_locations = [primary / "des"]
        wants_claude = "claude_code" in target_platforms
        wants_host_neutral = bool(
            {"codex", "copilot", "cursor", "opencode", "omp"} & target_platforms
        )
        if wants_claude and wants_host_neutral:
            secondary = (
                neutral_lib_python
                if primary == claude_lib_python
                else claude_lib_python
            )
            if secondary != primary:
                des_module_locations.append(secondary / "des")

        if self.dry_run:
            for lib_des in des_module_locations:
                if lib_des.exists():
                    self.logger.info(f"  🚨 [DRY RUN] Would remove {lib_des}")
            return

        with self.logger.progress_spinner("  🚧 Removing nWave Python runtime..."):
            for lib_des in des_module_locations:
                if lib_des.exists():
                    shutil.rmtree(lib_des)
                    self.logger.info(f"  🗑️ Removed {lib_des}")

                # The runtime data the installer ships beside each runtime
                # python dir (lib/nWave next to lib/python, nWave next to runtime).
                assets_root = lib_des.parent.parent / "nWave"
                if assets_root.exists():
                    shutil.rmtree(assets_root)
                    self.logger.info(f"  🗑️ Removed {assets_root}")

                # Cascade-clean empty parents (e.g. lib/python then lib, or
                # runtime then .nwave for the host-neutral location)
                for parent in (lib_des.parent, lib_des.parent.parent):
                    if parent.exists():
                        try:
                            if not any(parent.iterdir()):
                                parent.rmdir()
                                self.logger.info(f"  🗑️ Removed empty {parent.name}")
                        except OSError:
                            pass

    def remove_host_neutral_des_runtime(self) -> None:
        """Remove ~/.nwave/runtime/des/ (shared DES runtime for native hosts).

        Codex/Copilot/OpenCode adapters import the DES runtime from the
        host-neutral shared location (see host_neutral_runtime_dir()) rather
        than claude_config_dir/lib/python/des -- a native-only uninstall must
        remove it too, mirroring remove_lib_python for the Claude location.
        Only the "des" subtree is removed; sibling ~/.nwave content
        (config.json, nWave/ operator state, etc.) is untouched, and
        the "runtime" parent is removed only if it becomes empty.
        """
        runtime_des = host_neutral_runtime_dir() / "des"

        if self.dry_run:
            if runtime_des.exists():
                self.logger.info(
                    "  🚨 [DRY RUN] Would remove host-neutral DES runtime directory"
                )
            return

        with self.logger.progress_spinner("  🚧 Removing host-neutral DES runtime..."):
            if runtime_des.exists():
                shutil.rmtree(runtime_des)
                self.logger.info("  🗑️ Removed host-neutral DES runtime directory")

            runtime_parent = runtime_des.parent
            if runtime_parent.exists():
                try:
                    if not any(runtime_parent.iterdir()):
                        runtime_parent.rmdir()
                        self.logger.info(f"  🗑️ Removed empty {runtime_parent.name}")
                except OSError:
                    pass

    def _plugin_context(self):
        """Build the InstallContext the installer plugins' uninstall() expects."""
        try:
            from scripts.install.plugins.base import InstallContext
        except ImportError:
            from plugins.base import InstallContext

        return InstallContext(
            claude_dir=self.claude_config_dir,
            scripts_dir=self.claude_config_dir / "scripts",
            templates_dir=self.claude_config_dir / "templates",
            logger=self.logger,
        )

    def remove_native_assets(self) -> None:
        """Remove the Codex and OpenCode skills, agents, commands and hooks.

        Each installer plugin owns its manifest and is the sole remover of what
        it wrote; a plugin that cannot remove everything reports failure, which
        is recorded so validation refuses to claim success.
        """
        if self.dry_run:
            self.logger.info("  🚨 [DRY RUN] Would remove Codex and OpenCode assets")
            return

        try:
            from scripts.install.plugins.codex_agents_plugin import CodexAgentsPlugin
            from scripts.install.plugins.codex_skills_plugin import CodexSkillsPlugin
            from scripts.install.plugins.opencode_agents_plugin import (
                OpenCodeAgentsPlugin,
            )
            from scripts.install.plugins.opencode_commands_plugin import (
                OpenCodeCommandsPlugin,
            )
            from scripts.install.plugins.opencode_skills_plugin import (
                OpenCodeSkillsPlugin,
            )
        except ImportError:
            from plugins.codex_agents_plugin import CodexAgentsPlugin
            from plugins.codex_skills_plugin import CodexSkillsPlugin
            from plugins.opencode_agents_plugin import OpenCodeAgentsPlugin
            from plugins.opencode_commands_plugin import OpenCodeCommandsPlugin
            from plugins.opencode_skills_plugin import OpenCodeSkillsPlugin

        context = self._plugin_context()
        for plugin in (
            CodexSkillsPlugin(),
            CodexAgentsPlugin(),
            OpenCodeSkillsPlugin(),
            OpenCodeAgentsPlugin(),
            OpenCodeCommandsPlugin(),
        ):
            result = plugin.uninstall(context)
            if result.success:
                self.logger.info(f"  🗑️ {result.message}")
            else:
                self._removal_failures.append(result.message)
                self.logger.warn(f"  ⚠️ {result.message}")
        self._record_remaining_native_files()

    def _record_remaining_native_files(self) -> None:
        """Name every manifest-owned native file that survived the plugin passes."""
        try:
            from scripts.install.plugins.codex_agents_plugin import _codex_agents_dir
            from scripts.install.plugins.codex_skills_plugin import _codex_skills_dir
            from scripts.install.plugins.opencode_agents_plugin import (
                _opencode_agents_dir,
            )
            from scripts.install.plugins.opencode_commands_plugin import (
                _opencode_commands_dir,
            )
            from scripts.install.plugins.opencode_skills_plugin import (
                _opencode_skills_dir,
            )
        except ImportError:
            from plugins.codex_agents_plugin import _codex_agents_dir
            from plugins.codex_skills_plugin import _codex_skills_dir
            from plugins.opencode_agents_plugin import _opencode_agents_dir
            from plugins.opencode_commands_plugin import _opencode_commands_dir
            from plugins.opencode_skills_plugin import _opencode_skills_dir

        roots = (
            ManifestOwnedAssets(
                _codex_skills_dir(), ".nwave-manifest.json", "installed_skills", ""
            ),
            ManifestOwnedAssets(
                _codex_agents_dir(),
                ".nwave-agents-manifest.json",
                "installed_agents",
                ".toml",
            ),
            ManifestOwnedAssets(
                _opencode_skills_dir(), ".nwave-manifest.json", "installed_skills", ""
            ),
            ManifestOwnedAssets(
                _opencode_agents_dir(),
                ".nwave-agents-manifest.json",
                "installed_agents",
                ".md",
            ),
            ManifestOwnedAssets(
                _opencode_commands_dir(),
                ".nwave-commands-manifest.json",
                "installed_commands",
                ".md",
            ),
        )
        for root in roots:
            for path in root.remaining_files():
                self._removal_failures.append(f"{path} could not be removed")

    def remove_des_shims_and_scripts(self) -> None:
        """Remove the DES command shims and DES scripts under the Claude profile."""
        if self.dry_run:
            self.logger.info("  🚨 [DRY RUN] Would remove DES shims and scripts")
            return

        # Legacy shim and manifest names inlined: the retired plugin is
        # deleted and uninstall is the only remaining consumer of these lists.
        from scripts.shared.skill_distribution import SCRIPTS_FAMILY_KEY

        bin_dir = self.claude_config_dir / "bin"
        legacy_shims = (
            "des",
            "des-log-phase",
            "des-commit",
            "des-init-log",
            "des-verify-integrity",
            "des-health-check",
            "des-roadmap",
        )
        for shim_name in legacy_shims:
            self._unlink_installed(bin_dir / shim_name)

        scripts_dir = self.claude_config_dir / "scripts"
        if scripts_dir.exists():
            evidence = remove_family_record(scripts_dir, key=SCRIPTS_FAMILY_KEY)
            if evidence.blocked:
                self._removal_failures.append(
                    f"DES scripts could not be removed: {sorted(evidence.blocked)}"
                )
        self._remove_dir_if_empty(bin_dir)
        self._remove_dir_if_empty(scripts_dir)

    def remove_project_nwave_config(self) -> None:
        """Remove the installer-generated ``.nwave`` config of the current project.

        The directory is the installer's only when its ``.gitignore`` satisfies
        the one ownership predicate the writer uses
        (``is_nwave_generated_gitignore``); anything else in it is left alone.
        """
        # Same project resolution the installer uses (install_nwave.py): the
        # declared caller project, else the working directory.
        project_root = Path(os.environ.get("NWAVE_PROJECT_ROOT") or Path.cwd())
        project_nwave = project_root.resolve() / ".nwave"
        gitignore = project_nwave / ".gitignore"
        if self.dry_run:
            self.logger.info("  🚨 [DRY RUN] Would remove project .nwave config")
            return
        # Deliberately no ImportError fallback: a missing nwave_ai package must
        # fail the uninstall loudly rather than silently skip project removal.
        from nwave_ai.platform.gitignore import is_nwave_generated_gitignore

        try:
            generated = is_nwave_generated_gitignore(
                gitignore.read_text(encoding="utf-8")
            )
        except (OSError, UnicodeDecodeError):
            return
        if generated:
            self._unlink_installed(gitignore)
            self._unlink_installed(project_nwave / "config.json")
            self._remove_dir_if_empty(project_nwave)

    def remove_runtime_pointer_and_lock(self) -> None:
        """Remove the active-runtime pointer, install lock and an emptied state root.

        Runs after every runtime removal: the pointer is dropped when the
        runtime it names no longer holds a ``des`` package.
        """
        if self.dry_run:
            self.logger.info("  🚨 [DRY RUN] Would remove runtime pointer and lock")
            return

        pointer = active_runtime_pointer_path()
        try:
            named_runtime = Path(pointer.read_text(encoding="utf-8").strip())
        except (OSError, UnicodeDecodeError):
            named_runtime = None
        if named_runtime is None or not (named_runtime / "des").exists():
            self._unlink_installed(pointer)
        self._unlink_installed(install_lock_path())
        self._remove_dir_if_empty(nwave_config_dir())

    def _unlink_installed(self, path: Path) -> None:
        """Delete one installer-created file; a refusal is recorded, never hidden."""
        if not (path.is_symlink() or path.exists()):
            return
        try:
            path.unlink()
            self.logger.info(f"  🗑️ Removed {path.name}")
        except OSError as error:
            self._removal_failures.append(f"{path} could not be removed: {error}")

    def _remove_dir_if_empty(self, directory: Path) -> None:
        try:
            if directory.is_dir() and not any(directory.iterdir()):
                directory.rmdir()
                self.logger.info(f"  🗑️ Removed empty {directory.name}")
        except OSError:
            pass

    def remove_commands(self) -> None:
        """Remove nWave commands (delegates to shared nw-namespace remover)."""
        self._remove_nw_namespace_subdir("commands")

    def _remove_nw_namespace_subdir(self, noun: str) -> None:
        """Remove ~/.claude/{noun}/nw/ directory + cascade-clean empty parent.

        Shared by remove_agents("agents") and remove_commands("commands").
        Both followed identical 27-line bodies; consolidated 2026-05-03 (RPP L3).

        Args:
            noun: Plural label for logging + directory name ("agents" / "commands").
        """
        nested_dir = self.claude_config_dir / noun / "nw"
        parent_dir = self.claude_config_dir / noun

        if self.dry_run:
            self.logger.info(f"  🚨 [DRY RUN] Would remove nWave {noun}")
            if nested_dir.exists():
                self.logger.info(f"    🚨 [DRY RUN] Would remove {noun}/nw directory")
            return

        with self.logger.progress_spinner(f"  🚧 Removing nWave {noun}..."):
            if nested_dir.exists():
                shutil.rmtree(nested_dir)
                self.logger.info(f"  🗑️ Removed {noun}/nw directory")

            # Flat layout: a public/flat install writes flat {noun}/nw-*.md
            # symlinks into the dedicated nested_dir above; the nested remover
            # only clears the nested root, missing them. Ownership here is
            # POSITIVE, never prefix/glob: only a symlink whose raw target
            # lexically resolves inside nested_dir (dangling included, so it
            # is unlinked rather than followed -- a followed dangling link
            # would otherwise survive uninstall and crash the next install's
            # backup step) is ours. A regular file, a directory, or a symlink
            # pointing elsewhere is a preserved user sibling even when its
            # name starts with nw-.
            flat_removed = 0
            if parent_dir.exists():
                for entry in parent_dir.glob("nw-*"):
                    if _is_legacy_flat_nw_symlink(entry, nested_dir):
                        entry.unlink()
                        flat_removed += 1
            if flat_removed:
                self.logger.info(
                    f"  🗑️ Removed {flat_removed} legacy flat {noun}/nw-* symlinks"
                )

            # Remove parent directory if empty
            if parent_dir.exists():
                try:
                    if not any(parent_dir.iterdir()):
                        parent_dir.rmdir()
                        self.logger.info(f"  🗑️ Removed empty {noun} directory")
                    else:
                        self.logger.info(
                            f"  📂 Kept {noun} directory (contains other files)"
                        )
                except OSError:
                    self.logger.info(
                        f"  📂 Kept {noun} directory (contains other files)"
                    )

    def remove_config_files(self) -> None:
        """Remove nWave configuration files."""
        if self.dry_run:
            self.logger.info("  🚨 [DRY RUN] Would remove nWave configuration files")
            return

        with self.logger.progress_spinner("  🚧 Removing nWave configuration files..."):
            config_files = ["nwave-manifest.txt", "nwave-install.log"]

            for config_file in config_files:
                file_path = self.claude_config_dir / config_file
                if file_path.exists():
                    file_path.unlink()
                    self.logger.info(f"  🗑️ Removed {config_file}")

    def remove_backups(self) -> None:
        """Remove nWave backup directories."""
        if self.dry_run:
            self.logger.info("  🚨 [DRY RUN] Would remove nWave backup directories")
            return

        with self.logger.progress_spinner("  🚧 Removing nWave backup directories..."):
            backup_count = 0
            backups_dir = self.claude_config_dir / "backups"

            if backups_dir.exists():
                for backup_dir in backups_dir.glob("nwave-*"):
                    if backup_dir.is_dir():
                        # Skip the backup we just created during this uninstall
                        if (
                            self.backup_before_removal
                            and backup_dir == self.backup_manager.backup_dir
                        ):
                            self.logger.info(
                                f"  📦 Preserving current uninstall backup: {backup_dir.name}"
                            )
                            continue

                        shutil.rmtree(backup_dir)
                        backup_count += 1

            if backup_count > 0:
                self.logger.info(
                    f"  🗑️ Removed {backup_count} old nWave backup directories"
                )
            else:
                self.logger.info("  ✅ No old nWave backup directories found")

    def remove_des_hooks(self) -> None:
        """Remove installer-owned DES hooks from Claude Code settings.

        The retired plugin was the sole writer and cleanup authority for this
        surface.  The former standalone hook installer was a second writer
        with substring-based ownership detection, so it could delete a
        neighbouring user or External hook merely because its command happened to
        contain a DES-looking fragment.
        """
        if self.dry_run:
            self.logger.info("  🚨 [DRY RUN] Would remove DES hooks from settings.json")
            return

        with self.logger.progress_spinner("  🚧 Removing DES hooks..."):
            # Legacy settings/hooks cleanup delegates to the kept upgrade
            # shell: its manifest-witness cleanup is the single authority for
            # removing the retired hook registrations from the host documents
            # (Claude settings.json, Codex hooks.json, Cursor hooks.json and
            # the native manifests) while preserving operator-owned entries.
            from io import StringIO

            from nwave_ai.upgrade_shell import cleanup, real_port

            outcome = cleanup(
                home=str(Path.home()),
                out=StringIO(),
                err=StringIO(),
                fs=real_port(),
            )
            if outcome.exit_code == 0:
                self.logger.info("  🗑️ Removed DES hooks from settings.json")
            else:
                self.logger.warn(
                    f"  ⚠️ DES hook removal: upgrade cleanup reported "
                    f"{outcome.exit_code} indeterminate artifact(s); rerun uninstall "
                    "after closing the hosts"
                )

    def remove_copilot_des_hooks(self) -> None:
        """Remove the nWave DES hook config from the Copilot CLI hooks dir.

        slice-01 of copilot-cli-integration: the installer writes
        ``<COPILOT_HOME>/hooks/nwave-des.json`` (FM-1 file-in-dir) when Copilot
        is detected. Clean uninstall MUST remove it (and the manifest) while
        leaving any hook the operator authored themselves untouched -- the
        plugin owns its own dedicated file, so foreign hooks survive.
        """
        if self.dry_run:
            self.logger.info("  🚨 [DRY RUN] Would remove Copilot DES hook config")
            return

        # Legacy removal inlined: nWave owns its own dedicated hook file, so
        # any hook file the operator authored themselves (a different filename
        # in the hooks dir) is preserved untouched.
        copilot_dir = _copilot_config_dir()
        hook_path = copilot_dir / "hooks" / "nwave-des.json"
        try:
            if hook_path.exists():
                hook_path.unlink()
                self.logger.info(f"  Removed nWave DES hook from {hook_path}")
            manifest_path = copilot_dir / ".nwave-des-manifest.json"
            if manifest_path.exists():
                manifest_path.unlink()
                self.logger.info(f"  Removed Copilot DES manifest: {manifest_path}")
        except OSError as error:
            self.logger.warn(f"  ⚠️ Copilot DES hook removal failed: {error}")

    def remove_opencode_des_hooks(self) -> None:
        """Remove the nWave DES shim from the OpenCode plugins dir.

        The installer writes ``<OPENCODE_CONFIG_DIR>/plugins/nwave-des.ts``
        and its manifest when OpenCode is detected. Clean uninstall MUST
        remove both (mirrors remove_copilot_des_hooks) while leaving any
        plugin the operator authored themselves untouched -- OpenCodeDESPlugin
        owns only its own dedicated shim file.
        """
        if self.dry_run:
            self.logger.info("  🚨 [DRY RUN] Would remove OpenCode DES shim")
            return

        # Legacy shim removal inlined: the old OpenCodeDESPlugin is deleted,
        # and uninstall only ever removes that plugin's own two files -- the
        # shim and its manifest -- leaving operator-authored plugins alone.
        opencode_dir = _opencode_config_dir()
        shim_path = opencode_dir / "plugins" / "nwave-des.ts"
        manifest_path = opencode_dir / ".nwave-des-manifest.json"
        drift = _opencode_shim_sha256_drift(shim_path, manifest_path)
        if drift is not None:
            self.logger.warn(
                f"  DES shim sha256 drift detected before uninstall: {drift} "
                f"-- removing anyway (uninstall is unconditional); if this "
                f"was a manual edit, save a copy first."
            )
        try:
            if shim_path.exists():
                shim_path.unlink()
                self.logger.info(f"  Removed DES shim: {shim_path}")
            if manifest_path.exists():
                manifest_path.unlink()
                self.logger.info(f"  Removed DES manifest: {manifest_path}")
        except OSError as error:
            self.logger.error(f"  ❌ OpenCode DES shim removal failed: {error}")
            return

    def remove_cursor_des_hooks(self) -> None:
        """Remove the nWave DES hook from ~/.cursor/hooks.json.

        The legacy installer wrote a ``preToolUse`` entry into Cursor's global
        hooks.json when Cursor was detected. Clean uninstall MUST remove it
        while leaving any hook the operator authored themselves untouched —
        only entries carrying the legacy adapter marker are nWave-owned.
        """
        if self.dry_run:
            self.logger.info("  🚨 [DRY RUN] Would remove Cursor DES hook")
            return

        _ADAPTER_MARKER = "claude_code_hook_adapter"
        cursor_dir = _cursor_config_dir()
        hooks_path = cursor_dir / "hooks.json"

        def _is_nwave_entry(entry: object) -> bool:
            if not isinstance(entry, dict):
                return False
            command = entry.get("command", "")
            if isinstance(command, str) and _ADAPTER_MARKER in command:
                return True
            nested = entry.get("hooks")
            if isinstance(nested, list):
                return any(
                    isinstance(h, dict) and _ADAPTER_MARKER in str(h.get("command", ""))
                    for h in nested
                )
            return False

        try:
            if hooks_path.exists():
                try:
                    doc = json.loads(hooks_path.read_text(encoding="utf-8"))
                except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                    doc = {}
                if not isinstance(doc, dict) or not isinstance(doc.get("hooks"), dict):
                    doc = {}
                cleaned_events: dict[str, object] = {}
                for event_name, entries in doc["hooks"].items():
                    if not isinstance(entries, list):
                        cleaned_events[event_name] = entries
                        continue
                    cleaned_events[event_name] = [
                        entry for entry in entries if not _is_nwave_entry(entry)
                    ]
                cleaned: dict[str, object] = {"hooks": cleaned_events}
                if "version" in doc:
                    cleaned["version"] = doc["version"]
                events = cleaned.get("hooks", {})
                any_user_entries = any(
                    isinstance(v, list) and len(v) > 0 for v in events.values()
                )
                if any_user_entries:
                    hooks_path.write_text(
                        json.dumps(cleaned, indent=2) + "\n", encoding="utf-8"
                    )
                else:
                    hooks_path.unlink()
                self.logger.info(f"  Removed nWave DES hook from {hooks_path}")

            manifest_path = cursor_dir / ".nwave-des-manifest.json"
            if manifest_path.exists():
                manifest_path.unlink()
                self.logger.info(f"  Removed Cursor DES manifest: {manifest_path}")
        except OSError as error:
            self.logger.warn(f"  ⚠️ Cursor DES hook removal failed: {error}")

    def remove_kept_hook_registrations(self) -> None:
        """Remove the kept nWave hook registrations and the kept OMP hook shim.

        The kept hook plugin writes its registrations into the Claude, Codex,
        Cursor and Copilot hook files, and the OMP extension shim with its manifest.
        Only entries equal to a canonical kept registration are removed;
        operator-authored entries are preserved. A non-Claude hook file left with
        nothing else is deleted; Claude's settings.json is rewritten and never
        deleted. The OMP shim is removed only while it still matches its manifest.
        """
        if self.dry_run:
            self.logger.info(
                "  🚨 [DRY RUN] Would remove kept nWave hook registrations"
            )
            return

        from nwave_ai.hooks.registration import HOOK_FILE, without_registrations
        from scripts.shared.install_paths import codex_config_dir, omp_extensions_dir

        targets = (
            ("claude", self.claude_config_dir / HOOK_FILE["claude"]),
            ("codex", codex_config_dir() / HOOK_FILE["codex"]),
            ("cursor", _cursor_config_dir() / HOOK_FILE["cursor"]),
            ("copilot", _copilot_config_dir() / HOOK_FILE["copilot"]),
        )
        for host, path in targets:
            try:
                if not path.is_file():
                    continue
                before = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(before, dict):
                    continue
                after = without_registrations(before, host)
                if after == before:
                    continue
                if host != "claude" and _holds_no_entries(after):
                    path.unlink()
                else:
                    path.write_text(
                        json.dumps(after, indent=2) + "\n", encoding="utf-8"
                    )
                self.logger.info(
                    f"  🗑️ Removed kept nWave hook registrations from {path}"
                )
            except (OSError, ValueError) as error:
                self.logger.warn(
                    f"  ⚠️ Kept nWave hook removal failed for {path}: {error}"
                )

        omp_dir = omp_extensions_dir()
        omp_shim = omp_dir / "nwave-hooks.ts"
        omp_manifest = omp_dir / ".nwave-des-manifest.json"
        if (
            omp_shim.exists()
            and _opencode_shim_sha256_drift(omp_shim, omp_manifest) is None
        ):
            try:
                omp_shim.unlink()
                omp_manifest.unlink()
                self.logger.info(f"  🗑️ Removed kept OMP hooks extension: {omp_shim}")
            except OSError as error:
                self.logger.warn(
                    f"  ⚠️ Kept OMP hooks extension removal failed: {error}"
                )

    def remove_devin_skills(self) -> None:
        """Remove manifest-owned nWave skills from ~/.config/devin/skills/.

        The installer copies ``nw-*`` skill directories when Devin is
        detected. Clean uninstall removes only names recorded in the
        DevinSkillsPlugin manifest; user-created skills are never touched.
        """
        if self.dry_run:
            self.logger.info("  🚨 [DRY RUN] Would remove Devin skills")
            return

        try:
            from scripts.install.plugins.base import InstallContext
            from scripts.install.plugins.devin_skills_plugin import DevinSkillsPlugin
        except ImportError:
            from plugins.base import InstallContext
            from plugins.devin_skills_plugin import DevinSkillsPlugin

        context = InstallContext(
            claude_dir=self.claude_config_dir,
            scripts_dir=self.claude_config_dir / "scripts",
            templates_dir=self.claude_config_dir / "templates",
            logger=self.logger,
        )
        result = DevinSkillsPlugin().uninstall(context)
        if result.success:
            self.logger.info("  🗑️ Removed Devin skills")
        else:
            self.logger.warn(f"  ⚠️ Devin skills removal: {result.message}")

    def remove_omp_assets(self) -> None:
        """Remove manifest-owned OMP skills, agents, commands and extension.

        Resolves the SAME omp destination the installer plugins write through
        (``scripts.shared.install_paths`` omp helpers), so an uninstall can
        never remove from a root the installer did not write. Ownership is
        manifest-driven: only names recorded in the omp manifests are
        removed; foreign and user-created entries (including private
        symlinks) are never touched. A named-profile environment is honored
        by refusal: the uninstall reports the unsupported profile rather
        than silently operating on the default root.
        """
        if self.dry_run:
            self.logger.info(
                "  🚨 [DRY RUN] Would remove OMP skills, agents, commands and DES extension"
            )
            return

        try:
            from scripts.install.plugins.base import InstallContext
            from scripts.install.plugins.omp_agents_plugin import OmpAgentsPlugin
            from scripts.install.plugins.omp_commands_plugin import OmpCommandsPlugin
            from scripts.install.plugins.omp_common import OmpProfileNotSupported
            from scripts.install.plugins.omp_skills_plugin import OmpSkillsPlugin
        except ImportError:
            from plugins.base import InstallContext
            from plugins.omp_agents_plugin import OmpAgentsPlugin
            from plugins.omp_commands_plugin import OmpCommandsPlugin
            from plugins.omp_common import OmpProfileNotSupported
            from plugins.omp_skills_plugin import OmpSkillsPlugin

        context = InstallContext(
            claude_dir=self.claude_config_dir,
            scripts_dir=self.claude_config_dir / "scripts",
            templates_dir=self.claude_config_dir / "templates",
            logger=self.logger,
        )
        try:
            # OMP 18.5 resolves the skills root from PI_CODING_AGENT_DIR while
            # the agents root follows the config root. The uninstall
            # environment may no longer carry the install-time override
            # spelling, so candidates come from the persisted receipt
            # (install.host_paths.omp_skills_dir) AND both env-resolved
            # spellings. Each pass is manifest-driven and a no-op when its
            # root carries no trusted manifest, so a root that never saw an
            # install cannot lose foreign or private bytes.
            agents_result = OmpAgentsPlugin().uninstall(context)
            skills_results = []
            from scripts.shared.install_paths import (
                omp_config_root,
                omp_extensions_dir,
                omp_skills_dir,
            )

            receipt_candidates: list[str] = []
            receipt_path = Path.home() / ".nwave" / "config.json"
            try:
                receipt_doc = json.loads(receipt_path.read_text(encoding="utf-8"))
                recorded = (
                    receipt_doc.get("install", {})
                    .get("host_paths", {})
                    .get("omp_skills_dir")
                )
                if isinstance(recorded, str) and recorded:
                    receipt_candidates.append(recorded)
            except (OSError, json.JSONDecodeError):
                pass

            roots = {
                str(omp_skills_dir()): "env",  # current env spelling
                str(omp_config_root() / "agent" / "skills"): None,  # no override
            }
            for path in receipt_candidates:
                roots.setdefault(path, "receipt")
            previous_env = os.environ.get("PI_CODING_AGENT_DIR")
            try:
                for root_str, spelling in roots.items():
                    root = Path(root_str)
                    manifests = (
                        root / ".nwave-manifest.json",
                        root.parent / "commands" / ".nwave-commands-manifest.json",
                        root.parent / "extensions" / ".nwave-des-manifest.json",
                    )
                    if not any(path.exists() for path in manifests):
                        continue
                    if spelling is None:
                        os.environ.pop("PI_CODING_AGENT_DIR", None)
                    elif spelling == "receipt" and root.parent != (
                        omp_config_root() / "agent"
                    ):
                        # <override>/skills recorded at install time
                        os.environ["PI_CODING_AGENT_DIR"] = str(root.parent)
                    skills_results.append(OmpSkillsPlugin().uninstall(context))
                    skills_results.append(OmpCommandsPlugin().uninstall(context))
                    # The legacy OMP extension is manifest-owned: drop the
                    # shim and its manifest under the extensions root.
                    omp_extension_dir = omp_extensions_dir()
                    extension_manifest = omp_extension_dir / ".nwave-des-manifest.json"
                    if extension_manifest.is_file():
                        extension_shim = omp_extension_dir / "nwave-des.ts"
                        extension_shim.unlink(missing_ok=True)
                        extension_manifest.unlink(missing_ok=True)
            finally:
                if previous_env is None:
                    os.environ.pop("PI_CODING_AGENT_DIR", None)
                else:
                    os.environ["PI_CODING_AGENT_DIR"] = previous_env
        except OmpProfileNotSupported as e:
            self.logger.warn(f"  ⚠️ OMP asset removal skipped: {e}")
            return
        if all(r.success for r in skills_results) and agents_result.success:
            self.logger.info("  🗑️ Removed OMP assets (manifest-owned only)")
        else:
            failures = [
                result.message
                for result in (*skills_results, agents_result)
                if not result.success
            ]
            self.logger.warn(f"  ⚠️ OMP asset removal: {'; '.join(failures)}")

    def remove_des_hook_scripts(self) -> None:
        """Remove current and retired installer-owned DES hook scripts."""
        if self.dry_run:
            self.logger.info("  🚨 [DRY RUN] Would remove DES hook scripts")
            return

        # Legacy script names inlined: the current list shipped exactly one
        # script, and the small retired list is intentional migration cleanup
        # for old installations.
        scripts_dir = self.claude_config_dir / "scripts"
        removed_count = 0
        legacy_hook_scripts = (
            "git_stash_guard.py",
            "spine_ledger_gate.py",
            "spine_ledger_pre_commit_hook.py",
            "spine_ledger_subagent_stop_detector.py",
            "no_verify_reminder.py",
        )
        for hook_script_name in legacy_hook_scripts:
            hook_script_path = scripts_dir / hook_script_name
            if hook_script_path.exists():
                hook_script_path.unlink()
                removed_count += 1
                self.logger.info(f"  🗑️ Removed DES hook script: {hook_script_name}")

        if removed_count == 0:
            self.logger.info("  ✅ No DES hook scripts to remove (already clean)")

    def _has_flat_nw_residue(self, noun: str) -> bool:
        """True if a positively-identified legacy flat nw-* symlink survives
        under ~/.claude/{noun}/.

        Detects the orphan flat layout the nested-only remover used to miss,
        INCLUDING dangling symlinks (glob yields them without stat) -- but
        only a symlink whose raw target lexically resolves inside the
        dedicated {noun}/nw/ root (see `_is_legacy_flat_nw_symlink`). A
        user-owned flat file, directory, or a symlink pointing elsewhere is
        never residue, even when its name starts with nw-. Used by
        validate_removal so a genuine legacy leftover is an honest ❌, never
        a false ✅, while a coincidentally-named user sibling is never
        misclassified as nWave residue.
        """
        parent = self.claude_config_dir / noun
        if not parent.exists():
            return False
        nested_dir = parent / "nw"
        return any(
            _is_legacy_flat_nw_symlink(entry, nested_dir)
            for entry in parent.glob("nw-*")
        )

    def prepare_attribution_removal(self) -> None:
        """Retain caller and ownership evidence before global config deletion."""
        self._attribution_repository = Path(
            os.environ.get("NWAVE_PROJECT_ROOT") or Path.cwd()
        ).resolve()
        self._attribution_recorded_hooks_dir = read_attribution_hooks_dir(
            nwave_config_dir()
        )

    def remove_attribution(self) -> None:
        """Remove managed Claude credit, known fallback shims and shared runtime.

        Hook locations are retained before the global-config deletion prompt.
        A surviving shim is reported; the runtime is removed even in that case.
        An unremovable runtime reaches final removal validation as a failure.
        """
        if self.dry_run:
            self.logger.info(
                "  🚨 [DRY RUN] Would remove managed attribution settings, shims and runtime"
            )
            return

        with self.logger.progress_spinner("  🚧 Removing nWave attribution..."):
            try:
                config_dir = nwave_config_dir()
                if self._attribution_repository is None:
                    self.prepare_attribution_removal()
                warnings = remove_attribution_hook(
                    config_dir,
                    repository=self._attribution_repository,
                    recorded_hooks_dir=self._attribution_recorded_hooks_dir,
                )
                for warning in warnings:
                    self.logger.warn(f"  ⚠️ {warning}")
                remove_settings_attribution(
                    config_dir=config_dir, claude_dir=self.claude_config_dir
                )
                self.logger.info("  🗑️ Removed managed attribution settings and runtime")
            except Exception as exc:  # fail-safe: never abort the uninstall
                self.logger.warn(f"  ⚠️ Attribution removal skipped: {exc}")
                self._removal_failures.append(f"attribution removal failed: {exc}")

    def validate_removal(self) -> bool:
        """Validate complete removal."""
        if self.dry_run:
            self.logger.info("  🚨 [DRY RUN] Would validate complete removal")
            return True

        self.logger.info("  🔍 Validating complete removal...")

        inventory = scan_claude_ownership(self.claude_config_dir)
        manifest_file = self.claude_config_dir / "nwave-manifest.txt"
        install_log = self.claude_config_dir / "nwave-install.log"

        # Check DES hooks + managed attribution removed
        des_hooks_removed = True
        attribution_removed = True
        settings_file = self.claude_config_dir / "settings.json"
        if settings_file.exists():
            try:
                with open(settings_file, encoding="utf-8") as f:
                    config = json.load(f)
                    if "hooks" in config:
                        hooks_str = json.dumps(config["hooks"])
                        if (
                            "des/adapters/drivers/hooks/claude_code_hook_adapter"
                            in hooks_str
                        ):
                            des_hooks_removed = False
                    # Fail only on the MANAGED value; a user-modified credit must
                    # NOT fail validation (compare to the constant, not presence).
                    if (config.get("attribution") or {}).get(
                        "commit"
                    ) == NWAVE_MANAGED_COMMIT:
                        attribution_removed = False
            except (OSError, json.JSONDecodeError):
                pass

        checks = [
            (
                "Agents",
                not inventory.agents_legacy_root_present
                and not self._has_flat_nw_residue("agents"),
            ),
            (
                "Commands",
                not inventory.commands_legacy_root_present
                and not self._has_flat_nw_residue("commands"),
            ),
            ("DES Hooks", des_hooks_removed),
            ("Attribution", attribution_removed),
            ("Manifest", not manifest_file.exists()),
            ("Install Log", not install_log.exists()),
        ]

        errors = 0
        for name, removed in checks:
            if removed:
                self.logger.info(f"    ✅ {name} removed")
            else:
                self.logger.error(f"    ❌ {name} still exists")
                errors += 1

        skills_state = self._skills_removal_state()
        skills_clean = (
            skills_state in ("removed-completely-this-run", "already-clean")
            and not inventory.skills_owned_present
            and not inventory.skills_legacy_root_present
        )
        if skills_clean:
            self.logger.info("    ✅ Skills removed")
        else:
            category = {
                "absent-before-run": "absent",
                "corrupt": "corrupt",
                "blocked": "blocked",
            }.get(skills_state, "residue")
            self.logger.error(
                f"    ❌ Skills not verified clean:\n"
                f"{self._skills_removal_diagnosis(category)}"
            )
            errors += 1

        for family_label, owned_present, display_name in (
            ("templates", inventory.templates_owned_present, "Templates"),
            ("utility scripts", inventory.utilities_owned_present, "Utility scripts"),
            ("data", inventory.data_owned_present, "Data"),
        ):
            state = self._family_removal_state(family_label)
            # Unlike skills (always installed, so an unmanifested skills dir
            # is suspicious), these families are optional: a directory that
            # was never installer-owned -- no manifest, no owned residue --
            # is an idempotent no-op, not a validation failure. Only
            # "corrupt"/"blocked"/actual residue stay LOUD.
            clean = (
                state
                in ("removed-completely-this-run", "already-clean", "absent-before-run")
                and not owned_present
            )
            if clean:
                self.logger.info(f"    ✅ {display_name} removed")
            else:
                category = {
                    "corrupt": "corrupt",
                    "blocked": "blocked",
                }.get(state, "residue")
                self.logger.error(
                    f"    ❌ {display_name} not verified clean:\n"
                    f"{self._family_removal_diagnosis(family_label, category)}"
                )
                errors += 1

        for failure in self._removal_failures:
            self.logger.error(f"    ❌ Installed file still present: {failure}")
            errors += 1

        if errors == 0:
            self.logger.info("  ✅ Uninstallation validation passed")
            return True
        else:
            self.logger.error(
                f"  ❌ Uninstallation validation failed ({errors} errors)"
            )
            return False

    def create_uninstall_report(self) -> None:
        """Create uninstallation report."""
        if self.dry_run:
            self.logger.info("  🚨 [DRY RUN] Would create uninstall report")
            return

        backup_dir = (
            self.backup_manager.backup_dir if self.backup_before_removal else None
        )

        ManifestWriter.write_uninstall_report(self.claude_config_dir, backup_dir)

        self.logger.info("  📄 Uninstall report created")


def show_title_panel(logger: Logger, dry_run: bool = False) -> None:
    """Display styled title panel when uninstaller starts.

    Args:
        logger: Logger instance for styled output.
        dry_run: Whether running in dry-run mode.
    """
    print_logo(logger)
    mode_indicator = " 🚨 [DRY RUN]" if dry_run else ""
    logger.info("")
    logger.info(f"  🗑️ Uninstaller v{__version__}{mode_indicator}")
    logger.info("")


def show_uninstall_summary(logger: Logger, backup_dir=None) -> None:
    """Display uninstallation summary panel at end of successful uninstall.

    Args:
        logger: Logger instance for styled output.
        backup_dir: Path to backup directory (if created).
    """
    logger.info("")
    logger.info("  🍾 Framework removed successfully")
    logger.info("    ✅ All nWave agents removed")
    logger.info("    ✅ All nWave commands removed")
    logger.info("    ✅ DES hooks removed")
    logger.info("    ✅ Configuration files removed")
    logger.info("    ✅ Installation logs removed")
    logger.info("    ✅ Old backup directories removed")
    if backup_dir:
        logger.info(f"    📦 Backup: {backup_dir}")
    else:
        logger.info("    🗑️ No backup created")
    logger.info("")


def show_help():
    """Show help message."""
    print_logo()
    B, N = _ANSI_BLUE, _ANSI_NC
    help_text = f"""
{B}DESCRIPTION:{N}
    Completely removes the nWave ATDD agent framework from your global Claude config directory.
    This removes all specialized agents, commands, configuration files, logs, and backups.

{B}USAGE:{N}
    python uninstall_nwave.py [OPTIONS]

{B}OPTIONS:{N}
    --backup         Create backup before removal (recommended)
    --force          Skip confirmation prompts
    --dry-run        Show what would be removed without making any changes
    --help           Show this help message

{B}EXAMPLES:{N}
    python uninstall_nwave.py              # Interactive uninstall with confirmation
    python uninstall_nwave.py --dry-run    # Show what would be removed
    python uninstall_nwave.py --backup     # Create backup before removal
    python uninstall_nwave.py --force      # Uninstall without confirmation prompts

{B}WHAT GETS REMOVED:{N}
    - All nWave agents in agents/nw/ directory
    - All nWave commands in commands/nw/ directory
    - DES hooks from Claude Code settings.json
    - nWave configuration files (manifest)
    - nWave installation logs and backup directories

{B}IMPORTANT:{N}
    This action cannot be undone unless you use --backup option.
"""
    print(help_text)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Uninstall nWave framework", add_help=False
    )
    parser.add_argument(
        "--backup", action="store_true", help="Create backup before removal"
    )
    parser.add_argument(
        "--force", action="store_true", help="Skip confirmation prompts"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be done"
    )
    parser.add_argument("--help", "-h", action="store_true", help="Show help")

    args = parser.parse_args()

    if args.help:
        show_help()
        return 0

    uninstaller = NWaveUninstaller(
        backup_before_removal=args.backup, force=args.force, dry_run=args.dry_run
    )

    # Show title panel at startup
    show_title_panel(uninstaller.logger, dry_run=args.dry_run)

    if args.dry_run:
        uninstaller.logger.info("  🚨 DRY RUN MODE; no changes will be made")

    # Check for installation
    if not uninstaller.check_installation():
        return 0

    # A native-only (Codex/Copilot/OpenCode) uninstall has no Claude
    # discovery surface -- do not enable persistent uninstall logging under
    # claude_config_dir for it.
    if uninstaller.claude_installation_present:
        uninstaller.enable_uninstall_logging()

    # Confirm removal
    if not uninstaller.confirm_removal():
        uninstaller.logger.info("")
        uninstaller.logger.info("  ⚠️ Uninstallation cancelled by user")
        return 0

    uninstaller.prepare_attribution_removal()

    # Check global config (prompt keep/delete before backup)
    uninstaller.check_global_config()

    # Create backup
    uninstaller.create_backup()

    # Remove components
    uninstaller.remove_agents()
    uninstaller.remove_skills()
    uninstaller.remove_commands()
    uninstaller.remove_templates()
    uninstaller.remove_utility_scripts()
    uninstaller.remove_data()
    uninstaller.remove_lib_python()
    uninstaller.remove_host_neutral_des_runtime()
    uninstaller.remove_des_hooks()
    uninstaller.remove_copilot_des_hooks()
    uninstaller.remove_opencode_des_hooks()
    uninstaller.remove_cursor_des_hooks()
    uninstaller.remove_kept_hook_registrations()
    uninstaller.remove_devin_skills()
    uninstaller.remove_omp_assets()
    uninstaller.remove_des_hook_scripts()
    uninstaller.remove_attribution()
    uninstaller.remove_config_files()
    uninstaller.remove_backups()
    uninstaller.remove_native_assets()
    uninstaller.remove_des_shims_and_scripts()
    uninstaller.remove_project_nwave_config()
    uninstaller.remove_runtime_pointer_and_lock()

    # Validate and report
    if not uninstaller.validate_removal():
        uninstaller.logger.error("  ❌ Uninstallation failed validation")
        return 1

    # A native-only uninstall has no Claude discovery surface for the report
    # to live in -- skip writing it rather than creating claude_config_dir.
    if uninstaller.claude_installation_present:
        uninstaller.create_uninstall_report()

    # Show uninstall summary panel
    backup_dir = uninstaller.backup_manager.backup_dir if args.backup else None
    show_uninstall_summary(uninstaller.logger, backup_dir)

    return 0


if __name__ == "__main__":
    sys.exit(main())
