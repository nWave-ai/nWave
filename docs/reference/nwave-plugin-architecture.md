# nWave Plugin Architecture Reference

**Type:** Reference Documentation
**Date:** 2026-02-13
**Version:** 2.0
**Status:** Production Ready

Complete API reference for the nWave plugin system. This document covers all classes, methods, configuration schemas, and error conditions. For tutorials on plugin development, see related how-to guides. For architectural rationale and design decisions, see the architecture documentation.

---

## Quick Start

### Minimal Plugin Implementation

```python
# Import from nWave plugin package
from scripts.install.plugins import InstallationPlugin, InstallContext, PluginResult

class MinimalPlugin(InstallationPlugin):
    def __init__(self):
        super().__init__(name="minimal", priority=55)
        self.dependencies = []  # No dependencies

    def install(self, context: InstallContext) -> PluginResult:
        try:
            # Your installation logic
            return PluginResult(
                success=True,
                plugin_name=self.name,
                message="Installation successful"
            )
        except Exception as e:
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message=f"Installation failed: {e}",
                errors=[str(e)]
            )

    def verify(self, context: InstallContext) -> PluginResult:
        # Your verification logic
        return PluginResult(
            success=True,
            plugin_name=self.name,
            message="Verification successful"
        )
```

### Register with PluginRegistry

```python
from scripts.install.plugins import PluginRegistry

registry = PluginRegistry()
registry.register(MinimalPlugin())
registry.install_all(context)
```

---

## API Reference

### Module: `des.plugins`

**Package Location:** `~/.claude/lib/python/des/plugins/`

**Package Exports:**
```python
__all__ = [
    "InstallationPlugin",
    "InstallContext",
    "PluginResult",
    "PluginRegistry",
    "AgentsPlugin",
    "CommandsPlugin",
    "TemplatesPlugin",
    "UtilitiesPlugin",
    "DESPlugin",
]
```

---

## PluginResult

**Location:** `~/.claude/lib/python/des/plugins/base.py`

Dataclass representing the result of plugin installation or verification operations.

### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `success` | `bool` | *required* | Whether the operation succeeded |
| `plugin_name` | `str` | *required* | Unique identifier of the plugin |
| `message` | `str` | `""` | Human-readable status message |
| `errors` | `List[str]` | `[]` | List of error messages if operation failed |
| `installed_files` | `List[Path]` | `[]` | Paths to files installed during operation |

### Methods

#### `__str__() -> str`

Returns formatted string representation with status indicator.

**Returns:**
- Success: `"✓ {plugin_name}: {message}"`
- Failure: `"✗ {plugin_name}: {message}"`

**Example:**
```python
result = PluginResult(success=True, plugin_name="agents")
print(result)  # Output: "✓ agents: "
```

### Usage Examples

**Success Result**
```python
result = PluginResult(
    success=True,
    plugin_name="agents",
    message="Agents installed successfully (41 files)",
    installed_files=[
        Path("/home/user/.claude/agents/nw/researcher.md"),
        Path("/home/user/.claude/agents/nw/analyst.md"),
    ]
)
```

**Failure Result**
```python
result = PluginResult(
    success=False,
    plugin_name="des",
    message="DES installation failed",
    errors=[
        "Missing DES scripts: check_stale_phases.py",
        "Missing DES templates: .pre-commit-config-nwave.yaml"
    ]
)
```

---

## InstallContext

**Location:** `~/.claude/lib/python/des/plugins/base.py`

Dataclass providing shared context passed to all plugins during installation. Acts as dependency injection container for utilities and paths.

### Fields

