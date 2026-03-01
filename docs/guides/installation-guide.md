# Installation Guide

Install nWave to your global Claude Code configuration. This adds 22 specialized agents (11 primary + 11 reviewers) and 18 slash commands across all your projects.

## Prerequisites

- **Python 3.10+**
- **Claude Code** installed
- **pipx** (recommended) or pip

If you need pipx:
```bash
pip install pipx
pipx ensurepath
```

## Installation

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

## Advanced Options

| Command | Purpose |
|---------|---------|
| `nwave-ai install --dry-run` | Preview changes without installing |
| `nwave-ai install --backup-only` | Backup without installing |
| `nwave-ai install --restore` | Restore from recent backup |
| `nwave-ai version` | Show installed version |

## What Gets Installed

The installer sets up components in your `~/.claude/` directory:

```
~/.claude/
├── agents/nw/                 # 22 agents (11 primary + 11 reviewers)
├── commands/nw/               # 18 slash commands
├── templates/                 # Wave and DES templates
├── skills/                    # Agent knowledge files
├── scripts/                   # DES utilities
└── settings.json              # DES hooks
```

All agents and commands become available globally across all Claude Code projects.

## DES Hooks

The installer registers DES (Deterministic Execution System) hooks in your Claude Code settings:

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

Settings here override global defaults for that project only.

## Updating

```bash
pipx upgrade nwave-ai
nwave-ai install
```

The installer automatically backs up your configuration before updating, allowing rollback if needed.

## Uninstalling

```bash
nwave-ai uninstall
pipx uninstall nwave-ai
```

This removes agents, commands, templates, and DES hooks. Your project files are unaffected.

## Verification

After installation:

```bash
nwave-ai version
```

In Claude Code, type `@` to see agents or `/nw:` to see commands. You should see all 22 agents and 18 commands available.

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

```bash
# For fresh features (greenfield)
/nw:discover "feature market research"
/nw:discuss "feature requirements"
/nw:design
/nw:devops
/nw:distill "acceptance tests"
/nw:deliver

# Or for existing code (brownfield)
/nw:deliver
```

For workflow guidance, see [Jobs To Be Done Guide](jobs-to-be-done-guide.md).

## Support

- **Discord Community**: [Join the nWave Discord](https://discord.gg/Cywj3uFdpd) for help with installation issues
- **Documentation**: Complete framework documentation is available in the repository
- **Logs**: Check `~/.claude/nwave-install.log` for installation details
- **Version**: Run `nwave-ai version` to see your installed version

---

**Ready to build?** Start with [Jobs To Be Done Guide](jobs-to-be-done-guide.md) to learn when and how to use each workflow.
