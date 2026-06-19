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

Running a different editor or CLI? This guide also covers **OpenCode** and the **Codex CLI** further down, plus the plugin marketplace.

## CLI Installer (Recommended)

### Prerequisites

- **Python 3.10+**
- **Claude Code** installed
- **[uv](https://docs.astral.sh/uv/)** (recommended) or **[pipx](https://pipx.pypa.io/)** (supported, not recommended)

If you need uv:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```
See [uv installation docs](https://docs.astral.sh/uv/getting-started/installation/) for other platforms.

If you prefer pipx (supported fallback):
```bash
pip install pipx
pipx ensurepath
```

### One-line install

```bash
sh -c "$(curl -fsSL https://raw.githubusercontent.com/nWave-ai/nWave/main/scripts/install/install.sh)"
```

This bootstrap script picks a Python application installer, installs the
`nwave-ai` CLI with it, then runs `nwave-ai install` (and `nwave-ai doctor`) for
you. **uv is preferred**; **pipx is supported but not recommended**.

> **Use `sh -c "$(curl ...)"`, not `curl ... | sh`.** The `sh -c` form keeps your
> terminal on stdin so the script can prompt you. With `curl | sh`, stdin is the
> script itself and the confirmation prompt cannot work.

When it finishes, close and reopen Claude Code — the nWave agents and slash commands will appear in your command palette.

> **Windows users**: Use WSL (Windows Subsystem for Linux). Install with: `wsl --install`

### How the installer picks a tool

By default (`--tool auto`) the script chooses without asking when it safely can,
and only prompts when a non-recommended fallback is the sole option:

| Situation | What happens |
|-----------|--------------|
| `uv` is installed | Use `uv` (no prompt). |
| Only `pipx` is installed, **interactive** terminal | Warn that uv is recommended and ask to continue. **Yes** → use pipx. **No** → print uv install instructions and stop (exit 1). |
| Only `pipx` is installed, **non-interactive** (no TTY, e.g. CI) | Stop (exit 1) and print the three fixes: install uv, re-run with `--tool pipx`, or re-run with `--yes`. Bypass by passing `--yes` / `NWAVE_ASSUME_YES=1` (use pipx) or `--tool pipx` (explicit consent). |
| Neither is installed | Error (exit 1) with install instructions for uv (preferred) and pipx. |

Forcing a tool with `--tool uv` or `--tool pipx` skips the recommendation prompt
entirely. If the forced tool isn't installed, the script fails with that tool's
install instructions.

### Command-line flags

| Flag | Description |
|------|-------------|
| `-t`, `--tool <auto\|uv\|pipx>` | Installer to use. Default `auto` (uv preferred). Explicit `uv`/`pipx` is treated as consent and skips the prompt. |
| `-y`, `--yes` | Accept the pipx fallback without prompting. Useful for CI / non-interactive shells. |
| `-h`, `--help` | Print usage and exit. |

### Environment variables

Environment variables are the equivalent of the flags; a flag on the command
line overrides the matching variable.

| Variable | Equivalent | Effect |
|----------|-----------|--------|
| `NWAVE_INSTALLER_TOOL` | `--tool` | `auto` (default), `uv`, or `pipx`. |
| `NWAVE_ASSUME_YES` | `--yes` | Set to `1` (or `true`/`yes`) to accept the pipx fallback. |
| `NO_COLOR` | — | Set to any value to disable colored output. |

### Passing options through the one-liner

With the `sh -c "$(curl ...)"` form, put script options after a `--` separator:

```bash
# Force pipx even if uv is present (explicit consent — no prompt)
sh -c "$(curl -fsSL https://raw.githubusercontent.com/nWave-ai/nWave/main/scripts/install/install.sh)" -- --tool pipx

# Accept the pipx fallback without prompting (CI / non-interactive)
sh -c "$(curl -fsSL https://raw.githubusercontent.com/nWave-ai/nWave/main/scripts/install/install.sh)" -- --yes
```

The environment-variable form works too and needs no separator:

```bash
NWAVE_INSTALLER_TOOL=pipx NWAVE_ASSUME_YES=1 \
  sh -c "$(curl -fsSL https://raw.githubusercontent.com/nWave-ai/nWave/main/scripts/install/install.sh)"
```

### Exit codes

| Code | Meaning |
|------|---------|
| `0` | nWave installed and `nwave-ai doctor` reported no problems. Also returned when the `nwave-ai` CLI was installed but isn't on `PATH` yet — in that case `nwave-ai install` is deferred and you must run it manually after refreshing PATH (see "`nwave-ai` not found after install" below). |
| `1` | The installer could not proceed (neither tool present, a forced tool missing, pipx-only in a non-interactive shell without `--yes`, or you declined the pipx fallback) **or** installation finished but `nwave-ai doctor` reported a problem. |
| `2` | Usage error: unknown option, or a missing/invalid `--tool` value. |

After the package installs successfully, the script's exit code is the exit code
of `nwave-ai doctor` — so a non-zero result signals a genuine problem with the
installation, not a transient warning (doctor reports non-blocking warnings as a
passing check).

### Manual installation (step by step)

Prefer to run each step yourself instead of the bootstrap script? Pick a tool,
install the CLI, then install nWave into Claude Code.

**1. Install the `nwave-ai` CLI** with your preferred tool:

```bash
uv tool install nwave-ai     # recommended
pipx install nwave-ai        # supported
pip install nwave-ai         # plain pip
```

Don't have pipx? Install it with `pip install pipx && pipx ensurepath`.

**2. Install nWave into Claude Code:**

```bash
nwave-ai install
```

**3. Verify, then restart Claude Code:**

```bash
nwave-ai doctor
```

Close and reopen Claude Code — the nWave agents and slash commands appear in your command palette.

### `nwave-ai` not found after install

If installation succeeds but the `nwave-ai` command isn't found, your tool's bin
directory (usually `~/.local/bin`) isn't on `PATH` yet:

```bash
uv tool update-shell     # if you installed with uv
pipx ensurepath          # if you installed with pipx
```

Open a new shell, then finish with `nwave-ai install`.

### `nwave-ai install` options

These flags belong to the `nwave-ai` CLI (run after the package is installed),
not to the bootstrap script above:

| Command | Purpose |
|---------|---------|
| `nwave-ai install --dry-run` | Preview changes without installing |
| `nwave-ai install --backup-only` | Backup without installing |
| `nwave-ai install --restore` | Restore from recent backup |
| `nwave-ai version` | Show installed version |

## Installing for OpenCode

nWave also works with [OpenCode](https://github.com/opencode-dev/opencode), an open-source IDE for AI pair programming. Installation needs a few extra steps to configure OpenCode's environment.

**1. Install prerequisites:**
```bash
npm install -g opencode-ai
uv tool install nwave-ai        # or: pipx install nwave-ai
```

**2. Configure OpenCode:**
```bash
mkdir -p ~/.config/opencode
echo '{"model": "openai/gpt-4o-mini"}' > ~/.config/opencode/opencode.json
```

**3. Set your OpenAI API key:**
```bash
export OPENAI_API_KEY=your-key-here
```

**4. Install nWave into OpenCode:**
```bash
nwave-ai install
```

**Compatibility notes:**
- About 67% of nWave features work natively on OpenCode via compatibility paths.
- DES hooks integrate via OpenCode's `tool.execute.before` mechanism.
- Some advanced subagent coordination may differ from Claude Code. Use the core `/nw-discuss`, `/nw-design`, `/nw-distill`, `/nw-deliver` commands for best results.
- For full feature parity and support, Claude Code remains the primary environment.

## Installing for Codex CLI

nWave integrates with the [OpenAI Codex CLI](https://platform.openai.com/docs/guides/codex) via pre-tool-use hooks. Once installed, every Bash and file-edit action fires nWave's DES validation — the same enforcement that runs on Claude Code.

**Prerequisites:**
- OpenAI Codex CLI installed (`codex` binary on `PATH`) or a `~/.codex/` directory present
- Python 3.10+

**Auto-detect installation (recommended):**
```bash
uv tool install nwave-ai    # or, as a fallback: pipx install nwave-ai
nwave-ai install            # auto-detects Codex + installs hooks
```

**Explicit Codex installation:**
```bash
nwave-ai install --platform codex
```

**What gets written:** nWave creates `~/.codex/hooks.json` with an event-keyed structure:
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "^Bash$|^apply_patch$",
        "hooks": [
          {
            "type": "command",
            "command": "python -m des.adapters.drivers.hooks.claude_code_hook_adapter pre-tool-use"
          }
        ]
      }
    ]
  }
}
```

**Verify installation succeeded:**
```bash
cat ~/.codex/hooks.json | jq '.hooks.PreToolUse | length'
# Expected output: 1 (or higher if you have other hook entries)
```

**Troubleshooting:**

- **"Codex not detected"** — Check `which codex` and `ls ~/.codex/`. To force install before the Codex binary exists, use `--platform codex`. You'll need to install Codex separately before hooks will fire.
- **"Hook fires but audit log empty"** — Verify `~/.claude/des-audit.jsonl` is writable and `~/.claude/lib/python/des/` exists. Run a Codex action and check the log: `tail -5 ~/.claude/des-audit.jsonl | jq .`
- **"Codex says hook not loaded"** — Ensure `hooks.json` uses the event-keyed format above (not a legacy top-level array). Reinstall with `nwave-ai install --platform codex --force` if in doubt.

For detailed setup and workflow, see **[Installing for Codex CLI](../installing-codex.md)**.

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
├── skills/nw-*/               # 197 agent skill files (flat layout)
├── scripts/                   # DES utilities
├── lib/python/des/            # DES runtime imported by hooks
└── settings.json              # DES hooks (5 events: PreToolUse, SessionStart, SubagentStart, SubagentStop, PostToolUse)
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

**CLI method (uv, recommended):**
```bash
uv tool upgrade nwave-ai
nwave-ai install
```

**CLI method (pipx, fallback):**
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

**CLI method (uv, recommended):**
```bash
nwave-ai uninstall              # Removes agents, commands, config, DES hooks from ~/.claude/
uv tool uninstall nwave-ai     # Removes the nwave-ai Python package itself
```

**CLI method (pipx, fallback):**
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

### uv Issues

If `uv tool` commands fail:

```bash
# Verify uv is installed
uv --version

# Ensure the uv tool bin dir is on PATH
uv tool update-shell      # then restart your shell

# If uv is missing, reinstall it
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### pipx Issues

If pipx commands fail (pipx is a supported fallback):

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
2. Reinstall nWave (uv, recommended):

```bash
uv tool uninstall nwave-ai
uv tool install nwave-ai
nwave-ai install
```

Or via pipx (fallback):

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
