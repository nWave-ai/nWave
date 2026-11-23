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
`codex`, `cursor`, `copilot`, `omp`, `devin`, `pi`, `amp`, `all`. Auto-detection never
guesses a host: with no detected host the installer refuses before writing
anything.

| Platform | The installer deploys | Verified by | Guide |
|---|---|---|---|
| `claude-code` | Templates, utilities, agents, `/nw-*` commands, skills, and `settings.json` (hook registrations) | Container end-to-end install tests | [Installation guide](installation-guide/) |
| `opencode` | Skills, agents and `/nw-*` commands in the OpenCode config directory | Container end-to-end install tests | [Installation guide](installation-guide/) |
| `codex` | Skills under `~/.agents/skills/` (outside `~/.codex/`), TOML agents, hook integration | Container end-to-end install tests | [Installing for Codex](installing-codex.md) |
| `omp` | Skills, agents, `/nw-*` commands, and the `nwave-hooks.ts` extension, which carries OMP's hooks | Installer self-validation | [Installing for OMP](installing-omp.md) |
| `cursor` | A global user hooks file (`~/.cursor/hooks.json`) only | Installer self-validation | [Installing for Cursor](installing-cursor.md) |
| `copilot` | Hooks, public roles as custom agents (`~/.copilot/agents/`), public skills (`~/.copilot/skills/`); project-level agents, skills and prompt files (`.github/`) only when the user runs `nwave-ai project copilot enable --yes` | Installer self-validation, plus observations on the real CLI (below). VS Code chat: documented, not observed in VS Code | [Installing for Copilot](installing-copilot.md) |
| `devin` | Public skills under `~/.config/devin/skills/` plus a manifest | Installer self-validation | [Installing for Devin](installing-devin.md) |
| `amp` | Public skills under `~/.config/amp/skills/` plus a manifest, and the `nwave-hooks.ts` guard plugin in Amp's plugins directory | Installer self-validation | [Installing for Amp](installing-amp.md) |
| `all` | The union of all hosts | Combination of the above | — |

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
- **Copilot in VS Code chat: documented, not observed in VS Code.** The VS Code chat surface (the Copilot harness) reads
  the same personal folders as the CLI, per the vendor pages; no VS Code chat session has been run. The observation
  runbook is `docs/feature/copilot-chat-in-vscode/runbook.md`, and it is unobserved until a person records its results.
  The observations below are the terminal Copilot CLI only.
- **Copilot** has observations beyond the installer's report, all on the real
  Copilot CLI 1.0.103 with an isolated `COPILOT_HOME` and a scratch `HOME`.
  Each result names its receipt. The records behind those receipts are not published, so this guide states each
  observation with its limits and links to none of them. The guide [Installing for Copilot](installing-copilot.md)
  explains them:
  - Roles: the same command, `--agent nw-nwave-buddy --model auto` with the
    three-check prompt, answered as the role in 3 of 4 runs (receipts role-1 to
    role-4). The role's text reached the request in all four. Earlier runs of
    that command adopted the role once in two (t-0467). Not a rate.
  - Waves: the skill tool loaded `nw-discuss` in a real session (receipt
    wave-r5). Every public wave has a public skill.
  - Project instructions: the CLI lists `CLAUDE.md`, `AGENTS.md` and
    `.github/copilot-instructions.md`; the model quoted a line of the nWave
    section (receipt instr-r6).
  - Hooks: one event, `preToolUse`. Before the Copilot adapter a `git stash` ran
    (receipt hook-r7); with it the stash was refused (receipt hookfix), and the
    model then used the bypass the refusal names. An ordinary bash call is
    allowed (repository test, not a session).
  - Project level: a fresh home with only the project's `.github` files loaded
    the project skill and answered as the project role (receipt proj-r8).
  - Prompt files (`.github/prompts`): not loaded as prompts in the observed runs
    (receipts prompt-r9 and prompt-slash).
  - Only the CLI was observed. VS Code and Visual Studio were not tested, and
    nothing here says they load these files.

`nwave-ai doctor` checks the Claude Code installation. On a host-only
install it can report missing Claude assets without anything being broken;
use that host's installer validation instead.

## What you do and do not get on lighter hosts

- **Cursor (hook integration only):** no agents and no native skills are
  installed, so the specialist `/nw-*` role experience does not run there and
  your assistant cannot load the `nw-nwdes` skill. Point it at the
  [Deliver a feature](nwdes/deliver-feature.md) guide with the sentence from
  [For your assistant](README.md#for-your-assistant); the `nwdes` CLI from your
  shell stays as a fallback. The hooks wire the host to nWave, they do not give
  the host nWave's role agents.
- **Copilot:** the installer writes the public roles as custom agents and the
  public skills as skills (see above). Copilot has no custom slash commands, so
  a role is reached with `copilot --agent <name>` (or `/agent` interactively);
  in prompt mode that route answered as the role in 3 of 4 receipted runs, so it is
  not reliable (see above). The `nwdes` CLI from your shell is the dependable path.
- **Devin (skills-only):** the skills install as methodology guidance for
  Devin's sessions. There is no hook API on Devin and no agent surface, so
  nothing enforces or drives delivery automatically.
- **Amp:** skills and a tool-call guard plugin (Amp's `tool.call` event).
  Amp has no file-based role agents or custom slash commands, so a role is
  reached by asking for its `nw-*` skill by name.
- **OMP:** close to the full surface — skills, agents, `/nw-*` commands and
  a tool-call guard extension, which carries OMP's hooks; OMP's extension events
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
- [Installing for Amp](installing-amp.md)
- [Migrating from 3.x](migrating-from-3x.md)
- [Troubleshooting guide](troubleshooting-guide/)
