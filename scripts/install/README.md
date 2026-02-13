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

4. **`enhanced_backup_system.py`** - Advanced backup system
   - Framework conflict detection (SuperClaude vs nWave)
   - Namespace separation implementation
   - Restoration script generation
   - Comprehensive backup manifests

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

# Create backup only
python scripts/install/install_nwave.py --backup-only

# Restore from latest backup
python scripts/install/install_nwave.py --restore
```

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

### Enhanced Backup System

```bash
# Create comprehensive backup
python scripts/install/enhanced_backup_system.py backup

# List available backups
python scripts/install/enhanced_backup_system.py list

# Restore from specific backup
python scripts/install/enhanced_backup_system.py restore 20250121_143022

# Show backup system status
python scripts/install/enhanced_backup_system.py status
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
├── templates/          # Canonical schemas
│   └── step-tdd-cycle-schema.json
├── backups/            # Installation backups
│   ├── pre_nwave_<timestamp>/
│   ├── nwave-install-<timestamp>/
│   ├── nwave-uninstall-<timestamp>/
│   ├── nwave-update-<timestamp>/
│   └── restore_scripts/
└── nwave-manifest.txt  # Installation manifest
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

# Test backup system
python scripts/install/enhanced_backup_system.py status
python scripts/install/enhanced_backup_system.py list
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
