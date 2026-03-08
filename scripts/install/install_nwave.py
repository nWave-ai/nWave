#!/usr/bin/env python3
"""
nWave Framework Installation Script

Cross-platform installer for the nWave methodology framework.
Installs specialized agents and commands to global Claude config directory.

Usage: python install_nwave.py [--backup-only] [--restore] [--dry-run] [--help]
"""

import argparse
import sys
from pathlib import Path


# Add project root to sys.path to enable imports from scripts package
# This allows the script to work when run directly or as a module
_script_dir = Path(__file__).parent
_project_root = _script_dir.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


# Support both standalone execution and package import
try:
    from scripts.install.context_detector import detect_target_platforms
    from scripts.install.install_utils import (
        BackupManager,
        Logger,
        ManifestWriter,
        PathUtils,
    )
    from scripts.install.installation_verifier import InstallationVerifier
    from scripts.install.output_formatter import format_error
    from scripts.install.plugins.agents_plugin import AgentsPlugin
    from scripts.install.plugins.base import InstallContext
    from scripts.install.plugins.commands_plugin import CommandsPlugin
    from scripts.install.plugins.des_plugin import DESPlugin
    from scripts.install.plugins.opencode_agents_plugin import OpenCodeAgentsPlugin
    from scripts.install.plugins.opencode_commands_plugin import OpenCodeCommandsPlugin
    from scripts.install.plugins.opencode_skills_plugin import OpenCodeSkillsPlugin
    from scripts.install.plugins.registry import PluginRegistry
    from scripts.install.plugins.skills_plugin import SkillsPlugin
    from scripts.install.plugins.templates_plugin import TemplatesPlugin
    from scripts.install.plugins.utilities_plugin import UtilitiesPlugin
    from scripts.install.preflight_checker import PreflightChecker
except ImportError:
    # Fallback for standalone execution from scripts/install directory
    from context_detector import detect_target_platforms
    from install_utils import (
        BackupManager,
        Logger,
        ManifestWriter,
        PathUtils,
    )
    from installation_verifier import InstallationVerifier
    from output_formatter import format_error
    from plugins.agents_plugin import AgentsPlugin
    from plugins.base import InstallContext
    from plugins.commands_plugin import CommandsPlugin
    from plugins.des_plugin import DESPlugin
    from plugins.opencode_agents_plugin import OpenCodeAgentsPlugin
    from plugins.opencode_commands_plugin import OpenCodeCommandsPlugin
    from plugins.opencode_skills_plugin import OpenCodeSkillsPlugin
    from plugins.registry import PluginRegistry
    from plugins.skills_plugin import SkillsPlugin
    from plugins.templates_plugin import TemplatesPlugin
    from plugins.utilities_plugin import UtilitiesPlugin
    from preflight_checker import PreflightChecker

# ANSI color codes for --help output (only consumer)
_ANSI_BLUE = "\033[0;34m"
_ANSI_NC = "\033[0m"  # No Color


def _get_version() -> str:
    """Read version from package metadata (installed) or pyproject.toml (dev)."""
    # 1. Try importlib.metadata first (works when installed via pip/pipx)
    from importlib.metadata import PackageNotFoundError, version

    try:
        return version("nwave-ai")
    except PackageNotFoundError:
        pass

    # 2. Fallback: read pyproject.toml (dev checkout layout)
    pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
    if not pyproject_path.exists():
        return "0.0.0"
    try:
        try:
            import tomllib
        except ModuleNotFoundError:
            import tomli as tomllib  # type: ignore[no-redef]
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
        return data.get("project", {}).get("version", "0.0.0")
    except ModuleNotFoundError:
        import re

        content = pyproject_path.read_text()
        m = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
        return m.group(1) if m else "0.0.0"


