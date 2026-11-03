# Installing nWave for Codex CLI

Use this guide to install the nWave CLI into Codex. You need Python 3.11 or
later, Codex CLI, and a published `nwave-ai` package or a checked-out source
tree. Restart Codex after installation so it loads the new assets.

## Step 1: Install the CLI package

```bash
uv tool install nwave-ai     # recommended
# or, as a fallback:
pipx install nwave-ai
```

## Step 2: Install into Codex

The installer writes Codex-native assets — TOML agents, the hook wiring at
`~/.codex/hooks.json` and a manifest — plus the shared skills under
`~/.agents/skills/`, which live outside `~/.codex/`. Preview first, then
install:

```bash
nwave-ai install --platform codex --dry-run
nwave-ai install --platform codex
```

`pipx install nwave-ai` is a supported alternative to `uv tool install`.
Read the installer's final validation before opening Codex. A package name or
workflow definition does not identify a particular release; pin a version or
use an exact release receipt when your project requires one.

## Install from this source tree

From the nWave checkout:

```bash
uv sync
uv run python -m nwave_ai.cli install --platform codex
```

This installs from the checked-out revision. Keep the checkout if you plan to
run its CLI again.

### Codex global install checklist

Check the installer's final validation of Codex agents and shared skills, then
restart Codex. From the same environment, check the delivery command — the
one `nwdes` command you run at setup:

```bash
nwdes --help
```

Do not use a promised doctor count or the presence of a hook file as proof of
delivery verification. The host runs each slice's declared commands.

## Enable a project

In the project where you want nWave active:

```bash
nwave-ai project enable
nwave-ai status
```

`status` reports the effective activation, running CLI version, and whether
Codex installation manifests were found. It does not validate every Codex
action. If you installed from source, call the checkout's absolute
`.venv/bin/nwave-ai` path from the project directory instead.

The project command writes `.nwave/config.json` and updates `.gitignore`.
It can also add a managed section to `AGENTS.md` with your consent; `--yes`
accepts that optional guidance step. Commit the project config if teammates
should inherit the activation setting.

## Verify and recover

After restarting Codex, run `$nw-buddy` in the enabled project. If Codex does
not show the installed nWave skills, check the installer's reported Codex
validation and run `nwave-ai status` in that project. Reinstall with the
explicit `--platform codex` flag after correcting the reported cause; the
dry run also surfaces Codex ownership-collision refusals safely before a
real install.

`nwave-ai doctor` checks the Claude Code installation. A Codex-only install
may therefore report missing Claude Code assets; use the Codex installer
validation for that host. `status` is a read-only view, not a hook execution
test.

To remove nWave's installed assets, run `nwave-ai uninstall`. Remove the CLI
package separately with the same application installer you used to add it.
