# Troubleshooting Guide

Quick fixes for common nWave issues. The checks below inspect the Claude
Code installation; on Codex, OpenCode, OMP, Cursor, Copilot or Devin, use
the installer's own final validation and the
[per-host guides](../vendor-support.md) instead.

## Diagnostic Quick Check (Claude Code)

```bash
echo "Agents: $(ls ~/.claude/agents/nw/ 2>/dev/null | wc -l)"
echo "Commands: $(ls ~/.claude/commands/nw/ 2>/dev/null | wc -l)"
python3 --version
nwave-ai doctor
```

If agents or commands show 0, run: `nwave-ai install`, then restart Claude
Code. The exact agent count changes between releases — compare what you see
with the [agents index](../../reference/agents/index.md), not with a fixed
number.

---

## Installation Issues

### `uv: command not found`

**Cause**: `uv` is not installed. uv is the recommended installer for nwave-ai (pipx remains a supported fallback).

**Fix**:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```
Restart your terminal, then retry `uv tool install nwave-ai`. See [uv installation docs](https://docs.astral.sh/uv/getting-started/installation/) for other platforms.

### `pipx: command not found`

**Cause**: `pipx` is not installed. Don't confuse it with `pip` or `pipenv` — they are different tools. (pipx is supported as a fallback when uv is not available.)

**Fix**:
```bash
pip install pipx
pipx ensurepath
```
Restart your terminal, then retry `pipx install nwave-ai`.

> **Windows users**: Use WSL (Windows Subsystem for Linux), not PowerShell. Native Windows is not supported.

### Commands not recognized (`/nw-discuss` not found)

**Cause**: Framework not installed or Claude Code not restarted after install.

**Fix**:
```bash
nwave-ai install
```
Then close and reopen Claude Code.

### Doctor fails (Claude Code)

Run `nwave-ai doctor` and read the failing check's diagnostic line; each
line names the check that failed (for example `python_version`,
`framework_files`, `hooks_registered`, `config_ssot`, `version_sync`).
`doctor --fix` is not implemented — address the named check and rerun
`nwave-ai install --platform claude-code` and `doctor`, then restart Claude
Code. Doctor checks Claude Code assets: on a host-only install it can fail
without anything being broken; use that host's installer validation instead.

### Installation fails

**Cause**: Missing Python 3.11+, permission issues, or corrupted state.

**Fix**:
```bash
# Check Python (3.11 or newer required)
python3 --version

# Check permissions
ls -la ~/.claude/

# Clean reinstall
nwave-ai uninstall
nwave-ai install
```

### Partial installation (some agents missing)

**Cause**: Interrupted install or file permission mismatch.

**Fix**:
```bash
nwave-ai uninstall
nwave-ai install
```

### Both uv and pipx installed — wrong one being picked

**Symptom**: `nwave-ai plugin install <name>` is calling `pipx` (or `uv`) when you wanted the other one. Or you see two parallel virtual environments for nwave-ai itself.

**Cause**: nwave-ai picks the package manager that originally installed it (mirroring sys.executable). If both uv and pipx exist on your PATH and you installed via the non-default one, the auto-detection may miss it — for example if you set a custom `UV_TOOL_DIR`.

**Fix**: Set the `NWAVE_INSTALLER` environment variable to force a choice:

```bash
# Force uv for this shell:
export NWAVE_INSTALLER=uv
nwave-ai plugin install dedup

# Or one-shot:
NWAVE_INSTALLER=pipx nwave-ai plugin install dedup
```

Valid values: `uv`, `pipx`, `pip`. The override is honored only when the named tool is on PATH; otherwise nWave-ai falls back to auto-detection.

### Uninstall left files behind

Read the uninstaller's actual path report. Use `nwave-ai uninstall` from the
environment that owns the package, then inspect only the reported nWave-owned
assets. Preserve custom skills and unrelated host configuration. Remove the CLI
package separately with the package manager that installed it.

For a v3 installation, use its matching runtime and recovery instructions.
Updating the current package does not convert its delivery artifacts; see the
[migration guide](../migrating-from-3x.md).

---

## Agent Issues

### Agent gives generic responses (not adopting persona)

**Cause**: Agent specification files missing or not loaded.

**Fix**: Verify agent files exist and compare them with the
[agents index](../../reference/agents/index.md):

```bash
ls ~/.claude/agents/nw/nw-*.md | wc -l
```

If files are missing: `nwave-ai install`, then restart Claude Code.

---

## Platform-Specific Issues

### WSL: Path or permission errors

**Fix**:
```bash
chmod -R 755 ~/.claude/agents/nw/
chmod -R 755 ~/.claude/commands/nw/
```

### macOS: Python version conflicts

**Fix**: Ensure `python3` points to 3.11+:
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
curl -LsSf https://astral.sh/uv/install.sh | sh    # install uv first
uv tool install nwave-ai                            # or: pipx install nwave-ai
nwave-ai install
```

---

## Recovery

### Complete reset
```bash
nwave-ai uninstall
nwave-ai install
```

### Restore from backup

```bash
nwave-ai install --restore
```

`--backup-only` snapshots the Claude Code and Codex installations;
`--restore` restores the Claude Code snapshot (on a Codex-only install it
currently finds nothing to restore). No backup or restore exists for
OpenCode, Cursor, Copilot, OMP or Devin.

---

## Need More Help

1. Run the diagnostic above
2. Try: `nwave-ai install`
3. If still stuck:
   - **Discord**: [nWave Community](https://discord.gg/Cywj3uFdpd)
   - **GitHub**: [Report issue](https://github.com/nWave-ai/nWave/issues)

Include: diagnostic output, error message, OS, and Python version.
