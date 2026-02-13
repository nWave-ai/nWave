#!/usr/bin/env python3
"""
Enhanced Backup System for nWave Framework Installation

Prevents configuration loss and enables framework coexistence.
Detects conflicts between nWave and other frameworks (like SuperClaude).

Usage: python enhanced_backup_system.py {backup|restore|list|status} [TIMESTAMP]
"""

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

from install_utils import Logger, PathUtils


# ANSI color codes for terminal output (replaces legacy Colors class)
_ANSI_BLUE = "\033[0;34m"
_ANSI_NC = "\033[0m"  # No Color

__version__ = "1.0.0"


class EnhancedBackupSystem:
    """Enhanced backup system with conflict detection."""

    def __init__(self):
        """Initialize backup system."""
        self.claude_config_dir = PathUtils.get_claude_config_dir()
        self.backup_root_dir = self.claude_config_dir / "backups"
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.backup_dir = self.backup_root_dir / f"pre_nwave_{self.timestamp}"
        self.manifest_file = self.backup_dir / "backup_manifest.json"

        log_file = self.claude_config_dir / "backup_system.log"
        self.logger = Logger(log_file)

    def create_backup_structure(self) -> bool:
        """Create backup directory structure."""
        self.logger.info("Creating backup directory structure...")

        try:
            # Create main backup directories
            (self.backup_dir / "agents").mkdir(parents=True, exist_ok=True)
            (self.backup_dir / "commands").mkdir(parents=True, exist_ok=True)
            (self.backup_dir / "config").mkdir(parents=True, exist_ok=True)
            (self.backup_dir / "metadata").mkdir(parents=True, exist_ok=True)
            (self.backup_root_dir / "restore_scripts").mkdir(
                parents=True, exist_ok=True
            )

            self.logger.info(
                f"Backup directory structure created at: {self.backup_dir}"
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to create backup directory structure: {e}")
            return False

    def scan_existing_configuration(self) -> dict[str, int]:
        """Scan existing Claude configuration."""
        self.logger.info("Scanning existing Claude configuration...")

        config_summary = {
            "agents_count": 0,
            "commands_count": 0,
            "superclaud_commands": 0,
            "config_files": 0,
        }

        # Scan agents directory
        agents_dir = self.claude_config_dir / "agents"
        if agents_dir.exists():
            config_summary["agents_count"] = PathUtils.count_files(agents_dir, "*.md")
            self.logger.info(
                f"Found {config_summary['agents_count']} agent specification files"
            )
        else:
            self.logger.info("No agents directory found")

        # Scan commands directory
        commands_dir = self.claude_config_dir / "commands"
        if commands_dir.exists():
            config_summary["commands_count"] = PathUtils.count_files(
                commands_dir, "*.md"
            )
            self.logger.info(f"Found {config_summary['commands_count']} command files")

            # Scan for SuperClaude specific files
            config_summary["superclaud_commands"] = self._count_superclaud_commands(
                commands_dir
            )
            if config_summary["superclaud_commands"] > 0:
                self.logger.info(
                    f"Found {config_summary['superclaud_commands']} SuperClaude command files"
                )
        else:
            self.logger.info("No commands directory found")

        # Scan configuration files
        if (self.claude_config_dir / "settings.local.json").exists():
            config_summary["config_files"] += 1

        # Write scan summary
        summary_file = self.backup_dir / "metadata" / "scan_summary.txt"
        summary_content = f"""Agents: {config_summary["agents_count"]} files found
Commands: {config_summary["commands_count"]} files found
SuperClaude Commands: {config_summary["superclaud_commands"]} files found
Settings: {"settings.local.json found" if config_summary["config_files"] > 0 else "No settings file"}
"""
        summary_file.write_text(summary_content, encoding="utf-8")

        self.logger.info("Configuration scan completed")
        return config_summary

    def _count_superclaud_commands(self, commands_dir: Path) -> int:
        """Count SuperClaude command files."""
        count = 0
        for md_file in commands_dir.rglob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                if "sc:" in content:
                    count += 1
            except Exception:
                pass
        return count

    def detect_framework_conflicts(self) -> tuple[bool, list[dict]]:
        """
        Detect potential framework conflicts.

        Returns:
            Tuple of (conflicts_found, conflict_details)
        """
        self.logger.info("Detecting potential framework conflicts...")

        conflicts_found = False
        conflict_details = []

        # Check for nWave existing installation
        nwave_dir = self.claude_config_dir / "agents" / "cai"
        if nwave_dir.exists():
            self.logger.warn("Existing nWave installation detected")
            conflicts_found = True
            conflict_details.append(
                {
                    "type": "existing_nwave",
                    "severity": "HIGH",
                    "description": "nWave agents already exist",
                    "location": "agents/cai/",
                    "recommendation": "Backup and merge with new installation",
                }
            )

        # Check for SuperClaude commands
        commands_dir = self.claude_config_dir / "commands"
        if commands_dir.exists():
            sc_count = self._count_superclaud_commands(commands_dir)
            if sc_count > 0:
                self.logger.warn(f"SuperClaude commands detected: {sc_count} files")
                conflicts_found = True
                conflict_details.append(
                    {
                        "type": "superclaud_commands",
                        "severity": "CRITICAL",
                        "description": f"SuperClaude commands found: {sc_count} files",
                        "location": "commands/",
                        "recommendation": "Implement namespace separation (/sc/ vs /cai/)",
                    }
                )

        # Check for command name collisions
        nwave_commands = ["atdd", "root-why"]
        for cmd in nwave_commands:
            cmd_file = commands_dir / f"{cmd}.md" if commands_dir.exists() else None
            if cmd_file and cmd_file.exists():
                self.logger.warn(f"Command collision detected: {cmd}.md already exists")
                conflicts_found = True
                conflict_details.append(
                    {
                        "type": "command_collision",
                        "severity": "MEDIUM",
                        "description": f"Command file collision: {cmd}.md",
                        "location": f"commands/{cmd}.md",
                        "recommendation": "Rename existing or use namespace prefix",
                    }
                )

        # Write conflict report
        conflict_report = {
            "scan_timestamp": datetime.now().isoformat(),
            "conflicts_detected": conflicts_found,
            "conflict_details": conflict_details,
            "recommendations": [],
        }

        conflict_report_file = self.backup_dir / "metadata" / "conflict_analysis.json"
        conflict_report_file.write_text(
            json.dumps(conflict_report, indent=2), encoding="utf-8"
        )

        if conflicts_found:
            self.logger.error(
                f"Framework conflicts detected! See: {conflict_report_file}"
            )
        else:
            self.logger.info("No framework conflicts detected")

        return conflicts_found, conflict_details

    def backup_existing_configuration(self) -> bool:
        """Create comprehensive backup of existing configuration."""
        self.logger.info("Creating comprehensive backup of existing configuration...")

        try:
            # Backup agents directory
            agents_dir = self.claude_config_dir / "agents"
            if agents_dir.exists():
                backup_agents = self.backup_dir / "agents"
                shutil.copytree(agents_dir, backup_agents)
                self.logger.info("Agents directory backed up")

            # Backup commands directory
            commands_dir = self.claude_config_dir / "commands"
            if commands_dir.exists():
                backup_commands = self.backup_dir / "commands"
                shutil.copytree(commands_dir, backup_commands)
                self.logger.info("Commands directory backed up")

            # Backup configuration files
            settings_file = self.claude_config_dir / "settings.local.json"
            if settings_file.exists():
                backup_config = self.backup_dir / "config" / "settings.local.json"
                shutil.copy2(settings_file, backup_config)
                self.logger.info("Configuration files backed up")

            # Generate backup manifest
            self.generate_backup_manifest()

            self.logger.info("Configuration backup completed successfully")
            return True

        except Exception as e:
            self.logger.error(f"Backup failed: {e}")
            return False

    def generate_backup_manifest(self):
        """Generate backup manifest."""
        self.logger.info("Generating backup manifest...")

        # Count backed up files
        agents_count = PathUtils.count_files(self.backup_dir / "agents", "*.md")
        commands_count = PathUtils.count_files(self.backup_dir / "commands", "*.md")
        superclaud_commands = self._count_superclaud_commands(
            self.backup_dir / "commands"
        )
        config_count = (
            len(list((self.backup_dir / "config").rglob("*")))
            if (self.backup_dir / "config").exists()
            else 0
        )

        total_files = agents_count + commands_count + config_count

        # Check for nWave presence
        nwave_present = (self.claude_config_dir / "agents" / "cai").exists()
        superclaud_present = superclaud_commands > 0

        # Read conflict analysis
        conflict_file = self.backup_dir / "metadata" / "conflict_analysis.json"
        conflicts_detected = False
        if conflict_file.exists():
            try:
                with open(conflict_file, encoding="utf-8") as f:
                    conflict_data = json.load(f)
                    conflicts_detected = conflict_data.get("conflicts_detected", False)
            except Exception:
                pass

        manifest = {
            "backup_metadata": {
                "timestamp": datetime.now().isoformat(),
                "backup_dir": str(self.backup_dir),
                "backup_type": "pre_nwave_installation",
                "claude_config_dir": str(self.claude_config_dir),
            },
            "backup_summary": {
                "total_files": total_files,
                "agents_backed_up": agents_count,
                "commands_backed_up": commands_count,
                "superclaud_commands": superclaud_commands,
                "config_files_backed_up": config_count,
            },
            "backup_structure": {
                "agents": (self.backup_dir / "agents").exists(),
                "commands": (self.backup_dir / "commands").exists(),
                "config": (self.backup_dir / "config").exists(),
                "metadata": True,
            },
            "restoration_info": {
                "restoration_script": str(
                    self.backup_root_dir
                    / "restore_scripts"
                    / f"restore_{self.timestamp}.sh"
                ),
                "conflict_analysis": str(conflict_file),
                "scan_summary": str(self.backup_dir / "metadata" / "scan_summary.txt"),
            },
            "framework_analysis": {
                "nwave_present": nwave_present,
                "superclaud_present": superclaud_present,
                "conflicts_detected": conflicts_detected,
            },
        }

        self.manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        self.logger.info(f"Backup manifest generated: {self.manifest_file}")

    def generate_restoration_script(self):
        """Generate restoration script."""
        self.logger.info("Generating restoration script...")

        restore_script_path = (
            self.backup_root_dir / "restore_scripts" / f"restore_{self.timestamp}.sh"
        )

        restore_script_content = f"""#!/bin/bash

# nWave Framework Configuration Restoration Script
# Generated automatically by enhanced backup system

set -euo pipefail

BACKUP_DIR="{self.backup_dir}"
CLAUDE_CONFIG_DIR="{self.claude_config_dir}"
MANIFEST_FILE="$BACKUP_DIR/backup_manifest.json"

# Colors
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
NC='\\033[0m'

log_error() {{ echo -e "${{RED}}[ERROR]${{NC}} $1"; }}
log_success() {{ echo -e "${{GREEN}}[SUCCESS]${{NC}} $1"; }}
log_warn() {{ echo -e "${{YELLOW}}[WARN]${{NC}} $1"; }}

echo "=== nWave Configuration Restoration ==="
echo "Backup Location: $BACKUP_DIR"
echo "Restore Target: $CLAUDE_CONFIG_DIR"
echo ""

if [[ ! -f "$MANIFEST_FILE" ]]; then
    log_error "Backup manifest not found: $MANIFEST_FILE"
    exit 1
fi

# Display backup information (requires jq)
if command -v jq >/dev/null 2>&1; then
    echo "Backup Information:"
    jq -r '.backup_metadata | "Timestamp: \\(.timestamp)\\nBackup Type: \\(.backup_type)"' "$MANIFEST_FILE"
    echo ""

    echo "Files to Restore:"
    jq -r '.backup_summary | "Total Files: \\(.total_files)\\nAgents: \\(.agents_backed_up)\\nCommands: \\(.commands_backed_up)\\nSuperClaude Commands: \\(.superclaud_commands)\\nConfig Files: \\(.config_files_backed_up)"' "$MANIFEST_FILE"
    echo ""
fi

read -p "Continue with restoration? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Restoration cancelled."
    exit 0
fi

# Backup current state before restoration
CURRENT_BACKUP="$CLAUDE_CONFIG_DIR/backups/pre_restore_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$CURRENT_BACKUP"
if [[ -d "$CLAUDE_CONFIG_DIR/agents" ]]; then
    cp -r "$CLAUDE_CONFIG_DIR/agents" "$CURRENT_BACKUP/" 2>/dev/null || true
fi
if [[ -d "$CLAUDE_CONFIG_DIR/commands" ]]; then
    cp -r "$CLAUDE_CONFIG_DIR/commands" "$CURRENT_BACKUP/" 2>/dev/null || true
fi
log_success "Current configuration backed up to: $CURRENT_BACKUP"

# Restore agents
if [[ -d "$BACKUP_DIR/agents" ]]; then
    mkdir -p "$CLAUDE_CONFIG_DIR/agents"
    cp -r "$BACKUP_DIR/agents"/* "$CLAUDE_CONFIG_DIR/agents/" 2>/dev/null || true
    log_success "Agents restored"
fi

# Restore commands
if [[ -d "$BACKUP_DIR/commands" ]]; then
    mkdir -p "$CLAUDE_CONFIG_DIR/commands"
    cp -r "$BACKUP_DIR/commands"/* "$CLAUDE_CONFIG_DIR/commands/" 2>/dev/null || true
    log_success "Commands restored"
fi

# Restore config files
if [[ -d "$BACKUP_DIR/config" ]]; then
    cp -r "$BACKUP_DIR/config"/* "$CLAUDE_CONFIG_DIR/" 2>/dev/null || true
    log_success "Configuration files restored"
fi

echo ""
log_success "Configuration restoration completed successfully!"
echo "Current state backup available at: $CURRENT_BACKUP"
"""

        restore_script_path.write_text(restore_script_content, encoding="utf-8")
        restore_script_path.chmod(0o755)  # Make executable

        self.logger.info(f"Restoration script generated: {restore_script_path}")

    def implement_namespace_separation(self):
        """Implement namespace separation for framework coexistence."""
        self.logger.info(
            "Implementing namespace separation for framework coexistence..."
        )

        # Create namespace directory structure
        (self.claude_config_dir / "commands" / "sc").mkdir(parents=True, exist_ok=True)
        (self.claude_config_dir / "commands" / "cai").mkdir(parents=True, exist_ok=True)

        # Move SuperClaude commands to sc/ namespace if they exist
        commands_dir = self.claude_config_dir / "commands"
        if commands_dir.exists():
            for md_file in commands_dir.glob("*.md"):
                try:
                    content = md_file.read_text(encoding="utf-8")
                    if "sc:" in content:
                        target = (
                            self.claude_config_dir / "commands" / "sc" / md_file.name
                        )
                        shutil.move(str(md_file), str(target))
                        self.logger.info(
                            f"Moved SuperClaude command to namespace: sc/{md_file.name}"
                        )
                except Exception as e:
                    self.logger.warn(f"Failed to move {md_file.name}: {e}")

        self.logger.info("Namespace separation implemented")

    def execute_comprehensive_backup(self) -> bool:
        """Execute comprehensive backup system."""
        self.logger.info(
            "Starting comprehensive backup system for nWave installation..."
        )

        # Create backup structure
        if not self.create_backup_structure():
            return False

        # Scan existing configuration
        self.scan_existing_configuration()

        # Detect potential conflicts
        conflicts_found, _ = self.detect_framework_conflicts()
        if conflicts_found:
            self.logger.warn("Conflicts detected, but backup will continue...")

        # Backup existing configuration
        if not self.backup_existing_configuration():
            return False

        # Generate restoration script
        self.generate_restoration_script()

        # Implement namespace separation
        self.implement_namespace_separation()

        self.logger.info("Comprehensive backup completed successfully!")
        print()
        print("=== Backup Summary ===")
        print(f"Backup Location: {self.backup_dir}")
        print(f"Manifest File: {self.manifest_file}")
        print(
            f"Restoration Script: {self.backup_root_dir / 'restore_scripts' / f'restore_{self.timestamp}.sh'}"
        )
        print()
        print("Framework installation can now proceed safely.")
        print(f"Use 'bash restore_{self.timestamp}.sh' to restore if needed.")

        return True

    def list_backups(self):
        """List available backups."""
        print("Available backups:")
        if not self.backup_root_dir.exists():
            print("No backups found")
            return

        backups = sorted(self.backup_root_dir.glob("pre_nwave_*"))
        if not backups:
            print("No backups found")
        else:
            for backup in backups:
                print(f"  {backup.name}")

    def show_status(self):
        """Show backup system status."""
        print("Backup System Status:")
        print(f"Claude Config Directory: {self.claude_config_dir}")
        print(f"Backup Root Directory: {self.backup_root_dir}")
        print(f"Log File: {self.claude_config_dir / 'backup_system.log'}")
        print()

        if self.backup_root_dir.exists():
            backup_count = len(list(self.backup_root_dir.glob("pre_nwave_*")))
            print(f"Available backups: {backup_count}")
        else:
            print("No backup directory found")


def show_help():
    """Show help message."""
    help_text = f"""{_ANSI_BLUE}nWave Enhanced Backup System{_ANSI_NC}

{_ANSI_BLUE}USAGE:{_ANSI_NC}
    python enhanced_backup_system.py {{backup|restore|list|status}} [TIMESTAMP]

{_ANSI_BLUE}COMMANDS:{_ANSI_NC}
    backup          Create comprehensive backup before nWave installation
    restore TIMESTAMP  Restore from specific backup
    list           List available backups
    status         Show backup system status

{_ANSI_BLUE}EXAMPLES:{_ANSI_NC}
    python enhanced_backup_system.py backup                    # Create backup
    python enhanced_backup_system.py restore 20250914_143022   # Restore specific backup
    python enhanced_backup_system.py list                      # Show available backups
"""
    print(help_text)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Enhanced backup system for nWave framework", add_help=False
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=["backup", "restore", "list", "status"],
        help="Command to execute",
    )
    parser.add_argument("timestamp", nargs="?", help="Timestamp for restore command")
    parser.add_argument("--help", "-h", action="store_true", help="Show help")

    args = parser.parse_args()

    if args.help or not args.command:
        show_help()
        return 0 if args.help else 1

    backup_system = EnhancedBackupSystem()

    if args.command == "backup":
        return 0 if backup_system.execute_comprehensive_backup() else 1

    elif args.command == "restore":
        if not args.timestamp:
            backup_system.logger.error(
                "Please specify backup timestamp for restoration"
            )
            print(f"Usage: python {sys.argv[0]} restore TIMESTAMP")
            print("Available backups:")
            backup_system.list_backups()
            return 1

        restore_script = (
            backup_system.backup_root_dir
            / "restore_scripts"
            / f"restore_{args.timestamp}.sh"
        )
        if restore_script.exists():
            import subprocess

            result = subprocess.run(["bash", str(restore_script)])
            return result.returncode
        else:
            backup_system.logger.error(
                f"Restoration script not found: {restore_script}"
            )
            return 1

    elif args.command == "list":
        backup_system.list_backups()
        return 0

    elif args.command == "status":
        backup_system.show_status()
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
