# Installation Guide

Install nWave to your global Claude Code configuration. This adds 23 specialized agents (12 primary + 11 reviewers) and 22 slash commands across all your projects.

## v2.8.0 Breaking Change: Command Format

Starting with v2.8.0, all nWave commands use hyphens instead of colons:

- **Before**: `/nw:deliver`, `/nw:design`, `/nw:discuss`, etc.
- **After**: `/nw-deliver`, `/nw-design`, `/nw-discuss`, etc.

If you upgrade from an earlier version, run the installer again to clean up old `/nw:` commands. No data loss — only the command format changes.

## Choose Your Method

| Scenario | Use | Why |
|----------|-----|-----|
| First time | **CLI** | Full-featured, recommended |
| Team rollout | **CLI** | Same command format everywhere |
| Contributing | **CLI** | Dev scripts, internals access |

> **Why not Plugin?** The plugin marketplace install is currently missing DES enforcement, attribution hooks, and rigor profiles. It also uses a different command format (`/nw:deliver` vs `/nw-deliver`) due to Claude Code's plugin namespace system. We recommend CLI install for the full nWave experience. See [issue #31](https://github.com/nWave-ai/nWave/issues/31) for details.

## CLI Installer (Recommended)

### Prerequisites

- **Python 3.10+**
- **Claude Code** installed
- **pipx** (recommended) or pip

If you need pipx:
```bash
pip install pipx
pipx ensurepath
```

### Using pipx (Recommended)

```bash
pipx install nwave-ai
nwave-ai install
```

### Using pip

```bash
pip install nwave-ai
nwave-ai install
```

Then close and reopen Claude Code. The nWave agents and slash commands will appear in your command palette.

> **Windows users**: Use WSL (Windows Subsystem for Linux). Install with: `wsl --install`

### Advanced Options

| Command | Purpose |
|---------|---------|
| `nwave-ai install --dry-run` | Preview changes without installing |
| `nwave-ai install --backup-only` | Backup without installing |
| `nwave-ai install --restore` | Restore from recent backup |
| `nwave-ai version` | Show installed version |

## Plugin (Beta Preview — Not Feature-Complete)

> **Warning**: The plugin install is missing DES enforcement, attribution hooks, rigor profiles, and uses a different command format (`/nw:deliver` instead of `/nw-deliver`). Use CLI install above for the full experience.

The plugin method installs nWave directly from the Claude Code marketplace. No Python or pipx required.

From Claude Code, run:

```
/plugin marketplace add nwave-ai/nwave
/plugin install nw@nwave-marketplace
```

Restart Claude Code and type `/nw-` to see all available commands.

> **The plugin method is in beta preview and NOT feature-complete.** It provides agents and skills but NOT DES enforcement, attribution, or rigor profiles. Commands use `/nw:deliver` format (not `/nw-deliver`). For the full experience, use the CLI method above.

## What Gets Installed

Both methods install the same components to your `~/.claude/` directory:

```
~/.claude/
├── agents/nw/                 # 23 agents (12 primary + 11 reviewers)
├── commands/nw/               # 22 slash commands
├── templates/                 # Wave and DES templates
├── skills/                    # Agent knowledge files
├── scripts/                   # DES utilities
└── settings.json              # DES hooks
```

All agents and commands become available globally across all Claude Code projects.

## DES Hooks

Both methods register DES (Deterministic Execution System) hooks in your Claude Code settings:

- Pre-task validation
- Post-tool-use monitoring
- Subagent timeout tracking
- Audit logging

Configure globally in `~/.claude/settings.json` or per-project via `.nwave/des-config.json`.

## Per-Project Configuration

To customize DES behavior for a specific project, create `.nwave/des-config.json` in your project directory:

```json
{
  "audit_log_enabled": true,
  "audit_log_path": ".nwave/audit.log",
  "validation_enabled": true,
  "tool_monitoring_enabled": true,
  "max_execution_time": 3600,
  "subagent_timeout": 300
}
```

| Setting | Default | Description |
|---------|---------|-------------|
| `audit_log_enabled` | `true` | Enable DES execution audit trail for debugging |
| `audit_log_path` | `".nwave/audit.log"` | Where to write audit records |
| `validation_enabled` | `true` | Enforce TDD phase sequence; set `false` to disable DES checks |
| `tool_monitoring_enabled` | `true` | Monitor Task invocations for unbounded loops |
| `max_execution_time` | `3600` | Kill subagent after this many seconds (default: 1 hour) |
| `subagent_timeout` | `300` | Kill unresponsive subagent after this many seconds (default: 5 min) |

