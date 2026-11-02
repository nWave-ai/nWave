#!/usr/bin/env python3
"""
Installation Utilities for nWave Framework

Shared utilities for install/uninstall/update/backup scripts.
Cross-platform compatible (Windows, Mac, Linux).
"""

__version__ = "1.1.0"

import json
import os
import re
import shutil
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from scripts.shared.install_paths import agents_home, codex_config_dir


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
        # One-shot latch for the file-sink degrade (see `_write_to_file`): a
        # broken sink is broken for the whole run, so it is announced once
        # rather than once per line.
        self._log_sink_failure_reported = False

        # Disable colors on Windows if not in terminal
        self._use_colors = True
        if sys.platform == "win32" and not sys.stdout.isatty():
            self._use_colors = False

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

    def _write_to_file(self, level: str, message: str) -> None:
        """Write a structured log entry to the file sink.

        The parent directory is created HERE, at the write site, not in
        `__init__`: the constructor accepts `log_file=None` so logging can be
        deferred until after the ownership preflight, which means the directory
        cannot be prepared at construction time for a sink chosen later. That
        deferral is what commit d07aa112f introduced -- and it removed the
        constructor's mkdir without moving it here.

        A write failure degrades LOUDLY, exactly once. The bare `except: pass`
        this replaces made a missing log indistinguishable from an install that
        had nothing to say: the operator believed they had an install log and
        did not. Once, not per line -- a broken sink is broken for the whole
        run, and repeating the warning would bury the very output it accompanies.
        """
        if not self.log_file:
            return
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] {level}: {message}"
        try:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(log_msg + "\n")
        except Exception as exc:
            if not self._log_sink_failure_reported:
                self._log_sink_failure_reported = True
                print(
                    f"WARNING: the install log at {self.log_file} is NOT being "
                    f"written ({type(exc).__name__}: {exc}). "
                    "WHY: the sink could not be opened or created. "
                    "HOW: check that the directory is writable, then re-run to "
                    "capture a log. The installation continues either way, so "
                    "this run will simply leave no log file behind.",
                    file=sys.stderr,
                )

    def _log(self, level: str, message: str, color: str = "") -> None:
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
                    soft_wrap=True,
                )
            elif color and self._use_colors:
                print(f"{color}{message}{self._NC}")
            else:
                print(message)

        self._write_to_file(level, message)

    def info(self, message: str) -> None:
        """Log info message."""
        self._log("INFO", message)

    def warn(self, message: str) -> None:
        """Log warning message."""
        self._log("WARN", message, self._YELLOW)

    def warning(self, message: str) -> None:
        """Log warning message (stdlib logging.Logger-compatible name)."""
        self.warn(message)

    def error(self, message: str) -> None:
        """Log error message."""
        self._log("ERROR", message, self._RED)

    def step(self, message: str) -> None:
        """Log step message."""
        self._log("STEP", message, self._BLUE)

    @contextmanager
    def progress_spinner(
        self, message: str, spinner_style: str = "dots12"
    ) -> Iterator[None]:
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
    ) -> None:
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

    def panel(
        self, content: str, title: str | None = None, style: str = "blue"
    ) -> None:
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

    def print_styled(self, text: str, style: str = "") -> None:
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
    def get_opencode_config_dir() -> Path:
        """Get OpenCode config directory path.

        Honors the OPENCODE_CONFIG_DIR environment variable for test isolation
        and non-standard installations (analogous to CLAUDE_CONFIG_DIR for Claude).
        Defaults to the platform-standard ~/.config/opencode/.
        """
        config_dir = os.environ.get("OPENCODE_CONFIG_DIR")
        if config_dir:
            return Path(config_dir)
        return Path.home() / ".config" / "opencode"

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
        newest_time: float = 0

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
        skills_dir = self.claude_config_dir / "skills"

        if (
            not agents_dir.exists()
            and not commands_dir.exists()
            and not skills_dir.exists()
        ):
            self.logger.info("  ℹ️  No existing installation, skipping backup")
            return None

        self.logger.info("")
        self.logger.info(f"  💾 Backup at {self.backup_dir}")
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # Backup agents. ignore_dangling_symlinks: a prior uninstall could
        # leave orphan flat nw-*.md symlinks whose target was removed; copytree
        # follows symlinks by default and raises on broken ones, aborting the
        # whole install. Suppress the broken-symlink error so backup is robust.
        if agents_dir.exists():
            backup_agents = self.backup_dir / "agents"
            shutil.copytree(
                agents_dir,
                backup_agents,
                dirs_exist_ok=True,
                ignore_dangling_symlinks=True,
            )
            self.logger.info("  ✅ Agents backed up")

        # Backup commands
        if commands_dir.exists():
            backup_commands = self.backup_dir / "commands"
            shutil.copytree(
                commands_dir,
                backup_commands,
                dirs_exist_ok=True,
                ignore_dangling_symlinks=True,
            )
            self.logger.info("  ✅ Commands backed up")

        # Backup skills (includes any user-customized distributed SKILL.md)
        if skills_dir.exists():
            backup_skills = self.backup_dir / "skills"
            shutil.copytree(
                skills_dir,
                backup_skills,
                dirs_exist_ok=True,
                ignore_dangling_symlinks=True,
            )
            self.logger.info("  ✅ Skills backed up")

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

    def create_codex_backup(
        self,
        *,
        skills_dir: Path,
        agents_dir: Path,
        codex_dir: Path,
        dry_run: bool = False,
    ) -> Path | None:
        """Snapshot the complete Codex nWave control surface.

        Codex intentionally has no Claude discovery surface, so its normal
        installer backup lives in the nWave home rather than manufacturing a
        ``~/.claude`` directory.  This is still the one ``BackupManager``
        lifecycle: callers may put a migration quarantine *inside* the
        returned backup, never in a second recovery store.
        """
        if dry_run:
            self.logger.info(f"  🚨 [DRY RUN] Would backup Codex to {self.backup_dir}")
            return None

        tracked_files = (
            "hooks.json",
            ".nwave-des-manifest.json",
            "nwave_claude_code_hook_adapter_launcher.py",
        )
        if (
            not skills_dir.exists()
            and not agents_dir.exists()
            and not any((codex_dir / name).exists() for name in tracked_files)
        ):
            self.logger.info("  ℹ️  No existing Codex installation, skipping backup")
            return None

        self.logger.info("")
        self.logger.info(f"  💾 Codex backup at {self.backup_dir}")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        snapshot_root = self.backup_dir / "codex"
        if skills_dir.exists():
            shutil.copytree(skills_dir, snapshot_root / "skills", dirs_exist_ok=True)
        if agents_dir.exists():
            shutil.copytree(agents_dir, snapshot_root / "agents", dirs_exist_ok=True)
        config_dir = snapshot_root / "config"
        for name in tracked_files:
            source = codex_dir / name
            if source.is_file() and not source.is_symlink():
                config_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, config_dir / name)
        self._create_manifest()
        self.logger.info(f"  ✅ Codex backup complete → {self.backup_dir}")
        return self.backup_dir

    def _create_manifest(self) -> None:
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

    # ------------------------------------------------------------------
    # Retention policy (feature backup-retention-policy)
    # ------------------------------------------------------------------
    # See ``docs/feature/backup-retention-policy/discuss/scope.md`` for the
    # locked decisions D1-D5 that drive the semantics below.

    DEFAULT_MAX_BACKUP_COUNT = 10
    """Default cap when ~/.nwave/config.json:backups.max_count is unset (D4)."""

    BACKUP_GLOB = "nwave-*"
    """Pattern identifying nWave-managed backup directories.

    Pool semantics (D1): the same glob captures install / uninstall / update
    backups so they share a single retention pool.
    """

    def apply_retention(
        self,
        max_count: int | None = None,
        nwave_config_dir: Path | None = None,
    ) -> "RetentionResult":
        """Prune oldest nwave-* backup directories until count <= max_count.

        Pool semantics (D1): sums across types — ``nwave-install-*``,
        ``nwave-uninstall-*``, ``nwave-update-*`` share one pool.

        Sort semantics (D2): lex-sort on full backup dirname, no timestamp
        parsing (mirrors ``restore_backup`` in install_nwave.py).

        Foreign directories (anything not matching ``nwave-*``) are never
        touched.

        Args:
            max_count: Cap to enforce. If None, reads from global config or
                falls back to DEFAULT_MAX_BACKUP_COUNT.
            nwave_config_dir: Where to read ``config.json`` from when
                resolving the config-driven cap. Forwarded verbatim to
                ``read_backup_retention_config`` (None there defaults to
                ``Path.home() / ".nwave"``) -- an isolated caller (e.g. a K4
                harness campaign arm with NWAVE_AGENTS_HOME pinned) must pass
                its own pinned dir here, or this read-only config lookup
                still reaches the operator's real home even though nothing
                gets WRITTEN there. Byte-diff sentinel tests cannot see a
                read; this parameter is the fix, not a test technique.

        Returns:
            RetentionResult with the list of pruned directory names and the
            list of surviving backup directory names.

        Raises:
            ConfigValidationError: when the global config provides an invalid
                max_count (negative, non-integer, etc.) — see scenario S9.
        """
        cap = (
            max_count
            if max_count is not None
            else read_backup_retention_config(nwave_config_dir)
        )
        # Defensive: positional args bypass config validation. Validate again
        # so explicit max_count=-1 from a caller gets the same treatment as
        # config-driven invalid values.
        if not isinstance(cap, int) or isinstance(cap, bool) or cap < 0:
            raise ConfigValidationError(
                f"Invalid max_count {cap!r} — backups.max_count must be a "
                f"non-negative integer."
            )

        if not self.backup_root.exists():
            return RetentionResult(pruned=[], retained=[], cap_applied=cap)

        # D2: lex-sort on full dirname. Oldest = lex-smallest.
        existing = sorted(
            p for p in self.backup_root.glob(self.BACKUP_GLOB) if p.is_dir()
        )

        if len(existing) <= cap:
            return RetentionResult(
                pruned=[],
                retained=[p.name for p in existing],
                cap_applied=cap,
            )

        prune_count = len(existing) - cap
        to_prune = existing[:prune_count]
        survivors = existing[prune_count:]

        pruned_names: list[str] = []
        for victim in to_prune:
            shutil.rmtree(victim)
            pruned_names.append(victim.name)
            self.logger.info(f"  🗑  Pruned old backup {victim.name}")

        return RetentionResult(
            pruned=pruned_names,
            retained=[p.name for p in survivors],
            cap_applied=cap,
        )