__version__ = _get_version()

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

    def __init__(
        self, dry_run: bool = False, platform_override: set[str] | None = None
    ):
        """Initialize installer.

        Args:
            dry_run: When True, show what would be done without making changes.
            platform_override: Override auto-detected platforms. None means auto-detect.
        """
        self.dry_run = dry_run
        self._platform_override = platform_override
        self.script_dir = Path(__file__).parent
        self.project_root = PathUtils.get_project_root(self.script_dir)
        self.claude_config_dir = PathUtils.get_claude_config_dir()
        # Source-first: use nWave/ when in dev repo, dist/ only for distribution
        source_dir = self.project_root / "nWave"
        dist_dir = self.project_root / "dist"
        if source_dir.exists():
            self.framework_source = source_dir
        elif (dist_dir / "MANIFEST.json").exists():
            self.framework_source = dist_dir
        else:
            self.framework_source = source_dir  # fall through for error reporting

        log_file = self.claude_config_dir / "nwave-install.log"
        self.logger = Logger(log_file if not dry_run else None)
        self.backup_manager = BackupManager(self.logger, "install")

    def create_backup(self) -> None:
        """Create backup of existing installation."""
        self.backup_manager.create_backup(dry_run=self.dry_run)

    def restore_backup(self) -> bool:
        """Restore from most recent backup."""
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
        # Claude Code plugins (always registered -- default platform)
        registry.register(AgentsPlugin())
        registry.register(CommandsPlugin())
        registry.register(TemplatesPlugin())
        registry.register(SkillsPlugin())
        registry.register(UtilitiesPlugin())
        registry.register(DESPlugin())
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
        return registry

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
        if self.dry_run:
            self.logger.info(
                f"  🚨 [DRY RUN] Would install nWave framework to: {self.claude_config_dir}"
            )
            self.logger.info(
                f"  🚨 [DRY RUN] Would create target directory: {self.claude_config_dir}"
            )

            # Show what would be installed from nWave/ source
            agents_dir = self.project_root / "nWave" / "agents"
            commands_dir = self.project_root / "nWave" / "tasks" / "nw"

            if agents_dir.exists():
                agent_count = PathUtils.count_files(agents_dir, "nw-*.md")
                self.logger.info(
                    f"  🚨 [DRY RUN] Would install {agent_count} agent files"
                )

            if commands_dir.exists():
                command_count = PathUtils.count_files(commands_dir, "*.md")
                self.logger.info(
                    f"  🚨 [DRY RUN] Would install {command_count} command files"
                )

            return True

        self.logger.info("")
        self.logger.info(f"  💿 Installing nWave → {self.claude_config_dir}")

        # Create target directories
        self.claude_config_dir.mkdir(parents=True, exist_ok=True)

        # Detect target platforms
        detected_platforms = {p.value for p in detect_target_platforms()}
        if self._platform_override is not None:
            detected_platforms = self._platform_override

        # Create plugin registry and install all components
        registry = self._create_plugin_registry(target_platforms=detected_platforms)

        # Create installation context with all required utilities
        context = InstallContext(
            claude_dir=self.claude_config_dir,
            scripts_dir=self.project_root / "scripts" / "install",
            templates_dir=self.framework_source / "templates",
            logger=self.logger,
            project_root=self.project_root,
            framework_source=self.framework_source,
            dry_run=self.dry_run,
            target_platforms=detected_platforms,
        )

        self.logger.info("  📑 Installing Context...")
        with self.logger.progress_spinner("  🚧 Work in progress..."):
            # Execute all plugins through registry
            results = registry.install_all(context)

        # Check if any plugin failed
        for plugin_name, result in results.items():
            if not result.success:
                self.logger.error(
                    f"  ❌ Plugin '{plugin_name}' failed: {result.message}"
                )
                return False

        return True

    def _validate_schema_template(self) -> bool:
        """Validate TDD cycle schema template has required fields."""
        schema_file = (
            self.claude_config_dir / "templates" / "step-tdd-cycle-schema.json"
        )

        if not schema_file.exists():
            self.logger.error("  ❌ Schema template not found")
            return False

        try:
            import json

            with open(schema_file) as f:
                schema = json.load(f)

            # Check for schema_version field
            if "schema_version" not in schema:
                self.logger.error("  ❌ Schema missing 'schema_version' field")
                return False

            schema_version = schema.get("schema_version")

            # Validate schema version and phase count
            valid_schemas = {
                "2.0": {"phases": 8, "description": "8-phase TDD optimization"},
                "3.0": {
                    "phases": 7,
                    "description": "7-phase TDD (L4-L6 moved to orchestrator)",
                },
                "4.0": {
                    "phases": 5,
                    "description": "5-phase TDD (REVIEW/REFACTOR moved to deliver)",
                },
            }

            if schema_version not in valid_schemas:
                self.logger.warn(
                    f"  ⚠️ Schema version {schema_version}, expected 2.0, 3.0, or 4.0"
                )
                return False

            # Check phase count matches schema version
            phase_exec_log = schema.get("tdd_cycle", {}).get("phase_execution_log", [])
            expected_phases = valid_schemas[schema_version]["phases"]

            if len(phase_exec_log) != expected_phases:
                self.logger.error(
                    f"  ❌ Schema has {len(phase_exec_log)} phases, expected {expected_phases} for v{schema_version}"
                )
                return False

            schema_desc = valid_schemas[schema_version]["description"]
            self.logger.info(
                f"    👍 TDD cycle schema: v{schema_version} with {expected_phases} phases ({schema_desc})"
            )
            return True

        except Exception as e:
            self.logger.error(f"  ❌ Schema validation failed: {e}")
            return False

    def validate_installation(self) -> bool:
        """Validate installation using shared InstallationVerifier.

        Uses the InstallationVerifier module for consistent verification logic
        between standalone verification and post-build verification.

        Returns:
            True if verification passed, False otherwise.
        """
        self.logger.info("")
        self.logger.info("  🔎 Validate Installation...")
        with self.logger.progress_spinner("  🚧 Work in progress..."):
            # Use shared InstallationVerifier for consistent verification
            verifier = InstallationVerifier(claude_config_dir=self.claude_config_dir)
            result = verifier.run_verification()

            # Validate schema template (additional check specific to installer)
            schema_valid = self._validate_schema_template()

        # Plugin verification via registry.verify_all()
        plugin_registry = self._create_plugin_registry(silent=True)
        plugin_context = InstallContext(
            claude_dir=self.claude_config_dir,
            scripts_dir=self.project_root / "scripts" / "install",
            templates_dir=self.framework_source / "templates",
            logger=self.logger,
            project_root=self.project_root,
            framework_source=self.framework_source,
        )
        plugin_results = plugin_registry.verify_all(plugin_context)
        plugin_failures = {
            name: r for name, r in plugin_results.items() if not r.success
        }

        # Verify components: compare source files vs installed target
        # Supports both dist/ layout (agents/nw/, commands/nw/) and
        # nWave/ source layout (agents/nw-*.md, tasks/nw/*.md)
        all_synced = True

        # Agents: dist/agents/nw/ or nWave/agents/
        dist_agents = self.framework_source / "agents" / "nw"
        if dist_agents.exists():
            agents_source = dist_agents
        else:
            agents_source = self.project_root / "nWave" / "agents"
        agents_target = self.claude_config_dir / "agents" / "nw"
        if agents_source.exists():
            agent_source_files = sorted(agents_source.glob("nw-*.md"))
            agent_matched = sum(
                1 for f in agent_source_files if (agents_target / f.name).exists()
            )
            agent_expected = len(agent_source_files)
            agent_ok = agent_matched == agent_expected and agent_expected > 0
            if not agent_ok:
                all_synced = False
            self.logger.info(
                f"    {'✅' if agent_ok else '❌'} Agents verified ({agent_matched}/{agent_expected})"
            )

        # Commands: dist/commands/nw/ or nWave/tasks/nw/
        dist_commands = self.framework_source / "commands" / "nw"
        if dist_commands.exists():
            commands_source = dist_commands
        else:
            commands_source = self.project_root / "nWave" / "tasks" / "nw"
        commands_target = self.claude_config_dir / "commands" / "nw"
        if commands_source.exists():
            cmd_source_files = sorted(commands_source.glob("*.md"))
            cmd_matched = sum(
                1 for f in cmd_source_files if (commands_target / f.name).exists()
            )
            cmd_expected = len(cmd_source_files)
            cmd_ok = cmd_matched == cmd_expected and cmd_expected > 0
            if not cmd_ok:
                all_synced = False
            self.logger.info(
                f"    {'✅' if cmd_ok else '❌'} Commands verified ({cmd_matched}/{cmd_expected})"
            )

        # Templates from framework_source/templates/
        templates_source = self.framework_source / "templates"
        templates_target = self.claude_config_dir / "templates"
        if templates_source.exists():
            tmpl_files = [f for f in templates_source.iterdir() if f.is_file()]
            tmpl_matched = sum(
                1 for f in tmpl_files if (templates_target / f.name).exists()
            )
            tmpl_expected = len(tmpl_files)
            tmpl_ok = tmpl_matched == tmpl_expected and tmpl_expected > 0
            if not tmpl_ok:
                all_synced = False
            self.logger.info(
                f"    {'✅' if tmpl_ok else '❌'} Templates verified ({tmpl_matched}/{tmpl_expected})"
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
        script_matched = sum(1 for s in script_files if (scripts_target / s).exists())
        script_expected = len(script_files)
        script_ok = script_matched == script_expected and script_expected > 0
        if not script_ok:
            all_synced = False
        self.logger.info(
            f"    {'✅' if script_ok else '❌'} Scripts verified ({script_matched}/{script_expected})"
        )

        self.logger.info(
            f"    {'✅' if result.manifest_exists else '❌'} Manifest created"
        )
        self.logger.info(f"    {'✅' if schema_valid else '❌'} Schema validated")

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
            result.success and schema_valid and all_synced and not plugin_failures
        )

        if overall_success:
            self.logger.info("  🍾 Deployment validated")
            return True
        else:
            error_count = len(result.missing_essential_files) + (
                0 if schema_valid else 1
            )
            if not result.manifest_exists:
                error_count += 1
            self.logger.error(f"  ❌ Validation failed ({error_count} errors)")
            return False

    def create_manifest(self) -> None:
        """Create installation manifest."""
        if self.dry_run:
            self.logger.info("  🚨 [DRY RUN] Would create installation manifest")
            return

        ManifestWriter.write_install_manifest(
            self.claude_config_dir, self.backup_manager.backup_dir, self.script_dir
        )

        self.logger.info(
            f"  📄 Installation manifest created: {self.claude_config_dir / 'nwave-manifest.txt'}"
        )


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
    out(f"{wrap(_LOGO_ART[-1])}  \U0001f30a \U0001f30a \U0001f30a  v{__version__}")
    out("")
    for tagline in _TAGLINES:
        out(tagline)


