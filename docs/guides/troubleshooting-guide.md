# nWave Framework Troubleshooting Guide

## Quick Diagnostic

If you're experiencing issues with nWave, run this quick diagnostic first:

```bash
# Quick system check
echo "=== nWave Quick Diagnostic ==="
echo "Installation: $(ls ~/.claude/agents/nw/ 2>/dev/null && echo 'OK' || echo 'MISSING')"
echo "Commands: $(ls ~/.claude/commands/nw/ 2>/dev/null | wc -l) found"
```

## Installation Issues

### Framework Not Found

**Symptoms**:

- Commands like `/nw:discuss` not recognized
- No agents directory found
- Missing framework files

**Solutions**:

```bash
# Check installation
ls ~/.claude/agents/nw/ ~/.claude/commands/nw/

# If missing, reinstall
./scripts/install-nwave.sh

# If install fails, check source
ls nWave/agents/
```

### Installation Fails

**Common Causes**:

1. **Missing source files**
2. **Permission issues**
3. **Python not available for settings merge**

**Debug Steps**:

```bash
# Check source framework
ls nWave/agents/

# Check permissions
ls -la ~/.claude/

# Test with backup
./scripts/install-nwave.sh --backup-only

# Check Python availability
python3 --version
```

### Partial Installation

**Symptoms**:

- Some components missing
- Validation errors during install
- Incomplete functionality

**Solutions**:

```bash
# Uninstall and reinstall
./scripts/uninstall-nwave.sh --backup --force
./scripts/install-nwave.sh

# Check validation logs
cat ~/.claude/nwave-install.log
```

## Command Issues

### DW Commands Not Found

**Symptoms**:

- `/nw:discuss` command not recognized
- Commands not available in Claude Code
- Command completion not working

**Solutions**:

```bash
# Check command installation
ls ~/.claude/commands/nw/

# Expected commands
cat ~/.claude/commands/nw/start.md

# Reinstall commands
./scripts/install-nwave.sh
```

### Command Execution Errors

**Debug Steps**:

```bash
# Check command files
ls -la ~/.claude/commands/nw/

# Check permissions
find ~/.claude/commands/nw/ -name "*.md" -ls

# Verify command structure
head -20 ~/.claude/commands/nw/start.md
```

## Agent Issues

### Agents Not Responding

**Symptoms**:

- Agent selection not working
- No agent-specific behavior
- Generic responses only

**Solutions**:

```bash
# Check agent installation
ls ~/.claude/agents/nw/

# Verify agent files
head -20 ~/.claude/agents/nw/solution-architect.md
```

### Agent Context Issues

**Debug Steps**:

```bash
# Check agent specifications
ls ~/.claude/agents/nw/

# Verify agent organization
find ~/.claude/agents/nw/ -name "*.md" | wc -l
```

## Environment Issues

### WSL/Linux Issues

**Common Problems**:

- Path issues between Windows and WSL
- Permission mismatches
- Tool installation conflicts

**Solutions**:

```bash
# Check environment
echo $PATH
which python3 pip3

# Fix WSL permissions
sudo chmod -R 755 ~/.claude/agents/nw/
sudo chmod -R 755 ~/.claude/commands/nw/
```

### macOS Issues

**Common Problems**:

- Homebrew tool conflicts
- Python version issues
- Permission restrictions

**Solutions**:

```bash
# Check Python version
python3 --version
which python3

# Fix permissions
chmod -R 755 ~/.claude/agents/nw/
chmod -R 755 ~/.claude/commands/nw/
```

### Windows Issues

**Note**: Use WSL for Windows environments.

**Setup WSL**:

```bash
# Enable WSL in Windows
wsl --install

# Install nWave in WSL
cd /mnt/c/path/to/nwave
./scripts/install-nwave.sh
```

## Comprehensive Diagnostics

### Full System Check

```bash
#!/bin/bash
echo "=== nWave Comprehensive Diagnostic ==="
echo "Date: $(date)"
echo "User: $(whoami)"
echo "System: $(uname -a)"
echo ""

echo "=== Environment ==="
echo "PATH: $PATH"
echo "Shell: $SHELL"
echo ""

echo "=== Installation Check ==="
echo "Agents: $(ls ~/.claude/agents/nw/ 2>/dev/null | wc -l) agent files"
echo "Commands: $(ls ~/.claude/commands/nw/ 2>/dev/null | wc -l) commands"
echo ""

echo "=== Tool Availability ==="
for tool in python3 pip3; do
    if command -v "$tool" >/dev/null 2>&1; then
        echo "$tool: $(which $tool)"
    else
        echo "$tool: NOT FOUND"
    fi
done
echo ""

echo "=== Recent Logs ==="
tail -5 ~/.claude/nwave-install.log 2>/dev/null || echo "No install log found"
```

### Log Collection

```bash
# Collect comprehensive logs for support
{
    echo "=== nWave Support Information ==="
    echo "Generated: $(date)"
    echo "Version: $(head -5 ~/.claude/nwave-manifest.txt 2>/dev/null)"
    echo ""

    # Run full diagnostic
    bash comprehensive_diagnostic.sh

    echo ""
    echo "=== Recent Error Logs ==="
    find ~/.claude/ -name "*.log" -mtime -1 -exec echo "=== {} ===" \; -exec tail -10 {} \; 2>/dev/null

} > nwave-support-$(date +%Y%m%d-%H%M%S).log

echo "Support information collected in: nwave-support-$(date +%Y%m%d-%H%M%S).log"
```

## Getting Help

### Before Reporting Issues

1. **Run Quick Diagnostic**: Use the quick diagnostic at the top of this document
2. **Try Reinstallation**: Often fixes configuration issues
3. **Check Documentation**: Review `README.md`

### Reporting Issues

Include this information:

1. **Output of quick diagnostic**
2. **Complete error messages**
3. **Steps to reproduce the issue**
4. **Your environment details (OS, shell, Python version)**
5. **Recent changes to your system**

### Support Resources

- **Discord Community**: [Join the nWave Discord](https://discord.gg/DeYdSNk6) - Get help, share success stories, and connect with other users
- **Documentation**: `README.md`
- **GitHub Issues**: [https://github.com/nWave-ai/nWave/issues](https://github.com/nWave-ai/nWave/issues)
- **Installation Logs**: `~/.claude/nwave-install.log`
- **Backup Recovery**: `./scripts/install-nwave.sh --restore`

## Recovery Procedures

### Complete Reset

If all else fails, perform a complete reset:

```bash
# 1. Backup current state
./scripts/uninstall-nwave.sh --backup

# 2. Clean installation
./scripts/install-nwave.sh

# 3. Test functionality
ls ~/.claude/agents/nw/
ls ~/.claude/commands/nw/
```

### Restore from Backup

```bash
# List available backups
ls ~/.claude/backups/

# Restore from backup
./scripts/install-nwave.sh --restore
```

---

**Remember**: Most issues can be resolved by reinstallation if needed.
