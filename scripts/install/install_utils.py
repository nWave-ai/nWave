#!/usr/bin/env python3
"""
Installation Utilities for nWave Framework

Shared utilities for install/uninstall/update/backup scripts.
Cross-platform compatible (Windows, Mac, Linux).
"""

__version__ = "1.1.0"

import os
import re
import shutil
import sys
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path


class Logger:
    """Unified logger with pretty-print, spinner, table, and panel support.

    Single logger for all console and file output. Uses Rich when available
    for auto-highlighted output (paths in magenta, numbers in cyan), animated
    spinners, styled tables, and bordered panels. Falls back to plain text.
    """

    # ANSI fallback colors (used when Rich is not available)
    _YELLOW = "\033[1;33m"
    _RED = "\033[0;31m"
    _BLUE = "\033[0;34m"
    _NC = "\033[0m"  # No Color

    # Maps ANSI codes to Rich styles for the fallback→Rich bridge
    _ANSI_TO_RICH = {
        "\033[1;33m": "yellow",
        "\033[0;31m": "bold red",
        "\033[0;34m": "blue",
    }

    # Regex to strip Rich markup tags for file logging
    _MARKUP_RE = re.compile(r"\[/?[a-z][a-z0-9_ ]*\]")

    def __init__(self, log_file: Path | None = None, silent: bool = False):
        """Initialize logger with optional log file.

        Args:
            log_file: Path to log file. If None, only console logging is enabled.
            silent: If True, suppress console output (log to file only).
        """
        self.log_file = log_file
        self.silent = silent

        # Disable colors on Windows if not in terminal
        self._use_colors = True
        if sys.platform == "win32" and not sys.stdout.isatty():
            self._use_colors = False

        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)

        # Rich console for pretty-print (paths, numbers auto-highlighted)
        self._rich_console = None
        if not silent:
            try:
                from rich.console import Console
                from rich.theme import Theme

                theme = Theme(
                    {
                        "repr.path": "magenta",
                        "repr.number": "cyan",
                    }
                )
                self._rich_console = Console(theme=theme)
            except ImportError:
                pass

    @property
    def has_rich(self) -> bool:
        """Whether Rich console is available for markup."""
        return self._rich_console is not None

    def _write_to_file(self, level: str, message: str):
        """Write structured log entry to file."""
        if not self.log_file:
            return
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] {level}: {message}"
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(log_msg + "\n")
        except Exception:
            pass

    def _log(self, level: str, message: str, color: str = ""):
        """Internal logging method for info/warn/error/step."""
        # Console: pretty-print with Rich or ANSI fallback
        if not self.silent:
            if self._rich_console:
                style = self._ANSI_TO_RICH.get(color)
                self._rich_console.print(
                    message,
                    style=style,
                    markup=False,
                    highlight=not style,
                )
            elif color and self._use_colors:
                print(f"{color}{message}{self._NC}")
            else:
                print(message)

        self._write_to_file(level, message)

    def info(self, message: str):
        """Log info message."""
        self._log("INFO", message)

    def warn(self, message: str):
        """Log warning message."""
        self._log("WARN", message, self._YELLOW)

    def error(self, message: str):
        """Log error message."""
        self._log("ERROR", message, self._RED)

    def step(self, message: str):
        """Log step message."""
        self._log("STEP", message, self._BLUE)

    @contextmanager
    def progress_spinner(self, message: str, spinner_style: str = "dots12"):
        """Animated spinner during long operations. Falls back to plain step."""
        self._write_to_file("STEP", message)

        if self.silent or not self._rich_console:
            if not self.silent:
                print(message)
            yield
            return

        try:
            from rich.status import Status

            with Status(message, console=self._rich_console, spinner=spinner_style):
                yield
        except ImportError:
            print(message)
            yield

    def table(
        self, headers: list[str], rows: list[list[str]], title: str | None = None
    ):
        """Print a table. Rich table on screen, plain text in log file."""
        # File: plain text representation
        if title:
            self._write_to_file("INFO", title)
        for row in rows:
            self._write_to_file("INFO", "  " + " | ".join(str(c) for c in row))

        if self.silent:
            return

        if self._rich_console:
            try:
                from rich.table import Table

                t = Table(title=title)
                for h in headers:
                    t.add_column(h)
                for row in rows:
                    t.add_row(*row)
                self._rich_console.print(t)
                return
            except ImportError:
                pass

        # Plain text fallback
        if title:
            print(f"\n{title}")
            print("=" * len(title))
        header_line = " | ".join(headers)
        print(header_line)
        print("-" * len(header_line))
        for row in rows:
            print(" | ".join(str(c) for c in row))
        print()

    def panel(self, content: str, title: str | None = None, style: str = "blue"):
        """Print a bordered panel. Rich panel on screen, plain text in log file."""
        # File: plain text representation
        if title:
            self._write_to_file("INFO", f"--- {title} ---")
        for line in content.split("\n"):
            self._write_to_file("INFO", line)

        if self.silent:
            return

        if self._rich_console:
            try:
                from rich.panel import Panel

                self._rich_console.print(
                    Panel(content, title=title, border_style=style)
                )
                return
            except ImportError:
                pass

        # Plain text fallback
        width = max(len(line) for line in content.split("\n")) + 4
        if title:
            width = max(width, len(title) + 4)
        print("+" + "-" * (width - 2) + "+")
        if title:
            print(f"| {title.center(width - 4)} |")
            print("+" + "-" * (width - 2) + "+")
        for line in content.split("\n"):
            print(f"| {line.ljust(width - 4)} |")
        print("+" + "-" * (width - 2) + "+")

    def print_styled(self, text: str, style: str = ""):
        """Print with Rich markup/styling. Falls back to plain text."""
        # File: strip markup
        clean = self._MARKUP_RE.sub("", text)
        if clean.strip():
            self._write_to_file("INFO", clean)

        if self.silent:
            return

        if self._rich_console:
            self._rich_console.print(text, style=style or None)
        else:
            print(clean)