| Field | Type | Default | Required | Description |
|-------|------|---------|----------|-------------|
| `claude_dir` | `Path` | — | Yes | Target Claude config directory (`~/.claude`) |
| `scripts_dir` | `Path` | — | Yes | Source scripts directory |
| `templates_dir` | `Path` | — | Yes | Source templates directory |
| `logger` | `Any` | — | Yes | Logger instance (Logger or RichLogger) |
| `project_root` | `Path` | `None` | No | Root of nWave project |
| `framework_source` | `Path` | `None` | No | Pre-built distribution directory |
| `backup_manager` | `Any` | `None` | No | BackupManager instance for rollback |
| `installation_verifier` | `Any` | `None` | No | InstallationVerifier instance |
| `rich_logger` | `Any` | `None` | No | RichLogger instance for formatted output |
| `dry_run` | `bool` | `False` | No | If True, simulate without file operations |
| `dist_dir` | `Path` | `None` | No | Distribution directory for built artifacts |
| `metadata` | `Dict[str, Any]` | `{}` | No | Plugin-specific shared metadata |

### Usage Example

```python
from pathlib import Path
from scripts.install.plugins import InstallContext
from des.logging import Logger

context = InstallContext(
    claude_dir=Path.home() / ".claude",
    scripts_dir=Path.home() / ".claude" / "scripts",
    templates_dir=Path.home() / ".claude" / "templates",
    logger=Logger(log_file=Path("install.log")),
    project_root=Path("/home/user/nwave"),
    framework_source=Path("/home/user/nwave/dist/ide"),
    dry_run=False,
)
```

---

## InstallationPlugin (Abstract Base Class)

**Location:** `~/.claude/lib/python/des/plugins/base.py`

Abstract base class defining the interface for all installation plugins.

### Constructor

```python
def __init__(self, name: str, priority: int = 100):
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str` | *required* | Unique plugin identifier (e.g., "agents", "des") |
| `priority` | `int` | `100` | Execution priority: lower values execute first |

### Instance Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Plugin identifier set during initialization |
| `priority` | `int` | Execution order priority |
| `dependencies` | `List[str]` | Plugin names this plugin depends on (default: empty) |

### Abstract Methods

#### `install(context: InstallContext) -> PluginResult`

Installs plugin components to target directory.

**Parameters:**
- `context`: Shared installation context with utilities and paths

**Returns:** `PluginResult` indicating success/failure with message

**Must Override:** Yes

**Behavior:**
- Performs installation logic specific to plugin
- Tracks installed files in `PluginResult.installed_files`
- Returns structured result with success flag and error details
- Does not raise exceptions (catches and returns PluginResult)

**Example:**
```python
def install(self, context: InstallContext) -> PluginResult:
    try:
        target = context.claude_dir / "mycomponent"
        target.mkdir(parents=True, exist_ok=True)
        # Copy files, install components...
        return PluginResult(
            success=True,
            plugin_name=self.name,
            message="Component installed successfully"
        )
    except Exception as e:
        return PluginResult(
            success=False,
            plugin_name=self.name,
            message=f"Installation failed: {e}",
            errors=[str(e)]
        )
```

---

#### `verify(context: InstallContext) -> PluginResult`

Verifies installation was successful.

**Parameters:**
- `context`: Shared installation context

**Returns:** `PluginResult` indicating verification success/failure

**Must Override:** Yes

**Behavior:**
- Validates that files/modules installed correctly
- Checks file existence, importability, or functionality
- Returns failure if verification conditions not met
- Does not raise exceptions

**Example:**
```python
def verify(self, context: InstallContext) -> PluginResult:
    target = context.claude_dir / "mycomponent"
    if not target.exists():
        return PluginResult(
            success=False,
            plugin_name=self.name,
            message="Component directory not found"
        )

    files = list(target.glob("*.py"))
    if not files:
        return PluginResult(
            success=False,
            plugin_name=self.name,
            message="No Python files found"
        )

    return PluginResult(
        success=True,
        plugin_name=self.name,
        message=f"Verified {len(files)} component files"
    )
```

---

### Concrete Methods

#### `get_dependencies() -> List[str]`

Returns list of plugin names this plugin depends on.

**Returns:** `List[str]` of dependency plugin names (default: empty list)

