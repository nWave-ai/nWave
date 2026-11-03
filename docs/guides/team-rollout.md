# Team Rollout Guide

Each developer installs nWave into their own assistant host. The team shares
project activation and accepted delivery artifacts through the project
repository. Agree on a release channel and exact version or source revision
before comparing behavior across machines.

## First developer

Install the selected `nwave-ai` release, then deploy it to your host. For a
published package and Claude Code:

```bash
uv tool install nwave-ai
nwave-ai install --platform claude-code
nwave-ai doctor
```

For Codex, use `nwave-ai install --platform codex` and check the installer's
Codex validation. `doctor` checks Claude Code assets. Restart the selected
host after installation.

In the team project, enable nWave and inspect the effective state:

```bash
cd /path/to/team/project
nwave-ai project enable
nwave-ai status
```

Commit `.nwave/config.json` and the `.gitignore` change if all teammates
should inherit activation. Commit accepted wave artifacts under `docs/feature/`
with the work they describe. Optional personal settings in `~/.nwave/` are
not team artifacts.

## Joining developer

1. Clone or update the team project.
2. Install the agreed nWave version or source revision into your own host.
3. Restart the host.
4. Run `nwave-ai status` inside the project and confirm it reports active.
5. For Claude Code, run `nwave-ai doctor`. For Codex, check the installer's
   Codex validation.
6. Read the committed delivery artifacts, then ask `/nw-buddy` in Claude Code
   or `$nw-buddy` in Codex for the current project state.

If the project has no committed activation setting, each developer can run
`nwave-ai project enable` locally. Decide whether to commit that setting
before sharing it with the team.

## Recover inconsistent machines

Run `nwave-ai status` on each machine in the same project. Compare its running
CLI version, activation source, effective settings, and detected host assets.
A matching package name alone does not prove matching installed assets.
Reinstall the agreed version into the affected host and restart it. Do not
manually edit installed skills: a later install can replace them.

A package update does not convert an in-progress v3 delivery. Finish it on
3.22.2 or restart it with `nwdes feature new` (your assistant runs that
command). See the [migration guide](migrating-from-3x.md).
