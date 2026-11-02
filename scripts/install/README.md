<!-- version: 1.4.2 -->

# nWave Installation Scripts

Cross-platform Python-based installation tools for the nWave methodology framework.

## Overview

This directory contains Python scripts for installing, uninstalling, updating, and backing up the nWave framework. All scripts are cross-platform compatible (Windows, Mac, Linux).

## Files

### Core Scripts

1. **`install_nwave.py`** - Main installation script
   - Installs nWave framework to `~/.claude/`
   - Automatically builds framework if needed
   - Version-aware utility script management
   - Creates installation backups

2. **`uninstall_nwave.py`** - Uninstallation script
   - Completely removes nWave framework
   - Optional backup before removal
   - Validates complete uninstallation

3. **`update_nwave.py`** - Update orchestrator
   - Automates: Build → Uninstall → Install
   - Pre-update backups
   - Validates update success

### Utilities

- **`install_utils.py`** - Shared utilities module
  - Cross-platform logging with colors
  - Backup management
  - Path utilities
  - Version comparison
  - Manifest writing

## Usage

### Installation

```bash
# Basic installation
python scripts/install/install_nwave.py

# Dry run (show what would be installed)
python scripts/install/install_nwave.py --dry-run

# Target one platform explicitly (auto-detect is the default)
python scripts/install/install_nwave.py --platform claude-code
python scripts/install/install_nwave.py --platform codex
python scripts/install/install_nwave.py --platform omp

# Create backup only
python scripts/install/install_nwave.py --backup-only

# Restore from latest backup
python scripts/install/install_nwave.py --restore
```

### Target Platforms

`--platform` accepts `auto` (default), `claude-code`, `opencode`, `codex`,
`copilot`, `omp`, or `all`.

OMP (oh-my-pi) installs public task agents, skills and `/nw-*` commands into
its native discovery tree: `<config-root>/agent/agents/*.md`,
`<config-root>/agent/skills/<name>/SKILL.md` and
`<config-root>/agent/commands/nw-*.md`. The config root is `$HOME/.omp`
(renamed by `PI_CONFIG_DIR`); `PI_CODING_AGENT_DIR` relocates skills, commands
and extensions. Use `--dev` only to include private artifacts.
The command source is `nWave/tasks/nw/*.md` (or the distribution's
`tasks/nw/`), filtered using the catalog's public-agent command policy.
Underscore agent references are compared using hyphenated catalog keys;
unresolved references remain non-public.
Command-skills are not the command roster. Task `deliver.md` becomes flat
`commands/nw-deliver.md`, so its slash name is `/nw-deliver`; `--dev`
includes every task file. A public reinstall removes obsolete manifest-owned
command-skill projections as well as private task commands.
Roles are projected to the
OMP agent schema: Claude model aliases are omitted so roles inherit the
user's configured model, tools map to OMP's canonical lowercase names, and
role preload skills become `autoloadSkills` naming only public installed
skills (each skill delivered once). The examiner and product owner have
Bash and record their values through their kind's `nwdes` CLI verbs and close;
their installed roles have no structured reply schema. Other roles that
declare `StructuredOutput` retain their canonical `output` projection. Scoped
tool grants have no OMP form and are omitted with an explicit report, never
widened. The Python runtime is installed at `~/.nwave/runtime`,
independently of Claude installation order. Missing Python 3.10+ refuses
installation with remediation; `--dry-run` prints the public populations
and runtime plan. Tool-call enforcement is not part of the delivery builder.
A named profile (`OMP_PROFILE`/`PI_PROFILE`) is refused: only the default
profile is served. Uninstall uses the recorded manifest ownership and keeps
foreign commands and extensions.

Delivery roles record values through their kind's `nwdes` CLI verbs from the
checkout's top level; roots default to cwd and the repository root, and lane
verbs resolve the main worktree. The first add, set or remove creates the draft.
Use `open --from-current` to revise current authority; close with no draft
validates empty values. The CLI constructs records and identifiers,
then publishes them at `close`; the host does not copy a JSON role reply into
an apply command. The examiner and product owner use the same CLI channel as
other delivery roles, with Bash available on Claude and OMP and shell enabled
on Codex. The native host invokes the installed role; nwdes constructs its
brief and does not launch models.

### Uninstallation

```bash
# Interactive uninstall with confirmation
python scripts/install/uninstall_nwave.py

# With backup before removal
python scripts/install/uninstall_nwave.py --backup

# Force uninstall without prompts
python scripts/install/uninstall_nwave.py --force

# Dry run
python scripts/install/uninstall_nwave.py --dry-run
```

### Update

