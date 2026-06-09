# Troubleshooting Guide

Quick fixes for common nWave issues.

## Diagnostic Quick Check

```bash
echo "Agents: $(ls ~/.claude/agents/nw/ 2>/dev/null | wc -l)"
echo "Commands: $(ls ~/.claude/commands/nw/ 2>/dev/null | wc -l)"
python3 --version
```

If agents or commands show 0, run: `nwave-ai install`

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

Valid values: `uv`, `pipx`, `pip`. The override is honored only when the named tool is on PATH; otherwise nwave-ai falls back to auto-detection.

### Uninstall left files behind (fixed in v3.14)

**Symptom**: After running `nwave-ai uninstall --force` (v3.13.x or earlier), the uninstaller reported success but the following remained on disk:

- `~/.claude/skills/nw-*` directories (~197 dirs)
- `~/.claude/lib/python/des/` runtime
- 3 specific hook entries in `~/.claude/settings.json`: one with the `des-hook:pre-bash` prefix (matcher: `Bash`), and two `claude_code_hook_adapter` entries under `SessionStart` and `SubagentStart` events. (DES installs hooks across 5 event types total — `PreToolUse`, `SubagentStop`, `PostToolUse`, `SessionStart`, `SubagentStart` — but only the first three were correctly removed pre-fix.)

**Cause**: install/uninstall path drift — the installer wrote to `skills/nw-<name>/` (flat), the uninstaller searched the obsolete `skills/nw/` (nested); `lib/python/des/` was never targeted; and the hook removal iterated only 3 of the 5 registered event types (missing `SessionStart` and `SubagentStart`) plus its hook-detection pattern matched only `claude_code_hook_adapter`, not the shell-prefix `des-hook:` form used by the inline `Bash` matcher.

**Fix (v3.14.0-rc1)**: upgrade and re-run uninstall — it now removes all three classes correctly while preserving any non-`nw-` prefixed skills you created. Background: GitHub issue #39.

```bash
uv tool upgrade nwave-ai    # or: pipx upgrade nwave-ai
nwave-ai uninstall --force
# Verify residuals are gone:
ls ~/.claude/skills/nw-* 2>/dev/null | wc -l    # expected 0
ls ~/.claude/lib/python/des 2>/dev/null         # expected: not found
grep -c 'des\.' ~/.claude/settings.json 2>/dev/null  # expected 0
```

If you uninstalled under v3.13 and never re-installed, manually remove the leftover paths above — your custom skills (no `nw-` prefix) are untouched.

---

## Agent Issues

### Agent gives generic responses (not adopting persona)

**Cause**: Agent specification files missing or not loaded.

**Fix**: Verify agent files exist:
```bash
ls ~/.claude/agents/nw/nw-*.md | wc -l
```

Expected: 22 files (11 primary + 11 reviewers). If missing: `nwave-ai install`

---

## Platform-Specific Issues

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
curl -LsSf https://astral.sh/uv/install.sh | sh    # install uv first
uv tool install nwave-ai                            # or: pipx install nwave-ai
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
nwave-ai install --restore
```

---

## Need More Help

1. Run the diagnostic above
2. Try: `nwave-ai install`
3. If still stuck:
   - **Discord**: [nWave Community](https://discord.gg/Cywj3uFdpd)
   - **GitHub**: [Report issue](https://github.com/nWave-ai/nWave/issues)

Include: diagnostic output, error message, OS, and Python version.
