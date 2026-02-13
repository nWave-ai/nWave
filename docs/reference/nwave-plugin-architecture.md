# nWave Plugin Architecture Reference

**Version**: 2.1.0
**Date**: 2026-02-13
**Status**: Production Ready

API reference for the nWave installation plugin system.

**Source**: `scripts/install/plugins/`

---

## Quick Start

```python
from scripts.install.plugins import InstallationPlugin, InstallContext, PluginResult

class MyPlugin(InstallationPlugin):
    def __init__(self):
        super().__init__(name="my-plugin", priority=55)
        self.dependencies = []

    def install(self, context: InstallContext) -> PluginResult:
        # Your installation logic
        return PluginResult(success=True, plugin_name=self.name, message="Done")

    def verify(self, context: InstallContext) -> PluginResult:
        # Your verification logic
        return PluginResult(success=True, plugin_name=self.name, message="Verified")
```

---

## Core Classes

### PluginResult

**Source**: `scripts/install/plugins/base.py`

Dataclass for structured installation/verification results.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `success` | `bool` | *required* | Whether the operation succeeded |
| `plugin_name` | `str` | *required* | Unique plugin identifier |
| `message` | `str` | `""` | Human-readable status |
| `errors` | `list[str]` | `[]` | Error messages on failure |
| `installed_files` | `list[Path]` | `[]` | Paths to files installed |

### InstallContext

**Source**: `scripts/install/plugins/base.py`

Shared context passed to all plugins during installation.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `claude_dir` | `Path` | Yes | Target `~/.claude` directory |
| `scripts_dir` | `Path` | Yes | Source scripts directory |
| `templates_dir` | `Path` | Yes | Source templates directory |
| `logger` | `Any` | Yes | Logger instance |
| `project_root` | `Path` | No | Root of nWave project |
| `framework_source` | `Path` | No | Pre-built distribution directory |
| `backup_manager` | `Any` | No | BackupManager for rollback |
| `installation_verifier` | `Any` | No | InstallationVerifier instance |
| `rich_logger` | `Any` | No | RichLogger for formatted output |
| `dry_run` | `bool` | No | Simulate without file operations |
| `metadata` | `dict` | No | Plugin-specific shared data |

### InstallationPlugin (ABC)

**Source**: `scripts/install/plugins/base.py`

Abstract base class for all plugins.

**Constructor**: `__init__(name: str, priority: int = 100)`
- `name`: Unique identifier (e.g., `"agents"`, `"des"`)
- `priority`: Lower values execute first

**Abstract methods** (must override):
- `install(context: InstallContext) -> PluginResult`
- `verify(context: InstallContext) -> PluginResult`

**Concrete methods**:
- `get_dependencies() -> list[str]` — Returns dependency plugin names
- `set_dependencies(deps: list[str]) -> None` — Sets dependencies

---

## PluginRegistry

**Source**: `scripts/install/plugins/registry.py`

Manages plugin registration, dependency resolution (Kahn's topological sort), and orchestrated installation.

### Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `register(plugin)` | `None` | Register a plugin. Raises `ValueError` on duplicate name |
| `get_execution_order()` | `list[str]` | Plugin names in dependency-resolved order |
| `install_all(context, exclude=None)` | `dict[str, PluginResult]` | Install all plugins. Stops on first failure |
| `verify_all(context)` | `dict[str, PluginResult]` | Verify all plugins |
| `rollback_installation(context)` | `None` | Remove installed files and restore from backup |
| `get_dependents(plugin_name)` | `list[str]` | Plugins that depend on the given plugin |
| `uninstall(context, plugin_name)` | `PluginResult` | Uninstall a plugin. Blocks if dependents exist |

### Errors

| Method | Error | Cause |
|--------|-------|-------|
| `register()` | `ValueError: Plugin '{name}' already registered` | Duplicate name |
| `get_execution_order()` | `ValueError: Circular dependency detected` | Dependency cycle |
| `get_execution_order()` | `ValueError: depends on missing plugin '{dep}'` | Unregistered dependency |
| `uninstall()` | `success=False: dependent plugins exist` | Other plugins depend on it |

---

## Built-in Plugins

| Plugin | Priority | Dependencies | Installs To |
|--------|----------|--------------|-------------|
| `agents` | 10 | — | `~/.claude/agents/nw/` |
| `commands` | 20 | — | `~/.claude/commands/nw/` |
| `templates` | 30 | — | `~/.claude/templates/` |
| `utilities` | 40 | — | `~/.claude/scripts/` |
| `skills` | 45 | — | `~/.claude/commands/nw/` |
| `des` | 50 | templates, utilities | `~/.claude/lib/python/des/` |

### AgentsPlugin

**Source**: `scripts/install/plugins/agents_plugin.py`

Copies agent specification `.md` files to `~/.claude/agents/nw/`. Prefers `framework_source/agents/nw` if available, falls back to `project_root/nWave/agents`.

### CommandsPlugin

**Source**: `scripts/install/plugins/commands_plugin.py`

Copies command specifications to `~/.claude/commands/`. Source: `framework_source/commands`.

### TemplatesPlugin

**Source**: `scripts/install/plugins/templates_plugin.py`

Copies workflow templates (`.yaml`, `.md`) to `~/.claude/templates/`. Source: `context.templates_dir` or `framework_source/templates`.

### UtilitiesPlugin

**Source**: `scripts/install/plugins/utilities_plugin.py`

Copies utility scripts to `~/.claude/scripts/`. Performs version comparison — only upgrades when source version is newer.

### SkillsPlugin

**Source**: `scripts/install/plugins/skills_plugin.py`

Copies skill command files to `~/.claude/commands/nw/`.

### DESPlugin

**Source**: `scripts/install/plugins/des_plugin.py`

Installs the DES module, scripts, and templates. Validates prerequisites before install. Verifies DES module importability via subprocess.

**Required files**:
- Scripts: `check_stale_phases.py`, `scope_boundary_check.py`
- Templates: `.pre-commit-config-nwave.yaml`, `.des-audit-README.md`

---

## See Also

- [Installation Guide](../guides/installation-guide.md) — End-user install with `pipx install nwave-ai`
- [nWave Commands Reference](./nwave-commands-reference.md) — All commands and agents

---

**Last Updated**: 2026-02-13
**Type**: Reference
