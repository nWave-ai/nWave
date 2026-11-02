# Assigning models to roles

Give one nWave role a different model without changing its competence. The
principle: **the role defines the work; the model is your choice per role.**
nWave never hard-couples a role to a vendor's model line — where the host has
its own model configuration, nWave defers to it.

How you set the model depends on the host. Paths below are the installed
nWave asset directories each host uses.

## Claude Code

Installed role agents live in `~/.claude/agents/nw/` as Markdown files with
YAML frontmatter. Each carries a `model` field:

```yaml
---
name: nw-acceptance-designer
description: Authors the public executable oracle when required.
model: claude-opus-5
---
```

Allowed values include a concrete model (`claude-opus-5`, `sonnet`,
`haiku`) and `inherit`, which follows your session model. To change a role's
model, edit its `model` line.

## OMP (oh-my-pi)

The installer writes role agents to `~/.omp/agent/agents/` and **omits the
model field on purpose**: every nWave model declaration is a Claude alias,
and an alias there would route the role away from your configured OMP model.
Omission means the role inherits your active model. To pin a different model
for one role, use OMP's own agent model configuration; how to do that is
documented by OMP, not by nWave.

## Codex CLI

Role agents are installed as TOML files, and any Claude model selector in a
role is dropped at install time — the installer reports what it dropped, and
Codex answers with the model from its active configuration
(`~/.codex/config.toml`). The TOML agent schema accepts an optional
`model = "..."` field. If you set it on an installed agent, name a model
your Codex configuration recognizes (see Codex's own model documentation);
Claude model names are not valid here:

```toml
model = "<a-model-name-from-your-codex-configuration>"
```

## OpenCode

Installed agent files carry no `model` field — the projection removes it
together with `name` and `skills`. Model selection follows OpenCode's own
configuration; that mechanism is documented by OpenCode, not by nWave.

## Cursor, Copilot, Devin

These hosts install no role agents (Cursor and Copilot are wired through
hooks; Devin through skills only), so per-role model choice does not apply
there. See [Vendor support](vendor-support.md) for what each host
receives.

## Recording a model preference nWave can keep

Besides editing host files, you can record an explicit provider/model pair
in nWave's configuration with the CLI:

```bash
nwave-ai model set --provider {codex,claude} --model MODEL [--role ROLE [--competence COMPETENCE]] [--project]
```

It writes `model_runtime.default`, or `model_runtime.roles.<role>` with
`--role`, into the global file (or the project's `.nwave/config.json` with
`--project`). The supported providers are `codex` and `claude`; whether your
host reads `model_runtime` is that host's own model-configuration support —
the per-host sections above remain the authoritative mechanism per host. See
the [global configuration reference](../reference/global-config.md) for the
keys.

## Keep your edits across upgrades

`nwave-ai install` manages its asset directories and rewrites them on
reinstall. Keep a copy of your model edits outside the managed directories
and re-apply them after upgrading, the same way you would keep any other
local change to installed assets ([Migrate from nWave
3.x](migrating-from-3x.md)).

**Done:** the role you retargeted answers on the model you chose, and other
roles are unchanged.
