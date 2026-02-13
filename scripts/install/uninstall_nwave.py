#!/usr/bin/env python3
"""
nWave Framework Uninstallation Script

Cross-platform uninstaller for the nWave methodology framework.
Completely removes nWave framework from global Claude config directory.

Usage: python uninstall_nwave.py [--backup] [--force] [--dry-run] [--help]
"""

import argparse
import json
import shutil
import sys


try:
    from scripts.install.install_des_hooks import DESHookInstaller
    from scripts.install.install_nwave import print_logo
    from scripts.install.install_utils import (
        BackupManager,
        Logger,
        ManifestWriter,
        PathUtils,
        confirm_action,
    )
except ImportError:
    from install_des_hooks import DESHookInstaller
    from install_nwave import print_logo
    from install_utils import (
        BackupManager,
        Logger,
        ManifestWriter,
        PathUtils,
        confirm_action,
    )

# ANSI color codes for --help output (only consumer)
_ANSI_BLUE = "\033[0;34m"
_ANSI_NC = "\033[0m"  # No Color

__version__ = "1.1.0"


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
        log_file = self.claude_config_dir / "nwave-uninstall.log"
        self.logger = Logger(log_file if not dry_run else None)
        self.backup_manager = BackupManager(self.logger, "uninstall")

    def check_installation(self) -> bool:
        """Check for existing nWave installation."""
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

    def create_backup(self) -> None:
        """Create backup before removal."""
        if not self.backup_before_removal:
            return

        self.backup_manager.create_backup(dry_run=self.dry_run)

    def remove_agents(self) -> None:
        """Remove nWave agents."""
        if self.dry_run:
            self.logger.info("  🚨 [DRY RUN] Would remove nWave agents")
            agents_nw_dir = self.claude_config_dir / "agents" / "nw"
            if agents_nw_dir.exists():
                self.logger.info("    🚨 [DRY RUN] Would remove agents/nw directory")
            return

        with self.logger.progress_spinner("  🚧 Removing nWave agents..."):
            agents_nw_dir = self.claude_config_dir / "agents" / "nw"
            if agents_nw_dir.exists():
                shutil.rmtree(agents_nw_dir)
                self.logger.info("  🗑️ Removed agents/nw directory")

            # Remove parent agents directory if empty
            agents_dir = self.claude_config_dir / "agents"
            if agents_dir.exists():
                try:
                    if not any(agents_dir.iterdir()):
                        agents_dir.rmdir()
                        self.logger.info("  🗑️ Removed empty agents directory")
                    else:
                        self.logger.info(
                            "  📂 Kept agents directory (contains other files)"
                        )
                except OSError:
                    self.logger.info(
                        "  📂 Kept agents directory (contains other files)"
                    )

    def remove_skills(self) -> None:
        """Remove nWave skills."""
        if self.dry_run:
            self.logger.info("  🚨 [DRY RUN] Would remove nWave skills")
            skills_nw_dir = self.claude_config_dir / "skills" / "nw"
            if skills_nw_dir.exists():
                self.logger.info("    🚨 [DRY RUN] Would remove skills/nw directory")
            return

        with self.logger.progress_spinner("  🚧 Removing nWave skills..."):
            skills_nw_dir = self.claude_config_dir / "skills" / "nw"
            if skills_nw_dir.exists():
                shutil.rmtree(skills_nw_dir)
                self.logger.info("  🗑️ Removed skills/nw directory")

            # Remove parent skills directory if empty
            skills_dir = self.claude_config_dir / "skills"
            if skills_dir.exists():
                try:
                    if not any(skills_dir.iterdir()):
                        skills_dir.rmdir()
                        self.logger.info("  🗑️ Removed empty skills directory")
                    else:
                        self.logger.info(
                            "  📂 Kept skills directory (contains other files)"
                        )
                except OSError:
                    self.logger.info(
                        "  📂 Kept skills directory (contains other files)"
                    )

    def remove_commands(self) -> None:
        """Remove nWave commands."""
        if self.dry_run:
            self.logger.info("  🚨 [DRY RUN] Would remove nWave commands")
            commands_nw_dir = self.claude_config_dir / "commands" / "nw"
            if commands_nw_dir.exists():
                self.logger.info("    🚨 [DRY RUN] Would remove commands/nw directory")
            return

        with self.logger.progress_spinner("  🚧 Removing nWave commands..."):
            commands_nw_dir = self.claude_config_dir / "commands" / "nw"
            if commands_nw_dir.exists():
                shutil.rmtree(commands_nw_dir)
                self.logger.info("  🗑️ Removed commands/nw directory")

            # Remove parent commands directory if empty
            commands_dir = self.claude_config_dir / "commands"
            if commands_dir.exists():
                try:
                    if not any(commands_dir.iterdir()):
                        commands_dir.rmdir()
                        self.logger.info("  🗑️ Removed empty commands directory")
                    else:
                        self.logger.info(
                            "  📂 Kept commands directory (contains other files)"
                        )
                except OSError:
                    self.logger.info(
                        "  📂 Kept commands directory (contains other files)"
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
        """Remove DES hooks from Claude Code settings."""
        if self.dry_run:
            self.logger.info("  🚨 [DRY RUN] Would remove DES hooks from settings.json")
            return

        with self.logger.progress_spinner("  🚧 Removing DES hooks..."):
            des_installer = DESHookInstaller(self.claude_config_dir)
            success = des_installer.uninstall()

            if success:
                self.logger.info("  🗑️ Removed DES hooks from settings.json")
            else:
                self.logger.warn("  ⚠️ DES hooks not found (may not be installed)")

    def validate_removal(self) -> bool:
        """Validate complete removal."""
        if self.dry_run:
            self.logger.info("  🚨 [DRY RUN] Would validate complete removal")
            return True

        self.logger.info("  🔍 Validating complete removal...")

        agents_nw_dir = self.claude_config_dir / "agents" / "nw"
        commands_nw_dir = self.claude_config_dir / "commands" / "nw"
        manifest_file = self.claude_config_dir / "nwave-manifest.txt"
        install_log = self.claude_config_dir / "nwave-install.log"

        # Check DES hooks removed
        des_hooks_removed = True
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
            except (OSError, json.JSONDecodeError):
                pass

        checks = [
            ("Agents", not agents_nw_dir.exists()),
            ("Commands", not commands_nw_dir.exists()),
            ("DES Hooks", des_hooks_removed),
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

    # Confirm removal
    if not uninstaller.confirm_removal():
        uninstaller.logger.info("")
        uninstaller.logger.info("  ⚠️ Uninstallation cancelled by user")
        return 0

    # Create backup
    uninstaller.create_backup()

    # Remove components
    uninstaller.remove_agents()
    uninstaller.remove_skills()
    uninstaller.remove_commands()
    uninstaller.remove_des_hooks()
    uninstaller.remove_config_files()
    uninstaller.remove_backups()

    # Validate and report
    if not uninstaller.validate_removal():
        uninstaller.logger.error("  ❌ Uninstallation failed validation")
        return 1

    uninstaller.create_uninstall_report()

    # Show uninstall summary panel
    backup_dir = uninstaller.backup_manager.backup_dir if args.backup else None
    show_uninstall_summary(uninstaller.logger, backup_dir)

    return 0


if __name__ == "__main__":
    sys.exit(main())
