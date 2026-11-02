# Activating nWave in a Project

Installation makes nWave available to a coding host, but project activation
is **opt-in by default**. Use this guide after installing the `nwave-ai`
package (see the [installation guide](./installation-guide/README.md)):

```bash
cd /path/to/your/project
nwave-ai project enable
```

The `cd` matters: `project enable`, `project disable`, and `status` operate
on the current project's configuration. Do not run enable in an nWave
checkout unless that is the repository you intend to opt in.

<details>
<summary>Installed from a source checkout instead?</summary>

If the checkout's CLI is not on your `PATH`, activate its environment in
your shell first, then run the same commands from your project directory:

```bash
source /absolute/path/to/nWave/.venv/bin/activate
cd /path/to/your/project
```

</details>

## Enable and verify

```bash
nwave-ai project enable
nwave-ai status
```

The command reports `nWave activation for this project: enabled.`; `status`
should report `This project is active.` and show the activation source without
writing files. The enable command publishes `.nwave/config.json` with
`"enabled": true`. It also repairs the root `.gitignore` and the generated
`.nwave/.gitignore` so this config can be tracked while other generated
`.nwave/` contents remain ignored. It does **not** run `git add` or `git commit`
for you.

An interactive enable offers optional nWave beta-feedback guidance in both
`CLAUDE.md` and `AGENTS.md`. In a non-interactive shell without `--yes`,
activation still succeeds but that guidance is skipped. To add/update the
managed guidance without prompts later, run `nwave-ai project enable --yes`
from the same project. On disable, the CLI removes only its managed sections.
Review any guidance changes before committing them.

For a team-shared opt-in, first verify the configuration is **not ignored**
and inspect the proposed changes:

```bash
git check-ignore .nwave/config.json
git status --short -- .nwave/config.json .gitignore .nwave/.gitignore CLAUDE.md AGENTS.md
```

`git check-ignore` returning **no output** means the config is not ignored;
it does not mean it is already tracked. If a custom or parent ignore rule
still hides it, fix that rule and rerun the check. Stage and commit the
configuration and root ignore rule if you want teammates to inherit this
activation; optionally track the nested `.nwave/.gitignore` too:

```bash
git add .nwave/config.json .gitignore
git commit -m "Enable nWave for this project"
```

After staging or committing, `git ls-files -- .nwave/config.json` prints the
tracked path. If you do **not** want team-wide activation, do not commit
the config. The local activation still works on this machine.

## Start or continue work

Restart Claude Code after installing and invoke
`/nw-buddy What should I do next?` in the active project, or reopen Codex and
invoke `$nw-buddy` with the same question. These are host commands/skills,
not shell commands.

On POSIX, you can instead start an installed host through
`nwave-ai run HOST -- ARGS`, where `HOST` is `claude-code`, `codex`, `opencode`,
or `copilot`. The launcher does not install the host. Native startup remains
available; native hooks provide update guidance only, not automatic checks
or installation.

Project activation does **not** grant update permission. Automatic checking
and installation have separate, default-off consents. Automatic checks require
controlled prelaunch and idle evidence; installation additionally requires
install consent, acknowledgement that older unregistered sessions are closed,
and a commitment to use the controlled launcher for future sessions sharing
the package. Direct starts, disabled hooks, and detached work are outside that
controlled lifetime guarantee. Read the
[update configuration reference](../reference/global-config.md#updates-object-optional-global-only)
before granting either permission.

For this guide's local source/development installation, keep using the source
channel's explicit update procedure in the
[installation guide](./installation-guide/README.md); update consent does not
make that installation eligible for public package-index updates. If a
supported package replacement is interrupted, follow its reported recovery
action: recovery verifies the pinned version before completing host
synchronization and migration. Do not delete recovery evidence or assume a
rollback.

After an applicable completed wave, optional local HTML views are controlled
separately by documentation density; the Markdown remains authoritative. See
[configuring documentation density](./configuring-doc-density.md).

## Disable or change the default

```bash
nwave-ai project disable
nwave-ai status
```

Disable updates the same `.nwave/config.json` to `"enabled": false`, an
explicit opt-out. `status` should say `This project is inactive.` It does
not delete the config or commit the change. If the repo's config is shared,
commit the new value to share the opt-out. To reverse it, run
`nwave-ai project enable` again, check `status`, and commit if appropriate.

The machine-wide default is `opt-in`. `nwave-ai mode all` activates
repositories with **no declared enabled opinion**; `nwave-ai mode opt-in`
restores the safer default. Explicit project `"enabled": false` wins even
in `all` mode. Changing global mode affects this machine, not your team's
clones. Keep `opt-in` if you work across both nWave and non-nWave projects.

## How resolution works

The current reader checks an explicitly declared boolean `"enabled"` in:

1. This repository's `.nwave/config.json`.
2. Your global `~/.nwave/config.json`, when the repository has no opinion.
3. The global `activation.mode` (default `opt-in`) only when neither config
   declares an opinion.

A missing file, keyless document, or wrongly typed `enabled` does not mean
`false`: it declares no opinion. An explicit `false` overrides global `all`;
an explicit `true` overrides global `opt-in`. From a subdirectory inside a
Git repository, the config reader resolves the repository root. `status`
reads and reports the resulting state and its source without writing files.

**Legacy marker:** Earlier instructions referred to
`.nwave/local-config.json` with `"enabled_for_repo"`. That is a legacy
input handled during configuration migration, **not** a runtime activation
tier, what current `project enable|disable` writes, or a second marker to
create or commit for a new project. Keep any existing legacy file untouched
until the writer handles migration; do not copy its old key into a new file
or manually rename files to "fix" activation. If migration detects invalid
or conflicting values, it refuses the write and reports why; resolve the
reported conflict rather than guessing a conversion.

## Recovery

- **`nwave-ai` not found:** Activate the checkout's `.venv` in the current
  shell as shown above, or invoke the checkout's absolute
  `.venv/bin/nwave-ai` path. A local `uv sync` does not add the script to
  your global `PATH`.
- **Enable reports success, but `status` is inactive:** Check you are in the
  intended Git repository, read `.nwave/config.json` for boolean
  `"enabled": true`, and rerun `nwave-ai status` there. If you are in a
  different repo or outside Git, change to the intended repo and enable
  it there. Do not test tracking by looking for the retired marker.
- **Enable refuses to write or verify:** Follow the CLI's error: fix
  permissions on the project's `.nwave/` directory, resolve malformed or
  conflicting config declarations or concurrent edits to
  `.nwave/config.json`, and retry. `status` is read-only and can be used
  again after repair.
- **Status is active but the host command or hook is absent:** Project
  activation does not install host assets. Check the installer's final
  validation, run `nwave-ai doctor` for Claude Code (not as a Codex-only
  verification), reinstall into the selected host if necessary, and restart
  that host. See the [installation guide](./installation-guide/README.md).

## Related Guides and References

- **[nWave Global Config Reference](../reference/global-config.md)** — activation precedence and other settings
- **[Installation Guide](./installation-guide/README.md)** — local-source installation and host setup
