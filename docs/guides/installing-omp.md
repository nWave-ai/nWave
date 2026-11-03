# Installing nWave for OMP (oh-my-pi)

## Goal

After this guide, nWave agents, skills, `/nw-*` commands and the tool-call
guard extension are installed under `~/.omp/agent/`. Restart OMP and check
discovery in a fresh session.

## Prerequisites

- **Python 3.11 or later** — Check with `python3 --version`
- **uv** (recommended) **or pipx** (fallback) — Package installer. Install with:
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh    # uv (recommended)
  # or, as a fallback:
  python3 -m pip install pipx && pipx ensurepath     # pipx
  ```
- **OMP** — Install oh-my-pi via its official installer. Verify with
  `which omp` or `ls ~/.omp/agent/`.

## Install

### Step 1: Install nWave CLI

```bash
uv tool install nwave-ai     # recommended
# or, as a fallback:
pipx install nwave-ai
```

From a source checkout instead of the published package:

```bash
uv run python -m nwave_ai.cli install
```

### Step 2: Install into OMP (global)

Preview first, then install:

```bash
nwave-ai install --platform omp --dry-run
nwave-ai install --platform omp
```

The installer writes agents, skills, `/nw-*` commands and the
`nwave-hooks.ts` extension to `~/.omp/agent/`. Delivery uses the
package-installed `nwdes` console command, not host-local validation modules.

**Auto-detect note:** if OMP is present and auto-detect includes it,
`nwave-ai install` alone may be enough. Prefer `--platform omp` when you
want an explicit OMP-only install.

**PI_CONFIG_DIR override:** if OMP uses a custom config root (set via
`PI_CONFIG_DIR`), the installer resolves paths through the same env var.
Export it before running the installer:

```bash
PI_CONFIG_DIR=my-omp-profile nwave-ai install --platform omp
```

### Step 3: Check installation and discovery

Read the installer's final validation and check the installed directories:

```bash
test -d "$HOME/.omp/agent/agents"
test -d "$HOME/.omp/agent/skills"
test -f "$HOME/.omp/agent/extensions/nwave-hooks.ts"
nwdes --help
```

Use your configured root when `PI_CONFIG_DIR` is set. Restart OMP so the new
agents, skills and commands load and the extension takes effect, then open
the nwdes skill in a project — or paste the sentence from
[For your assistant](README.md#for-your-assistant) to start a delivery. OMP
installs no host hooks: the extension's
tool-call events differ from Claude Code hooks. Installation and file
presence do not prove delivery correctness: the host must run the slice's
declared verification commands and retain the results.

## Uninstall

```bash
nwave-ai uninstall
```

Use the uninstaller's reported ownership information; preserve user-created
agents, skills and unrelated host configuration.

To remove nWave entirely (CLI + tool wiring):

```bash
nwave-ai uninstall
uv tool uninstall nwave-ai    # or: pipx uninstall nwave-ai
```

## Common Issues

### Skills not visible in OMP

**Symptom:** Installed skills do not appear in OMP skill listings.

**Fix:** Confirm the skills directory:

```bash
ls "$HOME/${PI_CONFIG_DIR:-.omp}/agent/skills/" | grep nw-
```

If skills are missing, re-run:

```bash
nwave-ai install --platform omp --yes
```

## References

- **Delivery migration**: [Migrating from 3.x](./migrating-from-3x.md)
- **Vendor support**: [Vendor support](./vendor-support.md)
- **Cursor twin guide**: [Installing for Cursor](./installing-cursor.md)
- **Codex guide**: [Installing for Codex CLI](./installing-codex.md)
