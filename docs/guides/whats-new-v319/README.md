# What's New in nWave v3.19

## Per-Project Activation (Opt-In Gate)

nWave's DES hooks install **globally** into `~/.claude/settings.json`, so before v3.19 they fired in every repository you opened — including ones that had never used nWave. v3.19 makes them **opt-in per project**: in a repo that has not activated nWave, every gated hook silently exits 0 (allow). You cannot tell nWave is installed.

**What it does**: A pure, deterministic policy decides per repo whether DES hooks run, from two inputs:

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

**What it does**: A single lookup for `install`, `uninstall`, `doctor`, `status`, `project`, `mode`, `attribution`, `completion`, and `version` — every flag, exit code, and output string. It also documents that `nwave-ai install` consumes `--platform` / `--target` / `--yes` / `--density-only` itself and **forwards the rest** (`--dry-run`, `--backup-only`, `--restore`) to the underlying installer.

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
