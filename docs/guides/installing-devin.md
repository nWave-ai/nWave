# Installing nWave for Devin CLI

## Goal

After this guide, nWave skills are installed into Devin CLI's global discovery
root (`~/.config/devin/skills/`) and you can confirm the installation with a
short checklist.

**What Devin gets:** the public nWave methodology skill files in its native
discovery root. Live slash-command discovery inside a Devin session is not
covered by the installer's verification; check it in the host after
restarting. Devin 3000.6.14 has no hook API (confirmed 2026-10-11). The
installed Python package supplies `nwave-ai` and `nwdes`; the host runs
verification commands.

## Prerequisites

- **Python 3.11 or later** — Check with `python3 --version`
- **uv** (recommended) **or pipx** (fallback) — Install with:
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh    # uv (recommended)
  # or, as a fallback:
  python3 -m pip install pipx && pipx ensurepath     # pipx
  ```
- **Devin CLI** — Install from [devin.ai](https://devin.ai/). Verify with
  `which devin` or `ls ~/.config/devin/`.

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

### Step 2: Install into Devin (global)

Preview first, then install:

```bash
nwave-ai install --platform devin --dry-run
nwave-ai install --platform devin
```

The installer copies all public nWave skills into `~/.config/devin/skills/` and
writes a `.nwave-manifest.json` ownership file there so future upgrades and
uninstalls know exactly which directories belong to nWave. The v4 installer
writes no runtime copy; a Devin install touches only the skill directories and
that manifest.

**Auto-detect note:** if Devin CLI is present and auto-detect includes it,
`nwave-ai install` alone may be enough. Prefer `--platform devin` when you want
an explicit Devin-only install.

### Step 3: Check installation

Check the installer's native Devin verification and the manifest-owned skill
directories. It reports the number of skills it verified; the count depends on
the installed release, so do not treat one release's number as a stable
expectation.

The package supplies the `nwdes` command; confirm it — the one `nwdes`
command you run at setup:

```text
nwdes --help
```

Devin receives the skills only, so a fresh session finds nwdes partly on its
own: ask your assistant about the installed `nw-` skills, or point it at
[Deliver a feature](nwdes/deliver-feature.md) with the sentence from
[For your assistant](README.md#for-your-assistant).

On a Devin-only install, `nwave-ai doctor` may verify the native Devin skills
and still exit 1, because its baseline checks expect Claude settings and
framework directories:

```text
5/11 checks passed, 6 failed, 0 could not be verified
```

Do not install Claude assets to satisfy those checks for a Devin-only install.
Native skill verification is not a live discovery test; restart Devin and check
discovery in the host separately.

### Devin global install checklist

After install, confirm the key paths are in place:

```bash
test -d "$HOME/.config/devin/skills"
test -f "$HOME/.config/devin/skills/.nwave-manifest.json"
ls "$HOME/.config/devin/skills/" | grep "^nw-" | wc -l
```

Expected outcome:

- Both `test` commands pass.
- The `ls` output lists the public `nw-*` skills of the installed release.

One-shot copy/paste:

```bash
nwave-ai install --platform devin --yes \
  && test -d "$HOME/.config/devin/skills" \
  && test -f "$HOME/.config/devin/skills/.nwave-manifest.json" \
  && echo "Devin skills installed: $(ls "$HOME/.config/devin/skills/" | grep -c '^nw-') skills"
```

## What Got Installed

| Path | Purpose |
|------|---------|
| `~/.config/devin/skills/nw-*/` | nWave methodology skill directories |
| `~/.config/devin/skills/.nwave-manifest.json` | nWave ownership manifest for Devin |

The installer writes nothing under `~/.nwave/` for a Devin install. That
directory holds your configuration (`config.json`) and installer backups if
they exist; a `runtime/` folder there is a 3.x-era leftover, which a v4
install removes on upgrade.

**Host capabilities (confirmed 2026-10-11, Devin 3000.6.14):**

| Capability | Status |
|-----------|--------|
| Skills (methodology guidance) | Native skill files installed; installer verification passed. Live `/devin:nw-*` discovery is not covered by installer verification; check it in the host. |
| Pre-tool hook | Not available — Devin uses `permissions` (Exec allow-lists) instead |
| CLI execution (`nwave-ai`, `nwdes`) | Console scripts supplied by the installed Python package |

**Running the CLI:** use the console scripts from the environment where you
installed `nwave-ai`. A virtual-environment install places them in that
environment's executable directory. A tool-manager install uses that manager's
command path. If a command is not found, fix that environment's PATH or use its
executable directly; do not add a Claude-local PYTHONPATH or an alias.

`DEVIN_CONFIG_DIR` can relocate Devin's skill configuration root. A previous or
separately selected host can have additional assets; those are not prerequisites
for Devin.

## Upgrading

Re-run `nwave-ai install --platform devin` to pick up the latest skills. The
installer replaces only manifest-owned skill directories; your own
non-`nw-`-prefixed Devin skills are never touched.

## Uninstall

```bash
nwave-ai uninstall
```

For manual removal, open the ownership manifest
`~/.config/devin/skills/.nwave-manifest.json` in an editor. If you set
`DEVIN_CONFIG_DIR`, use that root instead. Inspect its `installed_skills` list.
Remove only the exact skill directories named in that manifest, then remove
the manifest. Preserve every unlisted directory, including user-created names
such as `nw-personal`. Never use a wildcard deletion based on the `nw-` prefix.

To remove the package's console commands, use the package manager that
installed `nwave-ai`, after running the framework uninstaller. The uninstaller
removes the manifest-owned Devin skills; it leaves your configuration and any
backups under `~/.nwave/` (and a 3.x-era `runtime/` leftover, which a v4
install removes on upgrade) — delete those yourself if you want a fully clean
machine.

## Common Issues

### Skills not discovered

**Symptom:** Devin does not list nWave skills in its registry.

**Steps:**

```bash
# Confirm the directory exists and contains skill dirs:
ls ~/.config/devin/skills/ | grep "^nw-" | head -5

# Confirm each skill has a SKILL.md:
ls ~/.config/devin/skills/nw-design/
```

If the files are present but Devin does not surface them, restart Devin CLI so
it rescans its global skills root.

### Wrong skill count after upgrade

Re-run the installer — a stale manifest may be tracking skills that were renamed
or removed in the new release:

```bash
nwave-ai install --platform devin --yes
# Check the installer's native Devin verification and ownership manifest.
```

### CLI path issues

Use the console scripts from the environment where the package was installed,
not a host-local Python module path or alias. Native Devin skill paths use its
configured discovery root, by default `~/.config/devin/skills/`; check
`DEVIN_CONFIG_DIR` if it is set.

## References

- **Delivery migration**: [Migrating from 3.x](./migrating-from-3x.md)
- **Vendor support**: [Vendor support](./vendor-support.md)
- **Cursor twin guide**: [Installing for Cursor](./installing-cursor.md)
- **Codex twin guide**: [Installing for Codex CLI](./installing-codex.md)
- **OMP twin guide**: [Installing for OMP](./installing-omp.md)
