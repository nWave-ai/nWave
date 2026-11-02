# What's New in nWave v3.19

> **Historical note.** This page records v3.19.0. Silent auto-adoption of an unmarked repository was retired in August 2026; run `nwave-ai project enable` explicitly. The current delivery route uses nwdes, without a workflow ledger or enforcement gates. See [Activating nWave in a Project](../activating-nwave-per-project.md) for current configuration.

## Per-Project Activation (Opt-In Gate)

v3.19 introduced per-project activation for globally installed assets. Current
activation is explicit; package installation alone does not enable a repository.
The historical policy used two inputs:

- A tracked marker file `.nwave/local-config.json` (`{"enabled_for_repo": true}` or `false`).
- A global default `activation.mode` in `~/.nwave/global-config.json` — `opt-in` (default; unmarked repos are inactive) or `all` (unmarked repos are active).

Three new CLI verbs manage it:

| Command | Use |
|---------|-----|
| `nwave-ai project enable` / `disable` | Turn nWave on or off for the current repo (writes the marker, fixes `.gitignore` so the marker stays tracked) |
| `nwave-ai mode all` / `opt-in` | Set the machine-wide default for unmarked repos |
| `nwave-ai status` | Show the global mode and whether the current repo is active (read-only) |

The marker is **version-controlled on purpose**: activation intent travels with the repo to every clone. A `disable` is **sticky** — auto-marking never overrides a deliberate opt-out. Commands resolve the nearest marker walking up from the current directory, stopping at `$HOME`.

**When to use**: Run `nwave-ai project enable` the first time you want nWave in a repo (or just run any `/nw-` command — see *Upgrading* below). Run `nwave-ai mode all` once if you would rather every repo be active by default.

**When to skip**: Nothing to do for repos you never use nWave in — the gate keeps them silent automatically.

See [Activating nWave in a Project](../activating-nwave-per-project.md) for the full mental model and the [Global Config reference](../../reference/global-config.md) for the `activation.mode` key.

## nwave-ai CLI Reference

The user-facing `nwave-ai` command surface now lives in one reference page.

**At v3.19**: The CLI reference covered `install`, `uninstall`, `doctor`, `status`, `project`, `mode`, `attribution`, `completion`, and `version`, including the then-available `--density-only` flag. That flag is retired; use the current [CLI Reference](../../reference/cli.md) for supported options and output.

**When to use**: Looking up a flag or exit code, or scripting `nwave-ai` in CI.

**When to skip**: Day-to-day work through `/nw-` commands inside Claude Code needs none of it.

See [CLI Reference](../../reference/cli.md).

## Upgrading from v3.18

No breaking changes, and **existing projects keep working with no action**:

- A repo with prior nWave use is **auto-adopted** (marker written `true`) at session start, or on your first `/nw-` command — so workflows you were already running stay active.
- The global default is `opt-in`; run `nwave-ai mode all` to restore "active everywhere" behavior if you prefer it.
- An explicit `nwave-ai project disable` is sticky and survives auto-marking.
- The marker and the `.gitignore` change it makes are committed with your repo; the regenerated `.nwave/.gitignore` does not need to be tracked.

For older releases, see [What's New in v3.14](../whats-new-v314/).
