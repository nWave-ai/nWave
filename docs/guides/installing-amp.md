# Installing nWave for Amp

## Goal

After this guide, nWave's public skills are installed where Amp reads user
skills (`~/.config/amp/skills/`), the nWave guard runs before Amp's shell and file
tool calls, and you can confirm both with a short checklist.

**What Amp gets:** the public nWave skill files and a guard plugin. Amp has no
file-based role agents and no custom slash commands, so a role is reached by
asking for its skill by name (for example "load nw-buddy"). The installed Python
package supplies `nwave-ai` and `nwdes`.

## Prerequisites

- **Python 3.11 or later**, and **uv** or **pipx**, as in the
  [Installation guide](installation-guide/).
- **Amp** — the CLI (`which amp`) or an Amp client using this machine's
  `~/.config/amp/`. The guard plugin runs with Bun, which Amp provides.

## Install

```bash
uv tool install nwave-ai
nwave-ai install --platform amp --dry-run
nwave-ai install --platform amp
```

The installer writes:

| Path | Purpose |
|------|---------|
| `~/.config/amp/skills/nw-*/` | nWave skill directories |
| `~/.config/amp/skills/.nwave-manifest.json` | Ownership manifest for those skills |
| `~/.config/amp/plugins/nwave-hooks.ts` | Guard plugin (`$XDG_CONFIG_HOME/amp/plugins/` when `XDG_CONFIG_HOME` is set) |
| `~/.config/amp/plugins/.nwave-des-manifest.json` | sha256 of the guard plugin nWave wrote |

The guard plugin answers Amp's `tool.call` event. For a shell call it sends the
command as `Bash`, and for an edit, create or patch call each modified file as
`Write` or `Edit`, to
`python -m nwave_ai.hooks PreToolUse --host amp`. A refusal comes back to the
agent as `reject-and-continue` with the guard's reason. If the guard cannot run
(for example the Python runtime moved), checked calls are refused with a message
telling you to rerun the installer.

The call that starts a subagent (`Task`) is not checked: Amp does not send it
to plugins' `tool.call` handlers. On other hosts nWave only logs that call and
never blocks it, so what Amp loses is that log entry. The subagent's own shell
and file calls are checked like any others.

**Skill precedence:** Amp uses the first skill it finds for a name, and
`~/.agents/skills/` (where the Codex install writes) comes before
`~/.config/amp/skills/`. With Codex also installed, Amp loads Codex's copy of
each skill; the bodies differ only in their host paths.

## Check installation

```bash
amp skill list | grep -c 'nw-'
amp plugins list | grep nwave-hooks
```

Expected: the count of the installed release's public skills, and
`nwave-hooks.ts active` with `events: tool.call`. In a running Amp session, run
`plugins: reload` from the command palette, or start a new thread, to pick up
the guard.

## Upgrading

Re-run `nwave-ai install --platform amp`. Only manifest-owned skill folders and
the guard plugin while it still matches its manifest are replaced; your own
skills and plugins are never touched.

## Uninstall

```bash
nwave-ai uninstall
```

It removes the skill folders the manifest lists and the guard plugin when it
still matches its recorded digest, and leaves every other skill and plugin.

## References

- [Vendor support](./vendor-support.md)
- [Installing for Devin](./installing-devin.md)
- Amp: [Skills](https://ampcode.com/docs/customize/skills), [Plugins](https://ampcode.com/docs/customize/plugins)