Settings here override global defaults for that project only.

## Updating

**CLI method:**
```bash
pipx upgrade nwave-ai
nwave-ai install
```

The installer automatically backs up your configuration before updating, allowing rollback if needed.

**Plugin method:**
```
/plugin marketplace update nwave-marketplace
```

Or enable auto-updates in Claude Code plugin settings.

nWave checks for new versions when you open Claude Code. Control check frequency via `update_check.frequency` in `~/.nwave/des-config.json`:

| Value | Behavior |
|-------|----------|
| `daily` | Check once per day |
| `weekly` | Check once per week |
| `every_session` | Check on every session start (default) |
| `never` | Disable update checks |

## Uninstalling

**CLI method:**
```bash
nwave-ai uninstall              # Removes agents, commands, config, DES hooks from ~/.claude/
pipx uninstall nwave-ai        # Removes the nwave-ai Python package itself
```

**Plugin method:**
```
/plugin uninstall nw
```

Both methods remove agents, commands, and configuration from `~/.claude/`. Your project files (`.nwave/`, source code) are never touched.

## Verification

### CLI method

```bash
nwave-ai version
```

Then in Claude Code, type `@` to see agents or `/nw-` to see commands.

### Plugin method

Restart Claude Code after installation. Type `/nw-` in the command palette — you should see all 22 commands. Type `@nw` to see agents.

> If commands don't appear after plugin install, quit Claude Code completely and reopen it.

## Troubleshooting

### Agents Not Appearing in Claude Code

If agents don't appear after installation:

1. Restart Claude Code completely (quit and reopen)
2. Verify installation completed successfully:

```bash
nwave-ai version
```

3. Check that `~/.claude/agents/nw/` exists with agent files
4. Ensure your Claude Code version is current (update via your package manager)

### Installation Failed

If the installer reports errors:

1. Check Python version:

```bash
python --version
# Must be 3.10 or higher
```

2. Ensure write access to `~/.claude/`:

```bash
ls -la ~/.claude/
```

3. If you see permission errors, check file permissions:

```bash
chmod 755 ~/.claude/
```

4. Restore from backup:

```bash
nwave-ai install --restore
```

### pipx Issues

If pipx commands fail:

```bash
# Verify pipx is installed
pipx --version

# Ensure pipx is in your PATH
which pipx

# If not found, reinstall pipx
pip install --user pipx
```

### Import Errors When Using nWave

If you see import errors when running nWave commands:

1. Ensure Claude Code is using the correct Python environment
2. Reinstall nWave:

```bash
pipx uninstall nwave-ai
pipx install nwave-ai
nwave-ai install
```

3. Restart Claude Code

### DES Audit Log Errors

If audit logging isn't working:

1. Create the `.nwave/` directory in your project:

```bash
mkdir -p .nwave
```

2. Verify `.nwave/` is writable:

```bash
touch .nwave/test.txt
rm .nwave/test.txt
```

3. Check DES configuration in `.nwave/des-config.json` is valid JSON

### Rollback After Update

If an update causes problems:

```bash
nwave-ai install --restore
```

This restores your previous configuration from the most recent backup.

## Next Steps

After installation, navigate to any project and start your first workflow:

```
# For fresh features (greenfield)
/nw-discover "feature market research"
/nw-discuss "feature requirements"
/nw-design
/nw-devops
/nw-distill "acceptance tests"
/nw-deliver

# Or for existing code (brownfield)
/nw-deliver
```

For workflow guidance, see [Jobs To Be Done Guide](../jobs-to-be-done-guide/).

## Support

- **Discord Community**: [Join the nWave Discord](https://discord.gg/Cywj3uFdpd) for help with installation issues
- **Documentation**: Complete framework documentation is available in the repository
- **Logs**: Check `~/.claude/nwave-install.log` for installation details
- **Version**: Run `nwave-ai version` to see your installed version

---

**Ready to build?** Start with [Jobs To Be Done Guide](../jobs-to-be-done-guide/) to learn when and how to use each workflow.
