# Installing nWave for Cursor

Install the package using one package manager, then wire Cursor:

```bash
uv tool install nwave-ai
# Alternative: pipx install nwave-ai
nwave-ai install --platform cursor --dry-run   # preview first
nwave-ai install --platform cursor
```

From a source checkout, use its environment instead:

```bash
uv sync
uv run python -m nwave_ai.cli install --platform cursor
```

Cursor receives hook wiring only — a global user hooks file
(`~/.cursor/hooks.json`) that applies across all Cursor projects on the
machine. No agents or native skills are installed, so nWave's `/nw-*` role
experience does not run inside Cursor and your assistant cannot load the
`nw-nwdes` skill: point it at the [Deliver a feature](nwdes/deliver-feature.md)
guide with the sentence from [For your assistant](README.md#for-your-assistant);
the `nwdes` CLI from your shell stays as a fallback. Read the installer's
final Cursor-specific validation and restart Cursor. `CURSOR_HOME` can
relocate the Cursor configuration root. Do not install Claude assets to
satisfy Claude-specific doctor failures for a Cursor-only installation. A
runtime copy of a skill does not mean Cursor discovers that skill natively;
use the discovery surface the installer reports for your host.

## Activate the project

In the project directory, using the same installed CLI:

```bash
nwave-ai project enable
nwave-ai status
nwdes --help
```

The status view reports configuration, not execution evidence. Delivery uses
nwdes prompts and role payloads; the host runs the slice's declared verification
commands. nwdes does not enforce TDD phases or maintain a workflow cursor.

## Recover or remove

If the host does not discover the installed assets, retain the installer's
validation output, check the configured Cursor root, and reinstall explicitly
with `--platform cursor`. Restart the host after reinstalling. A file's presence
alone does not prove it has been loaded by a live session.

Run `nwave-ai uninstall` before removing the CLI package with the same package
manager that installed it. Inspect its reported paths; do not delete unrelated
Cursor configuration or other tools' hooks.

## References

- [Installation guide](installation-guide/README.md)
- [Vendor support](vendor-support.md)
- [Codex installation](installing-codex.md)
- [Migrating from 3.x](migrating-from-3x.md)
