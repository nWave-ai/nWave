# Vendor support

What the nWave installer deploys on each host, how deeply each install is
verified, and what you do and do not get compared with Claude Code. For
install steps, see the per-host guides.

**DES**, where the name appears below, is the name of nWave's predecessor
delivery runtime (the name is historical; nWave documents no expansion of
it). v4 retires it: the source tree is removed, doctor no longer checks a
DES module, and the installer writes no runtime copy. Delivery runs through
`nwdes`.

## What each platform receives

The `--platform` flag accepts exactly: `auto`, `claude-code`, `opencode`,
`codex`, `cursor`, `copilot`, `omp`, `devin`, `all`. Auto-detection never
guesses a host: with no detected host the installer refuses before writing
anything.

| Platform | The installer deploys | Verified by | Guide |
|---|---|---|---|
| `claude-code` | Templates, utilities, agents, `/nw-*` commands, skills, hooks | Container end-to-end install tests | [Installation guide](installation-guide/) |
| `opencode` | Skills, agents, `/nw-*` commands, and a plugin in the OpenCode config directory | Container end-to-end install tests | [Installation guide](installation-guide/) |
| `codex` | Skills under `~/.agents/skills/` (outside `~/.codex/`), TOML agents, hook integration | Container end-to-end install tests | [Installing for Codex](installing-codex.md) |
| `omp` | Skills, agents, `/nw-*` commands, and the `nwave-hooks.ts` extension (no hooks) | Installer self-validation | [Installing for OMP](installing-omp.md) |
| `cursor` | A global user hooks file (`~/.cursor/hooks.json`) only | Installer self-validation | [Installing for Cursor](installing-cursor.md) |
| `copilot` | Hook integration only | Installer self-validation | No guide yet |
| `devin` | Public skills under `~/.config/devin/skills/` plus a manifest | Installer self-validation | [Installing for Devin](installing-devin.md) |
| `all` | The union of all seven hosts | Combination of the above | — |

## How deeply each host is verified

Two tiers, deliberately separated:

- **Container end-to-end install tests** exist for Claude Code, Codex and
  OpenCode: a published package is installed into a container per host and
  the installed surface (skills, agents, commands, hook wiring, upgrade
  path) is asserted by a dedicated test module.
- **Installer self-validation** is what the other hosts — Cursor, Copilot,
  OMP, Devin — rely on: the installer's own prerequisite checks, refusals
  and final validation report. No dedicated end-to-end install test covers
  them, so install-time evidence on those hosts is the installer's report
  rather than an independent test run.

`nwave-ai doctor` checks the Claude Code installation. On a host-only
install it can report missing Claude assets without anything being broken;
use that host's installer validation instead.

## What you do and do not get on lighter hosts

- **Cursor, Copilot (hook integration only):** no agents and no native
  skills are installed, so the specialist `/nw-*` role experience does not
  run there and your assistant cannot load the `nw-nwdes` skill. Point it at
  the [Deliver a feature](nwdes/deliver-feature.md) guide with the sentence
  from [For your assistant](README.md#for-your-assistant); the `nwdes` CLI
  from your shell stays as a fallback. The hooks wire the host to nWave,
  they do not give the host nWave's role agents.
- **Devin (skills-only):** the skills install as methodology guidance for
  Devin's sessions. There is no hook API on Devin and no agent surface, so
  nothing enforces or drives delivery automatically.
- **OMP:** close to the full surface — skills, agents, `/nw-*` commands and
  a tool-call guard extension — but no host hooks; OMP's extension events
  differ from Claude Code hooks.
- **Compared with Claude Code**, every other host lacks at least one of:
  the full shared surface (templates, utilities), native hook registration,
  or independently tested installs. Nothing on this page is a quality claim
  about your host — it is a statement of what is deployed and what checks
  it.

## Backup and restore scope

`nwave-ai install --backup-only` snapshots the Claude Code and Codex
installations (Codex snapshots land under `~/.nwave/backups/`).
`--restore` restores the Claude Code snapshot; on a Codex-only install it
currently finds nothing to restore. No backup or restore exists for
OpenCode, Cursor, Copilot, OMP or Devin — before upgrading on those hosts,
note what you installed and where, so you can reinstall deliberately if an
upgrade goes wrong.

## References

- [Installation guide](installation-guide/)
- [Installing for Cursor](installing-cursor.md)
- [Installing for Devin](installing-devin.md)
- [Installing for Codex](installing-codex.md)
- [Installing for OMP](installing-omp.md)
- [Migrating from 3.x](migrating-from-3x.md)
- [Troubleshooting guide](troubleshooting-guide/)