class RetentionResult:
    """Outcome of a retention pass — what was pruned, what survives.

    Minimal observable shape for acceptance tests. ``pruned`` is the list of
    backup directory names that were removed (sorted oldest-first).
    ``retained`` is the list of backup directory names still on disk (sorted
    oldest-first). ``cap_applied`` is the integer cap that was enforced.
    """

    def __init__(
        self,
        pruned: list[str] | None = None,
        retained: list[str] | None = None,
        cap_applied: int | None = None,
    ):
        self.pruned = pruned or []
        self.retained = retained or []
        self.cap_applied = cap_applied


class ConfigValidationError(ValueError):
    """Raised when ~/.nwave/config.json:backups.max_count is invalid.

    Inherits from ValueError so existing handlers that catch ValueError
    continue to work; specialised callers can pattern-match on this subclass.
    """


def read_backup_retention_config(
    nwave_config_dir: Path | None = None,
) -> int:
    """Resolve ``backups.max_count`` from ~/.nwave/config.json.

    Pure helper (Mandate 4): the validation logic lives here, isolated from
    the I/O of pruning. Returns the validated cap, or
    ``BackupManager.DEFAULT_MAX_BACKUP_COUNT`` when no override exists.

    Args:
        nwave_config_dir: Override for the config directory. When None,
            defaults to ``Path.home() / ".nwave"``.

    Returns:
        Integer cap >= 0.

    Raises:
        ConfigValidationError: when max_count is present but not a
            non-negative integer.
    """
    import json

    config_dir = nwave_config_dir or (Path.home() / ".nwave")
    config_file = config_dir / "config.json"

    if not config_file.exists():
        return BackupManager.DEFAULT_MAX_BACKUP_COUNT

    try:
        config = json.loads(config_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        raise ConfigValidationError(
            f"Could not parse {config_file} — backups.max_count cannot be "
            f"resolved: {err}"
        ) from err

    backups_section = config.get("backups") if isinstance(config, dict) else None
    if not isinstance(backups_section, dict) or "max_count" not in backups_section:
        return BackupManager.DEFAULT_MAX_BACKUP_COUNT

    raw_value = backups_section["max_count"]
    # ``bool`` is a subclass of ``int`` — reject it explicitly so True/False
    # do not silently pass as 1/0.
    if isinstance(raw_value, bool) or not isinstance(raw_value, int):
        raise ConfigValidationError(
            f"backups.max_count must be a non-negative integer; got {raw_value!r}."
        )
    if raw_value < 0:
        raise ConfigValidationError(
            f"backups.max_count must be >= 0; got {raw_value!r}."
        )
    return raw_value


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
        claude_config_dir: Path,
        backup_dir: Path | None,
        script_dir: Path,
        *,
        target_platforms: frozenset[str] | set[str] | None = None,
    ) -> None:
        """Write the Claude-surface installation manifest.

        ``Installer.create_manifest`` always supplies the effective target set
        for a multi-host installation.  This legacy manifest remains scoped to
        Claude (native adapters own their manifests), but accepting that set
        keeps the writer's public contract aligned with its caller and lets an
        all-target installation complete without a late ``TypeError``.
        """
        manifest_path = claude_config_dir / "nwave-manifest.txt"
        targets = (
            frozenset(target_platforms)
            if target_platforms
            else frozenset({"claude_code"})
        )

        agents_count = PathUtils.count_files(claude_config_dir / "agents", "*.md")
        commands_count = PathUtils.count_files(claude_config_dir / "commands", "*.md")
        skills_count = PathUtils.count_files(claude_config_dir / "skills", "*.md")

        backup_info = (
            f"- Backup directory: {backup_dir}" if backup_dir else "- No backup created"
        )

        if targets == {"claude_code"}:
            content = f"""nWave Framework Installation Manifest
========================================
Installed: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Source: {script_dir}
Version: Production Ready

Installation Summary:
- Total agents: {agents_count}
- Total commands: {commands_count}
- Total skills: {skills_count}
- Installation directory: {claude_config_dir}
{backup_info}

Framework Components:
- 41+ specialized AI agents with Single Responsibility Principle
- Wave processing architecture with clean context isolation
- Essential DW commands: discuss, design, distill, deliver
- Quality validation network with Level 1-6 refactoring

Usage:
- Use nWave commands: '/nw-discuss', '/nw-design', '/nw-distill', '/nw-deliver'
- Use '/nw-deliver "request"' to start a delivery; 'des state --repo-root "$(pwd -P)"' resumes one
- All agents available globally across projects

For help: https://github.com/nWave-ai/nWave
"""
        else:
            target_summary = ManifestWriter._target_manifest_summary(
                targets, claude_config_dir
            )
            content = f"""nWave Framework Installation Manifest
========================================
Installed: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Source: {script_dir}
Version: Production Ready

Installation Summary:
- Target platforms: {", ".join(sorted(targets))}
{target_summary}
{backup_info}

Framework Components:
- Host-specific nWave adapters were installed only for the listed target platforms
- Shared nWave runtime components are available to those target adapters

Usage:
- Use the nWave interfaces provided by each listed target platform

For help: https://github.com/nWave-ai/nWave
"""

        manifest_path.write_text(content, encoding="utf-8")

    @staticmethod
    def _installed_count(manifest_path: Path, key: str) -> str:
        """Count what the host plugin WROTE, never what the directory holds.

        A disk count measures the disk (stale orphans included); the plugin
        manifest is the list this install actually produced.  A missing or
        malformed manifest is reported loudly, not as zero.
        """
        try:
            document = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return "unattested (no plugin manifest)"
        names = document.get(key) if isinstance(document, dict) else None
        if not isinstance(names, list):
            return "unattested (malformed plugin manifest)"
        return str(len(names))

    @staticmethod
    def _target_manifest_summary(targets: frozenset[str], claude_dir: Path) -> str:
        """Render target-labelled facts without treating Claude state as universal."""
        lines: list[str] = []
        if "claude_code" in targets:
            lines.extend(
                (
                    f"- Claude Code agents: {PathUtils.count_files(claude_dir / 'agents', '*.md')}",
                    f"- Claude Code commands: {PathUtils.count_files(claude_dir / 'commands', '*.md')}",
                    f"- Claude Code skills: {PathUtils.count_files(claude_dir / 'skills', '*.md')}",
                )
            )
        if "codex" in targets:
            install_root = agents_home()
            codex_home = codex_config_dir()
            lines.extend(
                (
                    "- Codex skills: "
                    + ManifestWriter._installed_count(
                        install_root / ".agents" / "skills" / ".nwave-manifest.json",
                        "installed_skills",
                    ),
                    "- Codex agents: "
                    + ManifestWriter._installed_count(
                        codex_home / "agents" / ".nwave-agents-manifest.json",
                        "installed_agents",
                    ),
                    f"- Codex DES hook: {'configured' if (codex_home / 'hooks.json').is_file() else 'missing'}",
                )
            )
        return "\n".join(lines)

    @staticmethod
    def write_uninstall_report(
        claude_config_dir: Path, backup_dir: Path | None
    ) -> None:
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
    ) -> None:
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
