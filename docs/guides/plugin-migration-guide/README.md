# Migration Guide: Custom Installer to Plugin

## Overview

nWave supports two installation methods:
1. **Custom installer** (`nwave install`) -- installs to `~/.claude/`
2. **Plugin** -- installs to `~/.claude/plugins/cache/nwave/`

Both can coexist. This guide documents how to migrate from the custom installer to the plugin.

## Prerequisites

- Claude Code v1.x or later (with plugin support)
- Existing nWave custom installation (optional)

## Step 1: Install the Plugin

### From Anthropic Marketplace

```bash
claude plugin install nw
```

### From Self-Hosted Marketplace

```bash
claude plugin install nw --marketplace https://github.com/nwave-ai/nwave-plugin
```

## Step 2: Verify Plugin Works

Run a quick verification:

```bash
/nw-deliver "test-feature"
```

Verify:
- Agent discovery works (agents loaded from plugin)
- DES enforcement active (hook responses visible)
- Commands available (`/nw-` prefix works)

## Step 3: Remove Custom Installer (Optional)

If you want to fully migrate:

```bash
nwave uninstall
```

This removes:
- `~/.claude/agents/nw/`
- `~/.claude/commands/nw/`
- `~/.claude/skills/nw/`
- `~/.claude/lib/python/des/`
- DES hooks from `~/.claude/settings.json`

The plugin remains unaffected because it uses a completely separate directory tree.

## Coexistence Notes

- **Path separation**: Plugin files live in `~/.claude/plugins/cache/nwave/`, custom installer files in `~/.claude/agents/nw/` etc. No overlap.
- **Hook isolation**: Plugin hooks are in `plugin/hooks/hooks.json`, installer hooks in `~/.claude/settings.json`. Claude Code merges them.
- **Version conflicts**: If both are active with different versions, Claude Code uses the plugin version. No errors, but may see duplicate agents in autocomplete.
- **Recommendation**: Run one installation method at a time for cleanest experience.

## Verification Checklist

After migration, verify:
- [ ] `/nw-deliver` executes successfully
- [ ] DES enforcement blocks incorrect tool use during TDD phases
- [ ] Agent definitions are discovered (23 agents visible)
- [ ] All commands available (`/nw-design`, `/nw-discuss`, etc.)
- [ ] Skills load on demand (check agent output references skills)

## Rollback

To rollback to custom installer:
1. Remove plugin: `claude plugin uninstall nw`
2. Reinstall custom: `nwave install`