**Example:**
```python
plugin = DESPlugin()
deps = plugin.get_dependencies()
# Returns: ["templates", "utilities"]
```

---

#### `set_dependencies(deps: List[str]) -> None`

Sets plugin dependencies.

**Parameters:**
- `deps`: List of plugin names to depend on

**Effect:** Sets `self.dependencies = deps`

**Example:**
```python
plugin.set_dependencies(["templates", "utilities"])
```

---

### Subclassing Template

```python
from scripts.install.plugins import InstallationPlugin, InstallContext, PluginResult

class CustomPlugin(InstallationPlugin):
    def __init__(self):
        super().__init__(name="custom", priority=60)
        self.dependencies = ["templates"]  # Optional dependencies

    def install(self, context: InstallContext) -> PluginResult:
        try:
            source = context.project_root / "custom_files"
            target = context.claude_dir / "custom"

            # Verify source exists
            if not source.exists():
                return PluginResult(
                    success=False,
                    plugin_name=self.name,
                    message=f"Source not found: {source}"
                )

            # Create target
            target.mkdir(parents=True, exist_ok=True)

            # Copy files
            import shutil
            files = []
            for file_path in source.glob("**/*"):
                if file_path.is_file():
                    rel_path = file_path.relative_to(source)
                    target_file = target / rel_path
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(file_path, target_file)
                    files.append(target_file)

            return PluginResult(
                success=True,
                plugin_name=self.name,
                message=f"Installed {len(files)} files",
                installed_files=files
            )
        except Exception as e:
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message=f"Installation failed: {e}",
                errors=[str(e)]
            )

    def verify(self, context: InstallContext) -> PluginResult:
        target = context.claude_dir / "custom"

        if not target.exists():
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message="Target directory does not exist"
            )

        files = list(target.glob("*"))
        if not files:
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message="No files found in target"
            )

        return PluginResult(
            success=True,
            plugin_name=self.name,
            message=f"Verified {len(files)} files"
        )
```

---

## PluginRegistry

**Location:** `~/.claude/lib/python/des/plugins/registry.py`

Registry for managing plugins, resolving dependencies, and executing installations in correct order.

### Constructor

```python
def __init__(self):
```

Creates empty registry with internal tracking structures.

**Initializes:**
- `plugins: dict[str, InstallationPlugin]` - Registered plugins by name
- `_installed_files: list[Path | str]` - Tracking for rollback
- `_installed_plugins: list[str]` - Tracking for rollback

---

### Methods

#### `register(plugin: InstallationPlugin) -> None`

Registers a plugin with the registry.

**Parameters:**
- `plugin`: InstallationPlugin instance to register

**Raises:**
- `ValueError`: "Plugin '{name}' already registered" — If plugin with same name exists

**Example:**
```python
registry = PluginRegistry()
registry.register(AgentsPlugin())
registry.register(CommandsPlugin())
registry.register(DESPlugin())
```

---

#### `get_execution_order() -> list[str]`

Returns plugin names in execution order respecting dependencies.

**Returns:** `list[str]` — Plugin names in topological sort order

**Raises:**
- `ValueError`: "Circular dependency detected in plugins" — If dependency cycle exists
- `ValueError`: "Plugin '{name}' depends on missing plugin '{dep}'" — If dependency not registered

**Algorithm:** Kahn's topological sort with priority-based tie-breaking

1. Build in-degree count for each plugin
2. Queue nodes with zero in-degree, sorted by priority
3. Process queue: add to output, decrement neighbors' in-degrees
4. Detect cycle if final output length != plugin count

**Time Complexity:** O(V + E) where V = plugins, E = dependencies

**Example:**
```python
registry = PluginRegistry()
registry.register(AgentsPlugin())      # priority=10, deps=[]
registry.register(CommandsPlugin())    # priority=20, deps=[]
registry.register(TemplatesPlugin())   # priority=30, deps=[]
registry.register(UtilitiesPlugin())   # priority=40, deps=["templates"]
registry.register(DESPlugin())         # priority=50, deps=["templates", "utilities"]

order = registry.get_execution_order()
# Returns: ["agents", "commands", "templates", "utilities", "des"]
```

