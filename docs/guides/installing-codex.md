# Installing nWave for Codex CLI

## Goal

After this guide, every Bash and apply_patch tool invocation by OpenAI Codex CLI fires the nWave DES PreToolUse hook, producing audit-log entries you can inspect and verify.

## Prerequisites

- **Python 3.10 or later** — Check with `python3 --version`
- **pipx or uv** — Package installer. Install with:
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh    # uv
  # or
  python3 -m pip install pipx && pipx ensurepath      # pipx
  ```
- **OpenAI Codex CLI** — Download from [platform.openai.com/docs/guides/codex](https://platform.openai.com/docs/guides/codex) and install per OpenAI's instructions. Verify with `which codex` or `ls ~/.codex/`.

## Install

### Step 1: Install nWave CLI

```bash
pipx install nwave-ai
# or
uv tool install nwave-ai
```

### Step 2: Auto-detect and install into Codex

```bash
nwave-ai install
```

The installer automatically detects if Codex is present and wires the DES PreToolUse hook. If you see "DES hook installed successfully", you're ready to proceed.

**Explicit Codex installation** (if auto-detect doesn't find Codex):
```bash
nwave-ai install --platform codex
```

### Step 3: Verify installation

```bash
nwave-ai doctor
```

Expected output: confirmation that DES hooks are installed and writable.

## What Got Installed

| Path | Purpose |
|------|---------|
| `~/.codex/hooks.json` | Event-keyed Codex hook configuration |
| `~/.claude/lib/python/des/` | nWave DES validation module |
| `~/.claude/des-audit.jsonl` | Audit log (created on first hook fire) |

## End-to-End Smoke Test

Verify the installation is wired correctly by running a real Codex session and inspecting the audit log.

### Step 1: Start a Codex session
```bash
codex
# or: OPENAI_API_KEY=your-key codex
```

### Step 2: Run a Bash action
In Codex, invoke a simple Bash command (e.g., `ls /tmp` or `echo hello`).

### Step 3: Check the audit log
```bash
cat ~/.claude/des-audit.jsonl | jq 'select(.event == "HOOK_INVOKED" and .handler == "pre_tool_use")' | head -3
```

**Expected output:** At least one JSON object with:
```json
{
  "event": "HOOK_INVOKED",
  "handler": "pre_tool_use",
  "timestamp": "2026-05-14T...",
  ...
}
```

If you see this entry, DES enforcement is wired and working. If the log file is empty or missing, check the troubleshooting section below.

## Uninstall

To remove nWave DES hooks from Codex while preserving any custom hook entries:

```bash
nwave-ai uninstall
```

Or manually:
```bash
rm ~/.codex/hooks.json ~/.codex/.nwave-des-manifest.json
```

To remove nWave entirely:
```bash
nwave-ai uninstall
pipx uninstall nwave-ai    # or: uv tool uninstall nwave-ai
```

## Common Issues

### Legacy schema (top-level array)

**Symptom:** `~/.codex/hooks.json` is a JSON array `[...]` instead of an object `{...}`.

**Root cause:** Pre-FM-1 nWave version wrote the legacy schema that Codex doesn't recognize.

**Fix:** Reinstall to repair:
```bash
nwave-ai install --platform codex --force
```

### Missing `pre-tool-use` argv token

**Symptom:** Hook fires but exits with code 1 and produces no audit-log entry. Codex shows no validation output.

**Root cause:** Pre-FM-2 nWave version didn't include the required `pre-tool-use` argument to the hook command.

**Fix:** Upgrade to v3.15+:
```bash
pipx upgrade nwave-ai    # or: uv tool upgrade nwave-ai
nwave-ai install --platform codex --force
```

### Fictional `Task` tool in matcher

**Symptom:** `~/.codex/hooks.json` contains a regex with `Task` in it (e.g., `^Task$|^Bash$`), but Codex never fires the hook for `Task` because Codex doesn't emit that tool name.

**Root cause:** Pre-FM-3 nWave version mirrored the Claude Code plugin without reading Codex's actual tool registry.

**Fix:** Upgrade to v3.15+:
```bash
pipx upgrade nwave-ai
nwave-ai install --platform codex --force
```

### Hook didn't fire / audit log is empty

**Check 1: Verify hooks.json has the right schema**
```bash
jq '.hooks | keys' ~/.codex/hooks.json
# Expected output: ["PreToolUse"]
```

**Check 2: Verify the matcher regex**
```bash
jq -r '.hooks.PreToolUse[0].matcher' ~/.codex/hooks.json
# Expected output: ^Bash$|^apply_patch$ (or similar Codex tool names, not Task)
```

**Check 3: Verify the hook command is present**
```bash
jq -r '.hooks.PreToolUse[0].hooks[0].command' ~/.codex/hooks.json
# Expected output: command string ending with "pre-tool-use"
```

**Check 4: Verify the audit log directory is writable**
```bash
touch ~/.claude/des-audit.jsonl
# Should succeed without permission errors
```

**Check 5: Verify the DES module is installed**
```bash
python3 -c "from des.adapters.drivers.hooks import claude_code_hook_adapter; print('DES module OK')"
# If this fails, reinstall: nwave-ai install --force
```

If all checks pass but the audit log is still empty after running a Codex action, file a bug report with the output of `nwave-ai doctor`.

### "PYTHONPATH environment variable" warnings

**Symptom:** Codex shows warnings about PYTHONPATH when the hook fires.

**Cause:** nWave sets PYTHONPATH to resolve the DES module. This is normal and safe.

**Action:** No action needed. The warnings can be ignored.

## Earned Trust: Verify Your Installation

nWave's test suite includes an end-to-end test that validates the exact install contract you just completed:

```bash
# Clone the nWave repository (if you have a development setup)
git clone https://github.com/nWave-ai/nWave.git
cd nWave
python -m pytest tests/e2e/test_codex_real_boot.py -v
```

If both tests pass (one for Bash, one for legacy schema rejection), your installation is empirically verified. Two GREEN tests prove the wiring contract holds end-to-end.

## References

- **Codex hooks documentation**: [developers.openai.com/codex/hooks](https://developers.openai.com/codex/hooks)
- **nWave architecture**: See the [Architecture Guide](../architecture/) for details on DES enforcement and hook contracts
- **Feature validation**: Codex support was delivered in Epic `codex-empirical-e2e-support` (2026-05-13). See [`docs/feature/codex-empirical-e2e-support/feature-delta.md`](../feature/codex-empirical-e2e-support/feature-delta.md) for the complete specification.
