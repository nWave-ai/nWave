# What's new in v4

nWave 4.0 reworks how delivery runs. This page explains what changed and why
it matters when you use nWave. For the full release notes and upgrade
commands, read the
[4.0.0 release notes](https://github.com/nWave-ai/nWave/releases) on GitHub;
to move an existing 3.x installation, read
[Migrate from nWave 3.x](../migrating-from-3x.md).

## Delivery now runs through nwdes

**nwdes** is a command that builds one canonical **handoff** per feature — a
JSON file at `docs/feature/ID/handoff.json` in your repository that holds the
feature's recorded facts — and renders briefs, role prompts, output schemas
and review packets from it. It replaces the old delivery runtime as the way
work is structured.

The split of work is now explicit:

- The **host** (Claude Code, Codex, OpenCode, OMP, ...) runs the models and
  invokes the roles.
- **nwdes** builds the prompts and packets, and records the typed values that
  roles supply. It makes no model calls and enforces no gates.
- The **root assistant** (the session you are talking to) reads the results
  and decides what happens next.
- **Humans** decide genuine scope and trade-offs.

In practice this makes `nwdes` your assistant's tool: you point your
assistant at the guide and decide scope — see
[For your assistant](../README.md#for-your-assistant).

Work moves through one of three **routes**: **spine waves** (the `/nw-*`
commands with their gates and independent review), **host-led nwdes steps**
(the root drives roles with generated prompts), or **working directly** (no
gate or delivery authority). You choose by what must survive the session and
what a late refusal would cost. See
[Understanding nwdes](../understanding-nwdes/).

## The DES runtime is retired

**DES** is the name of nWave's predecessor delivery runtime (the name itself
is historical; nWave documents no expansion of it). v4 removes its source
tree, `nwave-ai doctor` no longer checks a DES module, and the installer
writes no runtime copy. Two consequences:

- A 3.x delivery in progress is finished on 3.22.2 (the last public 3.x
  release) or restarted with `nwdes feature new` from the original request.
  There is no converter for the old roadmap and execution log.
- Upgrading the package and rerunning `nwave-ai install` for your host
  removes the predecessor's footprint, including any legacy runtime copy a
  3.x install left at `~/.nwave/runtime/`. Hook and plugin wiring (a hooks
  file for Cursor and Copilot, a plugin for OpenCode, an extension for OMP)
  remains part of what the installer deploys on those hosts.

## Other changes that touch daily use

- **Python 3.11 or newer is required.** pip and uv refuse the install on
  Python 3.10, and the `python_version` doctor check fails below 3.11.
- **Commit attribution is on by default.** Commits in nWave-active
  repositories carry a `Co-Authored-By: nWave` trailer when no preference was
  ever declared. An explicit off still wins: `nwave-ai attribution off`.
- **Jev is on by default.** Jev, the remote TypeSafe System One service used
  for bounded semantic judgments, is authorized by default: no declaration
  is needed and no prompt refuses. Refuse it with `--jev unauthorized` on
  a call, or `"jev": "unauthorized"` in `~/.nwave/config.json` (the flag
  wins; nwdes never writes the key). The service works only when the
  `TYPESAFE_API_KEY` environment variable is set — that variable is a
  technical prerequisite, not the authorization. See
  [Understanding Jev](../understanding-jev.md).
- **Cursor and Devin are install platforms.** `nwave-ai install --platform
  cursor` wires Cursor through global user hooks; `--platform devin` installs
  the skills-only Devin integration.

Support depth differs per host: Claude Code, Codex and OpenCode have
container end-to-end install tests; Cursor, Copilot, OMP and Devin rely on
the installer's own validation. The honest matrix, including what each host
does and does not get, is [Vendor support](../vendor-support.md). The
`--backup-only` recovery point snapshots the Claude Code and Codex
installations; `--restore` restores the Claude Code snapshot (on a
Codex-only install it currently finds nothing to restore), and no backup or
restore exists for the other hosts.

## Where to go next

| You want to | Read |
|---|---|
| Deliver real work, step by step | [Deliver a feature](../nwdes/deliver-feature.md) |
| Fix one defect | [Fix a bug](../nwdes/fix-bug.md) |
| Understand the tool and its routes | [Understanding nwdes](../understanding-nwdes/) |
| Understand the artifacts a delivery produces | [Understanding delivery artifacts](../understanding-delivery-artifacts/) |
| Upgrade a 3.x install | [Migrate from nWave 3.x](../migrating-from-3x.md) |