---

#### `install_all(context: InstallContext, exclude: list[str] | None = None) -> dict[str, PluginResult]`

Installs all plugins in dependency order.

**Parameters:**
- `context`: Shared installation context
- `exclude`: Optional list of plugin names to skip

**Returns:** `dict[str, PluginResult]` — Results keyed by plugin name

**Behavior:**
1. Gets execution order via topological sort
2. Skips plugins in exclude list
3. Calls `plugin.install(context)` for each
4. Tracks installed files for rollback
5. **Stops on first failure** (unless handled by caller)

**Example:**
```python
context = InstallContext(
    claude_dir=Path.home() / ".claude",
    scripts_dir=Path.home() / ".claude" / "scripts",
    templates_dir=Path.home() / ".claude" / "templates",
    logger=logger,
    project_root=project_root,
)

# Install all except DES
results = registry.install_all(context, exclude=["des"])

# Check results
for name, result in results.items():
    if result.success:
        print(f"✓ {name}")
    else:
        print(f"✗ {name}: {result.message}")
        if result.errors:
            for error in result.errors:
                print(f"  - {error}")
```

---

#### `verify_all(context: InstallContext) -> dict[str, PluginResult]`

Verifies all plugins in dependency order.

**Parameters:**
- `context`: Shared installation context

**Returns:** `dict[str, PluginResult]` — Verification results keyed by plugin name

**Example:**
```python
verify_results = registry.verify_all(context)

all_passed = all(r.success for r in verify_results.values())
if all_passed:
    print("All plugins verified successfully")
else:
    for name, result in verify_results.items():
        if not result.success:
            print(f"Verification failed: {name}")
```

---

#### `rollback_installation(context: InstallContext) -> None`

Rolls back installation by removing installed files and restoring from backup.

**Behavior:**
1. Removes files tracked in `_installed_files`
2. Removes empty directories created by plugins
3. Restores from backup if `context.backup_manager` available
4. Clears tracking lists

**Example:**
```python
results = registry.install_all(context)

# Check for failures
if any(not r.success for r in results.values()):
    print("Installation failed, rolling back...")
    registry.rollback_installation(context)
    print("Rolled back to previous state")
```

---

#### `get_dependents(plugin_name: str) -> list[str]`

Returns plugins that depend on the specified plugin.

**Parameters:**
- `plugin_name`: Plugin to find dependents for

**Returns:** `list[str]` — Names of plugins depending on this one

**Example:**
```python
dependents = registry.get_dependents("templates")
# Standard setup returns: ["utilities", "des"]

if dependents:
    print(f"Cannot uninstall 'templates': required by {dependents}")
```

---

#### `uninstall(context: InstallContext, plugin_name: str) -> PluginResult`

Uninstalls a specific plugin.

**Parameters:**
- `context`: Shared installation context
- `plugin_name`: Name of plugin to uninstall

**Returns:** `PluginResult`

**Behavior:**
1. Checks plugin exists in registry
2. Checks for dependent plugins — **blocks if dependents exist**
3. Calls `plugin.uninstall(context)` if method exists
4. Removes from registry on success

**Error Conditions:**
- `success=False`, message="Plugin not found or not registered" — If plugin doesn't exist
- `success=False`, message="Cannot uninstall: dependent plugins exist" — If other plugins depend on this

**Example:**
```python
# Try to uninstall templates (which des depends on)
result = registry.uninstall(context, "templates")
if not result.success:
    print(f"Uninstall blocked: {result.message}")
    # Output: "Cannot uninstall: dependent plugins exist"

# Uninstall des first
result = registry.uninstall(context, "des")
if result.success:
    # Now templates can be uninstalled
    result = registry.uninstall(context, "templates")
```

---