def show_title_panel(logger: Logger, dry_run: bool = False) -> None:
    """Display styled title panel when installer starts."""
    print_logo(logger)

    if dry_run:
        logger.print_styled(" 🚨 \\[DRY RUN]")

    logger.print_styled("")


def show_installation_summary(logger: Logger) -> None:
    """Display installation summary panel at end of successful install."""
    logger.info("")
    logger.info(f"  🎉 nWave v{__version__} installed and healthy!")
    logger.info("")
    logger.info("  📖 Quick start")
    commands = [
        ("/nw:discover", "Evidence-based product discovery"),
        ("/nw:discuss", "Requirements gathering and business analysis"),
        ("/nw:design", "Architecture design with visual representation"),
        ("/nw:distill", "Acceptance test creation and business validation"),
        ("/nw:develop", "Outside-In TDD implementation with refactoring"),
        ("/nw:deliver", "Production readiness validation"),
    ]
    for cmd, desc in commands:
        logger.info(f"    {cmd:<16} {desc}")
    logger.info("")
    logger.info(
        "  💡 Open Claude Code in any project directory and type a /nw: command."
    )
    logger.info("  📚 Docs: https://github.com/nWave-ai/nWave")


def show_help():
    """Show help message."""
    B, N = _ANSI_BLUE, _ANSI_NC

    print()
    for line in _LOGO_ART[:-1]:
        print(f"{B}{line}{N}")
    print(f"{B}{_LOGO_ART[-1]}{N}  \U0001f30a \U0001f30a \U0001f30a  v{__version__}")
    print()
    for tagline in _TAGLINES:
        print(tagline)

    help_text = f"""
{B}DESCRIPTION:{N}
    Installs the nWave methodology framework to your global Claude config directory.
    This makes all specialized agents and commands available across all projects.

{B}USAGE:{N}
    python install_nwave.py [OPTIONS]

{B}OPTIONS:{N}
    --backup-only     Create backup of existing nWave installation without installing
    --restore         Restore from the most recent backup
    --dry-run         Show what would be installed without making any changes
    --help            Show this help message

{B}EXAMPLES:{N}
    python install_nwave.py                    # Install nWave framework
    python install_nwave.py --dry-run          # Show what would be installed
    python install_nwave.py --backup-only      # Create backup only
    python install_nwave.py --restore          # Restore from latest backup

{B}WHAT GETS INSTALLED:{N}
    - nWave specialized agents (DISCOVER\u2192DISCUSS\u2192DESIGN\u2192DEVOP\u2192DISTILL\u2192DELIVER methodology)
    - nWave command interface for workflow orchestration
    - ATDD (Acceptance Test Driven Development) integration
    - Outside-In TDD with double-loop architecture
    - Quality validation network with continuous refactoring
    - 7-phase TDD enforcement with schema versioning

{B}INSTALLATION LOCATION:{N}
    ~/.claude/agents/nw/    # nWave agent specifications
    ~/.claude/commands/nw/  # nWave command integrations
    ~/.claude/templates/    # TDD cycle schema templates

For more information: https://github.com/nWave-ai/nWave
"""
    print(help_text)