class PathUtils:
    """Cross-platform path utilities."""

    @staticmethod
    def get_claude_config_dir() -> Path:
        """Get Claude config directory path."""
        config_dir = os.environ.get("CLAUDE_CONFIG_DIR")
        if config_dir:
            return Path(config_dir)
        return Path.home() / ".claude"

    @staticmethod
    def get_project_root(script_path: Path) -> Path:
        """Get project root from script path."""
        # Assumes scripts are in scripts/ or scripts/install/
        if script_path.parent.name == "install":
            return script_path.parent.parent.parent
        return script_path.parent.parent

    @staticmethod
    def copy_tree_with_filter(
        src: Path, dst: Path, exclude_patterns: list[str] | None = None
    ) -> int:
        """
        Copy directory tree with optional exclusion patterns.

        Args:
            src: Source directory
            dst: Destination directory
            exclude_patterns: List of filename patterns to exclude (e.g., ["README.md"])

        Returns:
            Number of files copied
        """
        exclude_patterns = exclude_patterns or []
        copied_count = 0

        dst.mkdir(parents=True, exist_ok=True)

        for item in src.rglob("*"):
            if item.is_file():
                # Check exclusion patterns
                if any(pattern in item.name for pattern in exclude_patterns):
                    continue

                # Calculate relative path and create target
                rel_path = item.relative_to(src)
                target = dst / rel_path
                target.parent.mkdir(parents=True, exist_ok=True)

                shutil.copy2(item, target)
                copied_count += 1

        return copied_count

    @staticmethod
    def count_files(directory: Path, pattern: str = "*.md") -> int:
        """Count files matching pattern in directory."""
        if not directory.exists():
            return 0
        return len(list(directory.rglob(pattern)))

    @staticmethod
    def find_newest_file(
        directory: Path, patterns: list[str] | None = None
    ) -> Path | None:
        """Find newest file in directory matching patterns."""
        patterns = patterns or ["*.md", "*.py", "*.json"]
        newest = None
        newest_time = 0

        for pattern in patterns:
            for file in directory.rglob(pattern):
                if file.is_file():
                    mtime = file.stat().st_mtime
                    if mtime > newest_time:
                        newest_time = mtime
                        newest = file

        return newest