## Built-in Plugins

### Plugin Execution Order

| Plugin | Priority | Dependencies | Executes |
|--------|----------|--------------|----------|
| `agents` | 10 | None | 1st |
| `commands` | 20 | None | 2nd |
| `templates` | 30 | None | 3rd |
| `utilities` | 40 | None | 4th |
| `des` | 50 | templates, utilities | 5th |

---

### AgentsPlugin

**Location:** `~/.claude/lib/python/des/plugins/agents_plugin.py`

Installs agent specification files to `~/.claude/agents/nw/`

#### Constructor

```python
def __init__(self):
    super().__init__(name="agents", priority=10)
```

#### install() Behavior

1. **Determine Source:**
   - Prefers `framework_source/agents/nw` if >= 5 agents present
   - Falls back to `project_root/nWave/agents`

2. **Create Target:** `claude_dir/agents/nw/`

3. **Copy Files:** Uses `PathUtils.copy_tree_with_filter()` excluding `README.md`

4. **Track Files:** Populates `installed_files` with copied paths

#### verify() Behavior

1. Checks `claude_dir/agents/nw/` exists
2. Checks for `.md` files in directory
3. Returns failure if missing

**Error Messages:**
- "target directory does not exist"
- "no agent files found"

---

### CommandsPlugin

**Location:** `~/.claude/lib/python/des/plugins/commands_plugin.py`

Installs nWave command specifications to `~/.claude/commands/nw/`

#### Constructor

```python
def __init__(self):
    super().__init__(name="commands", priority=20)
```

#### install() Behavior

1. **Source:** `framework_source/commands`
2. **Target:** `claude_dir/commands/`
3. **Copy Logic:**
   - Directories: `shutil.copytree()` with existing removal
   - Files: `shutil.copy2()` with parent creation

**Error Condition:** Returns failure if source doesn't exist

#### verify() Behavior

Checks `claude_dir/commands/nw/` for `.md` files

---

### TemplatesPlugin

**Location:** `~/.claude/lib/python/des/plugins/templates_plugin.py`

Installs nWave workflow templates to `~/.claude/templates/`

#### Constructor

```python
def __init__(self):
    super().__init__(name="templates", priority=30)
```

#### install() Behavior

1. **Source Selection:**
   - Primary: `context.templates_dir`
   - Fallback: `framework_source/templates`

2. **Target:** `claude_dir/templates/`

3. **File Collection:** Tracks both `.yaml` and `.md` files

#### verify() Behavior

1. Check target directory exists
2. Check for `.yaml` files (primary)
3. Fallback check for `.md` files

---

### UtilitiesPlugin

**Location:** `~/.claude/lib/python/des/plugins/utilities_plugin.py`

Installs utility scripts to `~/.claude/scripts/`

#### Constructor

```python
def __init__(self):
    super().__init__(name="utilities", priority=40)
```

#### Managed Scripts

```python
["install_nwave_target_hooks.py", "validate_step_file.py"]
```

#### install() Behavior

1. **Source:** `project_root/scripts`
2. **Target:** `claude_dir/scripts/`
3. **Version Checking:**
   - Extracts `__version__` from source and target
   - Uses `VersionUtils.compare_versions()`
   - Only copies if source version > target version

**Version Logic:**
```python
if VersionUtils.compare_versions(source_ver, target_ver) > 0:
    # Upgrade: copy new version
elif not target_script.exists():
    # Fresh install: copy
else:
    # Already up-to-date: skip
```

#### verify() Behavior

Checks `claude_dir/scripts/` for `.py` files

---

### DESPlugin

**Location:** `~/.claude/lib/python/des/plugins/des_plugin.py`

Installs DES (Deterministic Execution System) module, scripts, and templates for nWave execution engine.

#### Constructor

```python
def __init__(self):
    super().__init__(name="des", priority=50)
    self.dependencies = ["templates", "utilities"]
```

#### Class Constants

