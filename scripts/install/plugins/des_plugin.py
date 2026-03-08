"""DES (Deterministic Execution System) installation plugin."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

from scripts.shared import hook_definitions as shared_hooks

from .base import InstallationPlugin, InstallContext, PluginResult


class DESPlugin(InstallationPlugin):
    """Plugin for installing DES (Deterministic Execution System).

    Demonstrates extensibility: adding DES requires only plugin registration
    without modifying core installer logic.

    Includes hooks installation that properly preserves all existing settings
    in settings.json (global config: permissions, other hooks, etc.).
    """

    # DES scripts installed to ~/.claude/scripts/
    DES_SCRIPTS = [
        "check_stale_phases.py",
        "scope_boundary_check.py",
    ]

    # DES templates installed to ~/.claude/templates/
    DES_TEMPLATES = [
        ".pre-commit-config-nwave.yaml",
        ".des-audit-README.md",
        "roadmap-schema.json",
    ]

    # Hook command template - substituted at install time:
    #   {lib_path}    → $HOME/.claude/lib/python (shell-expanded per machine)
    #   {python_path} → python3 (system PATH) for portability across machines
    #   {action}      → hook action (pre-task, subagent-stop, post-tool-use)
    # Uses $HOME for portability: settings.json is shared across machines
    # via ~/.claude synced directory, so paths must resolve per-machine.
    HOOK_COMMAND_TEMPLATE = (
        "PYTHONPATH={lib_path} {python_path} -m "
        "des.adapters.drivers.hooks.claude_code_hook_adapter {action}"
    )

    # Hook event types that DES registers (from shared definitions)
    HOOK_EVENTS = tuple(shared_hooks.HOOK_EVENT_TYPES)

    def __init__(self):
        """Initialize DES plugin with name, priority, and dependencies."""
        super().__init__(name="des", priority=50)
        self.dependencies = ["templates", "utilities"]
        self._original_settings: dict | None = None  # For uninstall restoration

    def validate_prerequisites(self, context: InstallContext) -> PluginResult:
        """Validate that DES prerequisites exist before installation.

        Checks for:
        1. DES scripts directory at nWave/scripts/des/
        2. DES templates at nWave/templates/

        Returns:
            PluginResult with success=False and clear error message if missing.
        """
        errors = []

        # Check for DES scripts directory
        scripts_dir = self._get_scripts_source_dir(context)
        if not scripts_dir.exists():
            errors.append(
                "DES scripts not found: nWave/scripts/des/. "
                "Ensure prerequisite scripts are created before DES installation."
            )
        else:
            # Check for required script files
            missing_scripts = []
            for script_name in self.DES_SCRIPTS:
                script_path = scripts_dir / script_name
                if not script_path.exists():
                    missing_scripts.append(script_name)
            if missing_scripts:
                errors.append(
                    f"Missing DES scripts: {', '.join(missing_scripts)}. "
                    f"Required scripts: {', '.join(self.DES_SCRIPTS)}"
                )

        # Check for DES templates (use framework_source for dist/ or nWave/)
        templates_dir = (
            context.framework_source / "templates"
            if context.framework_source
            else context.project_root / "nWave" / "templates"
            if context.project_root
            else Path("nWave/templates")
        )
        missing_templates = []
        for template_name in self.DES_TEMPLATES:
            template_path = templates_dir / template_name
            if not template_path.exists():
                missing_templates.append(template_name)

        if missing_templates:
            errors.append(
                f"DES templates not found: {', '.join(missing_templates)}. "
                f"Ensure prerequisite templates exist at nWave/templates/ before DES installation."
            )

        if errors:
            return PluginResult(
                success=False,
                plugin_name="des",
                message=f"DES prerequisite validation failed: {errors[0]}",
                errors=errors,
            )

        return PluginResult(
            success=True,
            plugin_name="des",
            message="DES prerequisites validated successfully",
        )

    def _get_scripts_source_dir(self, context: InstallContext) -> Path:
        """Get the source directory for DES scripts."""
        if context.framework_source:
            source_dir = context.framework_source / "scripts" / "des"
            if source_dir.exists():
                return source_dir
        if context.project_root:
            return context.project_root / "nWave" / "scripts" / "des"
        return Path("nWave/scripts/des")

    def install(self, context: InstallContext) -> PluginResult:
        """Install DES module, scripts, and templates.

        Validates prerequisites before installation to ensure graceful failure
        with clear error messages when required files are missing.
        """
        try:
            # Validate prerequisites first - fail fast with clear message
            prereq_result = self.validate_prerequisites(context)
            if not prereq_result.success:
                context.logger.error(
                    f"  ❌ DES prerequisite check failed: {prereq_result.message}"
                )
                return prereq_result

            # Install DES module
            module_result = self._install_des_module(context)
            if not module_result.success:
                return module_result

            # Install DES scripts
            scripts_result = self._install_des_scripts(context)
            if not scripts_result.success:
                return scripts_result

            # Install DES templates
            templates_result = self._install_des_templates(context)
            if not templates_result.success:
                return templates_result

            # Install DES hooks into settings.local.json
            hooks_result = self._install_des_hooks(context)
            if not hooks_result.success:
                return hooks_result

            # Bootstrap project-level DES config
            config_result = self._bootstrap_des_config(context)
            if not config_result.success:
                return config_result

            return PluginResult(
                success=True,
                plugin_name="des",
                message="DES installed successfully (module, scripts, templates, hooks, config)",
            )

        except Exception as e:
            return PluginResult(
                success=False,
                plugin_name="des",
                message=f"DES installation failed: {e}",
            )

    def _install_des_module(self, context: InstallContext) -> PluginResult:
        """Install DES Python module to ~/.claude/lib/python/des/."""
        try:
            # Check dist/ pre-built DES module first (imports already rewritten)
            pre_built = context.framework_source / "lib" / "python" / "des"
            using_prebuilt = pre_built.exists() and (pre_built / "__init__.py").exists()

            if using_prebuilt:
                source_dir = pre_built
            elif context.project_root:
                source_dir = context.project_root / "src" / "des"
            else:
                source_dir = Path("src/des")

            if not source_dir.exists():
                return PluginResult(
                    success=False,
                    plugin_name="des",
                    message=f"DES source not found: {source_dir}",
                )

            lib_python_dir = context.claude_dir / "lib" / "python"
            target_dir = lib_python_dir / "des"

            lib_python_dir.mkdir(parents=True, exist_ok=True)

            # Backup existing if present
            if context.backup_manager and target_dir.exists():
                context.logger.info(f"  💾 Backing up DES module: {target_dir}")
                context.backup_manager.backup_directory(target_dir)

            # Copy module
            if context.dry_run:
                context.logger.info(
                    f"  🚨 [DRY RUN] Would copy {source_dir} → {target_dir}"
                )
            else:
                if target_dir.exists():
                    shutil.rmtree(target_dir)
                shutil.copytree(source_dir, target_dir)

                # Skip rewriting if pre-built from dist/ (already done by build_dist.py)
                if not using_prebuilt:
                    self._rewrite_import_paths(target_dir, context)

                # Clear bytecode cache to prevent stale .pyc files
                self._clear_bytecode_cache(target_dir, context)

            return PluginResult(
                success=True,
                plugin_name="des",
                message=f"DES module copied to {target_dir}",
            )

        except Exception as e:
            return PluginResult(
                success=False,
                plugin_name="des",
                message=f"DES module install failed: {e}",
            )

    def _rewrite_import_paths(self, target_dir: Path, context: InstallContext) -> None:
        """Rewrite import paths in installed DES module.

        Transforms:
        - "from src.des." -> "from des."
        - "import src.des." -> "import des."
        - "src.des." in any context -> "des."

        This ensures the installed package works without PYTHONPATH pointing
        to the development source directory.
        """
        import re

        # Pattern to match import statements
        from_pattern = re.compile(r"\bfrom\s+src\.des\b")
        import_pattern = re.compile(r"\bimport\s+src\.des\b")
        # Pattern to match src.des. in any context (strings, comments, etc.)
        general_pattern = re.compile(r"\bsrc\.des\.")

        files_modified = 0
        files_skipped = 0
        for py_file in target_dir.rglob("*.py"):
            try:
                # Security: Skip symbolic links to prevent path traversal attacks
                if py_file.is_symlink():
                    context.logger.warn(f"  ⚠️ Skipping symlink (security): {py_file}")
                    files_skipped += 1
                    continue

                # Security: Verify path is within target_dir (defense in depth)
                try:
                    py_file.resolve().relative_to(target_dir.resolve())
                except ValueError:
                    context.logger.warn(f"  ⚠️ Skipping file outside target: {py_file}")
                    files_skipped += 1
                    continue

                # Security: Skip files larger than 10MB to prevent DoS
                file_size = py_file.stat().st_size
                if file_size > 10_000_000:  # 10MB limit
                    context.logger.warn(
                        f"  ⚠️ Skipping large file: {py_file} ({file_size} bytes)"
                    )
                    files_skipped += 1
                    continue

                # Read file content
                with open(py_file, encoding="utf-8") as f:
                    content = f.read()

                # Track if file was modified
                original_content = content

                # Rewrite import statements
                content = from_pattern.sub("from des", content)
                content = import_pattern.sub("import des", content)
                # Rewrite any remaining src.des. references (strings, comments, etc.)
                content = general_pattern.sub("des.", content)

                # Write back if modified
                if content != original_content:
                    with open(py_file, "w", encoding="utf-8") as f:
                        f.write(content)
                    files_modified += 1

            except Exception as e:
                context.logger.warn(f"  ⚠️ Failed to rewrite imports in {py_file}: {e}")

        if files_modified > 0:
            context.logger.info(f"  🔄 Rewrote import paths in {files_modified} files")
        if files_skipped > 0:
            context.logger.info(f"  ⚠️ Skipped {files_skipped} files for security")

    def _clear_bytecode_cache(self, target_dir: Path, context: InstallContext) -> None:
        """Clear __pycache__ directories from installed DES module.

        After copying and rewriting imports, stale .pyc files from previous
        installs can cause import errors or use outdated code. Removing all
        __pycache__ directories forces Python to recompile from source.
        """
        cleared = 0
        for cache_dir in target_dir.rglob("__pycache__"):
            if cache_dir.is_dir():
                shutil.rmtree(cache_dir)
                cleared += 1
        if cleared > 0:
            context.logger.info(
                f"  🧹 Cleared {cleared} __pycache__ directories from {target_dir}"
            )

    def _install_des_scripts(self, context: InstallContext) -> PluginResult:
        """Install DES utility scripts."""
        try:
            # Use framework source if available, fallback to nWave/scripts/des
            if context.framework_source:
                source_dir = context.framework_source / "scripts" / "des"
                if not source_dir.exists():
                    # Fallback to nWave/scripts/des if framework source doesn't have DES scripts
                    source_dir = context.project_root / "nWave" / "scripts" / "des"
            else:
                source_dir = Path("nWave/scripts/des")

            target_dir = context.claude_dir / "scripts"
            target_dir.mkdir(parents=True, exist_ok=True)

            installed = []
            for script_name in self.DES_SCRIPTS:
                source = source_dir / script_name
                target = target_dir / script_name

                if source.exists():
                    if not context.dry_run:
                        shutil.copy2(source, target)
                        target.chmod(0o755)
                    installed.append(script_name)

            return PluginResult(
                success=True,
                plugin_name="des",
                message=f"Installed {len(installed)} DES scripts",
            )

        except Exception as e:
            return PluginResult(
                success=False,
                plugin_name="des",
                message=f"DES scripts install failed: {e}",
            )

    def _install_des_templates(self, context: InstallContext) -> PluginResult:
        """Install DES templates."""
        try:
            # Use framework_source for dist/ or nWave/ layout
            source_dir = context.framework_source / "templates"
            target_dir = context.claude_dir / "templates"
            target_dir.mkdir(parents=True, exist_ok=True)

            installed = []
            for template_name in self.DES_TEMPLATES:
                source = source_dir / template_name
                target = target_dir / template_name

                if source.exists():
                    if not context.dry_run:
                        shutil.copy2(source, target)
                    installed.append(template_name)

            return PluginResult(
                success=True,
                plugin_name="des",
                message=f"Installed {len(installed)} DES templates",
            )

        except Exception as e:
            return PluginResult(
                success=False,
                plugin_name="des",
                message=f"DES templates install failed: {e}",
            )

    @staticmethod
    def _resolve_python_path() -> str:
        """Resolve the Python interpreter path for hook commands.

        Captures sys.executable (the installer's Python, which has all
        dependencies like PyYAML and pydantic) and makes it portable by
        replacing the home directory prefix with $HOME.

        If the current Python is a project-local .venv (e.g. during
        development), falls back to 'python3' to avoid embedding a
        machine-specific project path in settings.json.

        This ensures hooks run under the same Python that was used to
        install nWave — whether that's a pipx venv, pip venv, or system
        Python — so all dependencies are available at runtime.
        """
        python_path = sys.executable

        # Project-local .venv must not leak into settings.json
        if "/.venv/" in python_path or "\\.venv\\" in python_path:
            return "python3"

        home = str(Path.home())
        if python_path.startswith(home):
            python_path = "$HOME" + python_path[len(home) :]
        return python_path

    def _generate_hook_command(self, context: InstallContext, action: str) -> str:
        """Generate hook command with portable paths for cross-machine use.

        Uses $HOME shell variable instead of absolute paths so that
        settings.json works when synced across machines (via ~/.claude).
        Uses the installer's Python (with $HOME substitution) to ensure
        dependencies like PyYAML are available at hook runtime.

        Args:
            context: InstallContext with claude_dir
            action: Hook action (pre-task, subagent-stop, post-tool-use)

        Returns:
            Complete command string with $HOME-based paths
        """
        lib_path = "$HOME/.claude/lib/python"
        python_path = self._resolve_python_path()
        return self.HOOK_COMMAND_TEMPLATE.format(
            lib_path=lib_path,
            python_path=python_path,
            action=action,
        )

    def _install_des_hooks(self, context: InstallContext) -> PluginResult:
        """Install DES hooks into settings.json (global config).

        CRITICAL: Preserves ALL existing settings (permissions, other hooks, etc.).
        Only modifies the hooks.PreToolUse and hooks.SubagentStop arrays.

        Hook commands use PYTHONPATH to point to installed location:
        ~/.claude/lib/python/des/

        Replaces any old-format DES hooks with new format to prevent duplicates.
        Always removes and re-adds DES hooks to ensure latest format is used.
        """
        try:
            settings_file = context.claude_dir / "settings.json"

            # Load existing config (preserve everything)
            config = self._load_settings(settings_file)

            # Store original for uninstall restoration
            self._original_settings = json.loads(json.dumps(config))

            # Ensure hooks structure exists WITHOUT overwriting other keys
            if "hooks" not in config:
                config["hooks"] = {}
            for event in self.HOOK_EVENTS:
                if event not in config["hooks"]:
                    config["hooks"][event] = []

            # Generate the desired hook config using shared definitions
            def _installer_command(action: str) -> str:
                return self._generate_hook_command(context, action)

            def _installer_guard_command(action: str) -> str:
                python_cmd = self._generate_hook_command(context, action)
                return shared_hooks.build_guard_command(python_cmd)

            desired_hooks = shared_hooks.generate_hook_config(
                _installer_command, guard_command_fn=_installer_guard_command
            )

            # Check if hooks already exist with correct format
            def _has_command(hooks_list, command):
                return any(
                    any(h2.get("command") == command for h2 in h.get("hooks", []))
                    for h in hooks_list
                )

            def _has_matcher(hooks_list, matcher):
                return any(h.get("matcher") == matcher for h in hooks_list)

            all_up_to_date = True
            for event, desired_entries in desired_hooks.items():
                existing = config["hooks"].get(event, [])
                for entry in desired_entries:
                    cmd = entry["hooks"][0]["command"]
                    if not _has_command(existing, cmd):
                        all_up_to_date = False
                        break
                    matcher = entry.get("matcher")
                    if matcher and not _has_matcher(existing, matcher):
                        all_up_to_date = False
                        break
                if not all_up_to_date:
                    break

            if all_up_to_date:
                context.logger.info("  ✅ DES hooks up-to-date")
                return PluginResult(
                    success=True,
                    plugin_name="des",
                    message="DES hooks already installed",
                )

            # Remove any existing DES hooks (both old flat and new nested format)
            for event in self.HOOK_EVENTS:
                if event in config["hooks"]:
                    config["hooks"][event] = [
                        h
                        for h in config["hooks"][event]
                        if not shared_hooks.is_des_hook_entry(h)
                    ]

            # Add all DES hooks from shared definitions
            for event, entries in desired_hooks.items():
                for entry in entries:
                    config["hooks"][event].append(entry)

            if not context.dry_run:
                self._save_settings(settings_file, config, context)

            return PluginResult(
                success=True,
                plugin_name="des",
                message="DES hooks installed (preserving existing settings)",
            )

        except Exception as e:
            return PluginResult(
                success=False,
                plugin_name="des",
                message=f"DES hooks install failed: {e}",
            )

    _DEFAULT_UPDATE_CHECK_CONFIG = {
        "frequency": "daily",
        "skipped_versions": [],
    }

    _DEFAULT_DES_CONFIG = {
        "audit_logging_enabled": True,
        "audit_log_dir": ".nwave/des/logs",
    }

    def _write_json_config(self, path: Path, data: dict) -> None:
        """Write dict as pretty-printed JSON with trailing newline."""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")

    def _read_json_config(self, path: Path) -> dict:
        """Read JSON config file, returning empty dict on parse or IO error."""
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    def _migrate_config(
        self, config_file: Path, context: InstallContext
    ) -> PluginResult:
        """Add update_check to existing config that lacks it (migration path)."""
        existing = self._read_json_config(config_file)

        if "update_check" in existing:
            context.logger.info("  ✅ DES config already exists")
            return PluginResult(
                success=True,
                plugin_name="des",
                message="DES config already exists",
            )

        existing["update_check"] = self._DEFAULT_UPDATE_CHECK_CONFIG
        if not context.dry_run:
            self._write_json_config(config_file, existing)
            context.logger.info(
                f"  ✅ DES config migrated (update_check added): {config_file}"
            )
        return PluginResult(
            success=True,
            plugin_name="des",
            message=f"DES config migrated (update_check added) at {config_file}",
        )

    def _create_config(
        self, config_file: Path, nwave_dir: Path, context: InstallContext
    ) -> PluginResult:
        """Create des-config.json with default settings."""
        default_config = {
            **self._DEFAULT_DES_CONFIG,
            "update_check": self._DEFAULT_UPDATE_CHECK_CONFIG,
        }
        if context.dry_run:
            context.logger.info(f"  🚨 [DRY RUN] Would create {config_file}")
        else:
            nwave_dir.mkdir(parents=True, exist_ok=True)
            self._write_json_config(config_file, default_config)
            context.logger.info(f"  ✅ DES config created: {config_file}")
        return PluginResult(
            success=True,
            plugin_name="des",
            message=f"DES config bootstrapped at {config_file}",
        )

    def _bootstrap_des_config(self, context: InstallContext) -> PluginResult:
        """Bootstrap .nwave/des-config.json with default settings.

        Creates the config file if it doesn't exist. If it already exists
        and lacks the update_check key, adds it without overwriting any other
        keys (migration path). If update_check already present, no changes made.

        The config lives in the project directory (.nwave/), not ~/.claude,
        because audit log paths are project-relative.
        """
        try:
            project_root = context.project_root or Path.cwd()
            nwave_dir = project_root / ".nwave"
            config_file = nwave_dir / "des-config.json"

            if config_file.exists():
                return self._migrate_config(config_file, context)

            return self._create_config(config_file, nwave_dir, context)

        except Exception as e:
            return PluginResult(
                success=False,
                plugin_name="des",
                message=f"DES config bootstrap failed: {e}",
            )

    def _load_settings(self, settings_file: Path) -> dict:
        """Load settings from JSON file, return empty dict if not exists."""
        if not settings_file.exists():
            return {}

        try:
            with open(settings_file, encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {settings_file}: {e}")

    def _save_settings(
        self, settings_file: Path, config: dict, context: InstallContext
    ) -> None:
        """Save settings to JSON file with proper formatting and file locking.

        Uses exclusive file locking to prevent race conditions during concurrent
        modifications (defense in depth).
        """
        # Ensure directory exists
        settings_file.parent.mkdir(parents=True, exist_ok=True)

        # Try to import fcntl for Unix file locking
        try:
            import fcntl

            has_fcntl = True
        except ImportError:
            # Windows doesn't have fcntl, fallback to no locking
            has_fcntl = False

        # Write with proper formatting and optional file locking
        mode = "r+" if settings_file.exists() else "w"
        with open(settings_file, mode, encoding="utf-8") as f:
            try:
                # Acquire exclusive lock if available (Unix only)
                if has_fcntl:
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)

                # Truncate file if opened in r+ mode
                if mode == "r+":
                    f.seek(0)
                    f.truncate()

                # Write JSON with proper formatting
                json.dump(config, f, indent=2)
                f.write("\n")  # Add trailing newline

            finally:
                # Release lock if acquired
                if has_fcntl:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)

        context.logger.info(f"  ✅ Settings updated at {settings_file}")

    def _hooks_already_installed(self, config: dict) -> bool:
        """Check if DES hooks are already installed.

        Returns True if ANY hook event type has a DES hook.
        This handles cases where only partial hooks exist (e.g., old format).
        The install process will clean up and reinstall all properly.
        """
        if "hooks" not in config:
            return False

        return any(
            any(
                shared_hooks.is_des_hook_entry(h)
                for h in config["hooks"].get(event, [])
            )
            for event in self.HOOK_EVENTS
        )

    def _is_des_hook_entry(self, hook_entry: dict) -> bool:
        """Check if a hook entry is a DES hook.

        Delegates to shared hook_definitions module for consistent detection
        across plugin builder and installer paths.
        """
        return shared_hooks.is_des_hook_entry(hook_entry)

    def uninstall(self, context: InstallContext) -> PluginResult:
        """Uninstall DES plugin.

        Removes DES hooks from settings.local.json while preserving all other settings.
        Also removes DES module, scripts, and templates.
        """
        try:
            errors = []

            # 1. Remove DES hooks from settings
            hooks_result = self._uninstall_des_hooks(context)
            if not hooks_result.success:
                errors.append(hooks_result.message)

            # 2. Remove DES module
            des_module = context.claude_dir / "lib" / "python" / "des"
            if des_module.exists():
                shutil.rmtree(des_module)
                context.logger.info(f"  🗑️ Removed DES module: {des_module}")

            # 3. Remove DES scripts
            scripts_dir = context.claude_dir / "scripts"
            for script_name in self.DES_SCRIPTS:
                script_path = scripts_dir / script_name
                if script_path.exists():
                    script_path.unlink()
                    context.logger.info(f"  🗑️ Removed DES script: {script_name}")

            # 4. Remove DES templates
            templates_dir = context.claude_dir / "templates"
            for template_name in self.DES_TEMPLATES:
                template_path = templates_dir / template_name
                if template_path.exists():
                    template_path.unlink()
                    context.logger.info(f"  🗑️ Removed DES template: {template_name}")

            if errors:
                return PluginResult(
                    success=False,
                    plugin_name="des",
                    message=f"DES uninstall had errors: {'; '.join(errors)}",
                    errors=errors,
                )

            return PluginResult(
                success=True,
                plugin_name="des",
                message="DES uninstalled successfully",
            )

        except Exception as e:
            return PluginResult(
                success=False,
                plugin_name="des",
                message=f"DES uninstall failed: {e}",
            )

    def _uninstall_des_hooks(self, context: InstallContext) -> PluginResult:
        """Remove DES hooks from settings.json (global config).

        Preserves all other settings (permissions, other hooks, etc.).
        """
        try:
            settings_file = context.claude_dir / "settings.json"

            if not settings_file.exists():
                return PluginResult(
                    success=True,
                    plugin_name="des",
                    message="No settings file to clean up",
                )

            config = self._load_settings(settings_file)

            # Remove only DES hooks, preserve everything else
            if "hooks" in config:
                for event in self.HOOK_EVENTS:
                    if event in config["hooks"]:
                        config["hooks"][event] = [
                            h
                            for h in config["hooks"][event]
                            if not shared_hooks.is_des_hook_entry(h)
                        ]

            self._save_settings(settings_file, config, context)

            return PluginResult(
                success=True,
                plugin_name="des",
                message="DES hooks removed (other settings preserved)",
            )

        except Exception as e:
            return PluginResult(
                success=False,
                plugin_name="des",
                message=f"DES hooks uninstall failed: {e}",
            )

    def verify(self, context: InstallContext) -> PluginResult:
        """Verify DES installation."""
        errors = []

        # 1. Verify DES module importable under the SAME Python that hooks use
        # (sys.executable = installer's Python, which is also the hook Python)
        try:
            lib_python = str(context.claude_dir / "lib" / "python")
            # Use repr() to properly escape backslashes on Windows paths
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    f"import sys; sys.path.insert(0, {lib_python!r}); import yaml; from des.application import DESOrchestrator",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                errors.append(f"DES module import failed: {result.stderr}")
        except Exception as e:
            errors.append(f"DES module verify failed: {e}")

        # 2. Verify scripts present
        for script in self.DES_SCRIPTS:
            script_path = context.claude_dir / "scripts" / script
            if not script_path.exists():
                errors.append(f"Missing DES script: {script}")

        # 3. Verify templates present
        for template in self.DES_TEMPLATES:
            template_path = context.claude_dir / "templates" / template
            if not template_path.exists():
                errors.append(f"Missing DES template: {template}")

        # 4. Verify hooks installed in settings.json (global config)
        settings_file = context.claude_dir / "settings.json"
        if settings_file.exists():
            try:
                config = self._load_settings(settings_file)
                if not self._hooks_already_installed(config):
                    errors.append("DES hooks not found in settings.json")
            except Exception as e:
                errors.append(f"Could not verify DES hooks: {e}")
        else:
            errors.append("settings.json not found - DES hooks not installed")

        # 5. Verify DES config exists and is valid JSON
        context.logger.info("  \U0001f50e Verifying DES config...")
        project_root = context.project_root or Path.cwd()
        config_file = project_root / ".nwave" / "des-config.json"
        nwave_dir = project_root / ".nwave"
        if not config_file.exists():
            if nwave_dir.exists():
                default_config = {
                    "audit_logging_enabled": True,
                    "audit_log_dir": ".nwave/des/logs",
                }
                nwave_dir.mkdir(parents=True, exist_ok=True)
                with open(config_file, "w", encoding="utf-8") as f:
                    json.dump(default_config, f, indent=2)
                    f.write("\n")
                context.logger.info(
                    f"  \u2705 DES config created (migration): {config_file}"
                )
                des_cfg = default_config
            else:
                errors.append("DES config not found: .nwave/des-config.json")
        if not errors and config_file.exists():
            try:
                with open(config_file, encoding="utf-8") as f:
                    des_cfg = json.load(f)
                audit_on = "on" if des_cfg.get("audit_logging_enabled") else "off"
                log_dir = des_cfg.get("audit_log_dir", "not set")
                context.logger.info(f"  \u2705 DES config ({config_file}):")
                context.logger.info(f"    \u2699\ufe0f audit_logging={audit_on}")
                context.logger.info(f"    \u2699\ufe0f log_dir={log_dir}")
            except json.JSONDecodeError:
                errors.append("DES config is not valid JSON: .nwave/des-config.json")

        if errors:
            return PluginResult(
                success=False,
                plugin_name="des",
                message="DES verification failed",
                errors=errors,
            )

        return PluginResult(
            success=True,
            plugin_name="des",
            message="DES verification passed (module, scripts, templates, hooks, config OK)",
        )