class BackupManager:
    """Manages backups for nWave framework."""

    def __init__(self, logger: Logger, backup_type: str = "install"):
        """
        Initialize backup manager.

        Args:
            logger: Logger instance
            backup_type: Type of backup (install, uninstall, update)
        """
        self.logger = logger
        self.backup_type = backup_type
        self.claude_config_dir = PathUtils.get_claude_config_dir()
        self.backup_root = self.claude_config_dir / "backups"
        self.timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.backup_dir = self.backup_root / f"nwave-{backup_type}-{self.timestamp}"

    def create_backup(self, dry_run: bool = False) -> Path | None:
        """
        Create backup of current nWave installation.

        Args:
            dry_run: If True, only simulate backup

        Returns:
            Path to backup directory or None if nothing to backup
        """
        if dry_run:
            self.logger.info(f"  🚨 [DRY RUN] Would backup to {self.backup_dir}")
            return None

        # Check if there's anything to backup
        agents_dir = self.claude_config_dir / "agents"
        commands_dir = self.claude_config_dir / "commands"

        if not agents_dir.exists() and not commands_dir.exists():
            self.logger.info("  ℹ️  No existing installation, skipping backup")
            return None

        self.logger.info("")
        self.logger.info(f"  💾 Backup at {self.backup_dir}")
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # Backup agents
        if agents_dir.exists():
            backup_agents = self.backup_dir / "agents"
            shutil.copytree(agents_dir, backup_agents)
            self.logger.info("  ✅ Agents backed up")

        # Backup commands
        if commands_dir.exists():
            backup_commands = self.backup_dir / "commands"
            shutil.copytree(commands_dir, backup_commands)
            self.logger.info("  ✅ Commands backed up")

        # Backup config files
        for config_file in ["nwave-manifest.txt", "nwave-install.log"]:
            src = self.claude_config_dir / config_file
            if src.exists():
                shutil.copy2(src, self.backup_dir / config_file)
                self.logger.info(f"  ✅ {config_file} backed up")

        # Create manifest
        self._create_manifest()

        self.logger.info(f"  ✅ Backup complete → {self.backup_dir}")
        return self.backup_dir

    def _create_manifest(self):
        """Create backup manifest file."""
        manifest_path = self.backup_dir / "backup-manifest.txt"

        files_count = sum(1 for _ in self.backup_dir.rglob("*.md"))

        content = f"""nWave Framework Backup
Created: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Source: {self.claude_config_dir}
Backup Type: {self.backup_type}
Backup contents: {files_count} framework files
"""

        manifest_path.write_text(content, encoding="utf-8")


class VersionUtils:
    """Version comparison utilities."""

    @staticmethod
    def parse_version(version_str: str) -> tuple[int, ...]:
        """Parse semver string to tuple of integers."""
        try:
            return tuple(int(x) for x in version_str.split("."))
        except (ValueError, AttributeError):
            return (0, 0, 0)

    @staticmethod
    def compare_versions(version1: str, version2: str) -> int:
        """
        Compare two semantic versions.

        Returns:
            1 if version1 > version2
            0 if version1 == version2
            -1 if version1 < version2
        """
        v1 = VersionUtils.parse_version(version1)
        v2 = VersionUtils.parse_version(version2)

        if v1 > v2:
            return 1
        elif v1 < v2:
            return -1
        else:
            return 0

    @staticmethod
    def extract_version_from_file(file_path: Path) -> str:
        """Extract __version__ from Python file."""
        try:
            content = file_path.read_text(encoding="utf-8")
            for line in content.splitlines():
                if "__version__" in line:
                    # Extract version from '__version__ = "x.y.z"'
                    parts = line.split("=")
                    if len(parts) == 2:
                        version = parts[1].strip().strip('"').strip("'")
                        return version
        except Exception:
            pass
        return "0.0.0"