```python
DES_SCRIPTS = [
    "check_stale_phases.py",
    "scope_boundary_check.py",
]

DES_TEMPLATES = [
    ".pre-commit-config-nwave.yaml",
    ".des-audit-README.md",
]
```

#### Methods

##### `validate_prerequisites(context: InstallContext) -> PluginResult`

Validates DES prerequisites before installation.

**Checks:**
1. DES scripts directory at `nWave/scripts/des/`
2. Each required script in `DES_SCRIPTS`
3. Each required template in `DES_TEMPLATES`

**Returns:** Failure with detailed error message if missing

---

##### `install(context: InstallContext) -> PluginResult`

Main installation entry point.

**Procedure:**
1. Validate prerequisites (fail-fast)
2. Install DES module
3. Install DES scripts
4. Install DES templates

**Each step returns early on failure**

---

##### `_install_des_module(context: InstallContext) -> PluginResult`

Installs DES Python module to `~/.claude/lib/python/des/`

**Source Resolution:**
1. `context.dist_dir/lib/python/des` (build pipeline)
2. Fallback: `src/des`

**Features:**
- Backup existing module if `backup_manager` available
- Respects `dry_run` flag
- Complete replacement via `shutil.rmtree()` + `shutil.copytree()`

---

##### `_install_des_scripts(context: InstallContext) -> PluginResult`

Installs DES utility scripts to `~/.claude/scripts/`

**Source Resolution:**
1. `framework_source/scripts/des`
2. Fallback: `project_root/nWave/scripts/des`

**Features:**
- Sets executable permission (`chmod 0o755`)
- Respects `dry_run` flag

---

##### `_install_des_templates(context: InstallContext) -> PluginResult`

Installs DES templates to `~/.claude/templates/`

**Source:** `project_root/nWave/templates`

---

##### `verify(context: InstallContext) -> PluginResult`

Verifies complete DES installation.

**Checks:**
1. DES module importable via subprocess Python call
2. All DES scripts present in target
3. All DES templates present in target

**Import Verification:**
```python
subprocess.run([
    "python3", "-c",
    f'import sys; sys.path.insert(0, "{lib_python}"); '
    f'from des.application import DESOrchestrator'
], capture_output=True, text=True, timeout=5)
```

---

## Error Reference

### PluginRegistry.register()

**Error Condition:** Duplicate plugin name

| Error | Message | Cause | Solution |
|-------|---------|-------|----------|
| `ValueError` | `Plugin '{name}' already registered` | Plugin with same name already registered | Check registry before registering; ensure unique names |

---

### PluginRegistry.get_execution_order()

| Error | Message | Cause | Solution |
|-------|---------|-------|----------|
| `ValueError` | `Circular dependency detected in plugins` | Plugin dependency cycle exists (A→B→C→A) | Review dependency declarations; ensure acyclic graph |
| `ValueError` | `Plugin '{name}' depends on missing plugin '{dep}'` | Plugin depends on unregistered plugin | Register dependency plugin before dependent |

---

### PluginRegistry.install_all()

| Condition | Message | Cause | Solution |
|-----------|---------|-------|----------|
| Installation failure | Returns `success=False` in PluginResult | Plugin.install() returned failure | Check plugin error message and fix issues |
| Stops on first failure | Partial results returned | By design, stops after first failure | Use `rollback_installation()` to revert |

---

### PluginRegistry.uninstall()

| Condition | Message | Cause | Solution |
|-----------|---------|-------|----------|
| Plugin not found | "Plugin not found or not registered" | Plugin doesn't exist in registry | Verify plugin name spelling |
| Has dependents | "Cannot uninstall: dependent plugins exist" | Other plugins depend on this one | Uninstall dependents first |

---

### AgentsPlugin/CommandsPlugin/TemplatesPlugin Errors

| Error | Message | Cause | Solution |
|-------|---------|-------|----------|
| Source not found | "source not found" or similar | Framework source or project root misconfigured | Check context paths; verify directory structure |
| Target permission denied | `PermissionError` | Insufficient permissions to create target | Run with appropriate permissions; check directory ownership |