def _resolve_platform_override(platform_flag: str) -> set[str] | None:
    """Resolve CLI --platform flag to a platform override set.

    Args:
        platform_flag: One of "auto", "claude-code", "opencode", "all".

    Returns:
        None for auto-detect, or a set of platform string values.
    """
    platform_map = {
        "auto": None,
        "claude-code": {"claude_code"},
        "opencode": {"opencode"},
        "all": {"claude_code", "opencode"},
    }
    return platform_map[platform_flag]


def main():
    """Main entry point."""
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
        choices=["auto", "claude-code", "opencode", "all"],
        default="auto",
        help="Target platform (default: auto-detect)",
    )

    args = parser.parse_args()

    if args.help:
        show_help()
        return 0

    # Resolve platform override from CLI flag
    platform_override = _resolve_platform_override(args.platform)

    installer = NWaveInstaller(
        dry_run=args.dry_run, platform_override=platform_override
    )

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
        installer.create_backup()
        installer.logger.info("  🍾 Backup completed successfully")
        return 0

    # Handle restore mode
    if args.restore:
        if installer.restore_backup():
            installer.logger.info("  🍾 Restoration completed successfully")
            return 0
        else:
            return 1

    # Normal installation
    installer.create_backup()

    if not installer.install_framework():
        return 1

    # Create manifest after installation but before validation
    # This prevents circular dependency where validation fails because
    # manifest doesn't exist yet
    installer.create_manifest()

    if installer.validate_installation():
        installer.logger.info("")
        show_installation_summary(installer.logger)

        return 0
    else:
        installer.logger.error("  ❌ Installation failed validation")
        installer.logger.warn("  ⚠️ Restore with: python install_nwave.py --restore")
        return 1


if __name__ == "__main__":
    sys.exit(main())
