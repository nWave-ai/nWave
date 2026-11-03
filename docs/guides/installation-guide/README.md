# Installation Guide

Install the published **`nwave-ai` package**, then run its installer for
your host. Choose the host explicitly (`claude-code`, `opencode`, `codex`,
`cursor`, `copilot`, `omp`, `devin`), then enable nWave in the project where
you intend to work. Installation writes host-wide files (for example
`~/.claude/` for Claude Code, `~/.codex/` for Codex, `~/.cursor/` for
Cursor); it does **not** opt every project in.

A local-clone route remains available for source development; see
[Install from a source checkout](#install-from-a-source-checkout) below.

## Historical: v2.8.0 command-format change

Starting with v2.8.0, all nWave commands use hyphens instead of colons:

- **Before**: `/nw:deliver`, `/nw:design`, `/nw:discuss`, etc.
- **After**: `/nw-deliver`, `/nw-design`, `/nw-discuss`, etc.

If you upgrade from an earlier version, run the installer again to clean up old `/nw:` commands. No data loss — only the command format changes.

## Install the package

**Requirements:** Python 3.11 or newer, Git, and a supported coding host.
Install the coding host separately:
[Claude Code](https://claude.com/product/claude-code),
[Codex CLI](https://developers.openai.com/codex/cli),
[Cursor](https://cursor.com/), or another supported host. On Windows, use
WSL.

Install the CLI with the package manager you prefer:

```bash
uv tool install nwave-ai     # recommended
# or, as a fallback:
pipx install nwave-ai
```

Then install into your host. Preview first with `--dry-run`:

```bash
nwave-ai install --platform claude-code --dry-run   # preview
nwave-ai install --platform claude-code             # install
# OR, for Codex CLI:
nwave-ai install --platform codex
```

`--platform` accepts exactly `auto`, `claude-code`, `opencode`, `codex`,
`cursor`, `copilot`, `omp`, `devin`, `all`. Omitting `--platform` asks the
installer to auto-detect hosts; if none are detected, it refuses rather than
guessing. For scripted installation, `--yes` does not enable any project.
Installation does not ask for or write a density preference.

Restart the host after installation, then confirm the delivery command — the
one `nwdes` command you run at setup:

```bash
nwdes --help
```

Before an upgrade you can create a recovery point with
`nwave-ai install --backup-only`, which snapshots the Claude Code and Codex
installations. `nwave-ai install --restore` currently restores only the
Claude Code backup (on a Codex-only install it finds nothing to restore);
no backup or restore exists for OpenCode, Cursor, Copilot, OMP or Devin.
See [Migrate from nWave 3.x](../migrating-from-3x.md).

## Install from a source checkout

Use this route only for source development. **Requirements:** Python 3.11+,
Git, and [uv](https://docs.astral.sh/uv/) (recommended), or Python's `venv`
and `pip`.

```bash
git clone https://github.com/nWave-ai/nWave.git nWave
cd nWave
uv sync
```

The explicit `nWave` directory name keeps the paths below consistent.
Alternatively, in the checkout, use a local virtual environment instead of `uv sync`:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
```

Run **one** of these from the checkout, using the host you actually use:

```bash
uv run python -m nwave_ai.cli install --platform claude-code
# OR, for Codex CLI:
uv run python -m nwave_ai.cli install --platform codex
```

If you used `venv`/`pip`, replace `uv run python` with `.venv/bin/python`.
For scripted installation, `--yes` does not enable any project.

For source development, select development mode explicitly:

```bash
uv run python -m nwave_ai.cli install --dev --platform claude-code
```

Use `--platform codex` for Codex, or replace `uv run python` with
`.venv/bin/python` for the `venv`/`pip` route. Keep the checkout and repeat
`--dev` when reinstalling. Do not replace source or development installs with
a public-package upgrade; package replacement is refused for recorded
development mode.

An applied `--dev` installation activates `nwdes` and `nwave-ai` in
`~/.local/bin` for this checkout's installed runtime. Keep `~/.local/bin` on
your `PATH`; no manual relinking is needed. If the commands already run that
runtime, installation reports each as `unchanged` and leaves the launchers alone.
Otherwise, it reports each successfully selected launcher as `activated`.
For clean isolated installs or tests, put the launcher directory for the same
`HOME` used for installation on `PATH`, without borrowing operator launchers.
Commands already active for the selected runtime elsewhere on `PATH` remain
`unchanged`.

Activation and final verification fail loudly if either command cannot run the
checkout's runtime, including an earlier `PATH` entry shadowing it or a runtime
installed editable from another checkout. Follow the reported WHAT/WHY/HOW
remedy and rerun the installation. A regular file at an owned launcher path is
never overwritten: move it aside first. Previewing with `--dry-run` does not
activate launchers. Selection covers only `nwdes` and `nwave-ai`, and a later generation
installation can replace the stable links without changing the dev runtime.

### Verify the installed host

For **Claude Code**:

```bash
nwave-ai doctor
```

Doctor checks the Claude installation, including its hooks and files; if it
reports a failing check, address that check and rerun the install and doctor.
Quit and reopen Claude Code after every install or reinstall so it loads the
new agents, skills, and commands.

For a **Codex-only** install, use the installer's final validation of Codex
agents and shared skills, then reopen Codex. Claude-specific doctor failures
do not diagnose a Codex-only install.

For **Cursor-only**, **Copilot**, **OMP**, and **Devin** installs, use each
installer's final validation and the per-host guides:
[Cursor](../installing-cursor.md), [OMP](../installing-omp.md),
[Devin](../installing-devin.md), and the
[vendor support matrix](../vendor-support.md) for what each host receives.
On hosts other than Claude Code, doctor may report missing Claude assets on a
host-only install; that is not a defect of that install.

## Per-host guides

- **Codex CLI** — agents and skills; the host drives nwdes and runs the
  declared verification commands; installation is not evidence that a
  delivery has passed. Explicit installation:
  `nwave-ai install --platform codex`. Details:
  **[Installing for Codex CLI](../installing-codex.md)**.
- **Cursor** — integration via global user hooks in `~/.cursor/hooks.json`;
  the wiring applies across all Cursor projects on the machine. Explicit
  installation: `nwave-ai install --platform cursor`. Details:
  **[Installing for Cursor](../installing-cursor.md)**.
- **OpenCode** — install OpenCode itself first, then
  `nwave-ai install --platform opencode`. The installer writes OpenCode-native
  skills, agents and commands.
- **OMP, Devin** — see **[Installing for OMP](../installing-omp.md)** and
  **[Installing for Devin CLI](../installing-devin.md)**.

### Activate your project and start

In the project where you want nWave active:

```bash
cd /path/to/your/project
nwave-ai project enable
nwave-ai status
```

`status` should say `This project is active.` The enable command writes
`.nwave/config.json` with `"enabled": true` and repairs `.gitignore` to keep
that config trackable (Git does not commit it automatically). An interactive
enable also offers beta guidance in `CLAUDE.md` and `AGENTS.md`; in a
non-interactive shell it skips that optional guidance. Run
`nwave-ai project enable --yes` if you want to add it without prompts. Commit
the configuration and ignore-rule changes **if your team should inherit
activation**; if you want to undo it instead, run `nwave-ai project disable`
and check `nwave-ai status` again. See the
[per-project activation guide](../activating-nwave-per-project.md) for
precedence and recovery.

`status` is read-only and also reports the running CLI version, settings,
and detected host assets. The default activation mode is opt-in.

Restart the selected host and open it in the enabled project. In Claude Code,
try `/nw-buddy What should I do next?`; in Codex, invoke `$nw-buddy` and ask
the same question. These are host commands/skills, **not** shell commands.
Then describe the user, input, and expected result of your first request.
Existing projects can continue their current work without repeating onboarding.

### If something goes wrong

- **`nwave-ai: command not found`:** the CLI is not on your `PATH`. With a
  package install, check `uv tool list` / `pipx list` and the bin directory
  they report; with a source checkout, call
  `/absolute/path/to/nWave/.venv/bin/nwave-ai` directly.
- **No coding host detected:** retry with the explicit `--platform` value
  for your host.
- **Doctor fails:** read the failing check; `doctor --fix` is not implemented.
  For Claude, rerun `install --platform claude-code` and `doctor`, then
  restart Claude Code. Other hosts are checked with their installer
  validation, not Claude-only doctor checks.
- **`status` still says inactive:** run `nwave-ai project enable` from the
  intended project directory, inspect `.nwave/config.json` for a boolean
  `"enabled": true`, and rerun `status`. If enable reports a publication or
  verification error, repair the `.nwave/` directory or resolve concurrent
  edits to `.nwave/config.json` and retry. `project disable` writes an explicit
  `false`; it does not remove the file.

## Historical package recovery (not the current installation path)

The following procedure documents an older experimental package identity. It
requires a **verified corrected release receipt**. Do not use its
remote-source, package-manager, or migration commands to install nWave; use
the package installation above. It is retained only for owners of that exact
predecessor with an independently verified release receipt.

## Recover a previous experimental package identity (archive)

The prior experimental package was published as `nwave`
`4.0.0+atddpure.2d5a26a`, while its module and command were named `nwave_ai`
and `nwave-ai`. A corrected release uses the canonical distribution
`nwave-ai`. This procedure is for that specific predecessor only.

Wait for the corrected release receipt. Set `CORRECTED_REF` to the exact commit
recorded there; do not substitute an unverified branch or commit.

```bash
CORRECTED_REF='<exact corrected commit from the release receipt>'
EXPECTED_VERSION='<exact corrected version from the release receipt>'
CORRECTED_SOURCE="git+https://github.com/nWave-ai/nWave-experimental.git@${CORRECTED_REF}"
ROOT='/absolute/path/to/the/project-to-migrate'
```

Before changing packages, select exactly one owner. Inspect `uv tool list
--show-paths`, `pipx list --json`, and the affected virtual environment when it
is known. Use the uv branch only when uv reports the affected app; use the pipx
branch only when pipx reports it; use the same-venv branch only when the probe
is run with that exact affected interpreter. If more than one record can own the
installation, or none can, stop without changing packages.

For the selected uv or pipx predecessor, set `PREDECESSOR_TOOL` to the exact
tool-environment key that its manager record reports: `nwave-ai` for canonical
v3 or `nwave` for the verified obsolete predecessor. Bind only its interpreter
before the initial probe:

```bash
# uv
PREDECESSOR_TOOL='<exact key from uv tool list --show-paths>'
UV_TOOL_ROOT="$(uv tool dir)"
PREDECESSOR_PYTHON="$UV_TOOL_ROOT/$PREDECESSOR_TOOL/bin/python"
test -x "$PREDECESSOR_PYTHON" || exit 1
```

```bash
# pipx
PREDECESSOR_TOOL='<exact key from pipx list --json>'
PIPX_VENVS="$(pipx environment --value PIPX_LOCAL_VENVS)"
PREDECESSOR_PYTHON="$PIPX_VENVS/$PREDECESSOR_TOOL/bin/python"
test -x "$PREDECESSOR_PYTHON" || exit 1
```

Run the initial probe with `PREDECESSOR_PYTHON`. It must report that exact
predecessor identity before an obsolete owner can be removed.

After the corrected install, bind the canonical manager launch paths. For uv:

```bash
UV_TOOL_ROOT="$(uv tool dir)"
UV_BIN_DIR="$(uv tool dir --bin)"
MANAGER_PYTHON="$UV_TOOL_ROOT/nwave-ai/bin/python"
MANAGER_NWAVE_AI_CONSOLE="$UV_BIN_DIR/nwave-ai"
MANAGER_NWDES_CONSOLE="$UV_BIN_DIR/nwdes"
test -x "$MANAGER_PYTHON" -a -x "$MANAGER_NWAVE_AI_CONSOLE" -a -x "$MANAGER_NWDES_CONSOLE" || exit 1
```

For pipx, bind all canonical paths from its post-install records:

```bash
PIPX_RECORD="$(mktemp)"
pipx list --json > "$PIPX_RECORD"
PIPX_VENVS="$(pipx environment --value PIPX_LOCAL_VENVS)"
MANAGER_PYTHON="$PIPX_VENVS/nwave-ai/bin/python"
manager_app() {
  python3 -c 'import json,sys; v=json.load(open(sys.argv[1]))["venvs"]["nwave-ai"]["metadata"]["main_package"]["app_paths"]; out=[]; walk=lambda x: out.extend([x]) if isinstance(x,str) else [walk(y) for y in (x.values() if isinstance(x,dict) else x if isinstance(x,list) else [])]; walk(v); print(next(p for p in out if p.rsplit("/",1)[-1] == sys.argv[2]))' "$PIPX_RECORD" "$1"
}
MANAGER_NWAVE_AI_CONSOLE="$(manager_app nwave-ai)"
MANAGER_NWDES_CONSOLE="$(manager_app nwdes)"
test -x "$MANAGER_PYTHON" -a -x "$MANAGER_NWAVE_AI_CONSOLE" -a -x "$MANAGER_NWDES_CONSOLE" || exit 1
```

If any binding is absent, stop.
The manager-bin application paths are launch paths; the sibling paths reported
by the probe are identity evidence in the manager environment and need not be
the same filesystem paths.

Define this probe once. Its argument is the interpreter whose package and
console ownership it observes:

```bash
probe() {
"$1" -I - <<'PY'
import importlib.metadata as m, importlib.util, json, os, pathlib, sys
bin_dir = pathlib.Path(sys.executable).parent
apps = {name: bin_dir / (name + '.exe' if os.name == 'nt' else name) for name in ('nwave-ai', 'nwdes')}
distributions = {d.metadata['Name'].lower(): d.version for d in m.distributions()
                 if d.metadata.get('Name', '').lower() in {'nwave', 'nwave-ai'}}
owners = sorted(m.packages_distributions().get('nwave_ai', []))
entry_points = {name: sorted(d.metadata['Name'] for d in m.distributions() for e in d.entry_points
                             if e.group == 'console_scripts' and e.name == name)
                for name in apps}
spec = importlib.util.find_spec('nwave_ai')
print(json.dumps({'python': sys.executable, 'distributions': distributions,
                  'module_owners': owners, 'entry_point_owners': entry_points,
                  'applications': {name: {'path': str(path), 'executable': path.is_file() and os.access(path, os.X_OK)} for name, path in apps.items()},
                  'module_path': None if spec is None else spec.origin}, sort_keys=True))
PY
}
probe "$PREDECESSOR_PYTHON"
```

Continue only when the probe shows one canonical `nwave-ai` owner, the verified
obsolete `nwave` `4.0.0+atddpure.2d5a26a` owner, or the explicit same-venv pair
of those two owners. If it shows an unknown `nwave`, a third owner, or paths
outside the selected manager environment, stop without changing packages.

### uv or pipx: previous experimental `nwave` only

Remove the obsolete distribution before installing the canonical replacement:
it shares files with the corrected package. Run the block for the one manager
selected above.

```bash
# uv
uv tool uninstall nwave
uv tool install "${CORRECTED_SOURCE}"
```

```bash
# pipx
pipx uninstall nwave
pipx install "${CORRECTED_SOURCE}"
```

After the manager reports the new `nwave-ai` environment, resolve
`MANAGER_PYTHON`, `MANAGER_NWAVE_AI_CONSOLE`, and `MANAGER_NWDES_CONSOLE` again
from the selected manager record, then run `probe "$MANAGER_PYTHON"`. It must
show only `nwave-ai` as the module and both console-entry-point owner; both
manager launch paths and both probe sibling paths must be executable. Then
finish the deployed runtime and project migration:

```bash
probe "$MANAGER_PYTHON"
test "$("$MANAGER_PYTHON" -I -c 'import importlib.metadata as m; print(m.version("nwave-ai"))')" = "$EXPECTED_VERSION" || exit 1
test "$("$MANAGER_NWAVE_AI_CONSOLE" --version)" = "nwave-ai $EXPECTED_VERSION" || exit 1
"$MANAGER_NWAVE_AI_CONSOLE" --version
"$MANAGER_NWAVE_AI_CONSOLE" install --yes
"$MANAGER_NWAVE_AI_CONSOLE" doctor --json
```

### Same virtual environment containing both `nwave-ai` and obsolete `nwave`

Assign the exact interpreter from the initial mixed-state probe, then remove `nwave` first and
force-reinstall canonical `nwave-ai` so shared files are restored:

```bash
AFFECTED_PYTHON='<exact python field from the mixed-state probe>'
test -x "$AFFECTED_PYTHON" || exit 1
"$AFFECTED_PYTHON" -m pip uninstall -y nwave
"$AFFECTED_PYTHON" -m pip install --upgrade --force-reinstall "nwave-ai @ ${CORRECTED_SOURCE}"
```

Run `probe "$AFFECTED_PYTHON"`, then bind its exact sibling paths:

```bash
probe "$AFFECTED_PYTHON"
MANAGER_PYTHON="$AFFECTED_PYTHON"
MANAGER_NWAVE_AI_CONSOLE="$(dirname "$AFFECTED_PYTHON")/nwave-ai"
MANAGER_NWDES_CONSOLE="$(dirname "$AFFECTED_PYTHON")/nwdes"
test -x "$MANAGER_NWAVE_AI_CONSOLE" -a -x "$MANAGER_NWDES_CONSOLE" || exit 1
test "$("$MANAGER_PYTHON" -I -c 'import importlib.metadata as m; print(m.version("nwave-ai"))')" = "$EXPECTED_VERSION" || exit 1
test "$("$MANAGER_NWAVE_AI_CONSOLE" --version)" = "nwave-ai $EXPECTED_VERSION" || exit 1
```

Run the same `install` and `doctor` commands above only after the
probe shows exactly one `nwave-ai` owner.

### Canonical `nwave-ai` only

For a canonical installation, reinstall through the manager that owns it, then
repeat the post-install probe and the absolute executable commands above:
run one manager block only.

```bash
# uv
uv tool install --reinstall "${CORRECTED_SOURCE}"
```

```bash
# pipx
pipx install --force "${CORRECTED_SOURCE}"
```

The recovery order is package replacement, identity proof, runtime install,
then doctor. It preserves the existing refusal for ambiguous metadata; it does
not select a preferred owner automatically. Follow the migration guide for the
separate project compatibility decision.

### Historical PATH recovery (package-managed installations only)

For a verified older `uv tool` or `pipx` installation, `uv tool update-shell`
or `pipx ensurepath` can refresh the manager's bin directory. This does not
install from a source checkout; for a local checkout, activate its `.venv`
instead.

## CLI install options

Run `nwave-ai install --help` to see the installed script's options (from a
source checkout: `uv run python -m nwave_ai.cli install --help`).
`--platform` selects a host; `--dry-run` previews without installing;
`--backup-only` snapshots the Claude Code and Codex installations;
`--restore` restores the prior Claude Code backup (a Codex-only `--restore`
currently finds nothing to restore).

## Historical plugin marketplace route (unavailable)

Earlier documentation described a Claude Code marketplace plugin with a
different `/nw:` command namespace. That route is not the current
installation. Use the CLI steps above rather than attempting a plugin
marketplace install.

## What Gets Installed

The Claude target installs agents, commands, skills and templates under
`~/.claude/` (or the selected Claude config directory). Those assets become
visible after a restart. Other targets install their native host assets; see
the [vendor support matrix](../vendor-support.md) for the per-host list.

Delivery uses nwdes. The host invokes role prompts, and runs the declared
verification commands. The builder does not enforce a workflow or maintain a
completion ledger.

## Configuration

### Commit attribution

Use `nwave-ai attribution status` to inspect the effective preference and
its source; `nwave-ai attribution on` or `off` changes the machine preference.
Project configuration can override it. Credit is added only for active
repositories with a supported commit hook; nWave's preference does not
control the host's own co-authorship settings.

### Per-project settings

Set the supported project overrides with the CLI:

```bash
nwave-ai project set verbosity terse
nwave-ai project set attribution off
nwave-ai project set enabled true
nwave-ai status
```

`verbosity` accepts `terse`, `standard`, or `verbose`; `attribution` accepts
`on` or `off`; `enabled` accepts `true` or `false`. These commands write
`.nwave/config.json`, as do `project enable` and `project disable`. The
legacy `.nwave/local-config.json` is not what current `project enable` writes.
See the [activation guide](../activating-nwave-per-project.md)
for precedence, team sharing, and recovery, and the
[global configuration reference](../../reference/global-config.md) for other settings.

### Completed-wave reading and explanation

nwdes renders full briefs and HTML through `nwdes document`. A reading view is
not evidence that a wave completed or that a document was approved.

`documentation.expansion_prompt` separately controls optional explanation in
chat after a completed wave. Neither preference changes required verification
or chooses a provider/model. See the
[documentation configuration reference](../../reference/global-config.md#documentation-object)
for the supported values, preference provenance, and rendering limits.

## Updating

### Update a package installation

Upgrade the package with the manager that owns it, then rerun the installer
for the **same selected host**:

```bash
uv tool upgrade nwave-ai        # or: pipx upgrade nwave-ai
nwave-ai install --platform claude-code
nwave-ai doctor
```

For Codex, use `install --platform codex` instead; its final validation is
the Codex-specific check, whereas doctor checks Claude. Restart the host
after installation.

A package update does not migrate an in-progress v3 delivery. Finish it on
3.22.2 or restart with `nwdes feature new`; see the
[migration guide](../migrating-from-3x.md).

For a supported stable installation with recorded host destinations and a
verified package owner:

```bash
nwave-ai update --check
nwave-ai update --yes --root "$PWD"
```

Close active work before the explicit update: it takes the replacement lock
but does not establish global idle. It preserves recorded host destinations
and does not repeat project-guidance enrollment. Missing install provenance,
development mode, or an unsupported release channel can refuse replacement;
consent does not make those installations compatible.

### Update a source checkout

When you intentionally update your clone, resync its environment and rerun the
installer for the **same selected host**. For example, after updating the
checkout's source to the revision you want:

```bash
uv sync
uv run python -m nwave_ai.cli install --platform claude-code
uv run python -m nwave_ai.cli doctor
```

For Codex, use `install --platform codex` instead; its final validation is
the Codex-specific check, whereas doctor checks Claude. With the `venv`/`pip`
route, rerun `.venv/bin/python -m pip install -e .` in the checkout before
`.venv/bin/python -m nwave_ai.cli install --platform ...`. Restart the host
after installation.

## Controlled startup and update permissions

On POSIX, `nwave-ai run HOST -- ARGS` supports `claude-code`, `codex`,
`opencode`, and `copilot`; it does not install a missing host. For example:

```bash
nwave-ai run claude-code --
nwave-ai run codex -- --no-daemon
```

Automatic release checking and installation are separate permissions, both
**off by default**. A check-only grant cannot install anything. For a
compatible stable installation, grant checking explicitly:

```bash
nwave-ai update consent check on
```

Before granting automatic installation, close all older host sessions that
started before the activity registry was installed. Then, only if future
sessions sharing the package will use controlled startup, record both
acknowledgements:

```bash
nwave-ai update consent install on --confirm-old-sessions-closed
nwave-ai update consent controlled-launch on --confirm-controlled-launch
```

These flags record your statements; nWave cannot independently detect the
older sessions. Automatic installation requires both check and install
permissions plus the controlled-launch commitment. Revoke a grant with the
same command and `off`, without a confirmation flag.

The wrapper records the session before launching the host. Automatic checks
and installation require controlled prelaunch and idle evidence before the
first release request. Other sessions, unknown or malformed records, and
unfinished local work block both automatic actions. Ordinary native startup
remains available, but its update hooks are **advisory only**: native hooks
cannot provide a reliable admission boundary. Direct starts, disabled hooks,
and detached work are outside the controlled lifetime guarantee.

Inspect records with `nwave-ai update sessions`. Close a session in its host
first; remove a remaining record only with
`nwave-ai update sessions close KEY --confirm-closed`. Records are not cleared
by guessing from process state or age. An explicit `nwave-ai update --check`
remains read-only and available outside controlled startup. A manual
`update --yes` does not grant persistent consent.

These controls do not convert source/development installs into public-index
installations. Read the
[update configuration reference](../../reference/global-config.md#updates-object-optional-global-only)
before enabling either automatic action.

### Interrupted-update recovery

An interrupted replacement reports its stage and recovery action and retains
durable evidence. Even if the package version is current, checks and ordinary
updates report `update-incomplete`, not success. No broad rollback is promised.
After stopping all remaining updater processes and affected sessions, use the
reported environment and project root to run:

```bash
nwave-ai update --recover --yes --confirm-stopped
```

Recovery proves the **pinned package version**, repeats selected-host preflight
and synchronization, and applies the registered artifact migration. Evidence is
cleared only when all stages succeed. If the pinned package is missing or
wrong, follow the reported package-owner restoration command first. Do not
delete recovery markers or substitute an unpinned public upgrade.

## Uninstalling

Run `nwave-ai uninstall`; with a source checkout, activate its `.venv` first.
It removes nWave-managed installed assets; it does not erase your project's
`.nwave/config.json` or source files. If you only want to turn nWave off in
one project, use `nwave-ai project disable` there instead.

For a package installation, remove deployed assets with
`nwave-ai uninstall`, then remove its CLI with
`uv tool uninstall nwave-ai` or `pipx uninstall nwave-ai`, matching its owner.
This also leaves the project's `.nwave/` files in place.

## Verification and troubleshooting

For Claude, run `nwave-ai doctor` after installation. Then restart Claude
Code and look for `/nw-buddy` among commands. If it is absent, verify you
installed with `--platform claude-code` and address any failing doctor
checks; reinstall with that target if needed. `nwave-ai version` only proves
the CLI can run, not that host assets or a project activation were installed.

For Codex, rely on the Codex-target installer's final validation and check
the Codex-native assets as described above; doctor does not yet diagnose
Codex-only assets. Reopen Codex to load the installed skills. If the
installer refuses an ownership conflict, follow its reported remedy rather
than overwriting unowned files.

For either host, `nwave-ai status` from the intended project must say
`This project is active.` If not, run `nwave-ai project enable` there and
follow the [activation recovery guide](../activating-nwave-per-project.md#recovery).
If the installation fails because a destination is not writable, resolve
its ownership or permissions and retry; do not indiscriminately `chmod`
your entire Claude configuration. `doctor --fix` is not implemented.

## Next Steps

Enable nWave in your own project, verify with `nwave-ai status`, reopen
your selected host, and ask its buddy command/skill for the first action:
Claude Code `/nw-buddy What should I do next?`, or Codex `$nw-buddy` with
the same question. For workflow guidance, see
[Jobs To Be Done Guide](../jobs-to-be-done-guide/).

## Support

- **Discord Community**: [Join the nWave Discord](https://discord.gg/Cywj3uFdpd) for help with installation issues
- **Documentation**: Guides and references are in this repository.
- **Claude installer logs**: Check `~/.claude/nwave-install.log` for errors.
- **CLI**: Run `nwave-ai version`.

---

**Ready to build?** The `nwdes` steps are your assistant's to run: paste it
the sentence from [For your assistant](../README.md#for-your-assistant). To
see the command flow once by hand, walk the safe
[First feature with nwdes](../tutorial-nwdes-first-feature/) lesson in a
throwaway repository, then start real work with
[Deliver a feature](../nwdes/deliver-feature.md).