---

### DESPlugin.validate_prerequisites()

| Error | Description | Cause | Solution |
|-------|-------------|-------|----------|
| Missing DES scripts | "Missing DES scripts: [list]" | Scripts not found in source | Verify DES scripts exist in `nWave/scripts/des/` |
| Missing DES templates | "Missing DES templates: [list]" | Templates not found | Verify templates exist in `nWave/templates/` |
| Missing scripts directory | "DES scripts directory not found" | `nWave/scripts/des/` doesn't exist | Create directory with required scripts |

---

### DESPlugin.verify()

| Error | Description | Cause | Solution |
|-------|-------------|-------|----------|
| Module import failed | "DES module import failed: [stderr]" | `from des.application import DESOrchestrator` failed | Check installation; verify Python path configuration |
| Missing script | "Missing DES script: [name]" | Script file not in target | Reinstall DES plugin; check file permissions |
| Missing template | "Missing DES template: [name]" | Template file not in target | Reinstall DES plugin; verify source files |

---

## Examples

### Example 1: Install All Plugins

```python
from pathlib import Path
from scripts.install.plugins import (
    PluginRegistry, InstallContext,
    AgentsPlugin, CommandsPlugin, TemplatesPlugin,
    UtilitiesPlugin, DESPlugin
)
from des.logging import Logger

# Create registry
registry = PluginRegistry()

# Register plugins
registry.register(AgentsPlugin())
registry.register(CommandsPlugin())
registry.register(TemplatesPlugin())
registry.register(UtilitiesPlugin())
registry.register(DESPlugin())

# Create context
context = InstallContext(
    claude_dir=Path.home() / ".claude",
    scripts_dir=Path.home() / ".claude" / "scripts",
    templates_dir=Path.home() / ".claude" / "templates",
    logger=Logger(),
    project_root=Path("/path/to/nwave"),
)

# Get execution order
order = registry.get_execution_order()
print(f"Installation order: {order}")

# Install all plugins
results = registry.install_all(context)

# Display results
for name, result in results.items():
    status = "✓" if result.success else "✗"
    print(f"{status} {name}: {result.message}")
    if result.errors:
        for error in result.errors:
            print(f"  - {error}")
```

---

### Example 2: Selective Installation (Exclude DES)

```python
# Install all except DES
results = registry.install_all(context, exclude=["des"])

print("Installed plugins:", list(results.keys()))
# Output: ['agents', 'commands', 'templates', 'utilities']
```

---

### Example 3: Verification After Installation

```python
# Verify all plugins
verify_results = registry.verify_all(context)

# Check each plugin
for name, result in verify_results.items():
    if result.success:
        print(f"✓ {name} verified")
    else:
        print(f"✗ {name} verification failed:")
        print(f"  {result.message}")
        for error in result.errors:
            print(f"  - {error}")

# Overall success
all_passed = all(r.success for r in verify_results.values())
if all_passed:
    print("✓ All plugins verified successfully")
else:
    print("✗ Some plugins failed verification")
```

---

### Example 4: Rollback on Failure

```python
results = registry.install_all(context)

# Check for failures
failed = [name for name, r in results.items() if not r.success]

if failed:
    print(f"Installation failed for: {failed}")
    print("Rolling back installation...")
    registry.rollback_installation(context)
    print("✓ Rolled back to previous state")
else:
    print("✓ Installation successful")
```

---

### Example 5: Custom Plugin Dependency