class ManifestWriter:
    """Writes installation/uninstallation manifests."""

    @staticmethod
    def write_install_manifest(
        claude_config_dir: Path, backup_dir: Path | None, script_dir: Path
    ):
        """Write installation manifest."""
        manifest_path = claude_config_dir / "nwave-manifest.txt"

        agents_count = PathUtils.count_files(claude_config_dir / "agents", "*.md")
        commands_count = PathUtils.count_files(claude_config_dir / "commands", "*.md")

        backup_info = (
            f"- Backup directory: {backup_dir}" if backup_dir else "- No backup created"
        )

        content = f"""nWave Framework Installation Manifest
========================================
Installed: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Source: {script_dir}
Version: Production Ready

Installation Summary:
- Total agents: {agents_count}
- Total commands: {commands_count}
- Installation directory: {claude_config_dir}
{backup_info}

Framework Components:
- 41+ specialized AI agents with Single Responsibility Principle
- Wave processing architecture with clean context isolation
- Essential DW commands: discuss, design, distill, develop, deliver
- Quality validation network with Level 1-6 refactoring

Usage:
- Use nWave commands: '/nw:discuss', '/nw:design', '/nw:distill', '/nw:develop', '/nw:deliver'
- Use '/nw:start "feature description"' to initialize nWave workflow
- All agents available globally across projects

For help: https://github.com/nWave-ai/nWave
"""

        manifest_path.write_text(content, encoding="utf-8")

    @staticmethod
    def write_uninstall_report(claude_config_dir: Path, backup_dir: Path | None):
        """Write uninstallation report."""
        report_path = claude_config_dir / "framework-uninstall-report.txt"

        backup_info = (
            f"""Backup Information:
- Backup created: {backup_dir}
- Backup contains: Complete framework state before removal

"""
            if backup_dir
            else ""
        )

        content = f"""Framework Uninstallation Report
===============================
Uninstalled: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Computer: {os.uname().nodename if hasattr(os, "uname") else "unknown"}
User: {os.environ.get("USER", os.environ.get("USERNAME", "unknown"))}

Uninstall Summary:
- nWave agents removed from: {claude_config_dir}/agents/nw/
- nWave commands removed from: {claude_config_dir}/commands/nw/
- Configuration files removed
- Installation logs removed
- Backup directories cleaned

{backup_info}Uninstallation completed successfully.
"""

        report_path.write_text(content, encoding="utf-8")

    @staticmethod
    def write_update_report(
        claude_config_dir: Path, backup_dir: Path | None, backup_created: bool
    ):
        """Write update report."""
        report_path = claude_config_dir / "nwave-update-report.txt"

        agents_count = PathUtils.count_files(claude_config_dir / "agents/nw", "*.md")
        commands_count = PathUtils.count_files(
            claude_config_dir / "commands/nw", "*.md"
        )

        backup_step = (
            "3. ✅ Comprehensive backup creation"
            if backup_created
            else "3. ⏭️  Backup skipped"
        )

        backup_info = (
            f"""Backup Information:
- Backup created: {backup_dir}
- Backup contains: Complete pre-update framework state
- Restoration: See backup manifest for recovery commands

"""
            if backup_created
            else ""
        )

        content = f"""nWave Framework Update Report
===============================
Update Completed: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Computer: {os.uname().nodename if hasattr(os, "uname") else "unknown"}
User: {os.environ.get("USER", os.environ.get("USERNAME", "unknown"))}
Update Method: Automated orchestrated update

Update Process Summary:
1. ✅ Prerequisites validation
2. ✅ Current installation assessment
{backup_step}
4. ✅ Framework bundle build
5. ✅ Previous installation uninstall
6. ✅ New framework installation
7. ✅ Update validation

{backup_info}Final Installation Status:
- Agents: {agents_count} installed
- Commands: {commands_count} installed

Update completed successfully. Framework ready for use.
"""

        report_path.write_text(content, encoding="utf-8")


def confirm_action(prompt: str, force: bool = False) -> bool:
    """
    Prompt user for confirmation.

    Args:
        prompt: Confirmation prompt
        force: If True, skip confirmation

    Returns:
        True if confirmed, False otherwise
    """
    if force:
        return True

    try:
        response = input(f"{prompt} (y/N): ").strip().lower()
        return response in ("y", "yes")
    except (KeyboardInterrupt, EOFError):
        print("\n  ⚠️ Cancelled by user")
        return False
