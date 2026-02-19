# nWave Installation Guide

This guide helps you install the nWave framework to your global Claude Code configuration, making 22 specialized agents (11 primary, 11 reviewers) and 18 slash commands available across all your projects.

## Prerequisites

Before installing nWave, ensure you have:

- **Python 3.10 or higher**
- **Claude Code CLI** installed and configured
- **pipx** (recommended for installing nwave-ai)

If you need to install pipx, run:

```bash
pip install pipx
```

## Quick Start

### Install via pipx (Recommended)

```bash
pipx install nwave-ai
nwave-ai install
```

Close and reopen Claude Code. The nWave agents and slash commands will appear in your command palette.

### Install via pip

If you prefer pip:

```bash
pip install nwave-ai
nwave-ai install
```

## Installation Options

### Standard Installation

Installs the complete framework with automatic backup of existing configuration:

```bash
nwave-ai install
```

### Dry Run (Preview Changes)

Preview what will be installed without making changes:

```bash
nwave-ai install --dry-run
```

### Backup Only

Create a backup without installing:

```bash
nwave-ai install --backup-only
```

### Restore Previous Installation

Restore from the most recent backup:

```bash
nwave-ai install --restore
```

### Show Version

Display the installed nwave-ai version:

```bash
nwave-ai version
```

## What Gets Installed

The installer sets up nWave components in your `~/.claude/` directory:

```
~/.claude/
├── agents/nw/                  # 22 agent specifications (11 primary + 11 reviewers)
│   ├── nw-product-discoverer.md
│   ├── nw-product-owner.md
│   ├── nw-solution-architect.md
│   ├── nw-platform-architect.md
│   ├── nw-acceptance-designer.md
│   ├── nw-software-crafter.md
│   ├── nw-researcher.md
│   ├── nw-troubleshooter.md
│   ├── nw-data-engineer.md
│   ├── nw-documentarist.md
│   ├── nw-agent-builder.md
│   └── nw-*-reviewer.md         # 11 matching reviewer agents
├── commands/nw/                # 18 slash command definitions
│   ├── discover.md              # Wave commands (6)
│   ├── discuss.md
│   ├── design.md
│   ├── devops.md
│   ├── distill.md
│   ├── deliver.md
│   ├── execute.md               # Execution commands (4)
│   ├── review.md
│   ├── finalize.md
│   ├── roadmap.md
│   ├── research.md              # Cross-wave commands (6)
│   ├── document.md
│   ├── root-why.md
│   ├── refactor.md
│   ├── mikado.md
│   ├── mutation-test.md
│   ├── diagram.md               # Utility commands (2)
│   └── forge.md
├── templates/                  # Wave and DES templates
│   ├── execution-log-template.yaml
│   ├── roadmap-schema.yaml
│   ├── step-tdd-cycle-schema.json
│   └── ...
├── skills/                     # Agent knowledge files
│   ├── common/
│   ├── researcher/
│   ├── software-crafter/
│   ├── solution-architect/
│   └── ...
├── scripts/                    # DES utility and validation scripts
└── settings.json               # DES hooks registered here
```

This layout makes agents and commands available globally across all your Claude Code projects.

## DES Hooks

The installer registers DES (Deterministic Execution System) hooks in your Claude Code settings, enabling:

- Pre-task validation before agents execute
- Post-tool-use monitoring for error detection
- Subagent stop tracking to prevent hung tasks
- Comprehensive audit logging for compliance and debugging

DES hooks are configured in `~/.claude/settings.json` and can be customized per-project.

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

## Updating nWave

To update to a newer version:

```bash
pipx upgrade nwave-ai
nwave-ai install
```

The installer creates an automatic backup of your existing configuration before updating, allowing rollback if needed.

## Uninstalling nWave

To remove the nWave framework:

```bash
nwave-ai uninstall
pipx uninstall nwave-ai
```

This removes:
- Agent definitions from `~/.claude/agents/nw/`
- Slash command definitions from `~/.claude/commands/nw/`
- Templates and skills from `~/.claude/`
- DES hooks from settings.json

Your project files are not affected.

## Verifying Installation

After installation, verify nWave is available:

```bash
# Show installed version
nwave-ai version

# List available agents in Claude Code by typing @ in any project
# You should see: @product-discoverer, @product-owner, @solution-architect, etc.

# List slash commands by typing / in any project
# You should see: /nw:discover, /nw:discuss, /nw:design, /nw:devops, /nw:distill, /nw:deliver, etc.
```

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

- **Discord Community**: [Join the nWave Discord](https://discord.gg/DeYdSNk6) for help with installation issues
- **Documentation**: Complete framework documentation is available in the repository
- **Logs**: Check `~/.claude/nwave-install.log` for installation details
- **Version**: Run `nwave-ai version` to see your installed version

---

**Ready to build?** Start with [Jobs To Be Done Guide](jobs-to-be-done-guide.md) to learn when and how to use each workflow.