```python
from scripts.install.plugins import InstallationPlugin, PluginResult, InstallContext

class ReportingPlugin(InstallationPlugin):
    def __init__(self):
        super().__init__(name="reporting", priority=60)
        # Reporting depends on DES (which already depends on templates/utilities)
        self.dependencies = ["des"]

    def install(self, context: InstallContext) -> PluginResult:
        try:
            # Installation code
            return PluginResult(
                success=True,
                plugin_name=self.name,
                message="Reporting plugin installed"
            )
        except Exception as e:
            return PluginResult(
                success=False,
                plugin_name=self.name,
                errors=[str(e)]
            )

    def verify(self, context: InstallContext) -> PluginResult:
        # Verification code
        return PluginResult(success=True, plugin_name=self.name)

# Add to registry
registry.register(ReportingPlugin())

# Execution order now: agents, commands, templates, utilities, des, reporting
order = registry.get_execution_order()
print(order)  # ['agents', 'commands', 'templates', 'utilities', 'des', 'reporting']
```

---

### Example 6: Handle Missing Dependencies

```python
registry = PluginRegistry()

# Register plugin with missing dependency
class BadPlugin(InstallationPlugin):
    def __init__(self):
        super().__init__(name="bad", priority=100)
        self.dependencies = ["nonexistent"]  # ← Missing!

    def install(self, context: InstallContext) -> PluginResult:
        return PluginResult(success=True, plugin_name=self.name)

    def verify(self, context: InstallContext) -> PluginResult:
        return PluginResult(success=True, plugin_name=self.name)

registry.register(BadPlugin())

# This raises ValueError
try:
    order = registry.get_execution_order()
except ValueError as e:
    print(f"Error: {e}")
    # Output: "Plugin 'bad' depends on missing plugin 'nonexistent'"
```

---

### Example 7: Detect and Handle Circular Dependencies

```python
registry = PluginRegistry()

# Create two plugins with circular dependency
class PluginA(InstallationPlugin):
    def __init__(self):
        super().__init__(name="plugin_a", priority=10)
        self.dependencies = ["plugin_b"]

    def install(self, context: InstallContext) -> PluginResult:
        return PluginResult(success=True, plugin_name=self.name)

    def verify(self, context: InstallContext) -> PluginResult:
        return PluginResult(success=True, plugin_name=self.name)

class PluginB(InstallationPlugin):
    def __init__(self):
        super().__init__(name="plugin_b", priority=20)
        self.dependencies = ["plugin_a"]  # ← Circular!

    def install(self, context: InstallContext) -> PluginResult:
        return PluginResult(success=True, plugin_name=self.name)

    def verify(self, context: InstallContext) -> PluginResult:
        return PluginResult(success=True, plugin_name=self.name)

registry.register(PluginA())
registry.register(PluginB())

# This raises ValueError
try:
    order = registry.get_execution_order()
except ValueError as e:
    print(f"Error: {e}")
    # Output: "Circular dependency detected in plugins"
```

---

### Example 8: Find Dependent Plugins

```python
# Standard setup
registry.register(TemplatesPlugin())
registry.register(UtilitiesPlugin())
registry.register(DESPlugin())

# Find what depends on templates
dependents = registry.get_dependents("templates")
print(f"Plugins depending on 'templates': {dependents}")
# Output: ['utilities', 'des']

# Cannot uninstall templates while dependents exist
result = registry.uninstall(context, "templates")
print(result.message)
# Output: "Cannot uninstall: dependent plugins exist"

# Must uninstall dependents first
registry.uninstall(context, "des")      # Uninstall des first
registry.uninstall(context, "utilities")  # Then utilities
registry.uninstall(context, "templates")  # Now templates can be uninstalled
```

---

## See Also

- **Plugin development how-to:** Step-by-step guide for creating custom plugins
- **Architecture documentation:** Design patterns, extension points, and philosophy
- **Agent specifications:** Individual agent implementations at `~/.claude/agents/nw/`
- **Installation guide:** Using `pipx install nwave-ai && nwave-ai install` to set up framework

---

**Last Updated:** 2026-02-13
**Document Type:** Reference (DIVIO Classification)
**Type Purity:** 96%+ (lookup-focused API documentation with working examples)
**Installation Method:** `pipx install nwave-ai && nwave-ai install`