```bash
# Interactive update
python scripts/install/update_nwave.py

# With comprehensive backup
python scripts/install/update_nwave.py --backup

# Automated update (no prompts)
python scripts/install/update_nwave.py --force --backup

# Dry run
python scripts/install/update_nwave.py --dry-run
```

### Backups

Backups are managed by `BackupManager` in `install_utils.py`. Every
`install_nwave.py` and `uninstall_nwave.py` run creates a timestamped
`~/.claude/backups/nwave-<type>-<timestamp>/` snapshot of the existing
agents/, commands/, and manifests. Retention keeps the most recent N
(default 10, override via `~/.nwave/global-config.json:backups.max_count`).

```bash
# Restore from the most recent nWave backup
python scripts/install/install_nwave.py --restore
```

## Features

### Cross-Platform Compatibility

- **Windows**: Full support with proper path handling
- **Mac**: Native support with macOS-specific adjustments
- **Linux/WSL**: Optimized for Unix-like systems

### Intelligent Building

- Automatically runs source embedding before build
- Detects when rebuild is needed (source newer than dist)
- Falls back to source agents if build incomplete
- Validates build output before installation

### Version Management

- Compares semantic versions for utility scripts
- Only upgrades when source is newer
- Preserves existing configurations
- Version-aware installation

### Backup & Recovery

- **Comprehensive Backups**: Agents, commands, config files
- **Conflict Detection**: Identifies framework conflicts (nWave vs SuperClaude)
- **Namespace Separation**: Implements `/sc/` and `/cai/` separation
- **Restoration Scripts**: Auto-generated bash restoration scripts
- **Backup Manifests**: JSON manifests with full metadata

### Validation

- Pre-installation checks (prerequisites, existing installation)
- Post-installation validation (essential files, counts)
- Update validation (before/after comparison)
- Uninstallation validation (complete removal)

## Installation Locations

```
~/.claude/
├── agents/nw/          # nWave specialized agents
├── commands/nw/        # nWave workflow commands
├── scripts/            # Utility scripts for target projects
│   ├── install_nwave_target_hooks.py
│   └── validate_step_file.py
├── templates/          # Canonical templates
├── backups/            # Installation backups
│   ├── pre_nwave_<timestamp>/
│   ├── nwave-install-<timestamp>/
│   ├── nwave-uninstall-<timestamp>/
│   ├── nwave-update-<timestamp>/
│   └── restore_scripts/
└── nwave-manifest.txt  # Installation manifest

~/.omp/agent/           # OMP target (config root renamed by PI_CONFIG_DIR)
├── agents/             # nWave task agents (native *.md + .nwave-agents-manifest.json)
└── skills/             # nWave skills (native <name>/SKILL.md + .nwave-manifest.json)
```

## Logs

All operations are logged to:
- `~/.claude/nwave-install.log` - Installation logs
- `~/.claude/nwave-uninstall.log` - Uninstallation logs
- `~/.claude/nwave-update.log` - Update logs
- `~/.claude/backup_system.log` - Backup system logs

## Error Handling

- Graceful degradation (continues when non-critical operations fail)
- Detailed error messages with context
- Backup preservation on failure
- Recovery guidance when operations fail

## Migration from Shell Scripts

The original shell scripts (`install-nwave.sh`, `uninstall-nwave.sh`, `update-nwave.sh`, `enhanced-backup-system.sh`) have been superseded by these Python versions.

**Advantages of Python versions**:
- Cross-platform (Windows support)
- Better error handling
- Consistent logging
- Easier to maintain
- Type-safe operations
- No dependency on bash/jq/sed/awk

**Shell scripts remain available** for backward compatibility but are no longer actively maintained.

## Requirements

- Python 3.7+
- No external dependencies (uses stdlib only)
- Optional: `jq` for restoration script JSON parsing (not required for Python scripts)

## Development

### Adding New Features

1. Add shared functionality to `install_utils.py`
2. Update individual scripts as needed
3. Maintain backward compatibility with CLI arguments
4. Add tests to verify cross-platform behavior

### Testing

```bash
# Test all scripts with dry-run
python scripts/install/install_nwave.py --dry-run
python scripts/install/uninstall_nwave.py --dry-run
python scripts/install/update_nwave.py --dry-run

```

## Troubleshooting

### Build Fails

- Check `tools/build.py` exists
- Verify Python 3.7+ is installed
- Check log files for detailed errors

### Installation Fails Validation

- Check `~/.claude/agents/nw/` exists
- Verify essential commands exist
- Review installation log

### Restoration Fails

- Ensure backup directory exists
- Check backup manifest is valid
- Verify restoration script has execute permissions

## Support

- GitHub Issues: https://github.com/nWave-ai/nWave/issues
- Documentation: https://github.com/nWave-ai/nWave

## License

Part of the nWave framework. See project LICENSE for details.
