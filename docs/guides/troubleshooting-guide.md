# nWave Troubleshooting Guide

**Version**: 2.0.0
**Date**: 2026-02-13
**Status**: Production Ready

---

## Quick Diagnostic

```bash
echo "Agents: $(ls ~/.claude/agents/nw/ 2>/dev/null | wc -l) files"
echo "Commands: $(ls ~/.claude/commands/nw/ 2>/dev/null | wc -l) files"
python3 --version
```

If agents or commands show 0, reinstall: `nwave-ai install`

---

## Installation

### `pipx: command not found`

**Cause**: `pipx` is not installed. Don't confuse it with `pip` or `pipenv` — they are different tools.

**Fix**:
```bash
pip install pipx
pipx ensurepath
```
Restart your terminal, then retry `pipx install nwave-ai`.

> **Windows users**: Use WSL (Windows Subsystem for Linux), not PowerShell. Native Windows is not supported.

### Commands not recognized (`/nw:discuss` not found)

**Cause**: Framework not installed or Claude Code not restarted after install.

**Fix**:
```bash
nwave-ai install
```
Then close and reopen Claude Code.

### Installation fails

**Cause**: Missing Python 3, permission issues, or corrupted state.

**Fix**:
```bash
# Check Python
python3 --version

# Check permissions
ls -la ~/.claude/

# Clean reinstall
nwave-ai uninstall --backup --force
nwave-ai install
```

### Partial installation (some agents missing)

**Cause**: Interrupted install or file permission mismatch.

**Fix**:
```bash
nwave-ai uninstall --backup --force
nwave-ai install
```

---

## Agent Issues

### Agent gives generic responses (no persona)

**Cause**: Agent specification file missing or not loaded.

**Fix**: Verify agent files exist:
```bash
ls ~/.claude/agents/nw/nw-*.md | wc -l
# Expected: 22 files (11 primary + 11 reviewers)
```

If missing, reinstall: `nwave-ai install`

---

## Platform-Specific

### WSL: Path or permission errors

**Fix**:
```bash
chmod -R 755 ~/.claude/agents/nw/
chmod -R 755 ~/.claude/commands/nw/
```

### macOS: Python version conflicts

**Fix**: Ensure `python3` points to 3.10+:
```bash
python3 --version
which python3
```

### Windows: `No Python at 'c:\pythonXX\python.exe'`

**Cause**: pipx was installed with an older Python version that has since been
removed or upgraded. pipx still points to the old path.

**Fix**: Reinstall pipx with your current Python:
```bash
py -m pip install --force-reinstall pipx
pipx ensurepath
```

### Windows: Native Windows is not supported

nWave requires WSL (Windows Subsystem for Linux). The install and agents
will not work in cmd.exe or PowerShell.

```bash
wsl --install
# Then open a WSL terminal and run:
pipx install nwave-ai
nwave-ai install
```

---

## Recovery

### Complete reset

```bash
nwave-ai uninstall --backup
nwave-ai install
```

### Restore from backup

```bash
ls ~/.claude/backups/
nwave-ai install --restore
```

---

## Getting Help

1. Run the quick diagnostic at the top of this page
2. Try reinstalling (`nwave-ai install`)
3. If the issue persists:
   - **Discord**: [nWave Community](https://discord.gg/DeYdSNk6)
   - **GitHub Issues**: [github.com/nWave-ai/nWave/issues](https://github.com/nWave-ai/nWave/issues)

Include in your report: diagnostic output, error messages, OS, and Python version.

---

**Last Updated**: 2026-02-13
**Type**: How-to Guide
