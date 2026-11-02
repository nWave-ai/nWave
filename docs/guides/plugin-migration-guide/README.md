# Migration Guide: Custom Installer to Plugin

> **Historical route.** The plugin marketplace installation below is not the
> current installation path; the supported route is the `nwave-ai` package
> and its installer (see the
> [installation guide](../installation-guide/README.md)). This page is kept
> for readers who used the marketplace plugin while it existed.

## Overview

nWave supported two installation methods:

1. **Custom installer** (`nwave-ai install`) — installs to `~/.claude/`
2. **Plugin** — installs to `~/.claude/plugins/cache/nwave/`

Both could coexist. This guide documents how to migrate from the custom
installer to the plugin.

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
claude plugin install nw --marketplace https://github.com/nWave-ai/nwave-plugin
```

## Step 2: Verify Plugin Works

Run a quick verification:

```bash
/nw-deliver "test-feature"
```

Verify:
- Agent discovery works (agents loaded from plugin)
- Commands available (`/nw-` prefix works)

## Step 3: Remove Custom Installer (Optional)

If you want to fully migrate:

```bash
nwave-ai uninstall
```

This removes:
- `~/.claude/agents/nw/`
- `~/.claude/commands/nw/`
- `~/.claude/skills/nw/`

The plugin remains unaffected because it uses a completely separate directory tree.

## Coexistence Notes

- **Path separation**: Plugin files live in `~/.claude/plugins/cache/nwave/`, custom installer files in `~/.claude/agents/nw/` etc. No overlap.
- **Hook isolation**: Plugin hooks are in `plugin/hooks/hooks.json`, installer hooks in `~/.claude/settings.json`. Claude Code merges them.
- **Version conflicts**: If both are active with different versions, Claude Code uses the plugin version. No errors, but may see duplicate agents in autocomplete.
- **Recommendation**: Run one installation method at a time for cleanest experience.

## Verification Checklist

After migration, verify:
- [ ] `/nw-deliver` executes successfully
- [ ] The host runs the delivery's declared verification commands and records their results
- [ ] Agent definitions are discovered (compare with the [agents index](../../reference/agents/index.md), not a fixed count)
- [ ] All commands available (`/nw-design`, `/nw-discuss`, etc.)
- [ ] Skills load on demand (check agent output references skills)

## Rollback

To rollback to custom installer:
1. Remove plugin: `claude plugin uninstall nw`
2. Reinstall custom: `nwave-ai install`
